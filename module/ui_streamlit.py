import streamlit as st

# Standardized imports with fallback for direct execution (Streamlit Cloud compatibility)
try:
    from module.utils import default_ephemeris_path
except ImportError:
    from utils import default_ephemeris_path

try:
    from module.ui_translations import change_language
except ImportError:
    from ui_translations import change_language

try:
    from module.streamlit_ui.streamlit_common import _ensure_session_defaults
except ImportError:
    from streamlit_ui.streamlit_common import _ensure_session_defaults

try:
    from module.streamlit_ui.streamlit_workspace import _open_view_center
except ImportError:
    from streamlit_ui.streamlit_workspace import _open_view_center

try:
    from module.streamlit_ui.streamlit_menus import (
        LAYOUTS, render_sidebar,
        _left_open_menu, _left_create_menu, _left_save_menu, _left_export_menu,
        _left_chart_menu, _left_aspektarium_menu, _left_interpretation_menu,
        _left_notes_menu, _left_settings_menu, _left_revoluce_menu,
    )
except ImportError:
    from streamlit_ui.streamlit_menus import (
        LAYOUTS, render_sidebar,
        _left_open_menu, _left_create_menu, _left_save_menu, _left_export_menu,
        _left_chart_menu, _left_aspektarium_menu, _left_interpretation_menu,
        _left_notes_menu, _left_settings_menu, _left_revoluce_menu,
    )

try:
    from module.streamlit_ui.streamlit_pages import (
        _render_save_content, _render_export_content, _render_notes_content,
        _render_settings_content, _render_create_content, _render_chart_content,
        _render_aspektarium_content, _render_interpretation_content,
        _render_transit_or_direction_content, _render_informace_content,
        _render_revoluce_content, _render_synastrie_content, _render_footer_selector,
        _render_initial_dialog,
    )
except ImportError:
    from streamlit_ui.streamlit_pages import (
        _render_save_content, _render_export_content, _render_notes_content,
        _render_settings_content, _render_create_content, _render_chart_content,
        _render_aspektarium_content, _render_interpretation_content,
        _render_transit_or_direction_content, _render_informace_content,
        _render_revoluce_content, _render_synastrie_content, _render_footer_selector,
        _render_initial_dialog,
    )


def main():
    # -----------------------------
    # 1) Initial settings / session
    # -----------------------------
    _ensure_session_defaults()

    lang = change_language(default="cz")

    # -----------------------------
    # 2) Page config
    # -----------------------------
    st.set_page_config(
        page_title="Kefer Astrology",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # -----------------------------
    # 2.5) Check if initial dialog should be shown
    # -----------------------------
    if not st.session_state.get("initial_dialog_completed", False):
        _render_initial_dialog()
        return

    # -----------------------------
    # 3) Left navigation menu
    # -----------------------------
    render_sidebar()

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
        elif mode == "revoluce":
            _left_revoluce_menu()
        else:
            st.empty()

    # Helper defaults for compute
    engine_choice = st.session_state.get('settings_engine', "JPL / Skyfield")
    eph_path = st.session_state.get('settings_eph', default_ephemeris_path())

    # -----------------------------
    # RIGHT / CENTER per mode
    # -----------------------------
    if layout_kind == "two":
        # Render all main content in the center column; no separate right column is used.
        with c_center:
            if mode == "save":
                _render_save_content()
            elif mode == "export":
                _render_export_content()
            elif mode == "notes":
                _render_notes_content()
            elif mode == "settings":
                _render_settings_content()

    if mode == "create":
        with c_center:
            _render_create_content(engine_choice, eph_path)

    elif mode == "open":
        with c_center:
            _open_view_center()

    elif mode == "chart":
        with c_center:
            _render_chart_content(engine_choice, eph_path)

    elif mode == "aspektarium":
        with c_center:
            _render_aspektarium_content(engine_choice, eph_path)

    elif mode == "interpretation":
        with c_center:
            _render_interpretation_content()

    elif mode == "transzit":
        with c_center:
            _render_transit_or_direction_content(engine_choice, eph_path, lang, dynamic=False)

    elif mode == "dynamika":
        with c_center:
            _render_transit_or_direction_content(engine_choice, eph_path, lang, dynamic=True)

    elif mode == "informace":
        with c_center:
            _render_informace_content()

    elif mode == "revoluce":
        with c_center:
            _render_revoluce_content()

    elif mode == "synastrie":
        with c_center:
            _render_synastrie_content(engine_choice, eph_path)

    # Footer selector visible in all modes (if workspace loaded)
    with c_center:
        _render_footer_selector()

if __name__ == "__main__":
    main()
