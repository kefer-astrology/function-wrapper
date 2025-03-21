from context import Actual, combine_date_time, now
from z_visual import figure_3d
from project import Subject
import streamlit as st
from settings import change_language


def main():
    # 1 - initial setting
    lang = change_language(default="cz")

    # 2 - set page layout
    st.set_page_config(
        page_title="Astro visualization application",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # st.title("Astro - visualizer")
    sidebar_cont = {
        "first": st.sidebar.container(),
        "second": st.sidebar.container(),
        "confirm": st.sidebar.container(),
    }

    with sidebar_cont["first"]:
        with st.expander(lang["first"]):
            with st.form(key="first_info"):
                name1 = st.text_input(lang["name"], key="name1")
                loc1 = st.text_input(lang["place"], key="loc1")
                date1 = st.date_input(lang["date"])
                date1_time = st.time_input(lang["time"])
                event1 = st.form_submit_button(
                    lang["control"], use_container_width=True
                )
    with sidebar_cont["second"]:
        with st.expander(lang["second"]):
            with st.form(key="second_info"):
                name2 = st.text_input(lang["name"])
                loc2 = st.text_input(lang["place"])
                date2 = st.date_input(lang["date"])
                date2_time = st.time_input(lang["time"])
                event2 = st.form_submit_button(
                    lang["control"], use_container_width=True
                )
    with sidebar_cont["confirm"]:
        with st.form(key="confirmation"):
            computation = st.radio(
                lang["repr"], [lang[val] for val in lang.keys() if "repr_" in val]
            )
            compute = st.form_submit_button(lang["run"])

    first_event = combine_date_time(date1, date1_time)
    first_event_place = Actual(loc1, t="place")
    second_event = combine_date_time(date2, date2_time)
    second_event_place = Actual(loc2, t="place")
    # 3 - act if any button pressed
    if event1:
        st.write(f"{lang['name']}: {name1}")
        st.write(f" {lang['place']}: {first_event_place.value}")
        st.write(f"{lang['date']}: {first_event}")
    elif event2:
        st.write(f"{lang['name']}: {name2}")
        st.write(f" {lang['place']}: {second_event_place.value}")
        st.write(f"{lang['date']}: {second_event}")
    elif compute:  # ready for computation
        st.warning(
            f'{lang["display"]} {name1}: {lang["date"]} {first_event} / {lang["loc"]} {first_event_place}'
        )
        if computation == lang["repr_tropic"]:
            someone = Subject(name1)
            someone.at_place(first_event_place)
            someone.at_time(first_event)
            report = someone.report()
            st.write(report.print_report())
        elif computation == lang["repr_sider"]:
            someone = Subject(name1, s_type="Sidereal")
            someone.at_place(first_event)
            someone.at_time(first_event)
            # report = someone.report()
            # st.write(report.print_report())
        elif computation == lang["repr_hous"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(date1)
            report = someone.report()
            st.markdown(report.houses_table.replace("+", "|"))
        elif computation == lang["repr_plan"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(date1)
            report = someone.report()
            st.markdown(report.planets_table.replace("+", "|"))
        elif computation == lang["repr_moon"]:
            st.warning("Moon phases report - not active for now")
    else:
        st.write(lang["run"])


if __name__ == "__main__":
    main()
