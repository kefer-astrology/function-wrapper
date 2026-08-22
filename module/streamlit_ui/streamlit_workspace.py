"""Workspace loading, chart-focus, and storage helpers for the Streamlit UI."""
import datetime
import streamlit as st
from pathlib import Path

try:
    from module.models import ChartSubject, EngineType
except ImportError:
    from models import ChartSubject, EngineType

try:
    from module.utils import (
        import_chart_yaml,
        read_yaml_file,
        parse_yaml_content,
        parse_chart_yaml,
        resolve_user_path,
    )
except ImportError:
    from utils import (
        import_chart_yaml,
        read_yaml_file,
        parse_yaml_content,
        parse_chart_yaml,
        resolve_user_path,
    )

try:
    from module.services import list_open_view_rows
except ImportError:
    from services import list_open_view_rows

try:
    from module.workspace import (
        load_workspace, add_or_update_chart,
        scan_workspace_changes, save_workspace_modular, add_subject,
    )
except ImportError:
    from workspace import (
        load_workspace, add_or_update_chart,
        scan_workspace_changes, save_workspace_modular, add_subject,
    )

# Optional storage integration (positions-only storage like Tauri flow).
try:
    from module.storage import DuckDBStorage, DUCKDB_AVAILABLE
except ImportError:
    try:
        from storage import DuckDBStorage, DUCKDB_AVAILABLE
    except ImportError:
        DuckDBStorage = None
        DUCKDB_AVAILABLE = False

try:
    from module.streamlit_ui.streamlit_common import (
        UI_RECOVERABLE_EXC, _safe_get, _safe_subject_name, _safe_subject_location,
        _safe_event_dt, _safe_config,
    )
except ImportError:
    from streamlit_ui.streamlit_common import (
        UI_RECOVERABLE_EXC, _safe_get, _safe_subject_name, _safe_subject_location,
        _safe_event_dt, _safe_config,
    )


def _store_positions_if_possible(chart, positions, engine_override=None, eph_override=None):
    if not DUCKDB_AVAILABLE or DuckDBStorage is None:
        return
    if not positions:
        return
    manifest = st.session_state.get("workspace_manifest")
    if not manifest:
        return
    try:
        chart_id = _safe_get(chart, 'id') or _safe_get(chart, 'chart_id')
        if not chart_id:
            return
        subj = _safe_get(chart, 'subject')
        event_time = _safe_get(subj, 'event_time')
        if isinstance(event_time, datetime.datetime):
            dt_str = event_time.isoformat()
        elif isinstance(event_time, str):
            dt_str = event_time
        else:
            return
        engine_val = engine_override
        if isinstance(engine_val, EngineType):
            engine_val = engine_val.value
        elif engine_val is not None:
            engine_val = str(engine_val).lower()
        base_dir = Path(manifest).parent
        db_path = base_dir / "data" / "workspace.db"
        storage = DuckDBStorage(db_path)
        storage.store_positions(
            chart_id,
            dt_str,
            positions,
            engine=engine_val,
            ephemeris_file=eph_override,
        )
    except UI_RECOVERABLE_EXC:
        return


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
    except UI_RECOVERABLE_EXC:
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
        except UI_RECOVERABLE_EXC as e:
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
        except UI_RECOVERABLE_EXC:
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
    if st.button("Načíst ze složky", width='stretch', key="btn_load_folder"):
        try:
            if not base_dir:
                st.warning("Zadejte cestu ke složce")
            else:
                # Define a safe root directory for all workspaces
                workspace_root = (Path.cwd() / "workspaces").resolve()
                # Validate and resolve path to prevent path traversal attacks
                try:
                    resolved_base_path = resolve_user_path(base_dir, base_dir=workspace_root)
                    manifest = resolved_base_path / "workspace.yaml"
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
        except UI_RECOVERABLE_EXC as e:
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
        except UI_RECOVERABLE_EXC:
            changes = {'charts': {'new_on_disk': [], 'missing_on_disk': []}, 'subjects': {'new_on_disk': [], 'missing_on_disk': []}}
        # Import new charts
        try:
            for fname in (changes.get('charts', {}).get('new_on_disk', []) or []):
                path = str(Path(base_dir) / 'charts' / fname)
                try:
                    chart = import_chart_yaml(path)
                    add_or_update_chart(ws, chart, base_dir=base_dir)
                    imported += 1
                except UI_RECOVERABLE_EXC:
                    continue
        except UI_RECOVERABLE_EXC:
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
                except UI_RECOVERABLE_EXC:
                    continue
        except UI_RECOVERABLE_EXC:
            pass
        if imported:
            try:
                save_workspace_modular(ws, base_dir)
            except UI_RECOVERABLE_EXC:
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
    except UI_RECOVERABLE_EXC:
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
                    except UI_RECOVERABLE_EXC:
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
        except UI_RECOVERABLE_EXC:
            pass
        # Keep crt_name in sync if not managed by widget at this time
        try:
            if 'crt_name' in st.session_state and not st.session_state.get('crt_name'):
                st.session_state.crt_name = names[0]
        except UI_RECOVERABLE_EXC:
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
            except UI_RECOVERABLE_EXC:
                continue

    # Then check session charts (created without workspace)
    session_charts = st.session_state.get('session_charts', [])
    for ch in session_charts:
        try:
            subj_name = _safe_subject_name(ch)
            cid = _safe_get(ch, 'id') or _safe_get(ch, 'id', 'id')
            if subj_name == current_name or cid == current_name:
                return ch
        except UI_RECOVERABLE_EXC:
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
            except UI_RECOVERABLE_EXC:
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
            except UI_RECOVERABLE_EXC:
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
            except UI_RECOVERABLE_EXC:
                st.session_state.focused_date = None
                st.session_state.focused_time = None
        cfg = _safe_config(found)
        st.session_state.focused_mode = cfg.get('mode')
        st.session_state.focused_house = cfg.get('house')
        st.session_state.focused_zodiac = cfg.get('zodiac')
        st.session_state.focused_engine = cfg.get('engine')
        tags_val = _safe_get(found, 'tags') or _safe_get(found, 'tags', 'tags', []) or []
        st.session_state.focused_tags = list(tags_val or [])
    except UI_RECOVERABLE_EXC:
        pass
    # Sync non-widget value for compute defaults
    try:
        if 'crt_name' in st.session_state and not st.session_state.get('crt_name'):
            st.session_state.crt_name = st.session_state.current_person_name
    except UI_RECOVERABLE_EXC:
        pass
