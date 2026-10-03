"""Pull laps + results for every completed 2026 round (Race and Qualifying)
and save them to data/raw/ as parquet. Re-runnable: existing files are skipped,
so running it again after a new race only fetches the new round.

Usage: python scripts/pull_season.py
"""
import logging
from pathlib import Path

import fastf1
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(ROOT / "cache"))
fastf1.set_log_level(logging.WARNING)

YEAR = 2026
SESSIONS = ["R", "Q"]


def completed_schedule():
    sched = fastf1.get_event_schedule(YEAR, include_testing=False)
    race_utc = pd.to_datetime(sched["Session5DateUtc"]).dt.tz_localize("UTC")
    done = race_utc < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6)
    return sched[done]


def save(df, path, rnd, event):
    df = pd.DataFrame(df).copy()
    df.insert(0, "Round", rnd)
    df.insert(1, "EventName", event)
    df.to_parquet(path, index=False)


def main():
    sched = completed_schedule()
    sched.to_parquet(RAW / "schedule.parquet", index=False)
    print(f"{len(sched)} completed rounds")

    for _, ev in sched.iterrows():
        rnd, name = int(ev["RoundNumber"]), ev["EventName"]
        for ses in SESSIONS:
            laps_p = RAW / f"{rnd:02d}_{ses}_laps.parquet"
            res_p = RAW / f"{rnd:02d}_{ses}_results.parquet"
            if laps_p.exists() and res_p.exists():
                print(f"R{rnd:02d} {ses} {name}: already saved")
                continue
            try:
                s = fastf1.get_session(YEAR, rnd, ses)
                s.load(laps=True, telemetry=False, weather=False, messages=False)
                save(s.laps, laps_p, rnd, name)
                save(s.results, res_p, rnd, name)
                print(f"R{rnd:02d} {ses} {name}: {len(s.laps)} laps, {len(s.results)} results")
            except Exception as e:  # keep going; the completeness check will flag gaps
                print(f"R{rnd:02d} {ses} {name}: FAILED ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
