import argparse
from context import Actual
from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report, Literal
import sys
from settings import change_language
from visual import display_radial, display_3d


class Relation:
    def __init__(self, person1: object, person2: object) -> None:
        # Set the type, it can be Natal, Synastry or Transit
        type = "Synastry"
        complex = KerykeionChartSVG(person1, chart_type=type, second_obj=person2)
        complex.makeSVG()


class Subject:
    def __init__(self, s_name: str, s_type: str = "Tropic") -> None:
        self.computed = None
        self.name = s_name
        self.place = None
        self.time = None
        self.type = s_type

    def at_place(self, location: object) -> None:
        self.place = Actual(location, t="loc")

    def at_time(self, time: str) -> None:
        self.time = Actual(time, t="date")
        self.computed = AstrologicalSubject(
            self.name,
            self.time.value.year,
            self.time.value.month,
            self.time.value.day,
            self.time.value.hour,
            self.time.value.minute,
            lng=self.place.value.longitude if self.place.value else "",
            lat=self.place.value.latitude if self.place.value else "",
            tz_str=self.place.tz if self.place.value else "",
            city=self.place.value.address if self.place.value else "",
            zodiac_type=Literal[self.type],
            nation="GB",
        )

    def data(self):
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        return Report(self.computed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="basic methods available")
    parser.add_argument("-t", help="interactive text mode", type=str, default="")
    parser.add_argument("-i", help="generate image", type=str, default="")
    parser.add_argument(
        "-l", help="change language ('cz' default)", type=str, default="cz"
    )
    args = parser.parse_args()
    labels = change_language(default=args.l)
    if args.t:
        if args.i:
            print(labels["new"])
            name1 = input(labels["name"])
            place1 = input(labels["place"])
            date1 = input(labels["date"])
            print(labels["new"])
            name2 = input(labels["name"])
            place2 = input(labels["place"])
            date2 = input(labels["date"])
            first = Subject(name1, place1, date1)
            second = Subject(name2, place2, date2)
            chart = Relation(first, second)
        else:
            someone = Subject(input(labels["name"]))
            someone.at_place(input(labels["place"]))
            someone.at_time(input(labels["date"]))
            display_radial(*someone.data())
            # display_3d(*someone.data())
            show = someone.report()
            print(show.print_report())
    else:
        # from streamlit import cli as stcli
        try:
            from streamlit.web import cli as stcli

            sys.argv = ["streamlit", "run", "./smrk/ui_streamlit.py"]
            sys.exit(stcli.main())
        except ImportError:
            import ui_streamlit as st

            print("What?")
            st.main()
