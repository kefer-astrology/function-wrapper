import os
import sqlite3
from enum import Enum
from pathlib import Path

import yaml
import json
from pandas import read_sql_query
from typing import Union, Optional, List, Dict
from models import Workspace
from dataclasses import asdict, is_dataclass

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
    from .models import (
        Workspace, EphemerisSource, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation
    )

    def load_yaml_file(path: str):
        full_path = os.path.join(base_dir, path)
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_many(paths: list, cls):
        return [cls(**load_yaml_file(p)) for p in paths]

    # Load individual parts
    default_ephemeris = EphemerisSource(**manifest["default_ephemeris"])
    active_model = manifest["active_model"]

    chart_presets = load_many(manifest.get("chart_presets", []), ChartPreset)
    subjects = load_many(manifest.get("subjects", []), ChartSubject)
    charts = load_many(manifest.get("charts", []), ChartInstance)
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

    return Workspace(
        owner=manifest["owner"],
        default_ephemeris=default_ephemeris,
        active_model=active_model,
        chart_presets=chart_presets,
        subjects=subjects,
        charts=charts,
        layouts=layouts,
        annotations=annotations
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


