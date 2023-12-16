import argparse
from display import display_radial, display_3d
from pathlib import Path
from project import Subject, Relation
import sys
from settings import change_language


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
            