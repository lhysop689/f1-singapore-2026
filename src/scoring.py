"""Turn the three metrics into team scores, plus the robustness scenarios.

Published scoring (min-max): on each metric the best team scores 100, the
worst 0, and the rest in proportion to their raw value. The overall score is
the equal-weight mean of the three. See docs/methodology.md for why.
"""
import pandas as pd

import config
from src.metrics import corner_deficit, load, retention, tyre_wear


def metric_tables(sprints=True, include_mixed_weather=False, corner_lap_set=config.CORNER_LAP_SET):
    """Team-level value / se / n for each metric under the given data choices."""
    race_ses = {"R", "S"} if sprints else {"R"}
    quali_ses = {"Q", "SQ"} if sprints else {"Q"}
    excluded = () if include_mixed_weather else tuple(config.MIXED_WEATHER_GP_ROUNDS)
    return {
        "Position retention": retention(load("results", race_ses)),
        "Slow-corner speed": corner_deficit(load("corners", quali_ses), corner_lap_set),
        "Tyre wear": tyre_wear(load("laps", race_ses), exclude_gp_rounds=excluded),
    }


def to_scores(tables, method="minmax"):
    """Per-metric scores (higher = better) and the overall score and rank."""
    cols = {}
    for name, t in tables.items():
        higher_better, _ = config.METRICS[name]
        v = t["value"] if higher_better else -t["value"]
        if method == "minmax":
            cols[name] = 100 * (v - v.min()) / (v.max() - v.min())
        elif method == "rank":
            cols[name] = 100 * (v.rank() - 1) / (len(v) - 1)
        elif method == "zscore":
            cols[name] = (v - v.mean()) / v.std()
        else:
            raise ValueError(method)
    df = pd.DataFrame(cols)
    df["Overall"] = df[list(tables)].mean(axis=1)
    df["Overall rank"] = df["Overall"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("Overall", ascending=False)


def team_scores():
    """The published table: raw value, standard error, n, rank and score per metric."""
    tables = metric_tables()
    scores = to_scores(tables)
    out = pd.DataFrame(index=scores.index)
    for name, t in tables.items():
        higher_better, _ = config.METRICS[name]
        out[f"{name}: value"] = t["value"]
        out[f"{name}: se"] = t["se"]
        out[f"{name}: n"] = t["n"]
        out[f"{name}: rank"] = t["value"].rank(ascending=not higher_better, method="min").astype(int)
        out[f"{name}: score"] = scores[name]
    out["Overall score"] = scores["Overall"]
    out["Overall rank"] = scores["Overall rank"]
    out.index.name = "Team"
    return out


SCENARIOS = {
    "Published\n(min-max)": dict(),
    "Rank-based\nscoring": dict(method="rank"),
    "Z-score\nscoring": dict(method="zscore"),
    "Without\nSprints": dict(sprints=False),
    "Mixed-weather\nGPs included": dict(include_mixed_weather=True),
    "Whole-session\nquali laps": dict(corner_lap_set="all"),
}


def robustness():
    """Overall rank of every team under each alternative choice (one column per scenario)."""
    ranks = {}
    for label, opts in SCENARIOS.items():
        method = opts.get("method", "minmax")
        data_opts = {k: v for k, v in opts.items() if k != "method"}
        ranks[label] = to_scores(metric_tables(**data_opts), method)["Overall rank"]
    out = pd.DataFrame(ranks)
    out.index.name = "Team"
    return out.sort_values(out.columns[0])


def team_colors():
    """Official 2026 team colours from the timing data (latest round in scope)."""
    res = load("results", {"R"})
    latest = res[res["Round"] == res["Round"].max()]
    return {t: f"#{c}" for t, c in zip(latest["TeamName"], latest["TeamColor"])}
