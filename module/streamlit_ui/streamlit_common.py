"""Session-state bootstrap and safe-access primitives shared by every
Streamlit UI module (module/streamlit_*.py, module/ui_streamlit.py)."""
import datetime
import streamlit as st

try:
    from module.models import ChartMode, EngineType
except ImportError:
    from models import ChartMode, EngineType

try:
    from module.ui_translations import change_language
except ImportError:
    from ui_translations import change_language

# Exceptions we treat as recoverable in UI flows.
UI_RECOVERABLE_EXC = (AttributeError, KeyError, TypeError, ValueError, OSError, RuntimeError)


def _ensure_session_defaults():
    if 'settings' not in st.session_state:
        st.session_state["settings"] = {
            "chart": None,
            "language": change_language(default="cz"),
            "tags": ["Tag 1", "Tag 2", "Tag 3", "Tag 4"]
        }
    if "mode" not in st.session_state:
        # Land on the current-sky chart by default, not a blank creation form.
        st.session_state.mode = "chart"
    if "initial_dialog_completed" not in st.session_state:
        st.session_state.initial_dialog_completed = False
    if "workspace" not in st.session_state:
        st.session_state.workspace = None
    if "workspace_manifest" not in st.session_state:
        st.session_state.workspace_manifest = ""
    if "chart_type" not in st.session_state:
        st.session_state.chart_type = ChartMode.NATAL.value
    if "crt_name" not in st.session_state:
        st.session_state.crt_name = ""
    if "settings_section" not in st.session_state:
        st.session_state.settings_section = "general"
    if "save_export_type" not in st.session_state:
        st.session_state.save_export_type = "SFS"
    if "save_dest_path" not in st.session_state:
        st.session_state.save_dest_path = ""
    if "people" not in st.session_state:
        st.session_state.people = []
    if "session_charts" not in st.session_state:
        st.session_state.session_charts = []  # Charts created without workspace
    if "current_person_name" not in st.session_state:
        st.session_state.current_person_name = ""
    if "footer_select" not in st.session_state:
        st.session_state.footer_select = ""
    if "ws_default_engine" in st.session_state:
        normalized = _normalize_engine_select_value(st.session_state.get("ws_default_engine"))
        if normalized is not None:
            st.session_state["ws_default_engine"] = normalized
    if "workspace_report" not in st.session_state:
        st.session_state.workspace_report = None
    # Focused chart display fields (read-only, safe across modes)
    if "focused_place" not in st.session_state:
        st.session_state.focused_place = None
    if "focused_date" not in st.session_state:
        st.session_state.focused_date = None
    if "focused_time" not in st.session_state:
        st.session_state.focused_time = None
    if "focused_latlon" not in st.session_state:
        st.session_state.focused_latlon = None
    if "focused_tz" not in st.session_state:
        st.session_state.focused_tz = None
    if "focused_mode" not in st.session_state:
        st.session_state.focused_mode = None
    if "focused_house" not in st.session_state:
        st.session_state.focused_house = None
    if "focused_zodiac" not in st.session_state:
        st.session_state.focused_zodiac = None
    if "focused_engine" not in st.session_state:
        st.session_state.focused_engine = None
    if "focused_tags" not in st.session_state:
        st.session_state.focused_tags = []


def _safe_get(obj, attr: str, key: str = None, default=None):
    """Return obj.attr if present, else obj[key] if dict, else default."""
    try:
        if obj is None:
            return default
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            k = key or attr
            return obj.get(k, default)
    except UI_RECOVERABLE_EXC:
        return default
    return default


# JPL/Skyfield is the only engine; kept as a list (rather than a bare constant)
# since it's used directly as st.selectbox's options argument below.
ENGINE_SELECT_OPTIONS = ["JPL"]


def _normalize_engine_select_value(val):
    """Coerce any legacy engine value (old workspace files, saved session state) to 'JPL'."""
    if val is None:
        return None
    return "JPL"


def _engine_from_value(val):
    """Coerce any legacy engine value to EngineType.JPL; only JPL/Skyfield is computed."""
    if val is None:
        return None
    return EngineType.JPL


def _safe_subject_name(chart) -> str:
    subj = _safe_get(chart, 'subject')
    return _safe_get(subj, 'name') or _safe_get(subj, 'name', 'name', '') or ''


def _safe_subject_location(chart):
    subj = _safe_get(chart, 'subject')
    loc = _safe_get(subj, 'location')
    if loc is None:
        return None
    name = _safe_get(loc, 'name') or _safe_get(loc, 'name', 'name')
    lat = _safe_get(loc, 'latitude') or _safe_get(loc, 'latitude', 'latitude')
    lon = _safe_get(loc, 'longitude') or _safe_get(loc, 'longitude', 'longitude')
    tz = _safe_get(loc, 'timezone') or _safe_get(loc, 'timezone', 'timezone')
    return {'name': name, 'lat': lat, 'lon': lon, 'tz': tz}


def _safe_event_dt(chart):
    from datetime import datetime as _dt
    subj = _safe_get(chart, 'subject')
    dt = _safe_get(subj, 'event_time') or _safe_get(subj, 'event_time', 'event_time')
    # If string, try parse ISO
    if isinstance(dt, str):
        try:
            return _dt.fromisoformat(dt)
        except UI_RECOVERABLE_EXC:
            return None
    return dt


def _safe_config(chart):
    cfg = _safe_get(chart, 'config')
    return {
        'mode': _safe_get(cfg, 'mode'),
        'house': _safe_get(cfg, 'house_system') or _safe_get(cfg, 'house_system', 'house_system'),
        'zodiac': _safe_get(cfg, 'zodiac_type') or _safe_get(cfg, 'zodiac_type', 'zodiac_type'),
        'engine': _safe_get(cfg, 'engine') or _safe_get(cfg, 'engine', 'engine'),
    }
