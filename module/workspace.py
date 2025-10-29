import os
import sqlite3
from enum import Enum
from pathlib import Path
from datetime import datetime, date, time

import yaml
import json
from pandas import read_sql_query
from typing import Union, Optional, List, Dict, Iterator, Callable, Tuple
from dataclasses import asdict, is_dataclass
try:
    from module.models import (
        Workspace, EphemerisSource, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType
    )
except ImportError:
    from models import (
        Workspace, EphemerisSource, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType
    )

# ─────────────────────
# ⚙️ CONFIGURATION
# ─────────────────────

# Default localization settings
DEFAULT_LANGUAGE = "cs"
FALLBACK_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "cs", "fr"]

TRANSLATION_BACKEND = "yaml"
# Path to translation files (for YAML)
TRANSLATION_DIR = Path(__file__).parent / "locales"
# SQLite settings (optional)
TRANSLATION_DB = Path(__file__).parent / "settings.db"

# Default location
DEFAULT_LOCATION = {
    "name": "Prague",
    "latitude": 50.0875,
    "longitude": 14.4214,
    "timezone": "Europe/Prague"
}

# ──────────────────────────────
# PUBLIC API
# ──────────────────────────────

def load_workspace(workspace_path: str) -> Workspace:
    """
    Loads a modular workspace from a manifest YAML file.
    It resolves referenced file paths (relative to workspace.yaml).
    """
    if not Path(workspace_path).exists:
        raise FileNotFoundError(f"Workspace file not found: {workspace_path}")

    base_dir = os.path.dirname(workspace_path)

    with open(workspace_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    return _load_workspace_from_manifest(manifest, base_dir)


def save_workspace_flat(workspace: Workspace, path: str, format: str = "yaml"):
    """
    Save full workspace as a single flat file (for debug/export).
    """
    data = asdict(workspace)

    with open(path, "w", encoding="utf-8") as f:
        if format == "yaml":
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        elif format == "json":
            json.dump(data, f, indent=2)
        else:
            raise ValueError("Unsupported format: choose 'yaml' or 'json'")


# ──────────────────────────────
# MODULAR LOADER
# ──────────────────────────────

def _load_workspace_from_manifest(manifest: dict, base_dir: str) -> Workspace:
    """
    Internal function that resolves all parts of the workspace from file references.
    """

    def load_yaml_file(path: str):
        full_path = os.path.join(base_dir, path)
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_many(paths: list, cls):
        return [cls(**load_yaml_file(p)) for p in paths]

    # Load individual parts
    default_ephemeris = EphemerisSource(**manifest["default_ephemeris"])
    active_model = manifest["active_model"]

    # Presets (ensure nested ChartConfig)
    chart_presets = []
    for p in manifest.get("chart_presets", []):
        data = load_yaml_file(p)
        cfg = data.get("config")
        if isinstance(cfg, dict):
            data["config"] = ChartConfig(**cfg)
        chart_presets.append(ChartPreset(**data))

    subjects = load_many(manifest.get("subjects", []), ChartSubject)

    # Charts (ensure nested ChartSubject and ChartConfig)
    charts = []
    for p in manifest.get("charts", []):
        data = load_yaml_file(p)
        subj = data.get("subject")
        cfg = data.get("config")
        if isinstance(subj, dict):
            data["subject"] = ChartSubject(**subj)
        if isinstance(cfg, dict):
            data["config"] = ChartConfig(**cfg)
        # Ignore computed_chart on load if present (recomputable)
        data.pop("computed_chart", None)
        charts.append(ChartInstance(**data))

    layouts = load_many(manifest.get("layouts", []), ViewLayout)

    annotations = []
    for ann_path in manifest.get("annotations", []):
        full_path = os.path.join(base_dir, ann_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        annotations.append(Annotation(
            title=os.path.splitext(os.path.basename(ann_path))[0],
            content=content,
            created=None,
            author="unknown"
        ))

    # Workspace-level defaults
    preferred_language = manifest.get("preferred_language", DEFAULT_LANGUAGE)
    loc = manifest.get("default_location") or DEFAULT_LOCATION
    default_location = Location(**loc) if isinstance(loc, dict) else None
    default_house_system_val = manifest.get("default_house_system")
    default_house_system = None
    if isinstance(default_house_system_val, str):
        try:
            default_house_system = HouseSystem(default_house_system_val)
        except Exception:
            default_house_system = None
    default_aspects = manifest.get("default_aspects", [])
    color_theme = manifest.get("color_theme", "default")
    default_engine_val = manifest.get("default_engine", "jpl")
    try:
        default_engine = EngineType(default_engine_val)
    except Exception:
        default_engine = None

    return Workspace(
        owner=manifest["owner"],
        default_ephemeris=default_ephemeris,
        active_model=active_model,
        chart_presets=chart_presets,
        subjects=subjects,
        charts=charts,
        layouts=layouts,
        annotations=annotations,
        preferred_language=preferred_language,
        default_location=default_location,
        default_house_system=default_house_system,
        default_aspects=default_aspects,
        color_theme=color_theme,
        default_engine=default_engine
    )


# ─────────────────────
# 🌐 TRANSLATION SERVICE
# ─────────────────────

class TranslationBackend(str, Enum):
    YAML = "yaml"
    SQLITE = "sqlite"


class TranslationService:
    def __init__(self, backend: str = TRANSLATION_BACKEND):
        self.backend = TranslationBackend(backend)
        self.cache: Dict[str, Dict[str, Dict[str, str]]] = {}

    def get(self, domain: str, key: str, lang: Optional[str] = None) -> Optional[str]:
        lang = lang or DEFAULT_LANGUAGE
        data = self._load(domain, lang)
        return data.get(key)

    def inject_i18n(self, items: List, domain: str, lang: Optional[str] = None):
        lang = lang or DEFAULT_LANGUAGE
        translations = self._load(domain, lang)
        for item in items:
            item.i18n = translations.get(item.id, {})

    def _load(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        key = f"{domain}:{lang}"
        if key in self.cache:
            return self.cache[key]

        if self.backend == TranslationBackend.YAML:
            path = TRANSLATION_DIR / lang / f"{domain}.yml"
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                data = {}
        else:
            data = self._load_from_sqlite(domain, lang)

        self.cache[key] = data
        return data

    def _load_from_sqlite(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        data = {}
        try:
            with sqlite3.connect(TRANSLATION_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT key, label, value
                    FROM translations
                    WHERE domain = ? AND language = ?
                """, (domain, lang))
                for key, label, value in cursor.fetchall():
                    if key not in data:
                        data[key] = {}
                    data[key][label] = value
        except sqlite3.Error:
            data = {}
        return data

def change_language(default: str = "cz") -> dict:
    with sqlite3.connect(Path(__file__).parent / "settings.db") as dbcon:
        df = read_sql_query("SELECT * FROM language ORDER BY id;", dbcon)
    return dict(zip(df["col"], df[default]))


# ──────────────────────────────
# WORKSPACE SCAFFOLDING & MODULAR CRUD
# ──────────────────────────────

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    # simple sanitize -> lowercase, keep alnum, dash, underscore
    base = "".join(ch.lower() if ch.isalnum() else ("-" if ch in " -_" else "") for ch in (name or ""))
    return base.strip("-") or "item"


def _dump_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(_to_primitive(data), f, sort_keys=False, allow_unicode=True)


def _to_primitive(obj):
    """Recursively convert dataclasses, Enums, datetimes to YAML-serializable primitives."""
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_primitive(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        t = type(obj)
        return [ _to_primitive(v) for v in obj ]
    return obj


def _serialize(obj):
    return _to_primitive(obj)


def init_workspace(base_dir: Union[str, Path], owner: str, active_model: str, default_ephemeris: Dict[str, str]) -> Path:
    """Scaffold a new workspace directory with a manifest and subfolders.

    Creates:
    - workspace.yaml (manifest)
    - subjects/, charts/, layouts/, annotations/, presets/
    Returns path to the created manifest.
    """
    base = Path(base_dir)
    _ensure_dir(base)
    # subdirs
    subjects_dir = base / "subjects"
    charts_dir = base / "charts"
    layouts_dir = base / "layouts"
    annotations_dir = base / "annotations"
    presets_dir = base / "presets"
    for d in (subjects_dir, charts_dir, layouts_dir, annotations_dir, presets_dir):
        _ensure_dir(d)

    manifest = {
        "owner": owner,
        "default_ephemeris": default_ephemeris,
        "active_model": active_model,
        # workspace-level defaults
        "preferred_language": DEFAULT_LANGUAGE,
        "default_location": DEFAULT_LOCATION,
        "default_house_system": "Placidus",
        "default_aspects": [],
        "color_theme": "default",
        "default_engine": "jpl",
        # modular refs
        "chart_presets": [],
        "subjects": [],
        "charts": [],
        "layouts": [],
        "annotations": [],
    }
    manifest_path = base / "workspace.yaml"
    _dump_yaml(manifest_path, manifest)
    return manifest_path


def save_workspace_modular(workspace: Workspace, base_dir: Union[str, Path]) -> Path:
    """Save Workspace parts to individual YAML files under base_dir and write/overwrite manifest.
    Returns the path to the written manifest.
    """
    base = Path(base_dir)
    subjects_dir = base / "subjects"
    charts_dir = base / "charts"
    layouts_dir = base / "layouts"
    annotations_dir = base / "annotations"
    presets_dir = base / "presets"
    for d in (subjects_dir, charts_dir, layouts_dir, annotations_dir, presets_dir):
        _ensure_dir(d)

    manifest: Dict[str, Union[str, list, dict]] = {
        "owner": getattr(workspace, 'owner', ''),
        "default_ephemeris": _serialize(getattr(workspace, 'default_ephemeris', {})),
        "active_model": getattr(workspace, 'active_model', ''),
        # workspace-level defaults
        "preferred_language": getattr(workspace, 'preferred_language', DEFAULT_LANGUAGE),
        "default_location": _serialize(getattr(workspace, 'default_location', DEFAULT_LOCATION)),
        "default_house_system": str(getattr(workspace, 'default_house_system', 'Placidus')),
        "default_aspects": list(getattr(workspace, 'default_aspects', []) or []),
        "color_theme": getattr(workspace, 'color_theme', 'default'),
        "default_engine": (
            getattr(getattr(workspace, 'default_engine', None), 'value', None)
            or str(getattr(workspace, 'default_engine', 'jpl'))
        ),
        # modular refs to be filled below
        "chart_presets": [],
        "subjects": [],
        "charts": [],
        "layouts": [],
        "annotations": [],
    }

    # Presets
    for preset in (workspace.chart_presets or []):
        fname = f"{_safe_filename(getattr(preset, 'name', 'preset'))}.yml"
        rel = f"presets/{fname}"
        _dump_yaml(base / rel, _serialize(preset))
        manifest["chart_presets"].append(rel)

    # Subjects
    for subj in (workspace.subjects or []):
        fname = f"{_safe_filename(getattr(subj, 'id', getattr(subj, 'name', 'subject')))}.yml"
        rel = f"subjects/{fname}"
        _dump_yaml(base / rel, _serialize(subj))
        manifest["subjects"].append(rel)

    # Charts
    for chart in (workspace.charts or []):
        fname = f"{_safe_filename(getattr(chart, 'id', getattr(chart, 'subject', None) and getattr(chart.subject, 'name', 'chart')))}.yml"
        rel = f"charts/{fname}"
        _dump_yaml(base / rel, _serialize(chart))
        manifest["charts"].append(rel)

    # Layouts
    for layout in (workspace.layouts or []):
        fname = f"{_safe_filename(getattr(layout, 'name', 'layout'))}.yml"
        rel = f"layouts/{fname}"
        _dump_yaml(base / rel, _serialize(layout))
        manifest["layouts"].append(rel)

    # Annotations
    for ann in (workspace.annotations or []):
        fname = f"{_safe_filename(getattr(ann, 'title', 'note'))}.md"
        rel = f"annotations/{fname}"
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        with open(base / rel, "w", encoding="utf-8") as f:
            f.write(getattr(ann, 'content', ''))
        manifest["annotations"].append(rel)

    manifest_path = base / "workspace.yaml"
    _dump_yaml(manifest_path, manifest)
    return manifest_path


# CRUD helpers

def add_subject(ws: Workspace, subject, base_dir: Union[str, Path]) -> str:
    rel = f"subjects/{_safe_filename(getattr(subject, 'id', getattr(subject, 'name', 'subject')))}.yml"
    _dump_yaml(Path(base_dir) / rel, _serialize(subject))
    ws.subjects = (ws.subjects or []) + [subject]
    # caller should re-save manifest via save_workspace_modular
    return rel


def add_chart(ws: Workspace, chart, base_dir: Union[str, Path]) -> str:
    # prefer chart.id, fallback to subject name
    base_name = getattr(chart, 'id', None) or (getattr(chart, 'subject', None) and getattr(chart.subject, 'name', None)) or 'chart'
    # Prevent duplicates in memory collection
    identity = base_name
    for existing in (ws.charts or []):
        ex_id = getattr(existing, 'id', None) or (getattr(existing, 'subject', None) and getattr(existing.subject, 'name', None))
        if ex_id and ex_id == identity:
            # Already present -> no new file, return expected relative path
            return f"charts/{_safe_filename(identity)}.yml"

    # Prepare serializable data, removing computed payload
    data = _serialize(chart)
    if isinstance(data, dict):
        data.pop('computed_chart', None)
        # normalize per-chart config to inherit workspace defaults
        cfg = data.get('config') or {}
        try:
            # engine: drop if same as workspace default
            ws_engine = getattr(ws, 'default_engine', None)
            if ws_engine and cfg.get('engine') in (ws_engine, getattr(ws_engine, 'value', None)):
                cfg.pop('engine', None)
        except Exception:
            pass
        # override_ephemeris: drop unless explicitly needed (prefer workspace default)
        cfg.pop('override_ephemeris', None)
        try:
            # color_theme: drop if same as workspace default
            ws_theme = getattr(ws, 'color_theme', None)
            if ws_theme and cfg.get('color_theme') == ws_theme:
                cfg.pop('color_theme', None)
        except Exception:
            pass
        data['config'] = cfg

    rel = f"charts/{_safe_filename(base_name)}.yml"
    _dump_yaml(Path(base_dir) / rel, data)
    ws.charts = (ws.charts or []) + [chart]
    return rel


def update_chart(ws: Workspace, chart_id: str, updater: Callable) -> bool:
    if not ws.charts:
        return False
    for idx, c in enumerate(ws.charts):
        if getattr(c, 'id', None) == chart_id:
            ws.charts[idx] = updater(c)
            return True
    return False


def remove_chart(ws: Workspace, chart_id: str) -> bool:
    if not ws.charts:
        return False
    before = len(ws.charts)
    ws.charts = [c for c in ws.charts if getattr(c, 'id', None) != chart_id]
    return len(ws.charts) != before


def iter_charts(ws: Workspace) -> Iterator:
    for c in ws.charts or []:
        yield c


def summarize_chart(chart) -> Dict[str, Union[str, Dict[str, Union[str, float]]]]:
    subj = getattr(chart, 'subject', None)
    cfg = getattr(chart, 'config', None)
    loc = getattr(subj, 'location', None) if subj else None
    return {
        "id": getattr(chart, 'id', ''),
        "name": getattr(subj, 'name', '') if subj else '',
        "event_time": str(getattr(subj, 'event_time', '')) if subj else '',
        "location": {
            "name": getattr(loc, 'name', ''),
            "latitude": getattr(loc, 'latitude', None),
            "longitude": getattr(loc, 'longitude', None),
            "timezone": getattr(loc, 'timezone', ''),
        } if loc else {},
        "engine": str(getattr(cfg, 'engine', '')) if cfg else '',
        "zodiac_type": str(getattr(cfg, 'zodiac_type', '')) if cfg else '',
        "house_system": str(getattr(cfg, 'house_system', '')) if cfg else '',
        "tags": list(getattr(chart, 'tags', []) or []),
    }


# Batch recompute
try:
    from services import compute_positions_for_chart
except Exception:  # pragma: no cover
    compute_positions_for_chart = None  # type: ignore


def recompute_all(ws: Workspace) -> Dict[str, Dict[str, float]]:
    """Compute positions for all charts in a workspace. Returns mapping chart_id -> positions dict."""
    results: Dict[str, Dict[str, float]] = {}
    if not ws.charts or compute_positions_for_chart is None:
        return results
    for chart in ws.charts:
        try:
            positions = compute_positions_for_chart(chart)
            results[getattr(chart, 'id', '')] = positions or {}
        except Exception:
            results[getattr(chart, 'id', '')] = {}
    return results


def load_workspace_from_dir(base_dir: Union[str, Path]) -> Workspace:
    """Load a workspace given its base directory (containing workspace.yaml)."""
    base = Path(base_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Workspace directory not found: {base_dir}")
    manifest = base / "workspace.yaml"
    if not manifest.exists():
        raise FileNotFoundError(f"Workspace manifest not found: {manifest}")
    return load_workspace(str(manifest))


def add_or_update_chart(ws: Workspace, chart: ChartInstance, base_dir: Union[str, Path]) -> str:
    """Add a new chart or update an existing one by id or subject.name, persist YAML and manifest.
    Returns relative path to the chart YAML (e.g., charts/john-doe.yml).
    """
    identity = getattr(chart, 'id', None) or (getattr(chart, 'subject', None) and getattr(chart.subject, 'name', None)) or 'chart'
    rel = f"charts/{_safe_filename(identity)}.yml"
    # Update in-memory collection (replace if exists)
    replaced = False
    charts = list(ws.charts or [])
    for idx, existing in enumerate(charts):
        ex_id = getattr(existing, 'id', None) or (getattr(existing, 'subject', None) and getattr(existing.subject, 'name', None))
        if ex_id and ex_id == identity:
            charts[idx] = chart
            replaced = True
            break
    if not replaced:
        charts.append(chart)
    ws.charts = charts
    # Prepare serializable data similar to add_chart (drop computed, normalize config)
    data = _serialize(chart)
    if isinstance(data, dict):
        data.pop('computed_chart', None)
        cfg = data.get('config') or {}
        try:
            ws_engine = getattr(ws, 'default_engine', None)
            if ws_engine and cfg.get('engine') in (ws_engine, getattr(ws_engine, 'value', None)):
                cfg.pop('engine', None)
        except Exception:
            pass
        cfg.pop('override_ephemeris', None)
        try:
            ws_theme = getattr(ws, 'color_theme', None)
            if ws_theme and cfg.get('color_theme') == ws_theme:
                cfg.pop('color_theme', None)
        except Exception:
            pass
        data['config'] = cfg
    # Write chart YAML and persist manifest
    _dump_yaml(Path(base_dir) / rel, data)
    save_workspace_modular(ws, base_dir)
    return rel


def remove_chart_by_id(ws: Workspace, chart_id: str, base_dir: Union[str, Path]) -> bool:
    """Remove a chart by id and persist manifest. Returns True if removed."""
    ok = remove_chart(ws, chart_id)
    if ok:
        save_workspace_modular(ws, base_dir)
    return ok


def scan_workspace_changes(base_dir: Union[str, Path]) -> Dict[str, Dict[str, List[str]]]:
    """Scan the workspace directory for new or missing items compared to the manifest.
    Returns a dict with keys 'charts' and 'subjects', each containing
    {'new_on_disk': [...], 'missing_on_disk': [...]} where names are basenames.
    """
    base = Path(base_dir)
    manifest_path = base / "workspace.yaml"
    result: Dict[str, Dict[str, List[str]]] = {
        'charts': {'new_on_disk': [], 'missing_on_disk': []},
        'subjects': {'new_on_disk': [], 'missing_on_disk': []},
    }
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f) or {}
    except Exception:
        return result

    def _scan(subdir: str, key: str):
        disk = set(p.name for p in (base / subdir).glob("*.yml"))
        refs = set(Path(p).name for p in (manifest.get(key, []) or []))
        new_on_disk = sorted(list(disk - refs))
        missing_on_disk = sorted(list(refs - disk))
        return new_on_disk, missing_on_disk

    charts_new, charts_missing = _scan("charts", "charts")
    subs_new, subs_missing = _scan("subjects", "subjects")
    result['charts']['new_on_disk'] = charts_new
    result['charts']['missing_on_disk'] = charts_missing
    result['subjects']['new_on_disk'] = subs_new
    result['subjects']['missing_on_disk'] = subs_missing
    return result
