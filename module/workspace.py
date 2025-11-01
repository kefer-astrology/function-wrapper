import sqlite3
from enum import Enum
from pathlib import Path
from datetime import datetime, date, time

from pandas import read_sql_query
from typing import Union, Optional, List, Dict, Iterator, Callable, Tuple
from dataclasses import asdict, is_dataclass
try:
    from module.models import (
        Workspace, EphemerisSource, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType, WorkspaceDefaults
    )
except ImportError:
    from models import (
        Workspace, EphemerisSource, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType, WorkspaceDefaults
    )
try:
    from module.utils import read_yaml_file, write_yaml_file, write_json_file, resolve_under_base
except ImportError:
    from utils import read_yaml_file, write_yaml_file, write_json_file, resolve_under_base

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
    """Load a modular workspace from a manifest YAML file.
    
    Parameters:
    - workspace_path: Absolute or relative path to `workspace.yaml`.
    
    Returns:
    - Workspace dataclass assembled from the manifest and referenced parts.
    
    Notes:
    - Paths referenced in the manifest (e.g., `charts/*.yml`) are resolved
      relative to the manifest directory and validated for containment.
    """
    if not Path(workspace_path).exists():
        raise FileNotFoundError(f"Workspace file not found: {workspace_path}")

    base_dir = str(Path(workspace_path).parent)

    manifest = read_yaml_file(workspace_path)

    return _load_workspace_from_manifest(manifest, base_dir)


def save_workspace_flat(workspace: Workspace, path: str, format: str = "yaml"):
    """Save the entire Workspace as a single flat file (debug/export use).
    
    Parameters:
    - workspace: Workspace instance to serialize.
    - path: Destination file path (YAML or JSON).
    - format: "yaml" or "json" (default: "yaml").
    """
    data = asdict(workspace)

    if format == "yaml":
        write_yaml_file(path, data, sort_keys=False, allow_unicode=True)
    elif format == "json":
        write_json_file(path, data, indent=2)
    else:
        raise ValueError("Unsupported format: choose 'yaml' or 'json'")


# ──────────────────────────────
# MODULAR LOADER
# ──────────────────────────────

def _safe_engine(val):
    """Safely convert a string/enum value to EngineType or return None.
    
    Accepts:
    - EngineType instance (returned as-is)
    - String value (e.g., "jpl") or name (e.g., "JPL")
    - None
    """
    try:
        if val is None:
            return None
        if isinstance(val, EngineType):
            return val
        s = str(val).strip()
        if not s:
            return None
        # Try by value first (lowercase values like 'jpl')
        try:
            return EngineType(s.lower())
        except Exception:
            pass
        # Then by enum name (uppercase like 'JPL')
        return getattr(EngineType, s.upper(), None)
    except Exception:
        return None


def _load_workspace_from_manifest(manifest: dict, base_dir: str) -> Workspace:
    """Assemble a Workspace from a parsed manifest dict and base directory.
    
    This resolves referenced YAML files (subjects, charts, layouts, presets,
    annotations) relative to `base_dir` while validating paths.
    """
    def load_yaml_file(path: str):
        full_path = resolve_under_base(base_dir, path)
        return read_yaml_file(full_path)

    def load_many(items: list, cls):
        out = []
        for it in (items or []):
            try:
                if isinstance(it, str):
                    data = load_yaml_file(it)
                elif isinstance(it, dict):
                    data = it
                else:
                    continue
                if isinstance(data, dict):
                    out.append(cls(**data))
            except Exception:
                # skip malformed entries
                continue
        return out

    # Load individual parts
    # Prefer top-level default_ephemeris for backward-compat; else derive from 'default' block
    de = manifest.get("default_ephemeris")
    if isinstance(de, dict):
        default_ephemeris = EphemerisSource(name=de.get("name", ""), backend=de.get("backend", ""))
    elif isinstance(de, str):
        default_ephemeris = EphemerisSource(name="", backend=de)
    else:
        # Derive from 'default' block if present
        dblk = manifest.get('default') if isinstance(manifest.get('default'), dict) else {}
        ep_name = (dblk.get('ephemeris_backend') or "")
        ep_backend = (dblk.get('ephemeris_engine') or "")
        default_ephemeris = EphemerisSource(name=ep_name, backend=ep_backend)
    active_model = manifest.get("active_model", "default")

    # Presets (ensure nested ChartConfig)
    chart_presets = []
    for p in manifest.get("chart_presets", []) or []:
        try:
            data = load_yaml_file(p) if isinstance(p, str) else (p if isinstance(p, dict) else None)
            if not isinstance(data, dict):
                continue
            cfg = data.get("config")
            if isinstance(cfg, dict):
                data["config"] = ChartConfig(**cfg)
            chart_presets.append(ChartPreset(**data))
        except Exception:
            continue

    subjects = load_many(manifest.get("subjects", []), ChartSubject)

    # Charts (ensure nested ChartSubject and ChartConfig)
    charts = []
    for p in manifest.get("charts", []) or []:
        try:
            data = load_yaml_file(p) if isinstance(p, str) else (p if isinstance(p, dict) else None)
            if not isinstance(data, dict):
                continue
            subj = data.get("subject")
            cfg = data.get("config")
            if isinstance(subj, dict):
                data["subject"] = ChartSubject(**subj)
            if isinstance(cfg, dict):
                data["config"] = ChartConfig(**cfg)
            # Ignore computed_chart on load if present (recomputable)
            data.pop("computed_chart", None)
            charts.append(ChartInstance(**data))
        except Exception:
            continue

    layouts = load_many(manifest.get("layouts", []), ViewLayout)

    annotations = []
    for ann in manifest.get("annotations", []) or []:
        try:
            if isinstance(ann, str):
                full_path = resolve_under_base(base_dir, ann)
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                annotations.append(Annotation(
                    title=Path(ann).stem,
                    content=content,
                    created=None,
                    author="unknown"
                ))
            elif isinstance(ann, dict):
                # Expect keys: title, content, author, created (optional)
                annotations.append(Annotation(
                    title=ann.get("title", "note"),
                    content=ann.get("content", ""),
                    created=None,
                    author=ann.get("author", "unknown")
                ))
        except Exception:
            continue

    # New preferred schema mapping
    raw_aspects = manifest.get('aspects')
    if isinstance(raw_aspects, list):
        aspects = list(raw_aspects)
    else:
        # fallback to legacy key if present, else empty list
        aspects = list(manifest.get('default_aspects') or [])

    raw_default = manifest.get('default')
    default_block = raw_default if isinstance(raw_default, dict) else {}
    # Build WorkspaceDefaults
    ws_defaults = WorkspaceDefaults(
        ephemeris_engine=_safe_engine(default_block.get('ephemeris_engine')),
        ephemeris_backend=default_block.get('ephemeris_backend'),
        location_name=default_block.get('location_name'),
        location_latitude=default_block.get('location_latitude'),
        location_longitude=default_block.get('location_longitude'),
        timezone=default_block.get('timezone'),
        language=default_block.get('language'),
        theme=default_block.get('theme'),
    ) if default_block else None

    ws = Workspace(
        owner=manifest.get('owner', ''),
        default_ephemeris=default_ephemeris,
        active_model=active_model,
        chart_presets=chart_presets,
        subjects=subjects,
        charts=charts,
        layouts=layouts,
        annotations=annotations,
        model_overrides=None,
        aspects=aspects or [],
        default=ws_defaults,
    )
    return ws


# ─────────────────────
# 🌐 TRANSLATION SERVICE
# ─────────────────────

class TranslationBackend(str, Enum):
    YAML = "yaml"
    SQLITE = "sqlite"


class TranslationService:
    """Provide simple i18n label loading from YAML files or SQLite.
    
    Use `get(domain, key, lang)` for single lookups and `inject_i18n(items, ...)`
    to batch-attach translations under `item.i18n` keyed by item id.
    """
    def __init__(self, backend: str = TRANSLATION_BACKEND):
        self.backend = TranslationBackend(backend)
        self.cache: Dict[str, Dict[str, Dict[str, str]]] = {}

    def get(self, domain: str, key: str, lang: Optional[str] = None) -> Optional[str]:
        """Return translated value for a given domain/key in the selected language.
        
        Falls back to DEFAULT_LANGUAGE via `_load` if not provided.
        """
        lang = lang or DEFAULT_LANGUAGE
        data = self._load(domain, lang)
        return data.get(key)

    def inject_i18n(self, items: List, domain: str, lang: Optional[str] = None):
        """Attach translations for `items` in-place under `item.i18n`.
        
        Each `item` is expected to have an `id` attribute used as the lookup key.
        Domain and language select the translation file or DB rows.
        """
        lang = lang or DEFAULT_LANGUAGE
        translations = self._load(domain, lang)
        for item in items:
            item.i18n = translations.get(item.id, {})

    def _load(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        """Load and cache translation maps for a (domain, lang) pair."""
        key = f"{domain}:{lang}"
        if key in self.cache:
            return self.cache[key]

        if self.backend == TranslationBackend.YAML:
            path = TRANSLATION_DIR / lang / f"{domain}.yml"
            try:
                data = read_yaml_file(path)
            except FileNotFoundError:
                data = {}
        else:
            data = self._load_from_sqlite(domain, lang)

        self.cache[key] = data
        return data

    def _load_from_sqlite(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        """Load translations from SQLite table `translations`.
        
        Expected schema: (domain TEXT, language TEXT, key TEXT, label TEXT, value TEXT)
        Returns nested mapping: {key: {label: value}}.
        """
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
    """Return a simple language mapping from SQLite `language` table.
    
    Parameters:
    - default: column name to use for values, e.g., "cz" or "en".
    """
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
    write_yaml_file(path, _to_primitive(data), sort_keys=False, allow_unicode=True)


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
    """Scaffold a new workspace directory tree and write a base manifest.
    
    Creates subfolders `subjects/`, `charts/`, `layouts/`, `annotations/`, `presets/`
    and a `workspace.yaml` manifest that references none by default.
    
    Returns:
    - Absolute path to the created `workspace.yaml` file.
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
        "active_model": active_model,
        # preferred new structure
        "aspects": [],
        "default": {
            # engine = computation backend (e.g., jpl)
            "ephemeris_engine": (default_ephemeris.get("backend") or "jpl"),
            # backend = ephemeris file/model id (e.g., de430.bsp)
            "ephemeris_backend": default_ephemeris.get("name"),
            "location_name": (DEFAULT_LOCATION.get("name") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_latitude": (DEFAULT_LOCATION.get("latitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_longitude": (DEFAULT_LOCATION.get("longitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "timezone": (DEFAULT_LOCATION.get("timezone") if isinstance(DEFAULT_LOCATION, dict) else None),
            "language": DEFAULT_LANGUAGE,
            "theme": "default",
        },
        # modular refs
        "chart_presets": [],
        "subjects": [],
        "charts": [],
        "layouts": [],
        "annotations": [],
    }
    manifest_path = base / "workspace.yaml"
    write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    return manifest_path


def save_workspace_modular(workspace: Workspace, base_dir: Union[str, Path]) -> Path:
    """Persist a Workspace into modular YAML files and update `workspace.yaml`.
    
    Serializes presets, subjects, charts, layouts, and annotations into their
    respective subdirectories under `base_dir`. Writes/overwrites the manifest
    with relative references.
    
    Returns:
    - Absolute path to the updated `workspace.yaml`.
    """
    base = Path(base_dir)
    subjects_dir = base / "subjects"
    charts_dir = base / "charts"
    layouts_dir = base / "layouts"
    annotations_dir = base / "annotations"
    presets_dir = base / "presets"
    for d in (subjects_dir, charts_dir, layouts_dir, annotations_dir, presets_dir):
        _ensure_dir(d)

    # Write modular YAML files and collect relative references
    preset_refs = []
    for p in (workspace.chart_presets or []):
        ref = f"presets/{_safe_filename(p.name)}.yml"
        _dump_yaml(base / ref, _serialize(p))
        preset_refs.append(ref)

    subj_refs = []
    for s in (workspace.subjects or []):
        ref = f"subjects/{_safe_filename(getattr(s, 'id', getattr(s, 'name', 'subject')))}.yml"
        _dump_yaml(base / ref, _serialize(s))
        subj_refs.append(ref)

    chart_refs = []
    for c in (workspace.charts or []):
        ref = f"charts/{_safe_filename(getattr(c, 'id', getattr(getattr(c, 'subject', None), 'name', 'chart')))}.yml"
        _dump_yaml(base / ref, _serialize(c))
        chart_refs.append(ref)

    layout_refs = []
    for l in (workspace.layouts or []):
        ref = f"layouts/{_safe_filename(getattr(l, 'name', 'layout'))}.yml"
        _dump_yaml(base / ref, _serialize(l))
        layout_refs.append(ref)

    annotation_refs = []
    for a in (workspace.annotations or []):
        ref = f"annotations/{_safe_filename(getattr(a, 'title', 'note'))}.yml"
        _dump_yaml(base / ref, _serialize(a))
        annotation_refs.append(ref)

    # Build manifest in the new preferred structure
    d = workspace.default
    # determine ephemeris defaults from workspace.default_ephemeris
    ws_engine = getattr(workspace.default_ephemeris, 'backend', None) or 'jpl'
    ws_backend = getattr(workspace.default_ephemeris, 'name', None)
    if d is not None:
        # Prefer explicit values, else fall back to workspace/default constants
        default_block = {
            "ephemeris_engine": (getattr(d.ephemeris_engine, 'value', d.ephemeris_engine) if d.ephemeris_engine else ws_engine),
            # backend should reflect the ephemeris file/model name (e.g., de430.bsp)
            "ephemeris_backend": (d.ephemeris_backend or ws_backend),
            "location_name": (d.location_name if d.location_name is not None else (DEFAULT_LOCATION.get("name") if isinstance(DEFAULT_LOCATION, dict) else None)),
            "location_latitude": (d.location_latitude if d.location_latitude is not None else (DEFAULT_LOCATION.get("latitude") if isinstance(DEFAULT_LOCATION, dict) else None)),
            "location_longitude": (d.location_longitude if d.location_longitude is not None else (DEFAULT_LOCATION.get("longitude") if isinstance(DEFAULT_LOCATION, dict) else None)),
            "timezone": (d.timezone if d.timezone is not None else (DEFAULT_LOCATION.get("timezone") if isinstance(DEFAULT_LOCATION, dict) else None)),
            "language": (d.language if d.language is not None else DEFAULT_LANGUAGE),
            "theme": (d.theme if d.theme is not None else "default"),
        }
    else:
        # Populate sensible defaults even if workspace.default is None
        default_block = {
            "ephemeris_engine": ws_engine,
            "ephemeris_backend": ws_backend,
            "location_name": (DEFAULT_LOCATION.get("name") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_latitude": (DEFAULT_LOCATION.get("latitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_longitude": (DEFAULT_LOCATION.get("longitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "timezone": (DEFAULT_LOCATION.get("timezone") if isinstance(DEFAULT_LOCATION, dict) else None),
            "language": DEFAULT_LANGUAGE,
            "theme": "default",
        }

    manifest = {
        "owner": workspace.owner,
        "active_model": workspace.active_model,
        "aspects": list(getattr(workspace, 'aspects', []) or []),
        "default": default_block,
        # modular refs
        "chart_presets": preset_refs,
        "subjects": subj_refs,
        "charts": chart_refs,
        "layouts": layout_refs,
        "annotations": annotation_refs,
    }

    manifest_path = base / "workspace.yaml"
    write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    return manifest_path


# ──────────────────────────────
# MODULAR CRUD HELPERS (PUBLIC)
# ──────────────────────────────

def _prune_chart_yaml_payload(data: dict) -> dict:
    """Remove empty/default fields from a chart dict before YAML dump.
    
    - Drop 'computed_chart'
    - In 'config': drop 'override_ephemeris' and any keys with None/empty values
      (e.g., 'model', 'engine', 'ayanamsa', 'color_theme').
    - Drop any top-level keys explicitly listed as undesired when empty.
    """
    if not isinstance(data, dict):
        return data
    # Drop computed
    data.pop('computed_chart', None)
    cfg = data.get('config')
    if isinstance(cfg, dict):
        # Keys we always remove from config
        cfg.pop('override_ephemeris', None)
        # Remove null/empty values in known optional fields
        for k in list(cfg.keys()):
            v = cfg.get(k)
            if v is None or v == '' or (isinstance(v, (list, dict)) and not v):
                # keep only if it's a required key; otherwise drop
                if k in {'model', 'engine', 'ayanamsa', 'color_theme', 'override_ephemeris'}:
                    cfg.pop(k, None)
        data['config'] = cfg
    # Also clean any top-level optional strings if empty
    for k in ['color_theme']:
        if data.get(k) in (None, ''):
            data.pop(k, None)
    return data

def add_subject(ws: Workspace, subject, base_dir: Union[str, Path]) -> str:
    """Add a subject to a Workspace and write its YAML file.
    
    Returns the relative path (e.g., `subjects/john-doe.yml`) written to disk.
    Caller should re-save the manifest via `save_workspace_modular`.
    """
    rel = f"subjects/{_safe_filename(getattr(subject, 'id', getattr(subject, 'name', 'subject')))}.yml"
    _dump_yaml(resolve_under_base(base_dir, rel), _serialize(subject))
    ws.subjects = (ws.subjects or []) + [subject]
    return rel


def add_chart(ws: Workspace, chart, base_dir: Union[str, Path]) -> str:
    """Add a chart to a Workspace and write its YAML file; returns relative path."""
    base_name = getattr(chart, 'id', None) or (getattr(chart, 'subject', None) and getattr(chart.subject, 'name', None)) or 'chart'
    # Prevent duplicates in memory collection
    identity = base_name
    for existing in (ws.charts or []):
        ex_id = getattr(existing, 'id', None) or (getattr(existing, 'subject', None) and getattr(existing.subject, 'name', None))
        if ex_id and ex_id == identity:
            return f"charts/{_safe_filename(identity)}.yml"

    # Prepare serializable data, removing computed payload and ephemeral overrides
    data = _serialize(chart)
    if isinstance(data, dict):
        data = _prune_chart_yaml_payload(data)

    rel = f"charts/{_safe_filename(base_name)}.yml"
    _dump_yaml(resolve_under_base(base_dir, rel), data)
    ws.charts = (ws.charts or []) + [chart]
    return rel


def update_chart(ws: Workspace, chart_id: str, updater: Callable) -> bool:
    """Update a chart in-memory by id using a caller-provided updater; returns True if updated."""
    if not ws.charts:
        return False
    for idx, c in enumerate(ws.charts):
        if getattr(c, 'id', None) == chart_id:
            ws.charts[idx] = updater(c)
            return True
    return False


def remove_chart(ws: Workspace, chart_id: str) -> bool:
    """Remove a chart from the Workspace in-memory by its id; returns True if any removed."""
    if not ws.charts:
        return False
    before = len(ws.charts)
    ws.charts = [c for c in ws.charts if getattr(c, 'id', None) != chart_id]
    return len(ws.charts) != before


def iter_charts(ws: Workspace) -> Iterator:
    """Yield charts from the Workspace (safe for None)."""
    for c in ws.charts or []:
        yield c


def summarize_chart(chart) -> Dict[str, Union[str, Dict[str, Union[str, float]]]]:
    """Return a lightweight summary dict for a chart (safe accessors)."""
    subj = getattr(chart, 'subject', None)
    cfg = getattr(chart, 'config', None)
    loc = getattr(subj, 'location', None) if subj else None
    return {
        "id": getattr(chart, 'id', ''),
        "name": getattr(subj, 'name', '') if subj else '',
        "event_time": str(getattr(subj, 'event_time', '')) if subj else '',
        "location": getattr(loc, 'name', '') if loc else '',
        "engine": str(getattr(cfg, 'engine', '')) if cfg else '',
        "zodiac_type": str(getattr(cfg, 'zodiac_type', '')) if cfg else '',
        "house_system": str(getattr(cfg, 'house_system', '')) if cfg else '',
        "tags": list(getattr(chart, 'tags', []) or []),
    }


# Batch recompute
try:
    from services import compute_positions_for_chart  # type: ignore
except Exception:  # pragma: no cover
    compute_positions_for_chart = None  # type: ignore


def recompute_all(ws: Workspace) -> Dict[str, Dict[str, float]]:
    """Compute positions for all charts in a workspace; returns mapping chart_id -> positions dict."""
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
    """Load a workspace given its base directory (containing `workspace.yaml`)."""
    base = Path(base_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Workspace directory not found: {base_dir}")
    manifest_path = base / "workspace.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Workspace manifest not found: {manifest_path}")
    return load_workspace(str(manifest_path))


def add_or_update_chart(ws: Workspace, chart: ChartInstance, base_dir: Union[str, Path]) -> str:
    """Add a new chart or update an existing one by id or subject name; persist YAML and manifest.
    
    Returns the relative path to the chart YAML (e.g., `charts/john-doe.yml`).
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
    # Prepare serializable data similar to add_chart (drop computed and ephemeral overrides)
    data = _serialize(chart)
    if isinstance(data, dict):
        data = _prune_chart_yaml_payload(data)
    # Write chart YAML and persist manifest
    _dump_yaml(resolve_under_base(base_dir, rel), data)
    save_workspace_modular(ws, base_dir)
    return rel


def remove_chart_by_id(ws: Workspace, chart_id: str, base_dir: Union[str, Path]) -> bool:
    """Remove a chart by id and persist the manifest. Returns True if removed."""
    ok = remove_chart(ws, chart_id)
    if ok:
        save_workspace_modular(ws, base_dir)
    return ok


def scan_workspace_changes(base_dir: Union[str, Path]) -> Dict[str, Dict[str, List[str]]]:
    """Scan the workspace directory for drift relative to the manifest.
    
    Returns:
    - { 'charts': {'new_on_disk': [...], 'missing_on_disk': [...]},
        'subjects': {'new_on_disk': [...], 'missing_on_disk': [...]} }
      where item names are basenames (e.g., `john-doe.yml`).
    """
    base = Path(base_dir)
    manifest_path = base / "workspace.yaml"
    result: Dict[str, Dict[str, List[str]]] = {
        'charts': {'new_on_disk': [], 'missing_on_disk': []},
        'subjects': {'new_on_disk': [], 'missing_on_disk': []},
    }
    try:
        manifest = read_yaml_file(manifest_path)
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


def prune_workspace_manifest(base_dir: Union[str, Path]) -> Dict[str, List[str]]:
    """Prune workspace.yaml to remove references to modular files that no longer exist.
    
    This function does NOT write any new YAML files. It only removes stale
    entries from the manifest lists (charts, subjects, layouts, annotations,
    chart_presets) when the corresponding files are missing on disk.
    
    Returns a summary dict with keys removed_<section> listing removed refs.
    """
    base = Path(base_dir)
    manifest_path = base / "workspace.yaml"
    summary: Dict[str, List[str]] = {
        'removed_charts': [],
        'removed_subjects': [],
        'removed_layouts': [],
        'removed_annotations': [],
        'removed_presets': [],
    }
    try:
        manifest = read_yaml_file(manifest_path)
    except Exception:
        return summary

    def _filter_existing(key: str, subdir: str, removed_key: str):
        items = manifest.get(key, []) or []
        new_items = []
        removed: List[str] = []
        for it in items:
            # keep embedded dicts as-is
            if isinstance(it, dict):
                new_items.append(it)
                continue
            if isinstance(it, str):
                p = base / it if not it.startswith('/') else Path(it)
                if p.exists():
                    new_items.append(it)
                else:
                    removed.append(it)
        manifest[key] = new_items
        summary[removed_key] = removed

    _filter_existing('charts', 'charts', 'removed_charts')
    _filter_existing('subjects', 'subjects', 'removed_subjects')
    _filter_existing('layouts', 'layouts', 'removed_layouts')
    _filter_existing('annotations', 'annotations', 'removed_annotations')
    _filter_existing('chart_presets', 'presets', 'removed_presets')

    # Write back pruned manifest
    try:
        write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    except Exception:
        # If write fails, return original summary (nothing else to do)
        return summary
    return summary
