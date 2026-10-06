"""Step 1: download laps and results for every 2026 round up to config.LAST_ROUND.

Grand Prix (R) and Qualifying (Q) for every round; Sprint (S) and Sprint
Qualifying (SQ) on sprint weekends. Each session table is saved to
data/raw/{round}_{session}_{laps|results}.parquet. Files that already exist are
skipped, so the script is safe to re-run.
"""
import logging
import sys
import warnings
from pathlib import Path

import fastf1
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

warnings.filterwarnings("ignore", category=DeprecationWarning)


def rounds_in_scope():
    """The season schedule, limited to completed rounds up to the cutoff."""
    sched = fastf1.get_event_schedule(config.SEASON, include_testing=False)
    race_utc = pd.to_datetime(sched["Session5DateUtc"]).dt.tz_localize("UTC")
    done = race_utc < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6)
    return sched[done & (sched["RoundNumber"] <= config.LAST_ROUND)]


def save(df, path, rnd, event):
    df = pd.DataFrame(df).copy()
    df.insert(0, "Round", rnd)
    df.insert(1, "EventName", event)
    df.to_parquet(path, index=False)


def main():
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(config.CACHE_DIR))
    fastf1.set_log_level(logging.WARNING)

    sched = rounds_in_scope()
    sched.to_parquet(config.RAW_DIR / "schedule.parquet", index=False)
    print(f"{len(sched)} rounds in scope (cutoff: round {config.LAST_ROUND})")

    for _, ev in sched.iterrows():
        rnd, name = int(ev["RoundNumber"]), ev["EventName"]
        sessions = config.SESSIONS + (config.SPRINT_SESSIONS if ev["EventFormat"] == "sprint_qualifying" else [])
        for ses in sessions:
            laps_p = config.RAW_DIR / f"{rnd:02d}_{ses}_laps.parquet"
            res_p = config.RAW_DIR / f"{rnd:02d}_{ses}_results.parquet"
            if laps_p.exists() and res_p.exists():
                continue
            try:
                s = fastf1.get_session(config.SEASON, rnd, ses)
                s.load(laps=True, telemetry=False, weather=False, messages=False)
                save(s.laps, laps_p, rnd, name)
                save(s.results, res_p, rnd, name)
                print(f"R{rnd:02d} {ses} {name}: {len(s.laps)} laps, {len(s.results)} results")
            except Exception as e:  # keep going; step 3 flags any gaps
                print(f"R{rnd:02d} {ses} {name}: FAILED ({type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
