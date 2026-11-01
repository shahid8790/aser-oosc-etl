"""Step 1 - Extract and load.

Copies the 9 raw ASER 2012 Excel files into PostgreSQL unchanged
(column names are lower-cased so SQL needs no quoting).
Re-running is safe: each raw table is replaced.

Run: python 1_extract.py
"""
import sys

import pandas as pd

from db import DATA_DIR, get_engine

FILES = [
    "0tblProvince.xlsx", "1tblDistricts.xlsx", "2tblVillages.xlsx",
    "3VillageMapSurvey.xlsx", "4Household.xlsx", "5tlbHHChild.xlsx",
    "6Mother_Data.xlsx", "7Pvt_School.xlsx", "8Gov_School.xlsx",
]


def main():
    missing = [f for f in FILES if not (DATA_DIR / f).exists()]
    if missing:
        sys.exit(
            f"Missing files in {DATA_DIR}:\n  " + "\n  ".join(missing)
            + "\nSee data/README.md for how to obtain them."
        )

    engine = get_engine()
    for f in FILES:
        print(f"Loading {f} ...")
        df = pd.read_excel(DATA_DIR / f)
        df.columns = df.columns.str.lower()
        table = "raw_" + f.replace(".xlsx", "").lower()  # 5tlbHHChild.xlsx -> raw_5tlbhhchild
        df.to_sql(table, engine, if_exists="replace", index=False)
        print(f"  -> {table}: {len(df):,} rows")
    print("Extract complete: 9 raw tables loaded.")


if __name__ == "__main__":
    main()
