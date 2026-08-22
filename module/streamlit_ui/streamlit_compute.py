"""Astro-computation glue for the Streamlit UI: resolving which positions to
show, running a single compute, and applying Settings-page overrides."""
import datetime
import streamlit as st
from pathlib import Path

try:
    from module.models import EngineType, ZodiacType, Ayanamsa, TimeSystem
except ImportError:
    from models import EngineType, ZodiacType, Ayanamsa, TimeSystem

try:
    from module.utils import Actual, combine_date_time, prepare_horoscope
except ImportError:
    from utils import Actual, combine_date_time, prepare_horoscope

try:
    from module.services import Subject, compute_positions, build_radix_figure_for_chart
except ImportError:
    from services import Subject, compute_positions, build_radix_figure_for_chart

try:
    from module.z_visual import _canonical_positions
except ImportError:
    from z_visual import _canonical_positions

try:
    from module.streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC, _engine_from_value
except ImportError:
    from streamlit_ui.streamlit_common import UI_RECOVERABLE_EXC, _engine_from_value

try:
    from module.streamlit_ui.streamlit_workspace import (
        _get_focused_chart, _safe_subject_name, _safe_subject_location, _store_positions_if_possible,
    )
except ImportError:
    from streamlit_ui.streamlit_workspace import (
        _get_focused_chart, _safe_subject_name, _safe_subject_location, _store_positions_if_possible,
    )


def _run_compute(name, dt, place, engine_choice, eph_path):
    engine = EngineType.JPL if str(engine_choice).startswith("JPL") else None
    eph_override = eph_path if engine == EngineType.JPL else None

    chart = prepare_horoscope(
        name=name,
        dt=dt,
        loc=Actual(place, t="place").to_model_location(),
        engine=engine,
        ephemeris_path=eph_override,
    )
    st.session_state["settings"]["chart"] = chart
    horoscope = Subject(name)
    horoscope.at_place(place)
    horoscope.at_time(dt)
    try:
        # Routed through the same build_radix_figure_for_chart the real "chart" page uses
        # (not a bare compute_positions + build_radix_figure call), so the create-new preview
        # renders identically to every other chart in the app: canonical body set, real house
        # cusps/axes, and aspect lines - instead of a separately-assembled, out-of-sync figure.
        fig = build_radix_figure_for_chart(chart, engine_override=engine, ephemeris_path_override=eph_override)
    except UI_RECOVERABLE_EXC as e:
        # Log the error message first (as requested)
        msg = str(e)
        st.error(f"Chyba při výpočtu pozic: {msg}")

        # Handle common Skyfield kernel limitations
        # Note: compute_jpl_positions now automatically uses barycenters for Jupiter/Saturn with de421
        if eph_override and "de421" in Path(eph_override).name.lower():
            st.warning("Zvolený soubor efemerid de421.bsp - používá se barycentrum pro Jupiter a Saturn.\n"
                       "Pokud stále selhává, doporučeno: použijte de440s.bsp.")
        raise
    return horoscope, fig


def _resolve_current_positions(engine_choice, eph_path):
    """Resolve (name, positions) for the focused chart or current-sky fallback,
    honoring an active astrolab time shift. Used by 'aspektarium' to avoid
    duplicating the focused-chart/no-workspace branching four times.
    """
    from services import compute_positions_for_chart

    focused_chart = _get_focused_chart()
    ws = st.session_state.get('workspace')
    astrolab_active = st.session_state.get("astrolab_active")
    shifted_date = st.session_state.get("astrolab_shifted_date")
    shifted_time = st.session_state.get("astrolab_shifted_time")
    engine_choice_val = st.session_state.get('settings_engine', engine_choice)
    eph_path_val = st.session_state.get('settings_eph', eph_path)
    engine = _engine_from_value(engine_choice_val)

    if focused_chart:
        name = _safe_subject_name(focused_chart) or 'Radix'
        if astrolab_active and shifted_date and shifted_time:
            place_obj = _safe_subject_location(focused_chart) or {}
            place = place_obj.get('name') or 'Prague'
            dtc = combine_date_time(shifted_date, shifted_time)
            positions = compute_positions(engine, name, str(dtc), place, ephemeris_path=eph_path_val)
        else:
            positions = compute_positions_for_chart(focused_chart, ws=ws)
            _store_positions_if_possible(focused_chart, positions, None, None)
        return name, _canonical_positions(positions)

    name = st.session_state.get('crt_name') or st.session_state.get('current_person_name') or 'Radix'
    place = (st.session_state.get('ws_default_loc') or
             st.session_state.get('focused_place') or
             st.session_state.get('crt_place') or
             'Prague')
    if astrolab_active:
        date = shifted_date or datetime.date.today()
        time = shifted_time or datetime.datetime.now().time()
    else:
        date = st.session_state.get('focused_date') or st.session_state.get('crt_date') or datetime.date.today()
        time = st.session_state.get('focused_time') or st.session_state.get('crt_time') or datetime.datetime.now().time()
    dtc = combine_date_time(date, time)
    positions = compute_positions(engine, name, str(dtc), place, ephemeris_path=eph_path_val)
    return name, _canonical_positions(positions)


def _aspect_orb_overrides(selected_ids, key_prefix="asp"):
    preset = st.session_state.get(f"{key_prefix}_orb_preset", "Výchozí")
    if preset == "Těsný (2°)":
        return {aid: 2.0 for aid in selected_ids}
    if preset == "Široký (8°)":
        return {aid: 8.0 for aid in selected_ids}
    if preset == "Vlastní":
        custom_orb = st.session_state.get(f"{key_prefix}_custom_orb", 6.0)
        return {aid: custom_orb for aid in selected_ids}
    return None  # "Výchozí": use each aspect's own default_orb


def _apply_settings_overrides(chart) -> None:
    """Apply the enriched Settings page's session-state values onto a newly
    built ChartInstance's config, so zodiac/ayanamsa/observable-objects/aspect
    selections actually affect computation instead of sitting inert."""
    cfg = chart.config
    zodiac_val = st.session_state.get("ws_zodiac_type")
    if zodiac_val:
        cfg.zodiac_type = ZodiacType(zodiac_val)
        if zodiac_val == ZodiacType.SIDEREAL.value:
            ayanamsa_val = st.session_state.get("ws_ayanamsa")
            if ayanamsa_val:
                cfg.ayanamsa = Ayanamsa(ayanamsa_val)

    observable_objects = st.session_state.get("ws_observable_objects")
    if observable_objects:
        cfg.observable_objects = list(observable_objects)

    selected_aspects = st.session_state.get("ws_selected_aspects")
    if selected_aspects:
        cfg.selected_aspects = list(selected_aspects)
        orb_overrides = _aspect_orb_overrides(selected_aspects, key_prefix="ws")
        if orb_overrides:
            cfg.aspect_orbs = orb_overrides

    time_system_val = st.session_state.get("ws_time_system")
    if time_system_val:
        cfg.time_system = TimeSystem(time_system_val)
