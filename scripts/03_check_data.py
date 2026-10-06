"""Step 3: data coverage check, one row per round.

Shows what was downloaded and how clean it is, so gaps are visible before any
metric is computed. Writes reports/tables/data_coverage.csv.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


def read(rnd, ses, kind):
    path = config.RAW_DIR / f"{rnd:02d}_{ses}_{kind}.parquet"
    return pd.read_parquet(path) if path.exists() else None


def pct(series):
    return round(series.mean() * 100)


def main():
    sched = pd.read_parquet(config.RAW_DIR / "schedule.parquet")
    rows = []
    for _, ev in sched.iterrows():
        rnd = int(ev["RoundNumber"])
        laps, res = read(rnd, "R", "laps"), read(rnd, "R", "results")
        row = {"Round": rnd, "Event": ev["EventName"].replace(" Grand Prix", ""),
               "Sprint weekend": ev["EventFormat"] == "sprint_qualifying"}
        if laps is None or res is None:
            row["Note"] = "GP data missing"
            rows.append(row)
            continue
        row.update({
            "GP laps": len(laps),
            "Lap time present %": pct(laps["LapTime"].notna()),
            "Tyre info present %": pct(laps["Compound"].isin(config.DRY_COMPOUNDS + ["INTERMEDIATE", "WET"])),
            "Green-flag laps %": pct(laps["TrackStatus"].astype(str) == "1"),
            "Wet tyres used": bool(laps["Compound"].isin(["INTERMEDIATE", "WET"]).any()),
            "Classified finishers": int(pd.to_numeric(res["ClassifiedPosition"], errors="coerce").notna().sum()),
            "Teams": res["TeamName"].nunique(),
            "Corner speeds (Q)": (config.RAW_DIR / f"{rnd:02d}_Q_corners.parquet").exists(),
        })
        rows.append(row)
    table = pd.DataFrame(rows)
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.TABLES_DIR / "data_coverage.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
