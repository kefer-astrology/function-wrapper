import datetime
import streamlit as st
from pathlib import Path

# Standardized imports with fallback for direct execution (Streamlit Cloud compatibility)
try:
    from module.models import Annotation, ChartInstance, Location, ChartSubject, ChartConfig, EngineType, ChartMode
except ImportError:
    from models import Annotation, ChartInstance, Location, ChartSubject, ChartConfig, EngineType, ChartMode

try:
    from module.utils import (
        Actual,
        parse_sfs_content,
        combine_date_time,
        prepare_horoscope,
        default_ephemeris_path,
        import_chart_yaml,
        read_yaml_file,
        parse_yaml_content,
        parse_chart_yaml,
        ensure_aware,
        now_utc,
    )
except ImportError:
    from utils import (
        Actual,
        parse_sfs_content,
        combine_date_time,
        prepare_horoscope,
        default_ephemeris_path,
        import_chart_yaml,
        read_yaml_file,
        parse_yaml_content,
        parse_chart_yaml,
        ensure_aware,
        now_utc,
    )

try:
    from module.services import Subject, extract_kerykeion_points, compute_positions, list_open_view_rows
except ImportError:
    from services import Subject, extract_kerykeion_points, compute_positions, list_open_view_rows

try:
    from module.z_visual import build_radix_figure
except ImportError:
    from z_visual import build_radix_figure

try:
    from module.workspace import (
        change_language, load_workspace, add_or_update_chart,
        scan_workspace_changes, save_workspace_modular, summarize_chart, add_subject,
    )
except ImportError:
    from workspace import (
        change_language, load_workspace, add_or_update_chart,
        scan_workspace_changes, save_workspace_modular, summarize_chart, add_subject,
    )

# -----------------------------
# Toolbar / layout configuration
# -----------------------------
ACTIONS = [
    ("🆕", "create",   "Nový Horoskop"),
    ("📂", "open",     "Otevřít horoskop"),
    ("💾", "save",     "Uložit horoskop"),
    ("📤", "export",   "Exportovat Horoskop"),
    ("📊", "chart",    "Zobrazení horoskopu"),
    ("📋", "aspektarium", "Aspektárium"),
    ("📖", "interpretation", "Interpretace"),
    ("🔁", "transzit", "Transzity a direkce"),
    ("📝", "notes",    "Poznámky"),
    ("⚙️", "settings", "Nastavení"),
]

# Layout map
# For create/open we want a three-column layout; settings/save use two columns
LAYOUTS = {
    "create":          ("two", [1, 5]),
    "open":            ("two", [1, 5]),
    "save":            ("two",   [1, 5]),
    "export":          ("two",   [1, 5]),
    "settings":        ("two",   [1, 5]),
    "chart":           ("two", [1, 5]),
    "aspektarium":     ("two", [1, 5]),
    "interpretation":  ("two", [1, 5]),
    "transzit":        ("two", [1, 5]),
    "notes":           ("two", [1, 5]),
}


def render_toolbar():
    st.markdown(
        """
        <style>
          .toolbar { position: sticky; top: 0; z-index: 1000; background: var(--background-color);
                     padding: .4rem .3rem .6rem; border-bottom: 1px solid rgba(125,125,125,.25); }
          .tool-btn { width: 100%; }
          .brand { font-weight: 800; font-size: 28px; letter-spacing: 4px; padding: 4px 8px; display:inline-block; }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="toolbar">', unsafe_allow_html=True)
    # Build columns dynamically: [brand] + [one per action]
    weights = [2] + [1] * len(ACTIONS)
    cols = st.columns(weights)
    # Brand on the left
    with cols[0]:
        st.markdown("<span class='brand'>Kefer</span>", unsafe_allow_html=True)
    # Action buttons
    for i, (emoji, key, label) in enumerate(ACTIONS, start=1):
        with cols[i]:
            if st.button(f"{emoji} {label}", key=f"tb_{key}", use_container_width=True):
                st.session_state.mode = key
    st.markdown('</div>', unsafe_allow_html=True)


def _ensure_session_defaults():
    if 'settings' not in st.session_state:
        st.session_state["settings"] = {
            "chart": None,
            "language": change_language(default="cz"),
            "tags": ["Tag 1", "Tag 2", "Tag 3", "Tag 4"]
        }
    if "mode" not in st.session_state:
        st.session_state.mode = "create"
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
    except Exception:
        return default
    return default


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
        except Exception:
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


def _left_open_menu():
    # Track which view is active
    if "open_view_mode" not in st.session_state:
        st.session_state.open_view_mode = "horoskopy"
    
    if st.button("Horoskopy", use_container_width=True, key="left_my", type="primary" if st.session_state.open_view_mode == "horoskopy" else "secondary"):
        st.session_state.open_view_mode = "horoskopy"
        st.rerun()
    if st.button("Databáze osobností", use_container_width=True, key="left_db", type="primary" if st.session_state.open_view_mode == "db" else "secondary"):
        st.session_state.open_view_mode = "db"
        st.rerun()
    
    if st.session_state.open_view_mode == "horoskopy":
        st.info("Použijte vyhledávání k filtrování, importujte YAML do workspace.")
    else:
        st.info("Připojení k online databázi osobností. Funkcionalita bude implementována.")


def _left_create_menu():
    st.markdown("##### Vyberte typ horoskopu:")
    # Show chart types from ChartMode
    options = [ChartMode.NATAL.value, ChartMode.EVENT.value, ChartMode.HORARY.value, ChartMode.COMPOSITE.value]
    # Get current selection or default to NATAL
    current_type = st.session_state.get("chart_type", ChartMode.NATAL.value)
    # Find index of current selection
    try:
        current_index = options.index(current_type)
    except ValueError:
        current_index = 0
    
    chart_type = st.radio(
        "Typ horoskopu",
        options,
        key="chart_type_selector",
        index=current_index
    )
    # Sync with session state
    st.session_state["chart_type"] = chart_type
    st.info("Tip: Nastavení efemerid najdete v záložce Nastavení.")


def _left_open_workspace_menu():
    st.markdown("#### Otevřít Workspace")
    st.info("Zadejte cestu k workspace.yaml v hlavním panelu a načtěte workspace.")


def _left_initial_dialog_menu():
    """Left menu for initial dialog."""
    st.markdown("#### Nastavení")
    
    menu_items = [
        "Jazyk",
        "Lokace",
        "Systém domů",
        "Nastavení aspektů",
        "Vzhled",
        "Výpočetní engine",
        "Manuál",
    ]
    
    if "initial_dialog_section" not in st.session_state:
        st.session_state.initial_dialog_section = "Jazyk"
    
    for item in menu_items:
        if st.button(item, use_container_width=True, key=f"init_{item}"):
            st.session_state.initial_dialog_section = item


def _left_save_menu():
    st.markdown("**Formát uložení:**")
    save_format = st.radio(
        "Vyberte formát",
        ["default (yaml)", "sfs"],
        key="save_format_left",
        index=0
    )
    # Sync with center view
    st.session_state["save_export_type"] = "YAML" if save_format == "default (yaml)" else "SFS"


def _left_export_menu():
    st.markdown("**Formát exportu:**")
    export_format = st.radio(
        "Vyberte formát",
        ["Print", "PNG", "PDF"],
        key="export_format_left",
        index=0
    )
    # Sync with center view
    st.session_state["export_format"] = export_format


def _left_notes_menu():
    st.markdown("#### Poznámky")
    # List of notes/annotations
    focused_chart = _get_focused_chart()
    chart_name = st.session_state.get("current_person_name") or "Obecné"
    
    # Get annotations from workspace or session
    ws = st.session_state.get('workspace')
    annotations = []
    if ws and ws.annotations:
        annotations = list(ws.annotations)
    
    # Also get session annotations
    session_anns = st.session_state.get('session_annotations', [])
    if session_anns:
        annotations.extend(session_anns)
    
    if annotations:
        st.markdown("**Existující poznámky:**")
        for ann in annotations:
            if st.button(ann.title, use_container_width=True, key=f"note_{ann.title}"):
                st.session_state["selected_note"] = ann.title
                st.rerun()
    else:
        st.info("Žádné poznámky. Vytvořte novou poznámku vpravo.")
    
    if st.button("➕ Nová poznámka", use_container_width=True, key="new_note"):
        st.session_state["selected_note"] = None
        st.session_state["editing_note"] = True
        st.rerun()


def _left_chart_menu():
    # Get the name of the currently active horoscope - use same logic as workspace handling
    focused_chart = _get_focused_chart()
    if focused_chart:
        chart_name = _safe_subject_name(focused_chart) or "Zobrazení horoskopu"
    else:
        chart_name = st.session_state.get("current_person_name") or st.session_state.get("crt_name") or "Zobrazení horoskopu"
    with st.expander(chart_name, expanded=False):
        place = st.session_state.get("focused_place") or st.session_state.get("crt_place") or "—"
        latlon = st.session_state.get("focused_latlon")
        tz = st.session_state.get("focused_tz")
        st.markdown("**Základní nastavení**")
        st.write(f"Lokalita: {place}")
        if latlon or tz:
            lat, lon = (latlon or (None, None))
            st.caption(f"Souřadnice: {lat if lat is not None else '—'}, {lon if lon is not None else '—'} | Časová zóna: {tz or '—'}")
        
        st.markdown("**Konfigurace horoskopu**")
        st.write(f"Režim: {st.session_state.get('focused_mode') or '—'}")
        st.write(f"Systém domů: {st.session_state.get('focused_house') or '—'}")
        st.write(f"Zodiak: {st.session_state.get('focused_zodiac') or '—'}")
        st.write(f"Engine: {st.session_state.get('focused_engine') or '—'}")
        tags = st.session_state.get('focused_tags') or []
        if tags:
            st.caption("Tagy: " + ", ".join(tags))
    
    # Astrolab expandable for time shifting
    with st.expander("Astrolab", expanded=False):
        focused_chart = _get_focused_chart()
        if focused_chart:
            # Get base datetime from focused chart
            base_date = st.session_state.get("focused_date") or datetime.date.today()
            base_time = st.session_state.get("focused_time") or datetime.time(12, 0)
        else:
            base_date = st.session_state.get("crt_date") or datetime.date.today()
            base_time = st.session_state.get("crt_time") or datetime.time(12, 0)
        
        st.markdown("**Posun času**")
        col1, col2, col3 = st.columns(3)
        with col1:
            shift_years = st.number_input("Roky", value=0, step=1, key="astrolab_years")
        with col2:
            shift_months = st.number_input("Měsíce", value=0, step=1, key="astrolab_months")
        with col3:
            shift_days = st.number_input("Dny", value=0, step=1, key="astrolab_days")
        
        col4, col5, col6 = st.columns(3)
        with col4:
            shift_hours = st.number_input("Hodiny", value=0, step=1, key="astrolab_hours")
        with col5:
            shift_minutes = st.number_input("Minuty", value=0, step=1, key="astrolab_minutes")
        with col6:
            shift_seconds = st.number_input("Sekundy", value=0, step=1, key="astrolab_seconds")
        
        if st.button("Aplikovat posun", use_container_width=True, key="astrolab_apply"):
            from datetime import timedelta
            base_dt = datetime.datetime.combine(base_date, base_time)
            shifted_dt = base_dt + timedelta(
                days=shift_years*365 + shift_months*30 + shift_days,
                hours=shift_hours,
                minutes=shift_minutes,
                seconds=shift_seconds
            )
            st.session_state["astrolab_shifted_date"] = shifted_dt.date()
            st.session_state["astrolab_shifted_time"] = shifted_dt.time()
            st.session_state["astrolab_active"] = True
            st.rerun()
        
        if st.session_state.get("astrolab_active"):
            shifted_date = st.session_state.get("astrolab_shifted_date")
            shifted_time = st.session_state.get("astrolab_shifted_time")
            if shifted_date and shifted_time:
                st.info(f"Aktivní posun: {shifted_date} {shifted_time}")
                if st.button("Resetovat", use_container_width=True, key="astrolab_reset"):
                    st.session_state["astrolab_active"] = False
                    st.session_state["astrolab_shifted_date"] = None
                    st.session_state["astrolab_shifted_time"] = None
                    st.rerun()
    
    st.info("Zobrazení horoskopu: pozice se zobrazí automaticky při výběru horoskopu z workspace.")


def _left_aspektarium_menu():
    # Get the name of the currently active horoscope - use same logic as workspace handling
    focused_chart = _get_focused_chart()
    if focused_chart:
        chart_name = _safe_subject_name(focused_chart) or "Aspektárium"
    else:
        chart_name = st.session_state.get("current_person_name") or st.session_state.get("crt_name") or "Aspektárium"
    with st.expander(chart_name, expanded=False):
        # Prefer focused values from selected Workspace chart
        place = st.session_state.get("focused_place") or st.session_state.get("crt_place") or "—"
        # Extra details
        latlon = st.session_state.get("focused_latlon")
        tz = st.session_state.get("focused_tz")
        st.markdown("**Základní nastavení**")
        st.write(f"Lokalita: {place}")
        if latlon or tz:
            lat, lon = (latlon or (None, None))
            st.caption(f"Souřadnice: {lat if lat is not None else '—'}, {lon if lon is not None else '—'} | Časová zóna: {tz or '—'}")
        
        st.markdown("**Konfigurace horoskopu**")
        st.write(f"Režim: {st.session_state.get('focused_mode') or '—'}")
        st.write(f"Systém domů: {st.session_state.get('focused_house') or '—'}")
        st.write(f"Zodiak: {st.session_state.get('focused_zodiac') or '—'}")
        st.write(f"Engine: {st.session_state.get('focused_engine') or '—'}")
        tags = st.session_state.get('focused_tags') or []
        if tags:
            st.caption("Tagy: " + ", ".join(tags))
    
    # Astrolab expandable for time shifting
    with st.expander("Astrolab", expanded=False):
        focused_chart = _get_focused_chart()
        if focused_chart:
            # Get base datetime from focused chart
            base_date = st.session_state.get("focused_date") or datetime.date.today()
            base_time = st.session_state.get("focused_time") or datetime.time(12, 0)
        else:
            base_date = st.session_state.get("crt_date") or datetime.date.today()
            base_time = st.session_state.get("crt_time") or datetime.time(12, 0)
        
        st.markdown("**Posun času**")
        col1, col2, col3 = st.columns(3)
        with col1:
            shift_years = st.number_input("Roky", value=0, step=1, key="astrolab_years_asp")
        with col2:
            shift_months = st.number_input("Měsíce", value=0, step=1, key="astrolab_months_asp")
        with col3:
            shift_days = st.number_input("Dny", value=0, step=1, key="astrolab_days_asp")
        
        col4, col5, col6 = st.columns(3)
        with col4:
            shift_hours = st.number_input("Hodiny", value=0, step=1, key="astrolab_hours_asp")
        with col5:
            shift_minutes = st.number_input("Minuty", value=0, step=1, key="astrolab_minutes_asp")
        with col6:
            shift_seconds = st.number_input("Sekundy", value=0, step=1, key="astrolab_seconds_asp")
        
        if st.button("Aplikovat posun", use_container_width=True, key="astrolab_apply_asp"):
            from datetime import timedelta
            base_dt = datetime.datetime.combine(base_date, base_time)
            shifted_dt = base_dt + timedelta(
                days=shift_years*365 + shift_months*30 + shift_days,
                hours=shift_hours,
                minutes=shift_minutes,
                seconds=shift_seconds
            )
            st.session_state["astrolab_shifted_date"] = shifted_dt.date()
            st.session_state["astrolab_shifted_time"] = shifted_dt.time()
            st.session_state["astrolab_active"] = True
            st.rerun()
        
        if st.session_state.get("astrolab_active"):
            shifted_date = st.session_state.get("astrolab_shifted_date")
            shifted_time = st.session_state.get("astrolab_shifted_time")
            if shifted_date and shifted_time:
                st.info(f"Aktivní posun: {shifted_date} {shifted_time}")
                if st.button("Resetovat", use_container_width=True, key="astrolab_reset_asp"):
                    st.session_state["astrolab_active"] = False
                    st.session_state["astrolab_shifted_date"] = None
                    st.session_state["astrolab_shifted_time"] = None
                    st.rerun()
    
    st.info("Aspektárium: zobrazuje tabulku pozic.")


def _left_interpretation_menu():
    st.markdown("#### Interpretace")
    
    # Interpretation categories and items
    interpretation_items = {
        "Převahy pozitivní": [
            "Převaha modu/kvality znamení",
            "Převaha živlu",
            "Převaha v domech",
            "Převaha aspektů",
        ],
        "Negativní dynamika": [
            "Kvalita znamení",
            "Živlu",
            "V domech",
            "Aspektů",
        ],
        "Rozdělení": [
            "Rozdělení v kvadrantech",
            "Zdůraznění hemisféry",
        ],
        "Symboly a informace": [
            "Sabiánské symboly",
            "Detailní informace o poloze planet (starfisher - rozšířené info)",
        ],
        "Diagramy a konfigurace": [
            "Tvarový diagram horoskopu",
            "Planetární konfigurace",
            "Stellium",
        ],
        "Fáze a pozice": [
            "Lunární fáze",
            "Slunce a Luna (obzor)",
        ],
        "Planety": [
            "Merkur",
            "Venuše",
        ],
        "Osobnost": [
            "Poměr extroverze a introverze",
        ],
        "Ohniskové planety": [
            "Finální dispozitor",
            "Vládce horoskopu",
            "Singlton",
            "Rohová planeta",
            "Polohou",
            "Neaspektované planety (žádné hlavní aspekty)",
            "Obráběcí planeta",
            "Planeta spouštěcí",
            "Planety v kontaktu s abstraktními body horoskopu",
        ],
    }
    
    # Initialize interpretation selection if not exists
    if "interpretation_selection" not in st.session_state:
        st.session_state.interpretation_selection = None
    
    # Render menu items
    for category, items in interpretation_items.items():
        with st.expander(category, expanded=False):
            for item in items:
                if st.button(item, use_container_width=True, key=f"int_{item}"):
                    st.session_state.interpretation_selection = item
                    st.rerun()


def _left_settings_menu():
    st.markdown("#### Nastavení")
    if st.button("General", use_container_width=True, key="set_sec_gen"):
        st.session_state["settings_section"] = "general"
    if st.button("Advanced", use_container_width=True, key="set_sec_adv"):
        st.session_state["settings_section"] = "advanced"


def _run_compute(name, dt, place, engine_choice, eph_path):
    engine = EngineType.JPL if str(engine_choice).startswith("JPL") else None
    eph_override = eph_path if engine == EngineType.JPL else None

    st.session_state["settings"]["chart"] = prepare_horoscope(
        name=name,
        dt=dt,
        loc=Actual(place, t="place").to_model_location(),
        engine=engine,
        ephemeris_path=eph_override,
    )
    horoscope = Subject(name)
    horoscope.at_place(place)
    horoscope.at_time(dt)
    try:
        positions = compute_positions(engine, name, str(dt), place, ephemeris_path=eph_override)
    except Exception as e:
        # Log the error message first (as requested)
        msg = str(e)
        st.error(f"Chyba při výpočtu pozic: {msg}")
        
        # Handle common Skyfield kernel limitations
        # Note: compute_jpl_positions now automatically uses barycenters for Jupiter/Saturn with de421
        if engine == EngineType.JPL and eph_override and "de421" in Path(eph_override).name.lower():
            st.warning("Zvolený soubor efemerid de421.bsp - používá se barycentrum pro Jupiter a Saturn.\n"
                       "Pokud stále selhává, doporučeno: použijte de440s.bsp nebo přepněte engine na Kerykeion ve 'Nastavení > Advanced'.")
            # Fallback to Kerykeion if JPL still fails even with barycenters
            st.info("Přepínám na výchozí engine (Kerykeion).")
            engine = None
            positions = compute_positions(engine, name, str(dt), place, ephemeris_path=None)
        else:
            raise
    fig = build_radix_figure(positions)
    return horoscope, fig


def _update_people_list_from_workspace(ws):
    """Update the people list in session state from workspace charts and session charts."""
    try:
        names = []
        # Add workspace charts
        if ws and ws.charts:
            for c in ws.charts:
                nm = _safe_subject_name(c)
                if nm:
                    names.append(nm)
        # Add session charts
        session_charts = st.session_state.get('session_charts', [])
        for c in session_charts:
            nm = _safe_subject_name(c)
            if nm and nm not in names:  # Avoid duplicates
                names.append(nm)
    except Exception:
        names = []
    st.session_state.people = names
    return names


def _open_view_center():
    # Search row [Search ...][Import Chart (YAML)]
    # st.subheader("Otevřít horoskop")
    sc1, sc2 = st.columns([4,1])
    with sc1:
        st.text_input('Search...', key='open_search')
    with sc2:
        uploaded_yaml = st.file_uploader('Import Chart (YAML)', type=["yml", "yaml"], key="open_import")

    if uploaded_yaml is not None:
        try:
            data = parse_yaml_content(uploaded_yaml.read()) or {}
            # Use the proper parser that handles all type conversions and nested objects
            ch = parse_chart_yaml(data)
            if st.session_state.get('workspace') is None:
                st.warning('Nejprve načtěte workspace, aby bylo kam importovat.')
            else:
                base_dir = str(Path(st.session_state.workspace_manifest).parent)
                add_or_update_chart(st.session_state.workspace, ch, base_dir=base_dir)
                # Update people list after import
                _update_people_list_from_workspace(st.session_state.workspace)
                st.success('Chart importován do workspace.')
                # Trigger rerun to refresh the UI
                st.rerun()
        except Exception as e:
            st.error(f"Import selhal: {e}")

    # Get fresh workspace reference (may have been updated by import)
    ws = st.session_state.get("workspace")
    # List rows from workspace
    rows = list_open_view_rows(ws) if ws else []
    
    # Also add session charts (created without workspace)
    session_charts = st.session_state.get('session_charts', [])
    for ch in session_charts:
        try:
            subj = _safe_get(ch, 'subject')
            loc = _safe_get(subj, 'location') if subj else None
            name = _safe_subject_name(ch) or ''
            if not name:
                continue
            # Check if already in rows (avoid duplicates)
            if any(r.get('name') == name for r in rows):
                continue
            
            # Get chart type from config
            cfg = _safe_get(ch, 'config')
            chart_type = ''
            if cfg:
                mode = _safe_get(cfg, 'mode')
                if mode:
                    chart_type = str(mode) if hasattr(mode, 'value') else str(mode)
            
            event_time = _safe_event_dt(ch)
            event_time_str = str(event_time) if event_time else ''
            locd = _safe_subject_location(ch) or {}
            location_name = locd.get('name', '') if locd else ''
            tags_list = _safe_get(ch, 'tags') or []
            tags = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list)
            search_text = f"{name} {chart_type} {event_time_str} {location_name} {tags}".lower()
            rows.append({
                'name': name,
                'chart_type': chart_type,
                'event_time': event_time_str,
                'location': location_name,
                'tags': tags,
                'search_text': search_text,
            })
        except Exception:
            continue
    
    # Filter by search query
    q = (st.session_state.get('open_search') or '').strip().lower()
    if q:
        rows = [r for r in rows if q in (r.get('search_text','').lower())]

    # Header
    hc1, hc2, hc3, hc4, hc5 = st.columns([2,1.5,2,1.5,2])
    with hc1: st.markdown("**Name**")
    with hc2: st.markdown("**Type**")
    with hc3: st.markdown("**Event time**")
    with hc4: st.markdown("**Location**")
    with hc5: st.markdown("**Tags**")

    # Rows
    for info in rows:
        name = info.get('name','-')
        chart_type = info.get('chart_type','-')
        event_time = info.get('event_time','')
        location_name = info.get('location','')
        tags = info.get('tags','')
        c1, c2, c3, c4, c5 = st.columns([2,1.5,2,1.5,2])
        with c1:
            if st.button(name or '-', key=f"open_row_{name}"):
                _focus_chart_by_name(name)
                st.rerun()  # Trigger rerun to update UI with focused chart
        with c2:
            st.write(chart_type)
        with c3:
            st.write(event_time)
        with c4:
            st.write(location_name)
        with c5:
            st.write(tags)


def _open_workspace_center():
    st.subheader("Otevřít workspace")
    base_dir = st.text_input("Složka workspace (obsahuje workspace.yaml)", key="ws_folder")
    if st.button("Načíst ze složky", use_container_width=True, key="btn_load_folder"):
        try:
            if not base_dir:
                st.warning("Zadejte cestu ke složce")
            else:
                # Validate and resolve path to prevent path traversal attacks
                try:
                    base_path = Path(base_dir).resolve()
                    # Ensure path is absolute and properly resolved (resolve() normalizes and removes ..)
                    if not base_path.is_absolute():
                        raise ValueError("Invalid path: must be an absolute path")
                    # Additional check: ensure resolved path doesn't contain parent directory references
                    if ".." in base_path.parts:
                        raise ValueError("Invalid path: path traversal detected")
                    manifest = base_path / "workspace.yaml"
                except (ValueError, OSError) as e:
                    st.error(f"Neplatná cesta: {e}")
                    return
                
                if not manifest.is_file():
                    st.error("Soubor workspace.yaml ve složce nenalezen")
                else:
                    # Full folder available: do full scan/import
                    report = _load_workspace_and_sync(str(manifest), scan_and_import=True)
                    st.success("Workspace načten a synchronizován.")
                    _render_ws_report(report)
        except Exception as e:
            st.error(f"Nelze načíst workspace: {e}")


def _load_workspace_and_sync(manifest_path: str, scan_and_import: bool = True) -> dict:
    """Load workspace.yaml, optionally scan/import new charts/subjects from disk, save, and populate session lists. Returns a report dict."""
    base_dir = str(Path(manifest_path).parent)
    ws = load_workspace(manifest_path)
    changes = {'charts': {'new_on_disk': [], 'missing_on_disk': []}, 'subjects': {'new_on_disk': [], 'missing_on_disk': []}}
    imported = 0
    if scan_and_import:
        try:
            changes = scan_workspace_changes(base_dir)
        except Exception:
            changes = {'charts': {'new_on_disk': [], 'missing_on_disk': []}, 'subjects': {'new_on_disk': [], 'missing_on_disk': []}}
        # Import new charts
        try:
            for fname in (changes.get('charts', {}).get('new_on_disk', []) or []):
                path = str(Path(base_dir) / 'charts' / fname)
                try:
                    chart = import_chart_yaml(path)
                    add_or_update_chart(ws, chart, base_dir=base_dir)
                    imported += 1
                except Exception:
                    continue
        except Exception:
            pass
        # Import new subjects
        try:
            for fname in (changes.get('subjects', {}).get('new_on_disk', []) or []):
                path = str(Path(base_dir) / 'subjects' / fname)
                try:
                    data = read_yaml_file(path)
                    subj = ChartSubject(**data) if isinstance(data, dict) else None
                    if subj is not None:
                        add_subject(ws, subj, base_dir=base_dir)
                        imported += 1
                except Exception:
                    continue
        except Exception:
            pass
        if imported:
            try:
                save_workspace_modular(ws, base_dir)
            except Exception:
                pass
    # Update session
    st.session_state.workspace = ws
    # Build list of chart names for footer selector (workspace + session charts)
    try:
        names = []
        # Add workspace charts
        for c in (ws.charts or []):
            nm = _safe_subject_name(c)
            if nm:
                names.append(nm)
        # Add session charts (created without workspace)
        session_charts = st.session_state.get('session_charts', [])
        for c in session_charts:
            nm = _safe_subject_name(c)
            if nm and nm not in names:  # Avoid duplicates
                names.append(nm)
    except Exception:
        names = []
    st.session_state.people = names
    if names:
        st.session_state.current_person_name = names[0]
        # Initialize focused chart display fields based on the first chart
        try:
            first = next((c for c in (ws.charts or []) if _safe_subject_name(c) == names[0]), None)
            if first:
                locd = _safe_subject_location(first) or {}
                st.session_state.focused_place = locd.get('name')
                st.session_state.focused_latlon = (locd.get('lat'), locd.get('lon'))
                st.session_state.focused_tz = locd.get('tz')
                dtv = _safe_event_dt(first)
                if dtv is not None:
                    try:
                        st.session_state.focused_date = dtv.date()
                        st.session_state.focused_time = dtv.time()
                    except Exception:
                        st.session_state.focused_date = None
                        st.session_state.focused_time = None
                cfg = _safe_config(first)
                st.session_state.focused_mode = cfg.get('mode')
                st.session_state.focused_house = cfg.get('house')
                st.session_state.focused_zodiac = cfg.get('zodiac')
                st.session_state.focused_engine = cfg.get('engine')
                # tags can be list or missing
                tags_val = _safe_get(first, 'tags') or _safe_get(first, 'tags', 'tags', []) or []
                st.session_state.focused_tags = list(tags_val or [])
        except Exception:
            pass
        # Keep crt_name in sync if not managed by widget at this time
        try:
            if 'crt_name' in st.session_state and not st.session_state.get('crt_name'):
                st.session_state.crt_name = names[0]
        except Exception:
            pass
    # Build a report
    report = {
        'base_dir': base_dir,
        'charts_total': len(getattr(ws, 'charts', []) or []),
        'subjects_total': len(getattr(ws, 'subjects', []) or []),
        'imported_new_items': imported,
        'changes': changes,
        'scan_and_import': bool(scan_and_import),
    }
    st.session_state['workspace_report'] = report
    return report


def _render_ws_report(report: dict | None):
    if not report:
        return
    st.markdown("#### Report")
    st.write(f"Složka: {report.get('base_dir','')}")
    st.write(f"Počet horoskopů: {report.get('charts_total',0)}")
    st.write(f"Počet subjektů: {report.get('subjects_total',0)}")
    changes = report.get('changes', {}) or {}
    ch_new = changes.get('charts', {}).get('new_on_disk', [])
    ch_missing = changes.get('charts', {}).get('missing_on_disk', [])
    sb_new = changes.get('subjects', {}).get('new_on_disk', [])
    sb_missing = changes.get('subjects', {}).get('missing_on_disk', [])
    if ch_new or sb_new:
        st.info(f"Nově importováno: {report.get('imported_new_items',0)} (charts: {len(ch_new)}, subjects: {len(sb_new)})")
    if ch_missing or sb_missing:
        st.warning(f"Chybějící položky - charts: {len(ch_missing)}, subjects: {len(sb_missing)}")


def _get_focused_chart():
    """Get the currently focused chart from workspace or session charts, or None if not found."""
    current_name = st.session_state.get('current_person_name')
    if not current_name:
        return None
    
    # First check workspace
    ws = st.session_state.get('workspace')
    if ws and ws.charts:
        for ch in ws.charts:
            try:
                subj_name = _safe_subject_name(ch)
                cid = _safe_get(ch, 'id') or _safe_get(ch, 'id', 'id')
                if subj_name == current_name or cid == current_name:
                    return ch
            except Exception:
                continue
    
    # Then check session charts (created without workspace)
    session_charts = st.session_state.get('session_charts', [])
    for ch in session_charts:
        try:
            subj_name = _safe_subject_name(ch)
            cid = _safe_get(ch, 'id') or _safe_get(ch, 'id', 'id')
            if subj_name == current_name or cid == current_name:
                return ch
        except Exception:
            continue
    
    return None


def _focus_chart_by_name(name: str):
    """Focus an existing chart in workspace or session charts by subject name/id, update session context."""
    found = None
    
    # First check workspace
    ws = st.session_state.get('workspace')
    if ws and ws.charts:
        for ch in ws.charts:
            try:
                subj_name = _safe_subject_name(ch)
                cid = _safe_get(ch, 'id') or _safe_get(ch, 'id', 'id')
                if subj_name == name or cid == name:
                    found = ch
                    break
            except Exception:
                continue
    
    # Then check session charts
    if not found:
        session_charts = st.session_state.get('session_charts', [])
        for ch in session_charts:
            try:
                subj_name = _safe_subject_name(ch)
                cid = _safe_get(ch, 'id') or _safe_get(ch, 'id', 'id')
                if subj_name == name or cid == name:
                    found = ch
                    break
            except Exception:
                continue
    
    if not found:
        return
    
    st.session_state.current_person_name = _safe_subject_name(found) or name
    # Update focused chart display fields (safe keys)
    try:
        locd = _safe_subject_location(found) or {}
        st.session_state.focused_place = locd.get('name')
        st.session_state.focused_latlon = (locd.get('lat'), locd.get('lon'))
        st.session_state.focused_tz = locd.get('tz')
        dtv = _safe_event_dt(found)
        if dtv is not None:
            try:
                st.session_state.focused_date = dtv.date()
                st.session_state.focused_time = dtv.time()
            except Exception:
                st.session_state.focused_date = None
                st.session_state.focused_time = None
        cfg = _safe_config(found)
        st.session_state.focused_mode = cfg.get('mode')
        st.session_state.focused_house = cfg.get('house')
        st.session_state.focused_zodiac = cfg.get('zodiac')
        st.session_state.focused_engine = cfg.get('engine')
        tags_val = _safe_get(found, 'tags') or _safe_get(found, 'tags', 'tags', []) or []
        st.session_state.focused_tags = list(tags_val or [])
    except Exception:
        pass
    # Sync non-widget value for compute defaults
    try:
        if 'crt_name' in st.session_state and not st.session_state.get('crt_name'):
            st.session_state.crt_name = st.session_state.current_person_name
    except Exception:
        pass


def _render_footer_selector():
    """Render a footer-like selector for charts in workspace or session charts."""
    st.markdown("---")
    # Get names from both workspace and session charts
    names = st.session_state.get('people') or []
    
    # If no workspace charts, check session charts
    if not names:
        session_charts = st.session_state.get('session_charts', [])
        names = [(_safe_subject_name(c) or '') for c in session_charts if _safe_subject_name(c)]
        st.session_state.people = names
    
    if not names:
        st.caption("Žádné horoskopy. Vytvořte nový horoskop nebo otevřete workspace.")
        return
    
    default = st.session_state.get('current_person_name') or names[0]
    
    # Create buttons in a single row spanning full width
    st.markdown("**Vyberte horoskop:**")
    # Create columns for each chart name
    cols = st.columns(len(names))
    chosen = None
    for i, name in enumerate(names):
        with cols[i]:
            # Highlight the current selection
            is_selected = (name == default)
            button_type = "primary" if is_selected else "secondary"
            if st.button(name, use_container_width=True, key=f"footer_btn_{name}", type=button_type):
                chosen = name
    
    # Handle selection change
    if chosen and chosen != st.session_state.get('current_person_name'):
        _focus_chart_by_name(chosen)
        st.rerun()  # Trigger rerun to update UI with new chart


def _render_initial_dialog():
    """Render the initial dialog shown on first load."""
    st.title("Vítejte v Kefer Astrology")
    st.markdown("---")
    
    # Two column layout
    c_left, c_center = st.columns([1, 5])
    
    with c_left:
        _left_initial_dialog_menu()
    
    with c_center:
        section = st.session_state.get("initial_dialog_section", "Jazyk")
        
        if section == "Jazyk":
            st.subheader("Jazyk")
            lang_options = ["Čeština", "English", "Deutsch"]
            selected_lang = st.selectbox("Vyberte jazyk", lang_options, key="init_lang")
            st.session_state["settings"]["language"] = selected_lang
        
        elif section == "Lokace":
            st.subheader("Lokace")
            default_location = st.text_input("Výchozí lokalita", value="Prague", key="init_location")
            st.session_state["ws_default_loc"] = default_location
        
        elif section == "Systém domů":
            st.subheader("Systém domů")
            house_systems = [
                "Placidus", "Whole Sign", "Campanus", "Koch", "Equal",
                "Regiomontanus", "Vehlow", "Porphyry", "Alcabitius"
            ]
            selected_house = st.selectbox("Výchozí systém domů", house_systems, key="init_house")
            st.session_state["ws_house_sys"] = selected_house
        
        elif section == "Nastavení aspektů":
            st.subheader("Nastavení aspektů")
            aspects_input = st.text_input("Výchozí aspekty (čárkou oddělené)", value="0,60,90,120,180", key="init_aspects")
            st.session_state["ws_aspects"] = aspects_input
        
        elif section == "Vzhled":
            st.subheader("Vzhled")
            color_theme = st.selectbox("Barvy (téma)", ["default", "dark", "light"], key="init_theme")
            st.session_state["ws_color_theme"] = color_theme
        
        elif section == "Výpočetní engine":
            st.subheader("Výpočetní engine")
            engine_options = ["JPL / Skyfield", "Kerykeion / swisseph"]
            selected_engine = st.selectbox("Výchozí výpočetní engine", engine_options, key="init_engine")
            if selected_engine == "JPL / Skyfield":
                st.session_state["ws_default_engine"] = EngineType.JPL
            else:
                st.session_state["ws_default_engine"] = EngineType.SWISSEPH
        
        elif section == "Manuál":
            st.subheader("Manuál")
            st.info("Dokumentace a návod k použití bude přidán později.")
        
        # Workspace loading section (moved from open_workspace)
        st.markdown("---")
        st.subheader("Otevřít workspace")
        base_dir = st.text_input("Složka workspace (obsahuje workspace.yaml)", key="init_ws_folder")
        if st.button("Načíst ze složky", use_container_width=True, key="init_btn_load_folder"):
            try:
                if not base_dir:
                    st.warning("Zadejte cestu ke složce")
                else:
                    # Validate and resolve path to prevent path traversal attacks
                    try:
                        base_path = Path(base_dir).resolve()
                        # Check for path traversal attempts (should not contain .. after resolution)
                        if ".." in str(base_path) or not base_path.is_absolute():
                            raise ValueError("Invalid path: path traversal detected")
                        manifest = base_path / "workspace.yaml"
                    except (ValueError, OSError) as e:
                        st.error(f"Neplatná cesta: {e}")
                        return
                    
                    if not manifest.is_file():
                        st.error("Soubor workspace.yaml ve složce nenalezen")
                    else:
                        # Full folder available: do full scan/import
                        report = _load_workspace_and_sync(str(manifest), scan_and_import=True)
                        st.success("Workspace načten a synchronizován.")
                        _render_ws_report(report)
            except Exception as e:
                st.error(f"Nelze načíst workspace: {e}")
        
        # Proceed button
        st.markdown("---")
        if st.button("Pokračovat", use_container_width=True, type="primary", key="init_proceed"):
            st.session_state.initial_dialog_completed = True
            st.rerun()


def main():
    # -----------------------------
    # 1) Initial settings / session
    # -----------------------------
    _ensure_session_defaults()

    lang = change_language(default="cz")

    # -----------------------------
    # 2) Page config (hide Streamlit sidebar impact)
    # -----------------------------
    st.set_page_config(
        page_title="Kefer Astrology",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # -----------------------------
    # 2.5) Check if initial dialog should be shown
    # -----------------------------
    if not st.session_state.get("initial_dialog_completed", False):
        _render_initial_dialog()
        return

    # -----------------------------
    # 3) Top SPA toolbar
    # -----------------------------
    render_toolbar()

    # -----------------------------
    # Layout
    # -----------------------------
    mode = st.session_state.mode
    layout_kind, weights = LAYOUTS[mode]

    if layout_kind == "two":
        c_left, c_center = st.columns(weights)
    else:
        # Fallback, but we won't use a 3rd column; treat as two
        c_left, c_center = st.columns(weights[:2])

    # -----------------------------
    # LEFT PANEL per mode
    # -----------------------------
    with c_left:
        if mode == "create":
            _left_create_menu()
        elif mode == "open":
            _left_open_menu()
        elif mode == "save":
            _left_save_menu()
        elif mode == "export":
            _left_export_menu()
        elif mode == "chart":
            _left_chart_menu()
        elif mode == "aspektarium":
            _left_aspektarium_menu()
        elif mode == "interpretation":
            _left_interpretation_menu()
        elif mode == "notes":
            _left_notes_menu()
        elif mode == "settings":
            _left_settings_menu()
        else:
            st.empty()

    # Helper defaults for compute
    engine_choice = st.session_state.get('settings_engine', "JPL / Skyfield (local de421.bsp)")
    eph_path = st.session_state.get('settings_eph', default_ephemeris_path())

    # -----------------------------
    # RIGHT / CENTER per mode
    # -----------------------------
    if layout_kind == "two":
        # Render all main content in the center column; no separate right column is used.
        with c_center:
            if mode == "save":
                name_val = st.text_input("Jméno", key="save_name", value=st.session_state.get("crt_name", ""))
                # Format is selected in left menu
                save_format = st.session_state.get("save_export_type", "YAML")
                st.markdown(f"**Vybraný formát:** {save_format}")
                st.markdown("#### Cílová cesta")
                st.text_input("Cesta a název souboru", key="save_dest_path")
                if st.button("Uložit", use_container_width=True, key="do_save"):
                    st.success(f"Export ({save_format}) připraven do: {st.session_state.get('save_dest_path')}")

            elif mode == "export":
                export_title = st.session_state.get("current_person_name") or ""
                focused_chart = _get_focused_chart()
                if not focused_chart:
                    st.warning("Vyberte horoskop pro export.")
                else:
                    # Get export format from left menu (synced via session state)
                    export_format = st.session_state.get("export_format", "Print")
                    
                    st.markdown("**Zahrnout do exportu:**")
                    
                    # Checkboxes for what to include
                    include_name = st.checkbox("Název a údaje o Horoskopu", value=True, key="export_name")
                    include_chart = st.checkbox("Horoskop", value=True, key="export_chart")
                    include_location = st.checkbox("Poloha", value=True, key="export_location")
                    include_aspektarium = st.checkbox("Aspektárium", value=True, key="export_aspektarium")
                    include_info = st.checkbox("Info", value=True, key="export_info")
                    
                    st.markdown("---")
                    if st.button("Exportovat", use_container_width=True, type="primary", key="do_export"):
                        # TODO: Implement actual export functionality
                        st.success(f"Export ({export_format}) připraven. Funkcionalita exportu bude implementována.")
                        if include_name:
                            st.info("Zahrnuto: Název a údaje o Horoskopu")
                        if include_chart:
                            st.info("Zahrnuto: Horoskop")
                        if include_location:
                            st.info("Zahrnuto: Poloha")
                        if include_aspektarium:
                            st.info("Zahrnuto: Aspektárium")
                        if include_info:
                            st.info("Zahrnuto: Info")

            elif mode == "notes":
                focused_chart = _get_focused_chart()
                chart_name = st.session_state.get("current_person_name") or "Obecné"
                
                # Get or create annotation
                ws = st.session_state.get('workspace')
                selected_note_title = st.session_state.get("selected_note")
                editing_note = st.session_state.get("editing_note", False)
                
                # Note title input
                note_title = st.text_input(
                    "Název poznámky",
                    value=selected_note_title or f"Poznámka - {chart_name}",
                    key="note_title_input"
                )
                
                # Markdown editor
                note_content = ""
                if selected_note_title:
                    # Load existing note from workspace
                    if ws and ws.annotations:
                        for ann in ws.annotations:
                            if ann.title == selected_note_title:
                                note_content = ann.content
                                break
                    # Also check session annotations
                    if not note_content:
                        session_anns = st.session_state.get('session_annotations', [])
                        for ann in session_anns:
                            if ann.title == selected_note_title:
                                note_content = ann.content
                                break
                
                # Use streamlit's text_area for markdown editing (basic)
                # For a full markdown editor, you might want to use a custom component
                note_content = st.text_area(
                    "Obsah poznámky (Markdown)",
                    value=note_content,
                    height=400,
                    key="note_content_editor"
                )
                
                # Preview
                if note_content:
                    st.markdown("---")
                    st.markdown("**Náhled:**")
                    st.markdown(note_content)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Uložit poznámku", use_container_width=True, key="save_note"):
                        if note_title and note_content:
                            
                            # Create or update annotation
                            ann = Annotation(
                                title=note_title,
                                content=note_content,
                                created=now_utc(),
                                author="user"  # TODO: Get actual user
                            )
                            
                            if ws:
                                # Update workspace annotations
                                if not ws.annotations:
                                    ws.annotations = []
                                # Remove existing annotation with same title
                                ws.annotations = [a for a in ws.annotations if a.title != note_title]
                                ws.annotations.append(ann)
                                
                                # Save workspace if manifest exists
                                if st.session_state.get('workspace_manifest'):
                                    try:
                                        base_dir = str(Path(st.session_state.workspace_manifest).parent)
                                        save_workspace_modular(ws, base_dir)
                                        st.success(f"Poznámka '{note_title}' uložena do workspace.")
                                    except Exception as e:
                                        st.error(f"Chyba při ukládání: {e}")
                                else:
                                    st.info("Poznámka uložena v session. Otevřete workspace pro trvalé uložení.")
                            else:
                                # Store in session state
                                if "session_annotations" not in st.session_state:
                                    st.session_state.session_annotations = []
                                session_anns = st.session_state.session_annotations
                                session_anns = [a for a in session_anns if a.title != note_title]
                                session_anns.append(ann)
                                st.session_state.session_annotations = session_anns
                                st.success(f"Poznámka '{note_title}' uložena v session.")
                            
                            st.session_state["selected_note"] = note_title
                            st.session_state["editing_note"] = False
                            st.rerun()
                        else:
                            st.warning("Vyplňte název a obsah poznámky.")
                
                with col2:
                    if st.button("❌ Zrušit", use_container_width=True, key="cancel_note"):
                        st.session_state["selected_note"] = None
                        st.session_state["editing_note"] = False
                        st.rerun()

            elif mode == "settings":
                st.subheader("Aplikační nastavení")
                section = st.session_state.get("settings_section", "general")
                if section == "general":
                    st.checkbox("Dark mode", key="opt_dark")
                    st.slider("Velikost písma", 10, 28, 14, key="opt_font")
                    st.selectbox("Téma", ["Classic", "Minimal", "Material"], key="opt_theme")
                    st.markdown("---")
                    st.text_input("Preferovaný jazyk", key="ws_pref_lang")
                    st.text_input("Výchozí lokalita (text)", key="ws_default_loc")
                    st.selectbox("Výchozí systém domů", [
                        "Placidus", "Whole Sign", "Campanus", "Koch", "Equal",
                        "Regiomontanus", "Vehlow", "Porphyry", "Alcabitius"
                    ], key="ws_house_sys")
                    st.text_input("Výchozí aspekty (čárkou)", key="ws_aspects")
                    st.selectbox("Barvy (téma)", ["default", "dark", "light"], key="ws_color_theme")
                    st.selectbox("Výchozí engine", ["JPL", "swisseph", "jyotish", "custom"], key="ws_default_engine")
                else:
                    st.markdown("#### Efemeridy")
                    st.selectbox(
                        "Ephemeris Engine",
                        ["Kerykeion (default)", "JPL / Skyfield (local de421.bsp)"],
                        index=1,
                        key="settings_engine"
                    )
                    st.text_input(
                        "Ephemeris file (de421.bsp)",
                        value=st.session_state.get('settings_eph', default_ephemeris_path()),
                        disabled=not st.session_state['settings_engine'].startswith("JPL"),
                        key="settings_eph"
                    )
                    # Warn users when de421 is selected due to limited body coverage
                    eph_sel = st.session_state.get('settings_eph', '') or ''
                    if isinstance(eph_sel, str) and 'de421' in Path(eph_sel).name.lower():
                        st.info("Poznámka: de421.bsp neobsahuje centra vnějších planet (JUPITER, SATURN, …).\n"
                                "Pro plnou podporu použijte de440s.bsp nebo přepněte engine na Kerykeion.")
                st.success("Nastavení připraveno.")

    if mode == "create":
        with c_center:
            # Name is on the left; reuse st.session_state.crt_name
            horoscope_name = st.text_input("Jméno", key="crt_name", value=st.session_state.get("crt_name", ""))
            # Row 2: Čas / Datum in one row
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                input_time = st.time_input("Čas", key="crt_time", value=datetime.time(12, 0))
            with r2c2:
                input_date = st.date_input("Datum", key="crt_date", value=datetime.date.today())
            # Row 3: Lokalita
            input_location = st.text_input("Lokalita", key="crt_place", value="Prague")
            # Row 4: Tags
            st.text_input("Tagy (čárkou oddělené)", key="crt_tags")
            # Expandable section under rows
            with st.expander("Pokročilé volby", expanded=False):
                st.caption("Zde budou další pokročilé možnosti…")
            if st.button("Vypočítat a zobrazit", use_container_width=True, type="primary", key="crt_run"):
                dt_combined = combine_date_time(input_date, input_time)
                horoscope, fig = _run_compute(horoscope_name, dt_combined, input_location, engine_choice, eph_path)
                
                # Show table with all kerykeion point data (not just positions)
                kerykeion_df = extract_kerykeion_points(horoscope.computed)
                if not kerykeion_df.empty:
                    st.table(kerykeion_df)
                
                # Add chart to workspace if workspace is loaded
                ws = st.session_state.get('workspace')
                if ws:
                    try:
                        from services import build_chart_instance
                        # Get chart type and tags
                        chart_type = st.session_state.get('chart_type', ChartMode.NATAL.value)
                        tags_str = st.session_state.get('crt_tags', '')
                        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
                        
                        # Build ChartInstance
                        dt_str = ensure_aware(dt_combined, Actual(input_location, t="loc").tz).isoformat()
                        # Determine engine from session state
                        use_jpl = str(engine_choice).startswith("JPL")
                        chart = build_chart_instance(
                            name=horoscope_name,
                            dt_str=dt_str,
                            loc_text=input_location,
                            mode=chart_type,
                            ws=ws,
                            ephemeris_path=eph_path if use_jpl else None
                        )
                        # Ensure engine is set correctly if ephemeris_path is provided
                        if use_jpl and chart.config.engine is None:
                            chart.config.engine = EngineType.JPL
                        # Add tags if any
                        if tags:
                            chart.tags = tags
                        
                        # Add to workspace
                        base_dir = str(Path(st.session_state.workspace_manifest).parent)
                        add_or_update_chart(ws, chart, base_dir=base_dir)
                        _update_people_list_from_workspace(ws)
                        
                        # Focus on the new chart
                        st.session_state.current_person_name = horoscope_name
                        _focus_chart_by_name(horoscope_name)
                        
                        st.success(f"Horoskop '{horoscope_name}' přidán do workspace. Přepněte na sekci 'Horoskop' pro zobrazení grafu.")
                        
                        # Switch to chart view automatically
                        st.session_state.mode = "chart"
                        st.rerun()
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"Chyba při přidávání do workspace: {e}")
                        with st.expander("Detaily chyby", expanded=False):
                            st.code(error_details)
                else:
                    # No workspace: store chart in session state
                    # But create a temporary workspace-like object with defaults from initial dialog
                    try:
                        from services import build_chart_instance
                        # EngineType is already imported at module level, don't re-import
                        from models import Workspace, EphemerisSource, WorkspaceDefaults, HouseSystem
                        
                        # Get chart type and tags
                        chart_type = st.session_state.get('chart_type', ChartMode.NATAL.value)
                        tags_str = st.session_state.get('crt_tags', '')
                        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
                        
                        # Create a temporary workspace with defaults from initial dialog
                        temp_ws = None
                        if st.session_state.get('ws_default_engine') or st.session_state.get('ws_default_loc') or st.session_state.get('ws_house_sys'):
                            # Build ephemeris source
                            engine = st.session_state.get('ws_default_engine', EngineType.SWISSEPH)
                            eph_source = EphemerisSource(
                                backend=engine.value if isinstance(engine, EngineType) else str(engine),
                                name=None
                            )
                            
                            # Build workspace defaults
                            house_sys_str = st.session_state.get('ws_house_sys', 'Placidus')
                            house_sys = None
                            try:
                                house_sys = HouseSystem[house_sys_str.upper().replace(' ', '_')]
                            except:
                                house_sys = HouseSystem.PLACIDUS
                            
                            ws_defaults = WorkspaceDefaults(
                                ephemeris_engine=engine if isinstance(engine, EngineType) else EngineType.SWISSEPH,
                                ephemeris_backend=None,
                                location_name=st.session_state.get('ws_default_loc', 'Prague'),
                                location_latitude=None,
                                location_longitude=None,
                                timezone=None,
                                language=st.session_state.get('settings', {}).get('language', 'cs'),
                                theme=st.session_state.get('ws_color_theme', 'default'),
                                default_house_system=house_sys,
                                default_bodies=None,
                                default_aspects=None,
                                observable_objects=None,
                                aspect_settings=None
                            )
                            
                            temp_ws = Workspace(
                                owner="session",
                                default_ephemeris=eph_source,
                                active_model="western",
                                chart_presets=[],
                                subjects=[],
                                charts=[],
                                layouts=[],
                                annotations=[],
                                default=ws_defaults
                            )
                        
                        # Build ChartInstance with temporary workspace defaults
                        dt_str = ensure_aware(dt_combined, Actual(input_location, t="loc").tz).isoformat()
                        # Determine engine from session state
                        use_jpl = str(engine_choice).startswith("JPL")
                        chart = build_chart_instance(
                            name=horoscope_name,
                            dt_str=dt_str,
                            loc_text=input_location,
                            mode=chart_type,
                            ws=temp_ws,  # Use temp workspace with defaults
                            ephemeris_path=eph_path if use_jpl else None
                        )
                        # Ensure engine is set correctly if ephemeris_path is provided
                        if use_jpl and chart.config.engine is None:
                            chart.config.engine = EngineType.JPL
                        # Add tags if any
                        if tags:
                            chart.tags = tags
                        
                        # Store in session state
                        session_charts = st.session_state.get('session_charts', [])
                        # Remove existing chart with same name if present
                        session_charts = [c for c in session_charts if _safe_subject_name(c) != horoscope_name]
                        session_charts.append(chart)
                        st.session_state.session_charts = session_charts
                        
                        # Update people list (include both workspace and session charts)
                        _update_people_list_from_workspace(None)  # Will get session charts from state
                        
                        # Focus on the new chart
                        st.session_state.current_person_name = horoscope_name
                        _focus_chart_by_name(horoscope_name)
                        
                        st.success(f"Horoskop '{horoscope_name}' uložen v session.")
                        
                        # Switch to chart view
                        st.session_state.mode = "chart"
                        st.rerun()
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"Chyba při ukládání horoskopu: {e}")
                        with st.expander("Detaily chyby", expanded=False):
                            st.code(error_details)

    elif mode == "open":
        with c_center:
            _open_view_center()

    elif mode == "chart":
        with c_center:
            # Automatically compute positions from focused chart if workspace is loaded
            focused_chart = _get_focused_chart()
            if focused_chart:
                # Check if Astrolab shift is active
                astrolab_active = st.session_state.get("astrolab_active", False)
                shifted_date = st.session_state.get("astrolab_shifted_date")
                shifted_time = st.session_state.get("astrolab_shifted_time")
                
                if astrolab_active and shifted_date and shifted_time:
                    # Compute with shifted datetime
                    try:
                        name = _safe_subject_name(focused_chart) or 'Radix'
                        place_obj = _safe_subject_location(focused_chart) or {}
                        place = place_obj.get('name') or 'Prague'
                        dtc = combine_date_time(shifted_date, shifted_time)
                        engine_choice = st.session_state.get('settings_engine', engine_choice)
                        eph_path = st.session_state.get('settings_eph', eph_path)
                        horoscope, fig = _run_compute(name, dtc, place, engine_choice, eph_path)
                        # Use a unique key to prevent caching issues
                        chart_key = f"chart_shifted_{name}_{engine_choice}_{dtc}"
                        st.plotly_chart(fig, use_container_width=True, key=chart_key)
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"Chyba při výpočtu pozic: {e}")
                        with st.expander("Detaily chyby", expanded=False):
                            st.code(error_details)
                else:
                    # Normal chart display without shift
                    # Normal chart display without shift
                    try:
                        from services import build_radix_figure_for_chart
                        # Use session state engine if available, otherwise use chart's stored engine
                        engine_override = None
                        eph_override = None
                        # Check both settings_engine and ws_default_engine
                        engine_choice_val = st.session_state.get('settings_engine') or st.session_state.get('ws_default_engine')
                        if engine_choice_val:
                            if isinstance(engine_choice_val, EngineType):
                                engine_override = engine_choice_val
                            elif str(engine_choice_val).startswith("JPL"):
                                engine_override = EngineType.JPL
                            else:
                                engine_override = EngineType.SWISSEPH
                            eph_override = st.session_state.get('settings_eph', eph_path) if engine_override == EngineType.JPL else None
                        else:
                            # If no override, use chart's stored engine
                            cfg = _safe_get(focused_chart, 'config')
                            if cfg:
                                stored_engine = _safe_get(cfg, 'engine')
                                if stored_engine:
                                    engine_override = stored_engine
                        
                        ws = st.session_state.get('workspace')
                        # Recompute positions to ensure we have fresh data
                        from services import compute_positions_for_chart
                        positions = compute_positions_for_chart(focused_chart, ws=ws)
                        if not positions:
                            st.warning("⚠️ Nepodařilo se vypočítat pozice pro vybraný horoskop. Zkontrolujte nastavení engine a data horoskopu.")
                            with st.expander("Debug informace", expanded=False):
                                st.write(f"Chart: {focused_chart}")
                                st.write(f"Subject: {_safe_get(focused_chart, 'subject')}")
                                st.write(f"Location: {_safe_subject_location(focused_chart)}")
                                st.write(f"Event time: {_safe_event_dt(focused_chart)}")
                                st.write(f"Engine override: {engine_override}")
                                st.write(f"Ephemeris override: {eph_override}")
                        else:
                            fig = build_radix_figure_for_chart(focused_chart, engine_override=engine_override, ephemeris_path_override=eph_override, ws=ws)
                            # Use a unique key based on chart and engine to prevent caching issues
                            chart_name = _safe_subject_name(focused_chart) or 'unknown'
                            chart_key = f"chart_{chart_name}_{engine_override}_{st.session_state.get('astrolab_active', False)}_{id(focused_chart)}"
                            st.plotly_chart(fig, use_container_width=True, key=chart_key)
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"Chyba při výpočtu pozic: {e}")
                        with st.expander("Detaily chyby", expanded=False):
                            st.code(error_details)
            else:
                # No workspace: automatically compute and display for current datetime
                name = st.session_state.get('crt_name') or st.session_state.get('current_person_name') or 'Radix'
                # Use default location from initial dialog or fallback to Prague
                place = (st.session_state.get('ws_default_loc') or 
                        st.session_state.get('focused_place') or 
                        st.session_state.get('crt_place') or 
                        'Prague')
                # Use current datetime (or astrolab shifted if active)
                if st.session_state.get("astrolab_active"):
                    date = st.session_state.get("astrolab_shifted_date") or datetime.date.today()
                    time = st.session_state.get("astrolab_shifted_time") or datetime.datetime.now().time()
                else:
                    date = st.session_state.get('focused_date') or st.session_state.get('crt_date') or datetime.date.today()
                    time = st.session_state.get('focused_time') or st.session_state.get('crt_time') or datetime.datetime.now().time()
                
                try:
                    engine_choice = st.session_state.get('settings_engine', engine_choice)
                    eph_path = st.session_state.get('settings_eph', eph_path)
                    dtc = combine_date_time(date, time)
                    horoscope, fig = _run_compute(name, dtc, place, engine_choice, eph_path)
                    chart_key = f"chart_no_workspace_{name}_{dtc}_{place}_{engine_choice}"
                    st.plotly_chart(fig, use_container_width=True, key=chart_key)
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    st.error(f"Chyba při výpočtu pozic: {e}")
                    with st.expander("Detaily chyby", expanded=False):
                        st.code(error_details)

    elif mode == "aspektarium":
        with c_center:
            # Automatically compute positions from focused chart if workspace is loaded
            focused_chart = _get_focused_chart()
            if focused_chart:
                # Check if Astrolab shift is active
                if st.session_state.get("astrolab_active"):
                    shifted_date = st.session_state.get("astrolab_shifted_date")
                    shifted_time = st.session_state.get("astrolab_shifted_time")
                    if shifted_date and shifted_time:
                        # Compute with shifted datetime
                        try:
                            name = _safe_subject_name(focused_chart) or 'Radix'
                            place_obj = _safe_subject_location(focused_chart) or {}
                            place = place_obj.get('name') or 'Prague'
                            dtc = combine_date_time(shifted_date, shifted_time)
                            engine_choice_val = st.session_state.get('settings_engine', engine_choice)
                            eph_path_val = st.session_state.get('settings_eph', eph_path)
                            horoscope, fig = _run_compute(name, dtc, place, engine_choice_val, eph_path_val)
                            # Use compute_positions to get consistent data with the chart
                            from services import compute_positions
                            engine = EngineType.JPL if str(engine_choice_val).startswith("JPL") else (EngineType.SWISSEPH if str(engine_choice_val).startswith("SWISSEPH") else None)
                            positions = compute_positions(engine, name, str(dtc), place, ephemeris_path=eph_path_val if engine == EngineType.JPL else None)
                            if positions:
                                from pandas import DataFrame
                                positions_df = DataFrame([positions]).T
                                positions_df.columns = ['Longitude (°)']
                                st.table(positions_df)
                            else:
                                # Fallback to kerykeion points if compute_positions fails
                                st.table(extract_kerykeion_points(horoscope.computed))
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            st.error(f"Chyba při výpočtu pozic: {e}")
                            with st.expander("Detaily chyby", expanded=False):
                                st.code(error_details)
                    else:
                        # Fallback to normal chart positions
                        try:
                            from services import compute_positions_for_chart
                            # Pass workspace if available for observable objects
                            ws = st.session_state.get('workspace')
                            positions = compute_positions_for_chart(focused_chart, ws=ws)
                            
                            if not positions:
                                st.warning("Nepodařilo se vypočítat pozice pro vybraný horoskop.")
                                # Debug info
                                with st.expander("Debug informace", expanded=False):
                                    st.write(f"Chart: {focused_chart}")
                                    st.write(f"Subject: {_safe_get(focused_chart, 'subject')}")
                                    st.write(f"Location: {_safe_subject_location(focused_chart)}")
                                    st.write(f"Event time: {_safe_event_dt(focused_chart)}")
                            elif isinstance(positions, str):
                                st.error(f"Chyba: {positions}")
                            else:
                                from pandas import DataFrame
                                positions_df = DataFrame([positions]).T
                                positions_df.columns = ['Longitude (°)']
                                st.table(positions_df)
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            st.error(f"Chyba při výpočtu pozic: {e}")
                            with st.expander("Detaily chyby", expanded=False):
                                st.code(error_details)
                            # Additional debug info
                            with st.expander("Debug informace", expanded=False):
                                st.write(f"Chart: {focused_chart}")
                                st.write(f"Subject: {_safe_get(focused_chart, 'subject')}")
                                st.write(f"Location: {_safe_subject_location(focused_chart)}")
                                st.write(f"Event time: {_safe_event_dt(focused_chart)}")
                else:
                    # Normal positions without shift
                    try:
                        from services import compute_positions_for_chart
                        # Pass workspace if available for observable objects
                        ws = st.session_state.get('workspace')
                        positions = compute_positions_for_chart(focused_chart, ws=ws)
                        
                        if not positions:
                            st.warning("Nepodařilo se vypočítat pozice pro vybraný horoskop.")
                            # Debug info
                            with st.expander("Debug informace", expanded=False):
                                st.write(f"Chart: {focused_chart}")
                                st.write(f"Subject: {_safe_get(focused_chart, 'subject')}")
                                st.write(f"Location: {_safe_subject_location(focused_chart)}")
                                st.write(f"Event time: {_safe_event_dt(focused_chart)}")
                        elif isinstance(positions, str):
                            st.error(f"Chyba: {positions}")
                        else:
                            from pandas import DataFrame
                            positions_df = DataFrame([positions]).T
                            positions_df.columns = ['Longitude (°)']
                            st.table(positions_df)
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"Chyba při výpočtu pozic: {e}")
                        with st.expander("Detaily chyby", expanded=False):
                            st.code(error_details)
                        # Additional debug info
                        with st.expander("Debug informace", expanded=False):
                            st.write(f"Chart: {focused_chart}")
                            st.write(f"Subject: {_safe_get(focused_chart, 'subject')}")
                            st.write(f"Location: {_safe_subject_location(focused_chart)}")
                            st.write(f"Event time: {_safe_event_dt(focused_chart)}")
            else:
                # No workspace: automatically compute and display for current datetime
                name = st.session_state.get('crt_name') or st.session_state.get('current_person_name') or 'Radix'
                # Use default location from initial dialog or fallback to Prague
                place = (st.session_state.get('ws_default_loc') or 
                        st.session_state.get('focused_place') or 
                        st.session_state.get('crt_place') or 
                        'Prague')
                # Use current datetime (or astrolab shifted if active)
                if st.session_state.get("astrolab_active"):
                    date = st.session_state.get("astrolab_shifted_date") or datetime.date.today()
                    time = st.session_state.get("astrolab_shifted_time") or datetime.datetime.now().time()
                else:
                    date = st.session_state.get('focused_date') or st.session_state.get('crt_date') or datetime.date.today()
                    time = st.session_state.get('focused_time') or st.session_state.get('crt_time') or datetime.datetime.now().time()
                
                try:
                    engine_choice_val = st.session_state.get('settings_engine', engine_choice)
                    eph_path_val = st.session_state.get('settings_eph', eph_path)
                    dtc = combine_date_time(date, time)
                    horoscope, fig = _run_compute(name, dtc, place, engine_choice_val, eph_path_val)
                    # Use compute_positions to get consistent data with the chart
                    from services import compute_positions
                    engine = EngineType.JPL if str(engine_choice_val).startswith("JPL") else (EngineType.SWISSEPH if str(engine_choice_val).startswith("SWISSEPH") else None)
                    positions = compute_positions(engine, name, str(dtc), place, ephemeris_path=eph_path_val if engine == EngineType.JPL else None)
                    if positions:
                        from pandas import DataFrame
                        positions_df = DataFrame([positions]).T
                        positions_df.columns = ['Longitude (°)']
                        st.table(positions_df)
                    else:
                        # Fallback to kerykeion points if compute_positions fails
                        st.table(extract_kerykeion_points(horoscope.computed))
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    st.error(f"Chyba při výpočtu pozic: {e}")
                    with st.expander("Detaily chyby", expanded=False):
                        st.code(error_details)

    elif mode == "interpretation":
        with c_center:
            st.subheader("Interpretace")
            focused_chart = _get_focused_chart()
            
            if not focused_chart:
                st.info("Načtěte workspace a vyberte horoskop pro zobrazení interpretace.")
            else:
                # Get selected interpretation item
                selected = st.session_state.get("interpretation_selection")
                
                if not selected:
                    st.info("Vyberte položku interpretace z levého menu.")
                else:
                    st.markdown(f"### {selected}")
                    st.markdown("---")
                    
                    # Placeholder for interpretation content
                    # This will be populated with actual interpretation logic later
                    try:
                        from services import compute_positions_for_chart
                        positions = compute_positions_for_chart(focused_chart)
                        
                        if positions:
                            st.write(f"Interpretace pro: **{selected}**")
                            st.write("")
                            st.write("*(Implementace interpretační logiky bude přidána později)*")
                            st.write("")
                            st.caption(f"Počet vypočítaných pozic: {len(positions)}")
                        else:
                            st.warning("Nelze vypočítat pozice pro interpretaci.")
                    except Exception as e:
                        st.error(f"Chyba při načítání dat pro interpretaci: {e}")

    elif mode == "transzit":
        with c_center:
            st.subheader("Transzity a direkce")
            with st.form(key="second_info"):
                e2_name = st.text_input(lang["name"])
                e2_place = st.text_input(lang["place"])
                e2_date = st.date_input(lang["first_date"])
                e2_time = st.time_input(lang["time"])
                submitted = st.form_submit_button(lang["control"], use_container_width=True)
            if not e2_name:
                st.info("Nastavte prosím i druhou událost (vlevo nahoře tlačítka jsou pouze informační).")
            if st.button(lang["run"], use_container_width=True):
                name = st.session_state.get('crt_name', 'Radix')
                place = st.session_state.get('crt_place', 'Prague')
                date = st.session_state.get('crt_date', datetime.date.today())
                time = st.session_state.get('crt_time', datetime.time(12,0))
                engine_choice = st.session_state.get('settings_engine', engine_choice)
                eph_path = st.session_state.get('settings_eph', eph_path)
                dtc = combine_date_time(date, time)
                horoscope, fig = _run_compute(name, dtc, place, engine_choice, eph_path)
                st.subheader("Zobrazení horoskopu")
                chart_key = f"chart_transzit_{name}_{dtc}_{place}_{engine_choice}"
                st.plotly_chart(fig, use_container_width=True, key=chart_key)
                # Use compute_positions to get consistent data with the chart
                from services import compute_positions
                engine = EngineType.JPL if str(engine_choice).startswith("JPL") else (EngineType.SWISSEPH if str(engine_choice).startswith("SWISSEPH") else None)
                positions = compute_positions(engine, name, str(dtc), place, ephemeris_path=eph_path if engine == EngineType.JPL else None)
                if positions:
                    from pandas import DataFrame
                    positions_df = DataFrame([positions]).T
                    positions_df.columns = ['Longitude (°)']
                    st.table(positions_df)
                else:
                    # Fallback to kerykeion points if compute_positions fails
                    st.table(extract_kerykeion_points(horoscope.computed))
            else:
                st.warning(lang["run"])

    # Footer selector visible in all modes (if workspace loaded)
    with c_center:
        _render_footer_selector()

if __name__ == "__main__":
    main()
