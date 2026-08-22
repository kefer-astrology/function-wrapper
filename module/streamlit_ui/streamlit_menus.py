"""Left-side navigation (sidebar) and per-mode left-panel menu builders."""
import datetime
from pathlib import Path
import streamlit as st

try:
    from module.model_catalog import builtin_standard_model
except ImportError:
    from model_catalog import builtin_standard_model

try:
    from module.streamlit_ui.streamlit_workspace import _get_focused_chart, _safe_subject_name
except ImportError:
    from streamlit_ui.streamlit_workspace import _get_focused_chart, _safe_subject_name

try:
    from module.streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC
except ImportError:
    from streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC

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
    "informace":       ("two", [1, 5]),
    "dynamika":        ("two", [1, 5]),
    "revoluce":        ("two", [1, 5]),
    "synastrie":       ("two", [1, 5]),
}

# -----------------------------
# Left-side navigation menu (mirrors the React app's astrology-sidebar.tsx
# grouping/order: workspace actions, main views, then settings).
# -----------------------------
SIDEBAR_SECTIONS = [
    [
        ("create", "🆕", "Nový"),
        ("open", "📂", "Otevřít"),
        ("save", "💾", "Uložit"),
        ("export", "📤", "Export"),
    ],
    [
        ("chart", "📊", "Horoskop"),
        ("aspektarium", "📋", "Aspektárium"),
        ("informace", "ℹ️", "Informace"),
        ("transzit", "🔁", "Tranzity"),
        ("dynamika", "🧭", "Dynamika"),
        ("revoluce", "🌞", "Revoluce"),
        ("synastrie", "💞", "Synastrie"),
    ],
    [
        ("interpretation", "📖", "Interpretace"),
        ("notes", "📝", "Poznámky"),
    ],
    [
        ("settings", "⚙️", "Nastavení"),
    ],
]


def render_sidebar():
    """Persistent left-side navigation menu, listing every screen (mirrors the React app)."""
    with st.sidebar:
        st.markdown("### ✨ Kefer")
        current_mode = st.session_state.get("mode")
        for section in SIDEBAR_SECTIONS:
            for key, emoji, label in section:
                is_active = current_mode == key
                if st.button(
                    f"{emoji} {label}",
                    width='stretch',
                    key=f"sb_{key}",
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.mode = key
                    st.rerun()
            st.markdown("---")


def _left_open_menu():
    # Track which view is active
    if "open_view_mode" not in st.session_state:
        st.session_state.open_view_mode = "horoskopy"

    if st.button("Horoskopy", width='stretch', key="left_my", type="primary" if st.session_state.open_view_mode == "horoskopy" else "secondary"):
        st.session_state.open_view_mode = "horoskopy"
        st.rerun()
    if st.button("Databáze osobností", width='stretch', key="left_db", type="primary" if st.session_state.open_view_mode == "db" else "secondary"):
        st.session_state.open_view_mode = "db"
        st.rerun()

    if st.session_state.open_view_mode == "horoskopy":
        st.info("Použijte vyhledávání k filtrování, importujte YAML do workspace.")
    else:
        st.info("Připojení k online databázi osobností. Funkcionalita bude implementována.")


def _left_create_menu():
    # Matches the React app's NewHoroscope screen: chart type is a field in the
    # main form (see _render_create_content), not a side-panel control.
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
        if st.button(item, width='stretch', key=f"init_{item}"):
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
            if st.button(ann.title, width='stretch', key=f"note_{ann.title}"):
                st.session_state["selected_note"] = ann.title
                st.rerun()
    else:
        st.info("Žádné poznámky. Vytvořte novou poznámku vpravo.")

    if st.button("➕ Nová poznámka", width='stretch', key="new_note"):
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

    if focused_chart:
        _render_local_settings_override(focused_chart)

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

        if st.button("Aplikovat posun", width='stretch', key="astrolab_apply"):
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
                if st.button("Resetovat", width='stretch', key="astrolab_reset"):
                    st.session_state["astrolab_active"] = False
                    st.session_state["astrolab_shifted_date"] = None
                    st.session_state["astrolab_shifted_time"] = None
                    st.rerun()

    st.info("Zobrazení horoskopu: pozice se zobrazí automaticky při výběru horoskopu z workspace.")


_SOURCE_LABELS = {
    "application": "výchozí", "model": "model", "workspace": "workspace",
    "preset": "šablona", "chart": "lokální", "operation": "dočasné",
}


def _source_badge(source) -> str:
    if source is None:
        return ""
    key = str(getattr(source, "value", source)).lower()
    return f" _(zdroj: {_SOURCE_LABELS.get(key, key)})_"


def _render_local_settings_override(chart) -> None:
    """Show effective settings (with the resolution-chain layer each came from)
    for the focused chart, and let the user override individual fields at the
    CHART layer specifically. Mirrors module/resolution.py's precedence chain
    (application < model < workspace < preset < chart < operation): workspace
    Settings apply to every chart by default, a per-chart override here wins.
    """
    try:
        from module.resolution import current_model_report, standalone_model_report
    except ImportError:
        from resolution import current_model_report, standalone_model_report
    try:
        from module.workspace import add_or_update_chart
    except ImportError:
        from workspace import add_or_update_chart
    try:
        from module.models import HouseSystem, ZodiacType, Ayanamsa
    except ImportError:
        from models import HouseSystem, ZodiacType, Ayanamsa

    ws = st.session_state.get('workspace')
    try:
        report = current_model_report(ws, chart.config) if ws else standalone_model_report(chart.config)
    except UI_RECOVERABLE_EXC as e:
        st.caption(f"Efektivní nastavení se nepodařilo vyhodnotit: {e}")
        return

    eff = report.effective_settings
    src = eff.sources

    with st.expander("Efektivní nastavení", expanded=False):
        st.caption("Hodnoty platné pro tento horoskop a jejich zdroj (výchozí < model < workspace < šablona < lokální).")
        house_val = getattr(eff.default_house_system, "value", eff.default_house_system)
        st.write(f"Systém domů: **{house_val or '—'}**{_source_badge(src.default_house_system)}")
        zodiac_val = getattr(eff.zodiac_type, "value", eff.zodiac_type)
        st.write(f"Zodiak: **{zodiac_val or '—'}**{_source_badge(src.zodiac_type)}")
        ayanamsa_val = getattr(eff.ayanamsa, "value", eff.ayanamsa)
        st.write(f"Ayanamsa: **{ayanamsa_val or '—'}**{_source_badge(src.ayanamsa)}")
        st.write(f"Aspekty: **{', '.join(eff.default_aspects) or '—'}**{_source_badge(src.default_aspects)}")
        engine_val = getattr(eff.engine, "value", eff.engine)
        st.write(f"Engine: **{engine_val or '—'}**{_source_badge(src.engine)}")

    with st.expander("Přepsat lokálně pro tento horoskop", expanded=False):
        st.caption("Přepíše nastavení workspace jen pro tento konkrétní horoskop.")

        house_options = [h.value for h in HouseSystem]
        cur_house = getattr(chart.config.house_system, "value", chart.config.house_system)
        house_idx = house_options.index(cur_house) + 1 if cur_house in house_options else 0
        new_house = st.selectbox(
            "Systém domů", ["(dle workspace)"] + house_options, index=house_idx, key="local_override_house"
        )

        zodiac_options = [z.value for z in ZodiacType]
        cur_zodiac = getattr(chart.config.zodiac_type, "value", chart.config.zodiac_type)
        zodiac_idx = zodiac_options.index(cur_zodiac) + 1 if cur_zodiac in zodiac_options else 0
        new_zodiac = st.selectbox(
            "Zodiak", ["(dle workspace)"] + zodiac_options, index=zodiac_idx, key="local_override_zodiac"
        )
        new_ayanamsa = None
        if new_zodiac == ZodiacType.SIDEREAL.value:
            ayanamsa_options = [a.value for a in Ayanamsa]
            cur_ayanamsa = getattr(chart.config.ayanamsa, "value", chart.config.ayanamsa)
            ayanamsa_idx = ayanamsa_options.index(cur_ayanamsa) if cur_ayanamsa in ayanamsa_options else 0
            new_ayanamsa = st.selectbox("Ayanamsa", ayanamsa_options, index=ayanamsa_idx, key="local_override_ayanamsa")

        if st.button("💾 Uložit přepsání pro tento horoskop", key="local_override_save"):
            chart.config.house_system = None if new_house == "(dle workspace)" else HouseSystem(new_house)
            if new_zodiac == "(dle workspace)":
                chart.config.zodiac_type = None
                chart.config.ayanamsa = None
            else:
                chart.config.zodiac_type = ZodiacType(new_zodiac)
                chart.config.ayanamsa = Ayanamsa(new_ayanamsa) if new_ayanamsa else None

            try:
                if ws:
                    base_dir = str(Path(st.session_state.workspace_manifest).parent)
                    add_or_update_chart(ws, chart, base_dir=base_dir)
                else:
                    session_charts = st.session_state.get('session_charts', [])
                    for i, c in enumerate(session_charts):
                        if _safe_subject_name(c) == _safe_subject_name(chart):
                            session_charts[i] = chart
                    st.session_state.session_charts = session_charts
                st.success("Lokální přepsání uloženo.")
                st.rerun()
            except UI_RECOVERABLE_EXC as e:
                st.error(f"Nepodařilo se uložit přepsání: {e}")


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

        if st.button("Aplikovat posun", width='stretch', key="astrolab_apply_asp"):
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
                if st.button("Resetovat", width='stretch', key="astrolab_reset_asp"):
                    st.session_state["astrolab_active"] = False
                    st.session_state["astrolab_shifted_date"] = None
                    st.session_state["astrolab_shifted_time"] = None
                    st.rerun()

    with st.expander("Aspekty", expanded=True):
        model = builtin_standard_model()
        all_aspect_ids = [a.id for a in model.aspect_definitions]
        default_aspects = model.settings.default_aspects
        st.multiselect(
            "Zahrnuté aspekty",
            all_aspect_ids,
            default=st.session_state.get("asp_selected", default_aspects),
            key="asp_selected",
        )
        st.selectbox(
            "Orb",
            ["Výchozí", "Těsný (2°)", "Široký (8°)", "Vlastní"],
            key="asp_orb_preset",
        )
        if st.session_state.get("asp_orb_preset") == "Vlastní":
            st.number_input("Vlastní orb (°)", min_value=0.0, max_value=20.0, value=6.0, step=0.5, key="asp_custom_orb")


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
                if st.button(item, width='stretch', key=f"int_{item}"):
                    st.session_state.interpretation_selection = item
                    st.rerun()


def _left_settings_menu():
    st.markdown("#### Nastavení")
    if st.button("General", width='stretch', key="set_sec_gen"):
        st.session_state["settings_section"] = "general"
    if st.button("Advanced", width='stretch', key="set_sec_adv"):
        st.session_state["settings_section"] = "advanced"


def _left_revoluce_menu():
    st.markdown("#### Solární revoluce")
    st.number_input("Rok revoluce", min_value=1, max_value=3000, value=datetime.date.today().year, key="revoluce_year")
