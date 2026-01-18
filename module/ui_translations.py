"""
UI-specific translation and language functions.
This module handles SQLite-based UI settings (translations, language mappings).
Separated from core workspace logic to keep workspace.py pure YAML-based.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional
from enum import Enum

try:
    from pandas import read_sql_query
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# UI settings database path (UI-only, not used by core logic)
UI_SETTINGS_DB = Path(__file__).parent / "ui_settings.db"

# Default localization settings
DEFAULT_LANGUAGE = "cs"
FALLBACK_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "cs", "fr"]

TRANSLATION_BACKEND = "sqlite"  # Default to SQLite, with YAML fallback
# Path to translation files (for YAML)
TRANSLATION_DIR = Path(__file__).parent / "locales"


class TranslationBackend(str, Enum):
    YAML = "yaml"
    SQLITE = "sqlite"


class TranslationService:
    """Provide simple i18n label loading from YAML files or SQLite.
    
    **Architecture:**
    - **Base app (workspace.py)**: Language-agnostic, only stores language preference as string in YAML
    - **UI modules**: Use this service for translations
    
    **Backend behavior:**
    - **SQLITE mode (default)**: Loads from SQLite first, falls back to YAML if SQLite is empty/fails.
      This allows SQLite to override YAML while inheriting defaults from YAML files.
    - **YAML mode**: Loads only from YAML files (no SQLite).
    
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

    def inject_i18n(self, items: list, domain: str, lang: Optional[str] = None):
        """Attach translations for `items` in-place under `item.i18n`.
        
        Each `item` is expected to have an `id` attribute used as the lookup key.
        Domain and language select the translation file or DB rows.
        """
        lang = lang or DEFAULT_LANGUAGE
        translations = self._load(domain, lang)
        for item in items:
            item.i18n = translations.get(item.id, {})

    def _load(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        """Load and cache translation maps for a (domain, lang) pair.
        
        If backend is SQLITE, tries SQLite first, then falls back to YAML if SQLite
        returns empty or fails. This allows SQLite to override YAML while inheriting
        defaults from YAML files.
        """
        key = f"{domain}:{lang}"
        if key in self.cache:
            return self.cache[key]

        if self.backend == TranslationBackend.SQLITE:
            # Try SQLite first, fallback to YAML if empty or fails
            data = self._load_from_sqlite(domain, lang)
            if not data:
                # Fallback to YAML
                data = self._load_from_yaml(domain, lang)
        else:
            # YAML-only mode
            data = self._load_from_yaml(domain, lang)

        self.cache[key] = data
        return data

    def _load_from_yaml(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        """Load translations from YAML files.
        
        Args:
            domain: Translation domain (e.g., "aspects", "bodies")
            lang: Language code (e.g., "cs", "en")
            
        Returns:
            Dictionary mapping key -> {label: value}
        """
        try:
            from module.utils import read_yaml_file
        except ImportError:
            from utils import read_yaml_file
        path = TRANSLATION_DIR / lang / f"{domain}.yml"
        try:
            data = read_yaml_file(path)
        except FileNotFoundError:
            # Try fallback language if primary language file not found
            if lang != FALLBACK_LANGUAGE:
                try:
                    fallback_path = TRANSLATION_DIR / FALLBACK_LANGUAGE / f"{domain}.yml"
                    data = read_yaml_file(fallback_path)
                except FileNotFoundError:
                    data = {}
            else:
                data = {}
        return data

    def _load_from_sqlite(self, domain: str, lang: str) -> Dict[str, Dict[str, str]]:
        """Load translations from SQLite table `translations`.
        
        Expected schema: (domain TEXT, language TEXT, key TEXT, label TEXT, value TEXT)
        Returns nested mapping: {key: {label: value}}.
        """
        data = {}
        try:
            with sqlite3.connect(UI_SETTINGS_DB) as conn:
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
    
    Args:
        default: Column name to use for values, e.g., "cz" or "en", defaults to "cz"
        
    Returns:
        Dictionary mapping language keys to translated values
        
    Note:
        Falls back to empty dict if pandas or database is not available.
    """
    if not PANDAS_AVAILABLE:
        return {}
    
    try:
        with sqlite3.connect(UI_SETTINGS_DB) as dbcon:
            df = read_sql_query("SELECT * FROM language ORDER BY id;", dbcon)
        return dict(zip(df["col"], df[default]))
    except (sqlite3.Error, FileNotFoundError, KeyError):
        return {}
