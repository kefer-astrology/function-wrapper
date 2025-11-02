import datetime
import streamlit as st
from pathlib import Path

from models import ChartInstance, Location, ChartSubject, ChartConfig, EngineType, ChartMode
from utils import (
    Actual,
    parse_sfs_content,
    combine_date_time,
    prepare_horoscope,
    default_ephemeris_path,
    import_chart_yaml,
    read_yaml_file,
    parse_yaml_content,
)
from services import Subject, extract_kerykeion_points, compute_positions, list_open_view_rows
from z_visual import build_radix_figure
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
    ("📁", "open_workspace", "Otevřít workspace"),
    ("💾", "save",     "Uložit horoskop"),
    ("📊", "chart",    "Aspektárium"),
    ("🔁", "transzit", "Transzity a direkce"),
    ("⚙️", "settings", "Nastavení"),
]

# Layout map
# For create/open we want a three-column layout; settings/save use two columns
LAYOUTS = {
    "create":          ("two", [1, 5]),
    "open":            ("two", [1, 5]),
    "open_workspace":  ("two", [1, 5]),
    "save":            ("two",   [1, 5]),
    "settings":        ("two",   [1, 5]),
    "chart":           ("two", [1, 5]),
    "transzit":        ("two", [1, 5]),
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
    # Build columns dynamically: [brand] + [one per action] + [status]
    action_count = len(ACTIONS)
    weights = [2] + [1] * action_count + [4]
    cols = st.columns(weights)
    # Brand on the left
    with cols[0]:
        st.markdown("<span class='brand'>Kefer</span>", unsafe_allow_html=True)
    # Action buttons
    for i, (emoji, key, label) in enumerate(ACTIONS, start=1):
        with cols[i]:
            if st.button(f"{emoji} {label}", key=f"tb_{key}", use_container_width=True):
                st.session_state.mode = key
                st.session_state.status = f"Přepnuto na: {label}"
    # Status column
    with cols[-1]:
        st.caption(st.session_state.get("status", ""))
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
    st.subheader("Otevřít horoskop")
    #st.markdown("### ")  # spacer
    st.button("My Horoskopes", use_container_width=True, key="left_my")
    st.button("Persons Database", use_container_width=True, key="left_db")
    st.info("Použijte vyhledávání k filtrování, importujte YAML do workspace.")


def _left_create_menu():
    st.markdown("#### Nový horoskop")
    st.markdown("##### Typ:")
    # Show chart types from ChartMode
    options = [ChartMode.NATAL.value, ChartMode.EVENT.value, ChartMode.HORARY.value, ChartMode.COMPOSITE.value]
    for opt in options:
        btn_label = f"{opt}"
        if st.button(btn_label, use_container_width=True, key=f"ct_{opt}"):
            st.session_state["chart_type"] = opt
    st.info("Tip: Nastavení efemerid najdete v záložce Nastavení.")


def _left_open_workspace_menu():
    st.markdown("#### Otevřít Workspace")
    st.info("Zadejte cestu k workspace.yaml v hlavním panelu a načtěte workspace.")


def _left_save_menu():
    st.markdown("#### Uložit horoskop")
    st.caption("Nastavte parametry uložení v hlavním panelu.")


def _left_chart_menu():
    st.markdown("#### Aspektárium")
    # Use current chart name (fallback to focused person or generic label)
    chart_name = (
        st.session_state.get("crt_name")
        or st.session_state.get("current_person_name")
        or "Horoskop"
    )
    with st.expander(chart_name, expanded=False):
        # Prefer focused values from selected Workspace chart
        place = st.session_state.get("focused_place") or st.session_state.get("crt_place") or "—"
        date = st.session_state.get("focused_date") or st.session_state.get("crt_date")
        time = st.session_state.get("focused_time") or st.session_state.get("crt_time")
        date_str = str(date) if date else "—"
        time_str = str(time) if time else "—"
        st.markdown("**Základní nastavení**")
        st.write(f"Lokalita: {place}")
        st.write(f"Datum: {date_str}")
        st.write(f"Čas: {time_str}")
        # Extra details
        latlon = st.session_state.get("focused_latlon")
        tz = st.session_state.get("focused_tz")
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
    st.info("Aspektárium: spusťte výpočet v hlavním panelu.")


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
        # Handle common Skyfield kernel limitations (e.g., de421 lacks JUPITER/SATURN centers)
        msg = str(e)
        if engine == EngineType.JPL and eph_override and "de421" in Path(eph_override).name.lower():
            st.warning("Zvolený soubor efemerid de421.bsp neobsahuje všechna tělesa (např. JUPITER, SATURN, …).\n"
                       "Doporučeno: použijte de440s.bsp nebo přepněte engine na Kerykeion ve 'Nastavení > Advanced'.\n"
                       "Pokračuji s výchozím enginem (Kerykeion).")
            engine = None
            positions = compute_positions(engine, name, str(dt), place, ephemeris_path=None)
        else:
            raise
    fig = build_radix_figure(positions)
    return horoscope, fig


def _open_view_center():
    ws = st.session_state.get("workspace")

    # Search row [Search ...][Import Chart (YAML)]
    sc1, sc2 = st.columns([4,1])
    with sc1:
        st.text_input('Search...', key='open_search')
    with sc2:
        uploaded_yaml = st.file_uploader('Import Chart (YAML)', type=["yml", "yaml"], key="open_import")

    if uploaded_yaml is not None:
        try:
            data = parse_yaml_content(uploaded_yaml.read()) or {}
            subj = data.get('subject') or {}
            subject = ChartSubject(**subj) if isinstance(subj, dict) else None
            cfg = data.get('config') or {}
            config = ChartConfig(**cfg) if isinstance(cfg, dict) else None
            ch = ChartInstance(
                id=data.get('id') or (subject.name if subject else 'chart'),
                subject=subject,
                config=config,
                tags=data.get('tags') or []
            )
            if st.session_state.get('workspace') is None:
                st.warning('Nejprve načtěte workspace, aby bylo kam importovat.')
            else:
                base_dir = str(Path(st.session_state.workspace_manifest).parent)
                add_or_update_chart(st.session_state.workspace, ch, base_dir=base_dir)
                st.success('Chart importován do workspace.')
        except Exception as e:
            st.error(f"Import selhal: {e}")

    # List rows with filtering
    rows = list_open_view_rows(ws) if ws else []
    q = (st.session_state.get('open_search') or '').strip().lower()
    if q:
        rows = [r for r in rows if q in (r.get('search_text','').lower())]

    # Header
    hc1, hc2, hc3, hc4 = st.columns([2,2,2,2])
    with hc1: st.markdown("**Name**")
    with hc2: st.markdown("**Event time**")
    with hc3: st.markdown("**Location**")
    with hc4: st.markdown("**Tags**")

    # Rows
    for info in rows:
        name = info.get('name','-')
        event_time = info.get('event_time','')
        location_name = info.get('location','')
        tags = info.get('tags','')
        c1, c2, c3, c4 = st.columns([2,2,2,2])
        with c1:
            if st.button(name or '-', key=f"open_row_{name}"):
                _focus_chart_by_name(name)
                st.session_state.status = f"Focused: {name}"
        with c2:
            st.write(event_time)
        with c3:
            st.write(location_name)
        with c4:
            st.write(tags)


def _open_workspace_center():
    st.subheader("Otevřít workspace")
    base_dir = st.text_input("Složka workspace (obsahuje workspace.yaml)", key="ws_folder")
    if st.button("Načíst ze složky", use_container_width=True, key="btn_load_folder"):
        try:
            if not base_dir:
                st.warning("Zadejte cestu ke složce")
            else:
                manifest = str(Path(base_dir) / "workspace.yaml")
                if not Path(manifest).is_file():
                    st.error("Soubor workspace.yaml ve složce nenalezen")
                else:
                    # Full folder available: do full scan/import
                    report = _load_workspace_and_sync(manifest, scan_and_import=True)
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
    # Build list of chart names for footer selector
    try:
        names = []
        for c in (ws.charts or []):
            nm = _safe_subject_name(c)
            if nm:
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


def _focus_chart_by_name(name: str):
    """Focus an existing chart in the loaded workspace by subject name/id, update session context."""
    ws = st.session_state.get('workspace')

    found = None
    for ch in ws.charts:
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
    """Render a footer-like selector for charts in the loaded workspace."""
    st.markdown("---")
    names = st.session_state.get('people') or []
    if not names:
        st.caption("Žádné horoskopy ve workspace. Otevřete workspace pro výběr.")
        return
    default = st.session_state.get('current_person_name') or names[0]
    # Use Streamlit pills in single-select mode
    sel = st.pills("Vyberte horoskop", options=names, selection_mode="single", default=default, key="footer_select")
    # st.pills may return a single value (single mode) or a list; handle robustly
    chosen = sel[0] if isinstance(sel, list) else sel
    if chosen and chosen != st.session_state.get('current_person_name'):
        _focus_chart_by_name(chosen)


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
        elif mode == "open_workspace":
            _left_open_workspace_menu()
        elif mode == "save":
            _left_save_menu()
        elif mode == "chart":
            _left_chart_menu()
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
                st.subheader("Uložit horoskop")
                name_val = st.text_input("Jméno", key="save_name", value=st.session_state.get("crt_name", ""))
                export_types = ["SFS", "PNG", "SVG", "PDF", "CSV"]
                st.selectbox("Formát exportu", export_types, key="save_export_type")
                st.markdown("#### Cílová cesta")
                st.text_input("Cesta a název souboru", key="save_dest_path")
                if st.button("Uložit", use_container_width=True, key="do_save"):
                    st.success(f"Export ({st.session_state.get('save_export_type')}) připraven do: {st.session_state.get('save_dest_path')}")

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
            #st.subheader("Nový Horoskop")
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
            if st.button("Vypočítat a zobrazit", use_container_width=True, key="crt_run"):
                dt_combined = combine_date_time(input_date, input_time)
                horoscope, fig = _run_compute(horoscope_name, dt_combined, input_location, engine_choice, eph_path)
                st.subheader("Radix Chart")
                st.plotly_chart(fig, use_container_width=True)
                st.table(extract_kerykeion_points(horoscope.computed))

    elif mode == "open":
        with c_center:
            _open_view_center()

    elif mode == "open_workspace":
        with c_center:
            _open_workspace_center()

    elif mode == "chart":
        with c_center:
            st.subheader("Aspektárium")
            if st.button(lang["run"], use_container_width=True):
                name = st.session_state.get('crt_name', 'Radix')
                place = st.session_state.get('crt_place', 'Prague')
                date = st.session_state.get('crt_date', datetime.date.today())
                time = st.session_state.get('crt_time', datetime.time(12,0))
                engine_choice = st.session_state.get('settings_engine', engine_choice)
                eph_path = st.session_state.get('settings_eph', eph_path)
                dtc = combine_date_time(date, time)
                horoscope, fig = _run_compute(name, dtc, place, engine_choice, eph_path)
                st.subheader("Radix Chart")
                st.plotly_chart(fig, use_container_width=True)
                st.table(extract_kerykeion_points(horoscope.computed))

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
                st.subheader("Radix Chart")
                st.plotly_chart(fig, use_container_width=True)
                st.table(extract_kerykeion_points(horoscope.computed))
            else:
                st.warning(lang["run"])

    # Footer selector visible in all modes (if workspace loaded)
    with c_center:
        _render_footer_selector()

if __name__ == "__main__":
    main()
