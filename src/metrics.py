"""Team metrics for the Singapore GP analysis. Definitions: see METHOD.md.

Each metric has a per-row function (one row per driver-session or team-session,
for checking by hand) and a team-level summary.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
SESSION_TYPE = {"R": "GP", "Q": "GP", "S": "Sprint", "SQ": "Sprint"}
GRID_BAND = 2  # grid places pooled per band for the expected-gain baseline
DRY = ["SOFT", "MEDIUM", "HARD"]
MIXED_WEATHER_RACES = [5, 16]  # Canada, Kuala Lumpur: intermediates used in the GP


def load(kind, sessions):
    """Concatenate data/raw/{round}_{session}_{kind}.parquet for the given sessions."""
    frames = []
    for path in sorted(RAW.glob(f"*_{kind}.parquet")):
        ses = path.stem.split("_")[1]
        if ses in sessions:
            df = pd.read_parquet(path)
            df["Session"] = ses
            df["SessionType"] = SESSION_TYPE[ses]
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


# --- Metric 1: position retention -------------------------------------------

def retention_rows(results):
    """One row per classified driver per Grand Prix / Sprint.

    Gained = GridPosition - finish position (positive = places gained).
    Lost = the same, but gains count as 0 (only places lost).
    Unclassified drivers (ClassifiedPosition R/W/D...) are dropped.
    """
    df = results.copy()
    df["Finish"] = pd.to_numeric(df["ClassifiedPosition"], errors="coerce")
    df = df[df["Finish"].notna() & (df["GridPosition"] > 0)]
    df["Gained"] = df["GridPosition"] - df["Finish"]
    df["Lost"] = df["Gained"].clip(upper=0)
    # Places gained vs a typical car starting from the same grid slot (pooled in
    # bands of GRID_BAND places across all races): removes the built-in effect
    # that back-markers can only gain and front-runners can only lose.
    band = (df["GridPosition"] - 1) // GRID_BAND
    df["Expected"] = df.groupby(band)["Gained"].transform("mean")
    df["VsExpected"] = df["Gained"] - df["Expected"]
    return df[["Round", "EventName", "Session", "SessionType", "TeamName",
               "Abbreviation", "GridPosition", "Finish", "Gained", "Lost",
               "Expected", "VsExpected"]]


def retention(results, mode="net"):
    """Team mean places gained ('net'), lost ('lost'), or gained vs the typical
    car from the same grid slot ('adjusted'); higher is better."""
    col = {"net": "Gained", "lost": "Lost", "adjusted": "VsExpected"}[mode]
    rows = retention_rows(results)
    return (rows.groupby("TeamName")[col].agg(score="mean", n="size")
            .sort_values("score", ascending=False))


# --- Metric 2: slow-corner speed --------------------------------------------

def clean_corner_speeds(corners, lap_set="Q1", max_off_kmh=30):
    """Readings for one lap set with bad telemetry removed (MinSpeed -> NaN).

    Removed: readings where the speed channel was frozen (see
    scripts/pull_corner_speeds.py), and readings more than max_off_kmh from the
    median of the other valid readings at that corner.
    """
    df = corners[corners["LapSet"] == lap_set].reset_index(drop=True)
    speed = df["MinSpeed"].where(~df["Frozen"])
    keys = [df["Round"], df["Session"], df["Corner"]]
    median = speed.groupby(keys).transform("median")
    df["Valid"] = speed.notna() & ((speed - median).abs() <= max_off_kmh)
    df["CleanSpeed"] = speed.where(df["Valid"])
    return df


def corner_deficit_rows(corners, lap_set="Q1", slow_kmh=120, min_corners=3, min_teams=8):
    """One row per team per qualifying session.

    Slow corners = corners whose median (valid) minimum speed is below slow_kmh
    and that have at least min_teams valid readings. Deficit = team's average
    km/h below the fastest team at each slow corner, over the corners where its
    own reading is valid. Sessions with fewer than min_corners slow corners are
    dropped.
    """
    df = clean_corner_speeds(corners, lap_set)
    out = []
    for (rnd, ses), g in df.groupby(["Round", "Session"]):
        speeds = g.pivot_table(index="Team", columns="Corner", values="CleanSpeed")
        slow = speeds.columns[(speeds.median() < slow_kmh) & (speeds.count() >= min_teams)]
        if len(slow) < min_corners:
            continue
        gaps = speeds[slow].max() - speeds[slow]
        out.append(pd.DataFrame({
            "Round": rnd, "EventName": g["EventName"].iat[0], "Session": ses,
            "Team": gaps.index, "Deficit": gaps.mean(axis=1).values,
            "SlowCorners": len(slow), "ValidCorners": gaps.count(axis=1).values,
        }))
    return pd.concat(out, ignore_index=True)


def corner_deficit(corners, lap_set="Q1", **kw):
    """Team mean km/h deficit in slow corners; lower is better."""
    rows = corner_deficit_rows(corners, lap_set, **kw)
    return (rows.groupby("Team")["Deficit"].agg(score="mean", n="size")
            .sort_values("score"))


# --- Metric 3: tyre degradation ---------------------------------------------

def clean_stint_laps(laps, exclude_gp_rounds=MIXED_WEATHER_RACES):
    """Race/Sprint laps usable for degradation: dry tyres, green flag, not lap 1,
    not pit in/out laps, accurate timing, within 107% of the stint median."""
    df = laps[laps["Compound"].isin(DRY)
              & (laps["TrackStatus"].astype(str) == "1")
              & (laps["LapNumber"] > 1)
              & laps["PitInTime"].isna() & laps["PitOutTime"].isna()
              & laps["IsAccurate"] & laps["LapTime"].notna()].copy()
    df = df[~((df["Session"] == "R") & df["Round"].isin(exclude_gp_rounds))]
    df["LapS"] = df["LapTime"].dt.total_seconds()
    median = df.groupby(["Round", "Session", "Driver", "Stint"])["LapS"].transform("median")
    return df[df["LapS"] <= 1.07 * median]


def stint_rows(laps, min_laps=8, min_field_stints=3, **kw):
    """One row per stint: slope of lap time (s) against tyre age (laps), and the
    slope relative to the field average for the same session and compound.
    Positive RelSlope = the car loses time faster than the field."""
    df = clean_stint_laps(laps, **kw)
    out = []
    for (rnd, ses, drv, stint), g in df.groupby(["Round", "Session", "Driver", "Stint"]):
        if len(g) < min_laps or g["TyreLife"].nunique() < 2:
            continue
        slope = np.polyfit(g["TyreLife"], g["LapS"], 1)[0]
        out.append({"Round": rnd, "EventName": g["EventName"].iat[0], "Session": ses,
                    "SessionType": g["SessionType"].iat[0], "Team": g["Team"].iat[0],
                    "Driver": drv, "Stint": stint, "Compound": g["Compound"].iat[0],
                    "Laps": len(g), "Slope": slope})
    st = pd.DataFrame(out)
    grp = st.groupby(["Round", "Session", "Compound"])["Slope"]
    st["FieldStints"] = grp.transform("size")
    st["FieldSlope"] = grp.transform("mean")
    st = st[st["FieldStints"] >= min_field_stints].copy()
    st["RelSlope"] = st["Slope"] - st["FieldSlope"]
    return st


def tyre_deg(laps, **kw):
    """Team mean relative degradation (s/lap vs field); lower is better."""
    rows = stint_rows(laps, **kw)
    return (rows.groupby("Team")["RelSlope"].agg(score="mean", n="size")
            .sort_values("score"))
