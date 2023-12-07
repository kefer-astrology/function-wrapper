import argparse
from display import display_radial, display_3d
from pathlib import Path
from project import Subject, Relation
import sys
from settings import change_language

def create_dir(location):
    try:
        Path(location).mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"Folder {location} is already there")
    else:
        print(f"Folder {location} was created")


def get_source_file(location: str = "source", file_name="de430.bsp"):
    path = Path(f"./{location}/{file_name}")
    if path.is_file():
        print(f"SPK file ./{location}/{file_name} exists...")
    else:
        print(
            f"SPK file ./{location}/{file_name} downloading, wait some time please..."
        )
        # https://stackoverflow.com/questions/11768214/python-download-a-file-from-an-ftp-server
        import shutil
        import urllib.request as request
        from contextlib import closing

        bsp_location = f"https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/{file_name}"

        with closing(request.urlopen(bsp_location)) as r:
            with open(f"./{location}/{file_name}", "wb") as f:
                shutil.copyfileobj(r, f)
        print(f"SPK file ./{location}/{file_name} downloaded ....")


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
            