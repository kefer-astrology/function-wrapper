import argparse
from display import display_radial, display_3d
from pathlib import Path
from represent import Subject, Relation
from translation import change_language


def create_dir(dir_name):
    """try to create directory and continue of exists
    %dir_name% path to directory
    """
    try:
        Path(dir_name).mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"Folder {dir_name} is already there")
    else:
        print(f"Folder {dir_name} was created")


def get_source_file(dir_name: str = "source", file_name="de430.bsp"):
    path = Path(f"./{dir_name}/{file_name}")
    if path.is_file():
        print(f"SPK file ./{dir_name}/{file_name} exists...")
    else:
        print(
            f"SPK file ./{dir_name}/{file_name} downloading, wait some time please..."
        )
        # https://stackoverflow.com/questions/11768214/python-download-a-file-from-an-ftp-server
        import shutil
        import urllib.request as request
        from contextlib import closing

        bsp_location = f"https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/{file_name}"

        with closing(request.urlopen(bsp_location)) as r:
            with open(f"./{dir_name}/{file_name}", "wb") as f:
                shutil.copyfileobj(r, f)
        print(f"SPK file ./{dir_name}/{file_name} downloaded ....")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="basic methods available")
    parser.add_argument("-s", help="simple zodiac chart", type=str, default="")
    parser.add_argument("-i", help="generate image", type=str, default="")
    parser.add_argument(
        "-l", help="change language (english default)", type=str, default="cz"
    )
    args = parser.parse_args()
    labels = change_language(args.l)
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
        someone.report()
