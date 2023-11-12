from context import Actual
from current import Observation
from display import figure_3d
from represent import Subject
import streamlit as st
from settings import change_language


def main():
    # 1 - initial language setting
    # TODO: language will be read from CSV file
    lang = change_language(default="cz")

    # 2 - set page layout
    st.set_page_config(
        page_title="Astro visualization app",
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
                name1 = st.text_input(lang["name"])
                loc1 = st.text_input(lang["place"])
                start_date = st.date_input(lang["date"], value=Actual().value)
                start_time = st.time_input(lang["time"], Actual().value)
                st.form_submit_button(
                    "Verify setup", use_container_width=True
                )  # TODO: translate, on_click=set1()
    with sidebar_cont["second"]:
        with st.expander(lang["second"]):
            with st.form(key="second_info"):
                name2 = st.text_input(lang["name"])
                loc2 = st.text_input(lang["place"])
                end_date = st.date_input(lang["date"], value=Actual().value)
                end_time = st.time_input(lang["time"], Actual().value)
                st.form_submit_button(
                    "Verify setup", use_container_width=True
                )  # TODO: translate, on_click=set2()
    with sidebar_cont["confirm"]:
        with st.form(key="confirmation"):
            computation = st.selectbox(
                lang["repr"], [lang[val] for val in lang.keys() if "repr_" in val]
            )
            compute = st.form_submit_button(lang["run"])

    # 3 - act if button pressed
    if compute:  # CASE selected custom fields to visualize
        st.write(
            " ".join(
                (lang["display"], name1, lang["in_time"], str(start_date), "loc:", loc1)
            )
        )
        if computation == lang["repr_real"]:
            look = Observation()
            planets = look.where_is(Actual().value, of="altaz")
            figure = figure_3d(planets)
            st.plotly_chart(figure, theme="streamlit", use_container_width=True)
        elif computation == lang["repr_zodi"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(start_date)
            report = someone.report()
            st.write(report.print_report())
        elif computation == lang["repr_hous"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(start_date)
            report = someone.report()
            st.markdown(report.houses_table.replace("+", "|"))
        elif computation == lang["repr_plan"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(start_date)
            report = someone.report()
            st.markdown(report.planets_table.replace("+", "|"))
        elif computation == lang["repr_moon"]:
            someone = Subject(name1)
            someone.at_place(loc1)
            someone.at_time(start_date)
            report = someone.report()
            st.markdown(report.data_table.replace("+", "|"))
    else:
        st.write(lang["run"])


if __name__ == "__main__":
    main()
