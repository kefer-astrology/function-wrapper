from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


def run_tui():
    # Lazy import - only needed for TUI
    try:
        from module.services import Subject
        from module.utils import Actual
        from module.ui_translations import change_language
        from module.z_visual import display_radial, display_3d
        from module.services import create_relation_svg
    except ImportError:
        # Fallback for direct execution
        try:
            from services import Subject, create_relation_svg
            from utils import Actual
            from ui_translations import change_language
            from z_visual import display_radial, display_3d
        except ImportError as e:
            print(f"Failed to import required modules: {e}")
            print("\nMake sure you have installed the required dependencies:")
            print("  pip install -r requirements/base.txt")
            return 1
    print("Kefer Astrology sidecar (TUI)\n")
    print("1) Single Subject quick test")
    print("2) Synastry quick test")
    print("q) Quit")
    choice = input("> ").strip().lower()

    if choice == "1":
        name = input("Name: ")
        place = input("Place: ")
        date = input("Date (YYYY-MM-DD HH:MM): ")
        try:
            s = Subject(name)
            s.at_place(place)
            s.at_time(date)
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
        except Exception as e:
            print(f"Error creating subject: {e}")
            return 1
        return 0

    if choice == "2":
        print("First person:")
        n1 = input("  Name: ")
        p1 = input("  Place: ")
        d1 = input("  Date (YYYY-MM-DD HH:MM): ")
        print("Second person:")
        n2 = input("  Name: ")
        p2 = input("  Place: ")
        d2 = input("  Date (YYYY-MM-DD HH:MM): ")
        try:
            s1 = Subject(n1)
            s1.at_place(p1)
            s1.at_time(d1)
            s2 = Subject(n2)
            s2.at_place(p2)
            s2.at_time(d2)
            # Use create_relation_svg from services
            from kerykeion import AstrologicalSubject
            chart = create_relation_svg(s1.computed, s2.computed, chart_type="Synastry")
            print("Synastry SVG generated.")
        except Exception as e:
            print(f"Could not render SVG: {e}")
            return 1
        return 0

    return 0 if choice in ("q", "") else 0


def run_kivy():
    import os
    os.environ["KIVY_NO_ARGS"] = "1"
    # Import lazily so bare installs don’t pull GUI deps
    try:
        from module.ui_kivy import run as kivy_run
    except Exception as e:
        print("Kivy UI not available. Install dependencies:")
        print("  pip install -r requirements/kivy.txt")
        print(f"Details: {e}")
        return 1
    
    return kivy_run() or 0


def run_streamlit(file: str | None):
    # Use the Streamlit CLI; import happens only if requested
    try:
        from streamlit.web import cli as stcli
    except Exception as e:
        print("Streamlit not available. Install dependencies:")
        print("  pip install -r requirements/streamlit.txt")
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
