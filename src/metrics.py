"""The three team metrics. Definitions and reasoning: docs/methodology.md.

Each metric has two functions:
  *_rows(...)   one row per observation (driver-race, team-session or stint),
                so any number can be checked by hand;
  the summary   one row per team: `value` (mean), `se` (standard error of the
                mean) and `n` (observations).
All thresholds come from config.py.
"""
import numpy as np
import pandas as pd

import config

SESSION_TYPE = {"R": "GP", "Q": "GP", "S": "Sprint", "SQ": "Sprint"}


def load(kind, sessions):
    """Stack data/raw/{round}_{session}_{kind}.parquet for the given sessions,
    keeping only rounds up to the information cutoff."""
    frames = []
    for path in sorted(config.RAW_DIR.glob(f"*_{kind}.parquet")):
        rnd, ses = int(path.stem.split("_")[0]), path.stem.split("_")[1]
        if ses in sessions and rnd <= config.LAST_ROUND:
            df = pd.read_parquet(path)
            df["Session"] = ses
            df["SessionType"] = SESSION_TYPE[ses]
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarise(rows, team_col, value_col):
    g = rows.groupby(team_col)[value_col]
    out = pd.DataFrame({"value": g.mean(), "se": g.std() / np.sqrt(g.size()), "n": g.size()})
    out.index.name = "Team"
    return out


# --- Metric 1: position retention ------------------------------------------------

def retention_rows(results):
    """One row per classified driver per Grand Prix / Sprint.

    Gained     = GridPosition - finishing position (positive = places gained)
    Expected   = average Gained of all drivers starting from the same band of
                 config.GRID_BAND grid slots, across every race in scope
    VsExpected = Gained - Expected  (the metric)
    Lost       = Gained with gains set to 0 (kept for comparison only)

    Unclassified drivers (ClassifiedPosition R, W, D, ...) are dropped.
    """
    df = results.copy()
    df["Finish"] = pd.to_numeric(df["ClassifiedPosition"], errors="coerce")
    df = df[df["Finish"].notna() & (df["GridPosition"] > 0)].copy()
    df["Gained"] = df["GridPosition"] - df["Finish"]
    df["Lost"] = df["Gained"].clip(upper=0)
    band = (df["GridPosition"] - 1) // config.GRID_BAND
    df["Expected"] = df.groupby(band)["Gained"].transform("mean")
    df["VsExpected"] = df["Gained"] - df["Expected"]
    return df[["Round", "EventName", "Session", "SessionType", "TeamName", "Abbreviation",
               "GridPosition", "Finish", "Gained", "Lost", "Expected", "VsExpected"]]


def retention(results, mode="adjusted"):
    """Team mean places vs expected ('adjusted', the metric), raw places gained
    ('net') or places lost ('lost'). Higher is better."""
    col = {"adjusted": "VsExpected", "net": "Gained", "lost": "Lost"}[mode]
    return summarise(retention_rows(results), "TeamName", col).sort_values("value", ascending=False)


# --- Metric 2: slow-corner speed ---------------------------------------------------

def clean_corner_speeds(corners, lap_set=config.CORNER_LAP_SET):
    """Corner readings for one lap set, with bad telemetry set to NaN: frozen
    readings, and readings more than config.MAX_OFF_MEDIAN_KMH from the median
    of the other valid readings at that corner."""
    df = corners[corners["LapSet"] == lap_set].reset_index(drop=True)
    speed = df["MinSpeed"].where(~df["Frozen"])
    median = speed.groupby([df["Round"], df["Session"], df["Corner"]]).transform("median")
    df["Valid"] = speed.notna() & ((speed - median).abs() <= config.MAX_OFF_MEDIAN_KMH)
    df["CleanSpeed"] = speed.where(df["Valid"])
    return df


def corner_deficit_rows(corners, lap_set=config.CORNER_LAP_SET):
    """One row per team per qualifying session.

    Slow corner = median valid minimum speed below config.SLOW_CORNER_KMH, with
    at least config.MIN_TEAMS_PER_CORNER valid readings.
    Deficit     = the team's average km/h below the fastest team at each slow
                  corner (over corners where its own reading is valid).
    Sessions with fewer than config.MIN_SLOW_CORNERS slow corners are dropped,
    as are team-sessions with no valid reading at all (all frozen telemetry).
    """
    df = clean_corner_speeds(corners, lap_set)
    out = []
    for (rnd, ses), g in df.groupby(["Round", "Session"]):
        speeds = g.pivot_table(index="Team", columns="Corner", values="CleanSpeed")
        slow = speeds.columns[(speeds.median() < config.SLOW_CORNER_KMH)
                              & (speeds.count() >= config.MIN_TEAMS_PER_CORNER)]
        if len(slow) < config.MIN_SLOW_CORNERS:
            continue
        gaps = speeds[slow].max() - speeds[slow]
        out.append(pd.DataFrame({
            "Round": rnd, "EventName": g["EventName"].iat[0], "Session": ses,
            "Team": gaps.index, "Deficit": gaps.mean(axis=1).values,
            "SlowCorners": len(slow), "ValidCorners": gaps.count(axis=1).values,
        }))
    rows = pd.concat(out, ignore_index=True)
    return rows[rows["ValidCorners"] > 0].reset_index(drop=True)


def corner_deficit(corners, lap_set=config.CORNER_LAP_SET):
    """Team mean km/h behind the best team in slow corners. Lower is better."""
    return summarise(corner_deficit_rows(corners, lap_set), "Team", "Deficit").sort_values("value")


# --- Metric 3: tyre wear ---------------------------------------------------------------

def clean_stint_laps(laps, exclude_gp_rounds=tuple(config.MIXED_WEATHER_GP_ROUNDS)):
    """Grand Prix / Sprint laps usable for tyre wear: dry tyres, green flag,
    not lap 1, not pit in/out laps, accurate timing, within
    config.MAX_LAP_RATIO of the stint median. Mixed-weather GPs are excluded."""
    df = laps[laps["Compound"].isin(config.DRY_COMPOUNDS)
              & (laps["TrackStatus"].astype(str) == "1")
              & (laps["LapNumber"] > 1)
              & laps["PitInTime"].isna() & laps["PitOutTime"].isna()
              & laps["IsAccurate"] & laps["LapTime"].notna()].copy()
    df = df[~((df["Session"] == "R") & df["Round"].isin(list(exclude_gp_rounds)))]
    df["LapS"] = df["LapTime"].dt.total_seconds()
    median = df.groupby(["Round", "Session", "Driver", "Stint"])["LapS"].transform("median")
    return df[df["LapS"] <= config.MAX_LAP_RATIO * median]


def stint_rows(laps, **kw):
    """One row per stint.

    Slope     = least-squares slope of lap time (s) against tyre age (laps)
    RelSlope  = Slope - average Slope of all stints in the same session on the
                same compound (the metric; positive = slows faster than the field)
    """
    df = clean_stint_laps(laps, **kw)
    out = []
    for (rnd, ses, drv, stint), g in df.groupby(["Round", "Session", "Driver", "Stint"]):
        if len(g) < config.MIN_STINT_LAPS or g["TyreLife"].nunique() < 2:
            continue
        out.append({"Round": rnd, "EventName": g["EventName"].iat[0], "Session": ses,
                    "SessionType": g["SessionType"].iat[0], "Team": g["Team"].iat[0],
                    "Driver": drv, "Stint": stint, "Compound": g["Compound"].iat[0],
                    "Laps": len(g), "Slope": np.polyfit(g["TyreLife"], g["LapS"], 1)[0]})
    st = pd.DataFrame(out)
    grp = st.groupby(["Round", "Session", "Compound"])["Slope"]
    st["FieldStints"] = grp.transform("size")
    st["FieldSlope"] = grp.transform("mean")
    st = st[st["FieldStints"] >= config.MIN_FIELD_STINTS].copy()
    st["RelSlope"] = st["Slope"] - st["FieldSlope"]
    return st


def tyre_wear(laps, **kw):
    """Team mean tyre wear relative to the field, s/lap. Lower is better."""
    return summarise(stint_rows(laps, **kw), "Team", "RelSlope").sort_values("value")
