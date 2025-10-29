from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


# ---- your domain bits (import-only, keep these light) ----
try:
    from module.domain import Subject, Relation  # optional: your refactored domain
    from module.utils import Actual
    from module.workspace import change_language
    from module.z_visual import display_radial, display_3d
except Exception:
    from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report, Literal  # this should not be here
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


def run_tui():
    print("Kefer Astrology sidecar (TUI)\n")
    print("1) Single Subject quick test")
    print("2) Synastry quick test")
    print("q) Quit")
    choice = input("> ").strip().lower()

    if choice == "1":
        name = input("Name: ")
        place = input("Place: ")
        date = input("Date (YYYY-MM-DD HH:MM): ")
        if Subject is None:
            print("Domain not available. Ensure module/domain.py defines Subject.")
            return 1
        s = Subject(name, place, date)
        # quick smoke: print summary + degrees
        objs, degrees, labels = s.data()
        print("\nObjects:", objs)
        print("Degrees:", degrees)
        try:
            rep = s.report()
            print("\n--- Report ---")
            print(rep.print_report())
        except Exception as e:
            print(f"(report unavailable) {e}")
        return 0

    if choice == "2":
        if Subject is None or Relation is None:
            print("Domain not available. Ensure module/domain.py defines Subject & Relation.")
            return 1
        print("First person:")
        n1 = input("  Name: ")
        p1 = input("  Place: ")
        d1 = input("  Date (YYYY-MM-DD HH:MM): ")
        print("Second person:")
        n2 = input("  Name: ")
        p2 = input("  Place: ")
        d2 = input("  Date (YYYY-MM-DD HH:MM): ")
        s1 = Subject(n1, p1, d1)
        s2 = Subject(n2, p2, d2)
        rel = Relation(s1, s2, chart_type="Synastry")
        try:
            rel.make_svg()
            print("Synastry SVG generated.")
        except Exception as e:
            print(f"Could not render SVG: {e}")
        return 0

    return 0 if choice in ("q", "") else 0


def run_kivy():
    import os
    os.environ["KIVY_NO_ARGS"] = "1"
    # Import lazily so bare installs don’t pull GUI deps
    try:
        from module.ui_kivy import run as kivy_run
    except Exception as e:
        print("Kivy UI not available. Install extras and ensure module/ui_kivy.py exists.")
        print("Try: pip install .[kivy]")
        print(f"Details: {e}")
        return 1
    
    return kivy_run() or 0


def run_streamlit(file: str | None):
    # Use the Streamlit CLI; import happens only if requested
    try:
        from streamlit.web import cli as stcli
    except Exception as e:
        print("Streamlit not available. Install extras.")
        print("Try: pip install .[streamlit]")
        print(f"Details: {e}")
        return 1
    ui = file or "module/ui_streamlit.py"
    sys.argv = ["streamlit", "run", ui]
    return stcli.main()


def run_file(path: str):
    p = Path(path)
    if not p.exists():
        print(f"File not found: {p}")
        return 1
    # Run as a script in its own globals
    runpy.run_path(str(p), run_name="__main__")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="module",
        description="Kefer Astrology sidecar (TUI + UI launchers)",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--tui", action="store_true", help="run simple text UI (default)")
    g.add_argument("--kivy", action="store_true", help="run Kivy UI (module/ui_kivy.py)")
    g.add_argument("--streamlit", action="store_true", help="run Streamlit UI (module/ui_streamlit.py)")
    g.add_argument("--file", type=str, help="run an arbitrary UI Python file")
    parser.add_argument("--lang", default="cz", help="language code (passed to your own modules if needed)")
    args = parser.parse_args(argv)

    # default = TUI if nothing specified
    if not (args.kivy or args.streamlit or args.file):
        return run_tui()

    if args.kivy:
        return run_kivy()

    if args.streamlit:
        return run_streamlit(file=None)

    if args.file:
        return run_file(args.file)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
