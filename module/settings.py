import pandas as pd
import sqlite3
from pathlib import Path


def settings_file() -> Path:
    # print(f"Returned value: {Path(__file__).parent / 'settings.db'}")
    return Path(__file__).parent / "settings.db"


def change_language(default: str = "cz") -> dict:
    with sqlite3.connect(settings_file()) as dbcon:
        df = pd.read_sql_query("SELECT * FROM language;", dbcon)
    return dict(zip(df["col"], df[default]))


if __name__ == "__main__":
    t = change_language("cz")
    # print(t["display"])
