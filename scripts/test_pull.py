"""Field audit: load the most recent completed 2026 race (R + Q) and report
which fields the metrics need are actually present.

Usage: python scripts/test_pull.py [round_number]
"""
import sys
from pathlib import Path

import fastf1
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
fastf1.Cache.enable_cache(str(ROOT / "cache"))

LAP_FIELDS = ["Driver", "Team", "LapNumber", "LapTime", "Sector1Time", "Sector2Time",
              "Sector3Time", "Compound", "TyreLife", "Stint", "PitInTime", "PitOutTime",
              "TrackStatus", "IsAccurate"]
RACE_RESULT_FIELDS = ["Abbreviation", "TeamName", "GridPosition", "Position",
                      "ClassifiedPosition", "Status"]
QUALI_RESULT_FIELDS = ["Abbreviation", "TeamName", "Position", "Q1", "Q2", "Q3"]


def completed_rounds(year=2026):
    sched = fastf1.get_event_schedule(year, include_testing=False)
    now = pd.Timestamp.now(tz="UTC")
    race_utc = pd.to_datetime(sched["Session5DateUtc"]).dt.tz_localize("UTC")
    done = sched[race_utc < now - pd.Timedelta(hours=6)]
    return sched, done


def coverage(df, fields):
    rows = []
    for f in fields:
        if f not in df.columns:
            rows.append((f, "MISSING", ""))
        else:
            pct = df[f].notna().mean() * 100
            rows.append((f, f"{pct:5.1f}% non-null", str(df[f].dtype)))
    return pd.DataFrame(rows, columns=["field", "coverage", "dtype"]).to_string(index=False)


def main():
    sched, done = completed_rounds()
    print("=== 2026 schedule ===")
    print(sched[["RoundNumber", "EventName", "EventFormat", "Session5DateUtc"]].to_string(index=False))
    print(f"\nCompleted rounds: {len(done)}  (latest: R{done['RoundNumber'].max()} "
          f"{done.iloc[-1]['EventName']})")

    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else int(done["RoundNumber"].max())

    for ses_name, result_fields in [("R", RACE_RESULT_FIELDS), ("Q", QUALI_RESULT_FIELDS)]:
        s = fastf1.get_session(2026, rnd, ses_name)
        s.load(laps=True, telemetry=False, weather=False, messages=False)
        print(f"\n=== Round {rnd} {s.event['EventName']} - {s.name} ===")
        print(f"laps: {len(s.laps)} rows, {s.laps['Driver'].nunique()} drivers")
        print(coverage(s.laps, LAP_FIELDS))
        print("\nAll lap columns:", list(s.laps.columns))
        print(f"\nresults: {len(s.results)} rows")
        print(coverage(s.results, result_fields))
        if ses_name == "R":
            print("\nCompounds:", s.laps["Compound"].value_counts(dropna=False).to_dict())
            print("TrackStatus codes:", s.laps["TrackStatus"].value_counts(dropna=False).head(10).to_dict())
            print("\nGrid vs finish:")
            print(s.results[["Abbreviation", "TeamName", "GridPosition", "Position", "Status"]]
                  .to_string(index=False))
        print("\nTeams:", sorted(s.results["TeamName"].dropna().unique()))


if __name__ == "__main__":
    main()
