"""Rounds x fields completeness table for the saved parquet files.

Usage: python scripts/check_completeness.py
"""
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def pct(df, col):
    return round(df[col].notna().mean() * 100) if col in df.columns else None


def main():
    sched = pd.read_parquet(RAW / "schedule.parquet")
    rows = []
    for _, ev in sched.iterrows():
        rnd = int(ev["RoundNumber"])
        row = {"Rnd": rnd, "Event": ev["EventName"].replace(" Grand Prix", "")}
        try:
            rl = pd.read_parquet(RAW / f"{rnd:02d}_R_laps.parquet")
            rr = pd.read_parquet(RAW / f"{rnd:02d}_R_results.parquet")
            ql = pd.read_parquet(RAW / f"{rnd:02d}_Q_laps.parquet")
        except FileNotFoundError as e:
            row["Missing"] = Path(e.filename).name
            rows.append(row)
            continue
        green = rl["TrackStatus"].astype(str).eq("1")
        row.update({
            "R laps": len(rl),
            "LapTime%": pct(rl, "LapTime"),
            "Tyre%": min(pct(rl, "Compound"), pct(rl, "TyreLife"), pct(rl, "Stint")),
            "Green%": round(green.mean() * 100),
            "Accurate%": round(rl["IsAccurate"].mean() * 100),
            "Wet": rl["Compound"].isin(["INTERMEDIATE", "WET"]).any(),
            "Compounds": "/".join(sorted(rl["Compound"].dropna().unique()))[:24],
            "Classified": pd.to_numeric(rr["ClassifiedPosition"], errors="coerce").notna().sum(),
            "Grid0": (rr["GridPosition"] == 0).sum(),
            "Q laps": len(ql),
            "QSector%": min(pct(ql, f"Sector{i}Time") for i in (1, 2, 3)),
            "Teams": rr["TeamName"].nunique(),
        })
        rows.append(row)
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
