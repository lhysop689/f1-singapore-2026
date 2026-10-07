"""Step 4: compute the three metrics and the team scores.

Writes:
  reports/tables/team_scores.csv   value, standard error, n, rank and score per
                                   trait, plus the suitability score and rank
  reports/tables/robustness.csv    suitability rank under each alternative choice
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.scoring import robustness, team_scores  # noqa: E402


def main():
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    scores = team_scores()
    scores.round(4).to_csv(config.TABLES_DIR / "team_scores.csv")
    ranks = robustness()
    ranks.columns = [c.replace("\n", " ") for c in ranks.columns]
    ranks.to_csv(config.TABLES_DIR / "robustness.csv")

    pd.set_option("display.width", 200)
    show = scores[[c for c in scores.columns if c.endswith("score")] + ["Suitability rank"]].round(0)
    print(show.to_string())


if __name__ == "__main__":
    main()
