import datetime
import streamlit as st

from models import ChartInstance, Location, ChartSubject, ChartConfig
from utils import Actual, parse_sfs_content, combine_date_time, prepare_horoscope  #, now_utc
# from z_visual import figure_3d
from services import Subject, extract_kerykeion_points
from workspace import change_language


def main():
    # 1 - initial setting
    if 'settings' not in st.session_state:
        st.session_state["settings"] = {
            "chart": None,
            "language": change_language(default="cz"),
            "tags": ["Tag 1", "Tag 2", "Tag 3", "Tag 4"]
        }
    lang = change_language(default="cz")

    # 2 - set page layout
    st.set_page_config(
        page_title="Kefer Astrology",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 3 - sidebar containers
    sidebar_cont = {
        "first": st.sidebar.container(),
        "second": st.sidebar.container(),
        "selector": st.sidebar.container()
    }

    # 4 - events are kept together (connect to the content)
    event = { 1: {}, 2: {} }

    with sidebar_cont["first"]:
        with st.expander(lang["settings_radix"]):
            horoscope_name = st.text_input(lang["name_radix"])
            horoscope_type = st.radio(
                lang["type_radix"],
                (lang["nativity_radix"], lang["event_radix"], lang["horar_radix"]),
                horizontal=True
            )
            tags = st.multiselect("Tag", st.session_state['settings']['tags'])
            date_type = st.radio(
                lang["date"],
                (lang["date_gre"], lang["date_jul"]),
                horizontal=True
            )
            input_location = st.text_input(lang["place"], key="location")
            input_date = st.date_input(lang["first_date"], key="input_date")
            input_time = st.time_input(lang["time"], key="input_time")
            # with st.form(key="first_info"):
            #     event[1]["name"] = st.text_input(lang["name"], key="name1")
            #     event[1]["input_place"] = st.text_input(lang["place"], key="loc1")
            #     event[1]["input_date"] = st.date_input(lang["first_date"])
            #     event[1]["input_time"] = st.time_input(lang["time"])
            #     event[1]["pressed"] = st.form_submit_button(
            #         lang["control"], use_container_width=True
            #     )
    with sidebar_cont["second"]:
        with st.expander(lang["settings_advanced"]):
            daylight_saving_time = st.checkbox("Letní čas - automatické detekování", value=True)
            manual_option = st.radio(
                "Manuálně",
                ("NE", "ANO")
            )
            # Submit button
        with st.expander(lang["second_info"]):
            with st.form(key="second_info"):
                event[2]["name"] = st.text_input(lang["name"])
                event[2]["input_place"] = st.text_input(lang["place"])
                event[2]["input_date"] = st.date_input(lang["first_date"])
                event[2]["input_time"] = st.time_input(lang["time"])
                event[2]["pressed"] = st.form_submit_button(
                    lang["control"], use_container_width=True
                )
    with sidebar_cont["selector"]:
        #with st.form(key="confirmation"):
            # This will make sure the state updates properly on each selection change
            computation = st.radio(
                lang["repr"],
                [lang[val] for val in lang.keys() if "radix_" in val],
                key="computation_selector"  # Ensure Streamlit distinguishes between updates
            )
            # Button to trigger computation
            compute = st.button(lang["run"])

    # Put dates, times and places together
    event[1]["datetime"] = combine_date_time(input_date, input_time)
    event[1]["place"] = Actual(input_location, t="place")
    #event[2]["datetime"] = combine_date_time(event[2]["input_date"], event[2]["input_time"])
    #event[2]["place"] = Actual(event[2]["input_place"], t="place")

    # 5 - dynamic content before computation
    if computation == lang["radix_new"]:
        ### TO-DO Nové nastavení pro horoskop
        st.warning(
            f'{lang["display"]} {horoscope_name}: {lang["first_date"]} {event[1]["datetime"]} / {lang["loc"]} {input_location}'
        )
    elif computation == lang["radix_open"]:
        uploaded_file = st.file_uploader("Select a file to open", type=["sfs"])
        if uploaded_file is not None:
            encodings = ["utf-8-sig", "utf-16", "latin-1"]
            content = None
            for enc in encodings:
                try:
                    uploaded_file.seek(0)
                    content = uploaded_file.read().decode(enc)
                    break
                except Exception:
                    continue
            if content is None:
                st.error("Could not decode file with utf-8, utf-16, or latin-1.")
            else:
                try:
                    astro_model, display_config = parse_sfs_content(content)
                    st.success("SFS file loaded successfully!")
                    st.write(f"Model name: {astro_model.name}")
                    st.write(f"Bodies: {astro_model.body_definitions}")
                    st.write(f"Aspects: {len(astro_model.aspect_definitions)}")
                    st.write(f"Signs: {len(astro_model.signs)}")
                    st.write("Display config:", display_config)
                except Exception as e:
                    st.error(f"Failed to parse SFS file: {e}")

    elif computation == lang["radix_save"]:
        st.file_uploader("Here will be a set of adjustments....")
    elif computation == lang["radix_moon"]:
        st.warning("Moon phases report - not active for now")

    # 6 - act if any button pressed
    # if event[1]["pressed"]:
    #     st.write(f'{lang["name"]}: {event[1]["name"]}')
    #     st.write(f' {lang["place"]}: {event[1]["place"].value}')
    #     st.write(f'{lang["first_date"]}: {event[1]["datetime"]}')
    # elif event[2]["pressed"]:
    #     st.write(f'{lang["name"]}: {event[2]["name"]}')
    #     st.write(f'{lang["place"]}: {event[2]["place"].value}')
    #     st.write(f'{lang["first_date"]}: {event[2]["datetime"]}')
    if compute:  # ready for computation
        st.session_state["settings"]["chart"] = prepare_horoscope(name=horoscope_name, dt=event[1]["datetime"], loc=event[1]["place"])
        horoscope = Subject(horoscope_name)  # , s_type="Sidereal"
        horoscope.at_place(input_location)
        horoscope.at_time(event[1]["datetime"])
        report = horoscope.report()
        st.table(extract_kerykeion_points(horoscope.computed))
        #st.write(report.print_report())
        #st.markdown(report.houses_table.replace("+", "|"))
        #st.markdown(report.planets_table.replace("+", "|"))
    else:  # default display
        st.warning(lang["run"])

if __name__ == "__main__":
    main()
