"""Minimum speed at every corner for each team's fastest qualifying lap.

For Qualifying (Q) and Sprint Qualifying (SQ) of every completed 2026 round,
takes each team's fastest lap twice -- over the whole session (LapSet='all')
and over the first knockout part only (LapSet='Q1', where every car runs) --
and records the minimum telemetry speed within +-WINDOW_M of each corner
marker. Saves data/raw/{round}_{Q|SQ}_corners.parquet. Re-runnable: existing
files are skipped.

Usage: python scripts/pull_corner_speeds.py
"""
import logging
import warnings
from pathlib import Path

import fastf1
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
fastf1.Cache.enable_cache(str(ROOT / "cache"))
fastf1.set_log_level(logging.ERROR)
warnings.filterwarnings("ignore", category=DeprecationWarning)

YEAR = 2026
WINDOW_M = 60  # metres either side of the corner marker


def corner_min_speeds(lap, corners):
    tel = lap.get_car_data().add_distance()
    rows = []
    for _, c in corners.iterrows():
        near = tel[(tel["Distance"] > c["Distance"] - WINDOW_M)
                   & (tel["Distance"] < c["Distance"] + WINDOW_M)]
        rows.append({
            "Corner": f"{int(c['Number'])}{c['Letter'] or ''}",
            "CornerDistance": float(c["Distance"]),
            "MinSpeed": near["Speed"].min() if len(near) else None,
        })
    return rows


def session_rows(s, rnd, ses):
    corners = s.get_circuit_info().corners
    lap_sets = {"all": s.laps}
    try:
        lap_sets["Q1"] = s.laps.split_qualifying_sessions()[0]
    except Exception as e:
        print(f"  could not split {ses} into parts ({e}); 'all' only")
    rows = []
    for lap_set, laps in lap_sets.items():
        for team, team_laps in laps.groupby("Team"):
            lap = team_laps.pick_fastest()
            if lap is None or pd.isna(lap["LapTime"]):
                continue
            try:
                speeds = corner_min_speeds(lap, corners)
            except Exception as e:
                print(f"  {team} {lap_set}: telemetry failed ({e})")
                continue
            for r in speeds:
                rows.append({
                    "Round": rnd, "EventName": s.event["EventName"], "Session": ses,
                    "LapSet": lap_set, "Team": team, "Driver": lap["Driver"],
                    "LapTime": lap["LapTime"], "Compound": lap["Compound"], **r,
                })
    return pd.DataFrame(rows)


def main():
    sched = pd.read_parquet(RAW / "schedule.parquet")
    for _, ev in sched.iterrows():
        rnd = int(ev["RoundNumber"])
        sessions = ["Q"] + (["SQ"] if ev["EventFormat"] == "sprint_qualifying" else [])
        for ses in sessions:
            out = RAW / f"{rnd:02d}_{ses}_corners.parquet"
            if out.exists():
                print(f"R{rnd:02d} {ses}: already saved")
                continue
            try:
                s = fastf1.get_session(YEAR, rnd, ses)
                s.load(laps=True, telemetry=True, weather=False, messages=False)
                df = session_rows(s, rnd, ses)
                df.to_parquet(out, index=False)
                print(f"R{rnd:02d} {ses} {ev['EventName']}: {df['Team'].nunique()} teams, "
                      f"{df['Corner'].nunique()} corners")
            except Exception as e:
                print(f"R{rnd:02d} {ses} {ev['EventName']}: FAILED ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
