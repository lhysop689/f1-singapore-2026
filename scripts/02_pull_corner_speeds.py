"""Step 2: minimum speed at every corner for each team's fastest qualifying lap.

For Qualifying (Q) and Sprint Qualifying (SQ) of every round in scope, takes
each team's fastest lap twice -- over the whole session (LapSet='all') and over
the first knockout part only (LapSet='Q1', the one used by the analysis) -- and
records the minimum telemetry speed while the car is within
config.CORNER_RADIUS_M of each corner marker. Saves
data/raw/{round}_{Q|SQ}_corners.parquet; existing files are skipped.

Two 2026 telemetry problems are handled here:
- Corners are located by X/Y track position, not distance along the lap,
  because FastF1's distance is integrated from speed and drifts (up to ~3%).
- Stalled speed readings (one value repeated for config.FROZEN_RUN+ samples)
  are flagged in the `Frozen` column and dropped later by src/metrics.py.
"""
import logging
import sys
import warnings
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

warnings.filterwarnings("ignore", category=DeprecationWarning)
UNITS_PER_M = 10  # FastF1 position data is in 1/10 m


def frozen_speed(window):
    """True if the speed channel repeats one value for FROZEN_RUN+ consecutive car samples."""
    speeds = window.loc[window["Source"] == "car", "Speed"].to_numpy()
    longest = current = 1
    for a, b in zip(speeds[:-1], speeds[1:]):
        current = current + 1 if a == b else 1
        longest = max(longest, current)
    return bool(len(speeds) and longest >= config.FROZEN_RUN)


def corner_min_speeds(lap, corners):
    tel = lap.get_telemetry()  # car data merged with X/Y position
    x, y = tel["X"].to_numpy(), tel["Y"].to_numpy()
    rows = []
    for _, c in corners.iterrows():
        dist = np.hypot(x - c["X"], y - c["Y"]) / UNITS_PER_M
        # the stretch of samples around the closest pass, while still within the
        # radius -- avoids picking up another part of the track that runs nearby
        i0 = int(np.nanargmin(dist))
        lo, hi = i0, i0
        while lo > 0 and dist[lo - 1] <= config.CORNER_RADIUS_M:
            lo -= 1
        while hi < len(dist) - 1 and dist[hi + 1] <= config.CORNER_RADIUS_M:
            hi += 1
        window = tel.iloc[lo:hi + 1] if dist[i0] <= config.CORNER_RADIUS_M else tel.iloc[0:0]
        rows.append({
            "Corner": f"{int(c['Number'])}{c['Letter'] or ''}",
            "ClosestM": round(float(dist[i0]), 1),
            "Samples": len(window),
            "MinSpeed": window["Speed"].min() if len(window) else None,
            "Frozen": frozen_speed(window),
        })
    return rows


def session_rows(s, rnd, ses):
    corners = s.get_circuit_info().corners
    lap_sets = {"all": s.laps}
    try:
        lap_sets["Q1"] = s.laps.split_qualifying_sessions()[0]
    except Exception as e:
        print(f"  could not split {ses} into knockout parts ({e}); 'all' only")
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
                rows.append({"Round": rnd, "EventName": s.event["EventName"], "Session": ses,
                             "LapSet": lap_set, "Team": team, "Driver": lap["Driver"],
                             "LapTime": lap["LapTime"], "Compound": lap["Compound"], **r})
    return pd.DataFrame(rows)


def main():
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    fastf1.set_log_level(logging.ERROR)
    sched = pd.read_parquet(config.RAW_DIR / "schedule.parquet")
    for _, ev in sched.iterrows():
        rnd = int(ev["RoundNumber"])
        sessions = ["Q"] + (["SQ"] if ev["EventFormat"] == "sprint_qualifying" else [])
        for ses in sessions:
            out = config.RAW_DIR / f"{rnd:02d}_{ses}_corners.parquet"
            if out.exists():
                continue
            try:
                s = fastf1.get_session(config.SEASON, rnd, ses)
                s.load(laps=True, telemetry=True, weather=False, messages=False)
                df = session_rows(s, rnd, ses)
                df.to_parquet(out, index=False)
                print(f"R{rnd:02d} {ses} {ev['EventName']}: {df['Team'].nunique()} teams, "
                      f"{df['Corner'].nunique()} corners")
            except Exception as e:  # e.g. no corner map for a new circuit (Madrid, Kuala Lumpur)
                print(f"R{rnd:02d} {ses} {ev['EventName']}: skipped ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
