"""Center-content page renderers for every Streamlit mode, plus the initial
onboarding dialog and the cross-mode footer chart selector."""
import datetime
import zoneinfo
import streamlit as st
from pathlib import Path

try:
    from module.models import Annotation, ChartMode, ChartSubject, EngineType, ZodiacType, Ayanamsa, TimeSystem
except ImportError:
    from models import Annotation, ChartMode, ChartSubject, EngineType, ZodiacType, Ayanamsa, TimeSystem

try:
    from module.utils import (
        Actual, combine_date_time, ensure_aware, now_utc, resolve_user_path, default_ephemeris_path,
        prepare_horoscope,
    )
except ImportError:
    from utils import (
        Actual, combine_date_time, ensure_aware, now_utc, resolve_user_path, default_ephemeris_path,
        prepare_horoscope,
    )

try:
    from module.services import Subject, positions_to_dataframe, compute_positions, build_radix_figure_for_chart
except ImportError:
    from services import Subject, positions_to_dataframe, compute_positions, build_radix_figure_for_chart

try:
    from module.z_visual import build_synastry_figure
except ImportError:
    from z_visual import build_synastry_figure

try:
    from module.model_catalog import builtin_standard_model
except ImportError:
    from model_catalog import builtin_standard_model

try:
    from module.workspace import save_workspace_modular, add_or_update_chart
except ImportError:
    from workspace import save_workspace_modular, add_or_update_chart

try:
    from module.streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC, ENGINE_SELECT_OPTIONS, _engine_from_value
except ImportError:
    from streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC, ENGINE_SELECT_OPTIONS, _engine_from_value

try:
    from module.streamlit_ui.streamlit_workspace import (
        _get_focused_chart, _safe_subject_name, _safe_subject_location, _safe_event_dt, _safe_get,
        _store_positions_if_possible, _update_people_list_from_workspace, _focus_chart_by_name,
        _load_workspace_and_sync, _render_ws_report,
    )
except ImportError:
    from streamlit_ui.streamlit_workspace import (
        _get_focused_chart, _safe_subject_name, _safe_subject_location, _safe_event_dt, _safe_get,
        _store_positions_if_possible, _update_people_list_from_workspace, _focus_chart_by_name,
        _load_workspace_and_sync, _render_ws_report,
    )

try:
    from module.streamlit_ui.streamlit_compute import (
        _run_compute, _canonical_positions, _resolve_current_positions, _aspect_orb_overrides,
        _apply_settings_overrides,
    )
except ImportError:
    from streamlit_ui.streamlit_compute import (
        _run_compute, _canonical_positions, _resolve_current_positions, _aspect_orb_overrides,
        _apply_settings_overrides,
    )

try:
    from module.streamlit_ui.streamlit_menus import _left_initial_dialog_menu
except ImportError:
    from streamlit_ui.streamlit_menus import _left_initial_dialog_menu


def _render_aspects_table(positions):
    """Compute and render real aspects for `positions`, using the left panel's
    aspect-type/orb selection (see _left_aspektarium_menu)."""
    try:
        from module.astronomy import compute_normalized_chart_aspects
    except ImportError:
        from astronomy import compute_normalized_chart_aspects

    model = builtin_standard_model()
    selected_ids = st.session_state.get("asp_selected") or model.settings.default_aspects
    aspects = compute_normalized_chart_aspects(
        positions,
        aspect_orbs=_aspect_orb_overrides(selected_ids),
        selected_aspects=selected_ids,
        aspect_definitions=model.aspect_definitions,
    )
    st.markdown("#### Aspekty")
    if not aspects:
        st.info("Žádné aspekty nenalezeny pro zvolený výběr a orb.")
        return
    from pandas import DataFrame
    rows = sorted(aspects, key=lambda a: a["orb"])
    df = DataFrame([
        {
            "Od": a["from"],
            "Do": a["to"],
            "Aspekt": a["type"],
            "Úhel (°)": round(a["angle"], 2),
            "Orb (°)": round(a["orb"], 2),
        }
        for a in rows
    ])
    st.table(df)


def _render_aspektarium_content(engine_choice, eph_path):
    try:
        name, positions = _resolve_current_positions(engine_choice, eph_path)
    except UI_RECOVERABLE_EXC as e:
        import traceback
        error_details = traceback.format_exc()
        st.error(f"Chyba při výpočtu pozic: {e}")
        with st.expander("Detaily chyby", expanded=False):
            st.code(error_details)
    else:
        if not positions:
            st.warning("Nepodařilo se vypočítat pozice.")
        elif isinstance(positions, str):
            st.error(f"Chyba: {positions}")
        else:
            st.markdown("#### Pozice")
            st.table(positions_to_dataframe(positions))
            _render_aspects_table(positions)


def _render_transit_or_direction_content(engine_choice, eph_path, lang, dynamic: bool):
    """Shared content for 'transzit' (transits) and 'dynamika' (directions):
    real transit-to-natal cross-aspect detection via compute_normalized_cross_aspects,
    mirroring the React app's TransitsContent (period mode 'now' vs a date range,
    aspect-type/orb selection, and — for a range — a per-step Date/Bodies/Aspects
    count table). The backend does not yet distinguish directions/progressions
    from transits, so 'dynamika' computes the same way as 'transzit' for now.
    """
    try:
        from module.astronomy import compute_normalized_cross_aspects
    except ImportError:
        from astronomy import compute_normalized_cross_aspects

    key_prefix = "dyn" if dynamic else "tr"
    st.subheader("Direkce" if dynamic else "Transzity")
    if dynamic:
        st.caption("Direkce/progrese zatím používají stejný tranzitní výpočet jako Transzity.")

    try:
        natal_name, natal_positions = _resolve_current_positions(engine_choice, eph_path)
    except UI_RECOVERABLE_EXC as e:
        st.error(f"Chyba při výpočtu natální horoskopu: {e}")
        return
    if not natal_positions:
        st.warning("Nepodařilo se vypočítat natální pozice.")
        return
    st.caption(f"Natální horoskop: **{natal_name}**")

    place = st.session_state.get('ws_default_loc') or st.session_state.get('crt_place') or 'Prague'
    model = builtin_standard_model()
    all_aspect_ids = [a.id for a in model.aspect_definitions]
    selected_aspects = st.multiselect(
        "Aspekty", all_aspect_ids,
        default=st.session_state.get(f"{key_prefix}_selected", model.settings.default_aspects),
        key=f"{key_prefix}_selected",
    )
    st.selectbox("Orb", ["Výchozí", "Těsný (2°)", "Široký (8°)", "Vlastní"], key=f"{key_prefix}_orb_preset")
    if st.session_state.get(f"{key_prefix}_orb_preset") == "Vlastní":
        st.number_input("Vlastní orb (°)", min_value=0.0, max_value=20.0, value=6.0, step=0.5, key=f"{key_prefix}_custom_orb")
    orb_overrides = _aspect_orb_overrides(selected_aspects, key_prefix=key_prefix)

    engine = _engine_from_value(st.session_state.get('settings_engine', engine_choice))
    period_mode = st.radio("Okamžik", ["Nyní", "Rozsah dat"], key=f"{key_prefix}_period_mode", horizontal=True)

    if period_mode == "Nyní":
        if st.button("Vypočítat tranzity", width='stretch', key=f"{key_prefix}_run_now"):
            now = datetime.datetime.now()
            transit_positions = _canonical_positions(
                compute_positions(engine, "Transit", str(now), place, ephemeris_path=eph_path)
            )
            st.markdown(f"#### Tranzitní pozice ({now.strftime('%Y-%m-%d %H:%M')})")
            st.table(positions_to_dataframe(transit_positions))

            st.markdown("#### Radix s tranzitním kruhem")
            st.caption("Vnější kruh zobrazuje tranzitující tělesa nad natálním radixem.")
            natal_chart = _get_focused_chart()
            if natal_chart is None:
                natal_date = st.session_state.get('focused_date') or st.session_state.get('crt_date') or datetime.date.today()
                natal_time = st.session_state.get('focused_time') or st.session_state.get('crt_time') or datetime.datetime.now().time()
                natal_chart = prepare_horoscope(
                    name=natal_name,
                    dt=combine_date_time(natal_date, natal_time),
                    loc=Actual(place, t="place").to_model_location(),
                    engine=engine,
                    ephemeris_path=eph_path,
                )
            try:
                fig = build_radix_figure_for_chart(
                    natal_chart, ws=st.session_state.get('workspace'), transit_positions=transit_positions,
                )
                st.plotly_chart(fig, width='stretch', key=f"chart_{key_prefix}_transit_now")
            except UI_RECOVERABLE_EXC as e:
                st.error(f"Chyba při vykreslení radixu s tranzity: {e}")

            aspects = compute_normalized_cross_aspects(
                transit_positions, natal_positions,
                aspect_orbs=orb_overrides, selected_aspects=selected_aspects,
                aspect_definitions=model.aspect_definitions,
            )
            st.markdown("#### Tranzitní aspekty k natálu")
            if not aspects:
                st.info("Žádné aspekty nenalezeny pro zvolený výběr a orb.")
            else:
                from pandas import DataFrame
                rows = sorted(aspects, key=lambda a: a["orb"])
                st.table(DataFrame([
                    {
                        "Tranzitující": a["from"], "Natální": a["to"], "Aspekt": a["type"],
                        "Úhel (°)": round(a["angle"], 2), "Orb (°)": round(a["orb"], 2),
                    }
                    for a in rows
                ]))
    else:
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("Od", value=datetime.date.today(), key=f"{key_prefix}_from_date")
        with col2:
            to_date = st.date_input("Do", value=datetime.date.today() + datetime.timedelta(days=7), key=f"{key_prefix}_to_date")
        step_days = st.number_input("Krok (dny)", min_value=1, max_value=30, value=1, key=f"{key_prefix}_step_days")
        max_steps = 60  # keep the synchronous UI responsive; each step is a full position+aspect computation
        if st.button("Vypočítat tranzitní sérii", width='stretch', key=f"{key_prefix}_run_series"):
            if to_date < from_date:
                st.error("'Do' musí být po 'Od'.")
            else:
                total_days = (to_date - from_date).days
                num_steps = min(max_steps, max(1, total_days // int(step_days) + 1))
                rows = []
                for i in range(num_steps):
                    day = from_date + datetime.timedelta(days=i * int(step_days))
                    if day > to_date:
                        break
                    dt = datetime.datetime.combine(day, datetime.time(12, 0))
                    transit_positions = _canonical_positions(
                        compute_positions(engine, "Transit", str(dt), place, ephemeris_path=eph_path)
                    )
                    aspects = compute_normalized_cross_aspects(
                        transit_positions, natal_positions,
                        aspect_orbs=orb_overrides, selected_aspects=selected_aspects,
                        aspect_definitions=model.aspect_definitions,
                    )
                    rows.append({"Datum": day.isoformat(), "Tělesa": len(transit_positions), "Aspekty": len(aspects)})
                if total_days // int(step_days) + 1 > max_steps:
                    st.warning(f"Zobrazeno prvních {max_steps} kroků (omezeno pro rychlost UI).")
                from pandas import DataFrame
                st.markdown("#### Tranzitní série")
                st.table(DataFrame(rows))


def _render_informace_content():
    """Reference table of computable bodies (glyph + label), mirroring the React InformationView."""
    st.subheader("Informace")
    st.caption("Přehled všech vypočítatelných objektů horoskopu.")
    model = builtin_standard_model()
    rows = [
        {
            "Glyph": body.glyph,
            "ID": body.id,
            "Label": (body.i18n or {}).get("en", body.id),
            "Type": getattr(body.object_type, "value", body.object_type),
        }
        for body in model.body_definitions
    ]
    from pandas import DataFrame
    st.table(DataFrame(rows))


def _render_revoluce_content():
    """Prepared (not yet computed) page for solar revolution/return charts."""
    st.subheader("Solární revoluce")
    year = st.session_state.get("revoluce_year", datetime.date.today().year)
    st.markdown(
        f"Solární revoluce pro rok **{year}** — okamžik, kdy se Slunce vrátí na svou natální pozici."
    )
    st.info(
        "Výpočet solární revoluce zatím není implementován v `module.services` "
        "(potřebuje nalezení přesného okamžiku návratu Slunce, ne jen statický výpočet). "
        "Tato stránka je připravená pro budoucí zapojení."
    )
    st.button("Vypočítat revoluci", width='stretch', disabled=True)


def _render_synastrie_content(engine_choice, eph_path):
    """Two-subject synastry overlay, using build_synastry_figure (mirrors React's SynastryView)."""
    st.subheader("Synastrie")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Osoba 1**")
        n1 = st.text_input("Jméno", key="syn_n1", value=st.session_state.get('crt_name', ''))
        p1 = st.text_input("Lokalita", key="syn_p1", value=st.session_state.get('crt_place', 'Prague'))
        d1 = st.date_input("Datum", key="syn_d1", value=datetime.date.today())
        t1 = st.time_input("Čas", key="syn_t1", value=datetime.time(12, 0))
    with col2:
        st.markdown("**Osoba 2**")
        n2 = st.text_input("Jméno", key="syn_n2")
        p2 = st.text_input("Lokalita", key="syn_p2", value="Prague")
        d2 = st.date_input("Datum", key="syn_d2", value=datetime.date.today())
        t2 = st.time_input("Čas", key="syn_t2", value=datetime.time(12, 0))

    if not n1 or not n2:
        st.info("Zadejte jméno pro obě osoby.")
        return

    if st.button("Vypočítat synastrii", width='stretch', key="run_synastrie"):
        try:
            s1 = Subject(n1)
            s1.at_place(p1)
            s1.at_time(str(combine_date_time(d1, t1)))
            s2 = Subject(n2)
            s2.at_place(p2)
            s2.at_time(str(combine_date_time(d2, t2)))
            fig = build_synastry_figure(s1.positions, s2.positions, s1.name, s2.name)
            st.plotly_chart(fig, width='stretch', key=f"chart_synastrie_{n1}_{n2}")
        except UI_RECOVERABLE_EXC as e:
            st.error(f"Chyba při výpočtu synastrie: {e}")


def _render_save_content():
    name_val = st.text_input("Jméno", key="save_name", value=st.session_state.get("crt_name", ""))
    # Format is selected in left menu
    save_format = st.session_state.get("save_export_type", "YAML")
    st.markdown(f"**Vybraný formát:** {save_format}")
    st.markdown("#### Cílová cesta")
    st.text_input("Cesta a název souboru", key="save_dest_path")
    if st.button("Uložit", width='stretch', key="do_save"):
        st.success(f"Export ({save_format}) připraven do: {st.session_state.get('save_dest_path')}")


def _render_export_content():
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
        if st.button("Exportovat", width='stretch', type="primary", key="do_export"):
            export_dir = None
            manifest = st.session_state.get("workspace_manifest")
            if manifest:
                export_dir = Path(manifest).parent / "exports"
            else:
                export_dir = Path.cwd() / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            safe_title = "".join(ch.lower() if ch.isalnum() else "-" for ch in (export_title or "export"))
            safe_title = safe_title.strip("-") or "export"
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            export_path = export_dir / f"{safe_title}_{timestamp}.txt"
            lines = [f"Export format: {export_format}"]
            if include_name:
                lines.append(f"Name: {export_title}")
            if include_location:
                loc = _safe_subject_location(focused_chart) or {}
                lines.append(f"Location: {loc.get('name', '')}")
            if include_info:
                subj = _safe_get(focused_chart, 'subject')
                lines.append(f"Event time: {_safe_get(subj, 'event_time')}")
            if include_chart:
                lines.append("Chart: exported separately (not included in text export).")
            if include_aspektarium:
                lines.append("Aspektarium: compute on demand (not included in text export).")
            export_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            st.success(f"Export ({export_format}) uložen: {export_path}")


def _render_notes_content():
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
        if st.button("💾 Uložit poznámku", width='stretch', key="save_note"):
            if note_title and note_content:

                # Create or update annotation
                ann = Annotation(
                    title=note_title,
                    content=note_content,
                    created=now_utc(),
                    author=st.session_state.get("active_user") or st.session_state.get("ws_owner") or "user"
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
                        except UI_RECOVERABLE_EXC as e:
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
        if st.button("❌ Zrušit", width='stretch', key="cancel_note"):
            st.session_state["selected_note"] = None
            st.session_state["editing_note"] = False
            st.rerun()


def _render_settings_content():
    st.subheader("Aplikační nastavení")
    section = st.session_state.get("settings_section", "general")
    if section == "general":
        st.text_input("Výchozí lokalita (text)", key="ws_default_loc")
        st.selectbox("Výchozí systém domů", [
            "Placidus", "Whole Sign", "Campanus", "Koch", "Equal",
            "Regiomontanus", "Vehlow", "Porphyry", "Alcabitius"
        ], key="ws_house_sys")
        st.selectbox("Barvy (téma)", ["default", "dark", "light"], key="ws_color_theme")
        st.selectbox("Výchozí engine", ENGINE_SELECT_OPTIONS, key="ws_default_engine")

        st.markdown("---")
        st.markdown("#### Zodiak")
        zodiac_val = st.selectbox(
            "Typ zodiaku", [ZodiacType.TROPICAL.value, ZodiacType.SIDEREAL.value], key="ws_zodiac_type"
        )
        if zodiac_val == ZodiacType.SIDEREAL.value:
            st.selectbox(
                "Ayanamsa",
                [a.value for a in Ayanamsa],
                key="ws_ayanamsa",
            )
            if st.session_state.get("ws_ayanamsa") == Ayanamsa.USER_DEFINED.value:
                st.caption("Poznámka: 'UserDefined' zatím nemá vlastní číselnou hodnotu — používá se Fagan-Bradley.")

        st.markdown("---")
        st.markdown("#### Pozorované objekty")
        _model = builtin_standard_model()
        all_body_ids = [b.id for b in _model.body_definitions]
        st.multiselect(
            "Výchozí pozorované objekty (prázdné = vše)",
            all_body_ids,
            default=st.session_state.get("ws_observable_objects", []),
            key="ws_observable_objects",
        )

        st.markdown("---")
        st.markdown("#### Aspekty (výchozí pro nové horoskopy)")
        all_aspect_ids = [a.id for a in _model.aspect_definitions]
        st.multiselect(
            "Výchozí aspekty",
            all_aspect_ids,
            default=st.session_state.get("ws_selected_aspects", _model.settings.default_aspects),
            key="ws_selected_aspects",
        )
        st.selectbox(
            "Výchozí orb", ["Výchozí", "Těsný (2°)", "Široký (8°)", "Vlastní"], key="ws_orb_preset"
        )
        if st.session_state.get("ws_orb_preset") == "Vlastní":
            st.number_input("Vlastní orb (°)", min_value=0.0, max_value=20.0, value=6.0, step=0.5, key="ws_custom_orb")

        st.markdown("---")
        st.selectbox("Časový systém", [t.value for t in TimeSystem], key="ws_time_system")

        st.markdown("---")
        ws = st.session_state.get('workspace')
        if ws:
            st.caption(
                "Systém domů / pozorované objekty / aspekty+orb / engine / časový systém jsou "
                "**workspace-úroveň** — platí pro všechny horoskopy, pokud nejsou přepsány "
                "lokálně (viz 'Přepsat lokálně' v levém panelu na stránce Horoskop). "
                "Zodiak/Ayanamsa se aktuálně použijí jako výchozí jen při vytvoření nového "
                "horoskopu v této session (nejsou součástí workspace-úrovně v rozhodovacím řetězci)."
            )
            if st.button("💾 Uložit nastavení workspace", key="ws_settings_save"):
                try:
                    from module.models import HouseSystem
                except ImportError:
                    from models import HouseSystem
                try:
                    house_str = st.session_state.get("ws_house_sys")
                    if house_str:
                        ws.default.default_house_system = HouseSystem[house_str.upper().replace(' ', '_')]
                    observable_objects = st.session_state.get("ws_observable_objects")
                    if observable_objects:
                        ws.default.default_bodies = list(observable_objects)
                    selected_aspects = st.session_state.get("ws_selected_aspects")
                    if selected_aspects:
                        ws.default.default_aspects = list(selected_aspects)
                        orb_overrides = _aspect_orb_overrides(selected_aspects, key_prefix="ws")
                        if orb_overrides:
                            ws.default.default_aspect_orbs = orb_overrides
                    engine_val = st.session_state.get("ws_default_engine")
                    if engine_val:
                        ws.default.ephemeris_engine = _engine_from_value(engine_val)
                    time_system_val = st.session_state.get("ws_time_system")
                    if time_system_val:
                        ws.default.time_system = TimeSystem(time_system_val)
                    ws.default.theme = st.session_state.get("ws_color_theme", ws.default.theme)

                    base_dir = str(Path(st.session_state.workspace_manifest).parent)
                    save_workspace_modular(ws, base_dir)
                    st.success("Nastavení workspace uložena na disk.")
                except UI_RECOVERABLE_EXC as e:
                    st.error(f"Nepodařilo se uložit nastavení workspace: {e}")
        else:
            st.info(
                "Bez načteného workspace se tato nastavení použijí jen jako výchozí při "
                "vytvoření nového horoskopu v této session (nepersistují se na disk)."
            )
    else:
        st.markdown("#### Efemeridy")
        st.session_state["settings_engine"] = "JPL / Skyfield"
        st.caption("Ephemeris Engine: JPL / Skyfield")
        st.text_input(
            "Ephemeris file (de440s.bsp)",
            value=st.session_state.get('settings_eph', default_ephemeris_path()),
            key="settings_eph"
        )
        # Warn users when de421 is selected due to limited body coverage
        eph_sel = st.session_state.get('settings_eph', '') or ''
        if isinstance(eph_sel, str) and 'de421' in Path(eph_sel).name.lower():
            st.info("Poznámka: de421.bsp neobsahuje centra vnějších planet (JUPITER, SATURN, …).\n"
                    "Pro plnou podporu použijte de440s.bsp.")
    st.success("Nastavení připraveno.")


def _render_create_content(engine_choice, eph_path):
    """Mirrors the React app's NewHoroscope screen: name, type, date/time (with
    an auto/manual timezone toggle and an optional Julian Day input), location
    (search-and-confirm or manual lat/lon), tags, and an optional Roden Rating.
    """
    horoscope_name = st.text_input("Jméno", key="crt_name", value=st.session_state.get("crt_name", ""))

    chart_type = st.radio(
        "Typ",
        [ChartMode.NATAL.value, ChartMode.EVENT.value, ChartMode.HORARY.value, ChartMode.COMPOSITE.value],
        key="crt_type",
        horizontal=True,
    )
    st.session_state["chart_type"] = chart_type

    st.markdown("#### Datum a čas")
    time_system = st.radio(
        "Časový systém", ["Gregoriánský", "Juliánský den (JD)"], key="crt_time_system", horizontal=True
    )
    if time_system == "Juliánský den (JD)":
        jd_str = st.text_input("Juliánský den (např. 2451545.0)", key="crt_jd")
        input_date = input_time = None
    else:
        jd_str = None
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            input_time = st.time_input("Čas", key="crt_time", value=datetime.time(12, 0))
        with r2c2:
            input_date = st.date_input("Datum", key="crt_date", value=datetime.date.today())

    tz_mode = st.radio(
        "Časové pásmo", ["Automaticky (dle lokality)", "Manuálně"], key="crt_tz_mode", horizontal=True
    )
    manual_tz = None
    if tz_mode == "Manuálně":
        manual_tz = st.selectbox(
            "Časové pásmo", sorted(zoneinfo.available_timezones()), key="crt_manual_tz"
        )

    st.markdown("#### Lokalita")
    loc_mode = st.radio("Lokalita", ["Vyhledat", "Manuálně (lat/lon)"], key="crt_loc_mode", horizontal=True)
    if loc_mode == "Vyhledat":
        input_location = st.text_input("Lokalita", key="crt_place", value="Prague")
        if st.button("🔍 Vyhledat", key="crt_geocode"):
            try:
                loc_model = Actual(input_location, t="loc").to_model_location()
                if loc_model:
                    st.success(f"{loc_model.name} — {loc_model.latitude:.4f}, {loc_model.longitude:.4f} ({loc_model.timezone})")
                else:
                    st.warning("Lokalitu se nepodařilo najít.")
            except UI_RECOVERABLE_EXC as e:
                st.warning(f"Vyhledávání se nezdařilo: {e}")
    else:
        st.text_input("Název lokality (jen popisek)", key="crt_loc_name", value="")
        c1, c2 = st.columns(2)
        with c1:
            lat = st.number_input(
                "Zeměpisná šířka", min_value=-90.0, max_value=90.0, value=50.0875, step=0.0001,
                format="%.4f", key="crt_lat",
            )
        with c2:
            lon = st.number_input(
                "Zeměpisná délka", min_value=-180.0, max_value=180.0, value=14.4213, step=0.0001,
                format="%.4f", key="crt_lon",
            )
        input_location = f"{lat},{lon}"

    st.markdown("#### Tagy")
    tags_str = st.text_input("Tagy (čárkou oddělené)", key="crt_tags")
    parsed_tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
    if parsed_tags:
        st.markdown(
            " ".join(
                f"<span style='background:rgba(125,125,125,.18);border-radius:8px;"
                f"padding:2px 10px;margin-right:4px;font-size:0.85em'>{t}</span>"
                for t in parsed_tags
            ),
            unsafe_allow_html=True,
        )

    roden_rating = st.selectbox(
        "Roden Rating (přesnost času narození)",
        ["Bez hodnocení", "AA", "A", "B", "C", "DD", "X"],
        key="crt_roden",
    )

    if st.button("Vypočítat a zobrazit", width='stretch', type="primary", key="crt_run"):
        if not horoscope_name:
            st.error("Zadejte jméno.")
            return
        if time_system == "Juliánský den (JD)":
            if not jd_str:
                st.error("Zadejte Juliánský den.")
                return
            try:
                dt_combined = Actual(jd_str, t="date").value
            except UI_RECOVERABLE_EXC as e:
                st.error(f"Neplatný Juliánský den: {e}")
                return
        else:
            dt_combined = combine_date_time(input_date, input_time)

        tags = list(parsed_tags)
        if roden_rating != "Bez hodnocení":
            tags.append(f"roden:{roden_rating}")

        horoscope, fig = _run_compute(horoscope_name, dt_combined, input_location, engine_choice, eph_path)

        # Show table with all computed point data (not just positions)
        positions_df = positions_to_dataframe(horoscope.positions)
        if not positions_df.empty:
            st.table(positions_df)

        # Add chart to workspace if workspace is loaded
        ws = st.session_state.get('workspace')
        if ws:
            try:
                from services import build_chart_instance
                # chart_type and tags were already resolved above from the form fields

                # Build ChartInstance
                dt_str = ensure_aware(dt_combined, manual_tz or Actual(input_location, t="loc").tz).isoformat()
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
                _apply_settings_overrides(chart)
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
            except UI_RECOVERABLE_EXC as e:
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
                from models import Workspace, WorkspaceDefaults, HouseSystem

                # chart_type and tags were already resolved above from the form fields

                # Create a temporary workspace with defaults from initial dialog
                temp_ws = None
                if st.session_state.get('ws_default_engine') or st.session_state.get('ws_default_loc') or st.session_state.get('ws_house_sys'):
                    # Get engine
                    engine = _engine_from_value(st.session_state.get('ws_default_engine')) or EngineType.JPL

                    # Build workspace defaults
                    house_sys_str = st.session_state.get('ws_house_sys', 'Placidus')
                    house_sys = None
                    try:
                        house_sys = HouseSystem[house_sys_str.upper().replace(' ', '_')]
                    except (KeyError, AttributeError, TypeError):
                        house_sys = HouseSystem.PLACIDUS

                    ws_defaults = WorkspaceDefaults(
                        ephemeris_engine=engine if isinstance(engine, EngineType) else EngineType.JPL,
                        ephemeris_backend=None,
                        default_location=None,
                        language=st.session_state.get('settings', {}).get('language', 'cs'),
                        theme=st.session_state.get('ws_color_theme', 'default'),
                        default_house_system=house_sys,
                        default_bodies=None,
                        default_aspects=None,
                    )

                    temp_ws = Workspace(
                        owner="session",
                        active_model="western",
                        chart_presets=[],
                        subjects=[],
                        charts=[],
                        layouts=[],
                        annotations=[],
                        default=ws_defaults
                    )

                # Build ChartInstance with temporary workspace defaults
                dt_str = ensure_aware(dt_combined, manual_tz or Actual(input_location, t="loc").tz).isoformat()
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
                _apply_settings_overrides(chart)
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
            except UI_RECOVERABLE_EXC as e:
                import traceback
                error_details = traceback.format_exc()
                st.error(f"Chyba při ukládání horoskopu: {e}")
                with st.expander("Detaily chyby", expanded=False):
                    st.code(error_details)


def _render_chart_content(engine_choice, eph_path):
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
                st.plotly_chart(fig, width='stretch', key=chart_key)
            except UI_RECOVERABLE_EXC as e:
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
                    engine_override = _engine_from_value(engine_choice_val)
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
                _store_positions_if_possible(focused_chart, positions, engine_override, eph_override)
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
                    st.plotly_chart(fig, width='stretch', key=chart_key)
            except UI_RECOVERABLE_EXC as e:
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
            st.plotly_chart(fig, width='stretch', key=chart_key)
        except UI_RECOVERABLE_EXC as e:
            import traceback
            error_details = traceback.format_exc()
            st.error(f"Chyba při výpočtu pozic: {e}")
            with st.expander("Detaily chyby", expanded=False):
                st.code(error_details)


def _render_interpretation_content():
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
                _store_positions_if_possible(focused_chart, positions, None, None)

                if positions:
                    st.write(f"Interpretace pro: **{selected}**")
                    st.write("")
                    st.write("*(Implementace interpretační logiky bude přidána později)*")
                    st.write("")
                    st.caption(f"Počet vypočítaných pozic: {len(positions)}")
                else:
                    st.warning("Nelze vypočítat pozice pro interpretaci.")
            except UI_RECOVERABLE_EXC as e:
                st.error(f"Chyba při načítání dat pro interpretaci: {e}")


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
            if st.button(name, width='stretch', key=f"footer_btn_{name}", type=button_type):
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
            st.caption("JPL / Skyfield")
            st.session_state["ws_default_engine"] = "JPL"

        elif section == "Manuál":
            st.subheader("Manuál")
            st.info("Dokumentace a návod k použití bude přidán později.")

        # Workspace loading section (moved from open_workspace)
        st.markdown("---")
        st.subheader("Otevřít workspace")
        base_dir = st.text_input("Složka workspace (obsahuje workspace.yaml)", key="init_ws_folder")
        if st.button("Načíst ze složky", width='stretch', key="init_btn_load_folder"):
            try:
                if not base_dir:
                    st.warning("Zadejte cestu ke složce")
                else:
                    workspace_root = (Path.cwd() / "workspaces").resolve()
                    # Validate and resolve path to prevent path traversal attacks
                    try:
                        base_path = resolve_user_path(base_dir, base_dir=workspace_root)
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
            except UI_RECOVERABLE_EXC as e:
                st.error(f"Nelze načíst workspace: {e}")

        # Proceed button
        st.markdown("---")
        if st.button("Pokračovat", width='stretch', type="primary", key="init_proceed"):
            st.session_state.initial_dialog_completed = True
            st.rerun()
