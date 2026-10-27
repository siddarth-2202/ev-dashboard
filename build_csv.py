"""Turn the scraper's per-RTO CSV files into data/ev_data.csv for the dashboard.

Usage (from the ev-dashboard folder):
    python build_csv.py "H:\\Python scripts\\vahan-scraper\\vahan-scraper-main\\vahan_data" --strict
"""
import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# RTO code (as in the portal's folder names) -> label shown on the dashboard.
RTOS = {
    "KA1": "Bengaluru Central (KA1)",
    "KA2": "Bengaluru West (KA2)",
    "KA3": "Bengaluru East (KA3)",
    "KA4": "Bengaluru North (KA4)",
    "KA5": "Bengaluru South (KA5)",
    "KA41": "Jnanabharathi (KA41)",
    "KA50": "Yelahanka (KA50)",
    "KA51": "Electronic City (KA51)",
    "KA53": "Krishnarajapuram (KA53)",
    "KA59": "Chandapura (KA59)",
}
# Vahan fuel name -> dashboard category. Two fuel names can share one category:
# Vahan moved vehicles from PETROL/HYBRID to PETROL(E20)/HYBRID, so they are added together.
FUELS = {
    "ELECTRIC(BOV)": "Electric (BOV)",
    "PURE EV": "Pure EV",
    "STRONG HYBRID EV": "Strong Hybrid EV",
    "PETROL/HYBRID": "Petrol Hybrid (incl. E20)",
    "PETROL(E20)/HYBRID": "Petrol Hybrid (incl. E20)",
    "DIESEL/HYBRID": "Diesel Hybrid",
}
CATEGORIES = list(dict.fromkeys(FUELS.values()))


def to_number(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0).astype(int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vahan_dir", help="the vahan_data folder created by the scraper")
    ap.add_argument("--out", default="data/ev_data.csv")
    ap.add_argument("--strict", action="store_true",
                    help="refuse to overwrite the file if the new data looks wrong")
    args = ap.parse_args()

    files = sorted(Path(args.vahan_dir).glob("*/*/Fuel__Month_Wise/*.csv"))
    if not files:
        sys.exit("No scraper files found. Check the folder path.")

    parts = []
    for f in files:
        m = re.search(r"_-_(KA\d+)__", f.parent.parent.name)
        if not m or m.group(1) not in RTOS or not f.stem.isdigit():
            continue
        code, year = m.group(1), int(f.stem)
        df = pd.read_csv(f, dtype=str)
        df["Fuel"] = df["Fuel"].str.strip().str.upper()
        df = df[df["Fuel"].isin(FUELS)]
        got = {}
        for fuel, n in zip(df["Fuel"], to_number(df["TOTAL"])):
            got[FUELS[fuel]] = got.get(FUELS[fuel], 0) + int(n)
        for cat in CATEGORIES:  # a missing fuel counts as 0, as in the old sheet
            parts.append((year, RTOS[code], cat, got.get(cat, 0)))

    out = pd.DataFrame(parts, columns=["year", "rto_location", "vehicle_category", "registrations"])
    out = out.sort_values(["year", "rto_location", "vehicle_category"])

    # Safety checks: never replace good data with a broken scrape.
    problems = []
    new_tot = out.groupby("year")["registrations"].sum()
    for y, g in out.groupby("year"):
        n = g["rto_location"].nunique()
        if n != len(RTOS):
            problems.append(f"{y}: only {n} of {len(RTOS)} RTOs found")
    if Path(args.out).exists():
        old_tot = pd.read_csv(args.out).groupby("year")["registrations"].sum()
        for y, ov in old_tot.items():
            nv = int(new_tot.get(y, 0))
            if nv < 0.85 * ov:
                problems.append(f"{y}: total fell from {ov:,} to {nv:,}")
    for p in problems:
        print("PROBLEM:", p)
    if problems and args.strict:
        sys.exit("Not overwriting the existing file.")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    # Record the refresh date (India time) so the dashboard can show "Last updated".
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat()
    Path(args.out).with_name("last_updated.txt").write_text(today + "\n")

    print(f"Wrote {len(out)} rows to {args.out}")
    print("\nRegistrations per category and year:")
    print(out.pivot_table(index="vehicle_category", columns="year", values="registrations", aggfunc="sum")
          .to_string(float_format=lambda v: f"{v:,.0f}"))


if __name__ == "__main__":
    main()
