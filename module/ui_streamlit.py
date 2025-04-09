import streamlit as st
from utils import Actual, combine_date_time  #, now_utc
# from z_visual import figure_3d
from services import Subject, extract_kerykeion_points
from workspace import change_language


def main():
    # 1 - initial setting
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
        with st.expander(lang["first_info"]):
            with st.form(key="first_info"):
                event[1]["name"] = st.text_input(lang["name"], key="name1")
                event[1]["input_place"] = st.text_input(lang["place"], key="loc1")
                event[1]["input_date"] = st.date_input(lang["first_date"])
                event[1]["input_time"] = st.time_input(lang["time"])
                event[1]["pressed"] = st.form_submit_button(
                    lang["control"], use_container_width=True
                )
    with sidebar_cont["second"]:
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
    event[1]["datetime"] = combine_date_time(event[1]["input_date"], event[1]["input_time"])
    event[1]["place"] = Actual(event[1]["input_place"], t="place")
    event[2]["datetime"] = combine_date_time(event[2]["input_date"], event[2]["input_time"])
    event[2]["place"] = Actual(event[2]["input_place"], t="place")

    # 5 - dynamic content before computation
    if computation == lang["radix_new"]:
        ### TO-DO Nové nastavení pro horoskop
        st.subheader(lang["settings_radix"])
        with st.form(key="horoscope_form"):
            horoscope_name = st.text_input(lang["name_radix"])
            horoscope_type = st.radio(
                lang["type_radix"],
                (lang["nativity_radix"], lang["event_radix"], lang["horar_radix"]),
                horizontal=True
            )
            tags = st.multiselect("Tag", ["Tag 1", "Tag 2", "Tag 3", "Tag 4"])
            date_type = st.radio(
                lang["date"],
                (lang["date_gre"], lang["date_jul"]),
                horizontal=True
            )
            location = st.write(lang["loc"] + ": rozbalit menu vlevo <<")
            with st.expander(lang["settings_advanced"]):
                daylight_saving_time = st.checkbox("Letní čas - automatické detekování", value=True)
                manual_option = st.radio(
                    "Manuálně",
                    ("NE", "ANO")
                )
                # Submit button
            new_radix_submit_button = st.form_submit_button("Odeslat")

        if new_radix_submit_button:
            st.write(lang["name_radix"], horoscope_name)
            st.write(lang["type_radix"], horoscope_type)
            st.write("Tag:", tags)
            st.write("Datum:", date_type)
            st.write("Letní čas:", "Ano" if daylight_saving_time else "Ne")
            st.write("Manuálně:", manual_option)
    elif computation == lang["radix_open"]:
        st.file_uploader("Select a file to open")
    elif computation == lang["radix_save"]:
        st.file_uploader("Here will be a set of adjustments....")
    elif computation == lang["radix_moon"]:
        st.warning("Moon phases report - not active for now")

    # 6 - act if any button pressed
    if event[1]["pressed"]:
        st.write(f'{lang["name"]}: {event[1]["name"]}')
        st.write(f' {lang["place"]}: {event[1]["place"].value}')
        st.write(f'{lang["first_date"]}: {event[1]["datetime"]}')
    elif event[2]["pressed"]:
        st.write(f'{lang["name"]}: {event[2]["name"]}')
        st.write(f'{lang["place"]}: {event[2]["place"].value}')
        st.write(f'{lang["first_date"]}: {event[2]["datetime"]}')
    elif compute:  # ready for computation
        st.warning(
            f'{lang["display"]} {event[1]["name"]}: {lang["first_date"]} {event[1]["datetime"]} / {lang["loc"]} {event[1]["place"]}'
        )
        horoscope = Subject(event[1]["name"])  # , s_type="Sidereal"
        horoscope.at_place(event[1]["place"])
        horoscope.at_time(event[1]["datetime"])
        report = horoscope.report()
        st.table(extract_kerykeion_points(horoscope.computed))
        st.write(report.print_report())
        st.markdown(report.houses_table.replace("+", "|"))
        st.markdown(report.planets_table.replace("+", "|"))
    else:  # default display
        st.warning(lang["run"])

if __name__ == "__main__":
    main()
