"""Team scores: each metric's raw value, rank (1 = best) and min-max score
(best team = 100, worst = 0, others in proportion), plus the overall score
(equal-weight mean of the three). Writes outputs/scores.csv.

Usage: python scripts/score.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.metrics import corner_deficit, load, retention, tyre_deg  # noqa: E402

OUT = ROOT / "outputs"

# metric -> (team-level series, True if higher raw value is better)
METRICS = {
    "Position retention": lambda: (retention(load("results", {"R", "S"}), "adjusted")["score"], True),
    "Slow-corner speed": lambda: (corner_deficit(load("corners", {"Q", "SQ"}), "Q1")["score"], False),
    "Tyre wear": lambda: (tyre_deg(load("laps", {"R", "S"}))["score"], False),
}
UNITS = {"Position retention": "places vs expected",
         "Slow-corner speed": "km/h behind best",
         "Tyre wear": "s/lap vs field"}


def scores():
    cols = {}
    for name, get in METRICS.items():
        raw, higher_better = get()
        rank = raw.rank(ascending=not higher_better, method="min").astype(int)
        oriented = raw if higher_better else -raw
        cols[(name, "raw")] = raw
        cols[(name, "rank")] = rank
        cols[(name, "score")] = 100 * (oriented - oriented.min()) / (oriented.max() - oriented.min())
    df = pd.DataFrame(cols)
    df[("Overall", "score")] = df.xs("score", axis=1, level=1).mean(axis=1)
    df[("Overall", "rank")] = df[("Overall", "score")].rank(ascending=False, method="min").astype(int)
    return df.sort_values(("Overall", "rank"))


def main():
    df = scores()
    flat = df.copy()
    flat.columns = [f"{m} {k}" for m, k in df.columns]
    flat.index.name = "Team"
    OUT.mkdir(exist_ok=True)
    flat.round(4).to_csv(OUT / "scores.csv")
    show = df.xs("score", axis=1, level=1).round(0).astype(int).join(df[("Overall", "rank")].rename("Overall rank"))
    print(show.to_string())


if __name__ == "__main__":
    main()
