"""Minimum speed at every corner for each team's fastest qualifying lap.

For Qualifying (Q) and Sprint Qualifying (SQ) of every completed 2026 round,
takes each team's fastest lap twice -- over the whole session (LapSet='all')
and over the first knockout part only (LapSet='Q1', where every car runs) --
and records the minimum telemetry speed while the car is within RADIUS_M of
each corner marker on the track map. Saves
data/raw/{round}_{Q|SQ}_corners.parquet. Re-runnable: existing files are skipped.

Corners are located by X/Y position, not by distance along the lap: FastF1's
distance is integrated from speed and drifts (up to ~3% per lap), which put
some corner windows on the following straight.

Usage: python scripts/pull_corner_speeds.py
"""
import logging
import warnings
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
fastf1.Cache.enable_cache(str(ROOT / "cache"))
fastf1.set_log_level(logging.ERROR)
warnings.filterwarnings("ignore", category=DeprecationWarning)

YEAR = 2026
RADIUS_M = 60  # metres from the corner marker
UNITS_PER_M = 10  # FastF1 position data is in 1/10 m
FROZEN_RUN = 3  # identical consecutive speed samples that mark a stalled reading


def corner_min_speeds(lap, corners):
    tel = lap.get_telemetry()  # car data merged with X/Y position
    x, y = tel["X"].to_numpy(), tel["Y"].to_numpy()
    rows = []
    for _, c in corners.iterrows():
        dist = np.hypot(x - c["X"], y - c["Y"]) / UNITS_PER_M
        # the stretch of samples around the closest pass, while still within
        # RADIUS_M -- avoids picking up another part of the track that runs nearby
        i0 = int(np.nanargmin(dist))
        lo, hi = i0, i0
        while lo > 0 and dist[lo - 1] <= RADIUS_M:
            lo -= 1
        while hi < len(dist) - 1 and dist[hi + 1] <= RADIUS_M:
            hi += 1
        window = tel.iloc[lo:hi + 1] if dist[i0] <= RADIUS_M else tel.iloc[0:0]
        rows.append({
            "Corner": f"{int(c['Number'])}{c['Letter'] or ''}",
            "ClosestM": round(float(dist[i0]), 1),
            "Samples": len(window),
            "MinSpeed": window["Speed"].min() if len(window) else None,
            "Frozen": frozen_speed(window),
        })
    return rows


def frozen_speed(window, run=FROZEN_RUN):
    """True if the speed channel repeats one value for `run`+ consecutive car
    samples in the window. The 2026 feed sometimes stalls for up to ~1 s, which
    in a corner (where speed always changes) gives a false reading."""
    speeds = window.loc[window["Source"] == "car", "Speed"].to_numpy()
    longest = current = 1
    for a, b in zip(speeds[:-1], speeds[1:]):
        current = current + 1 if a == b else 1
        longest = max(longest, current)
    return bool(len(speeds) and longest >= run)


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
