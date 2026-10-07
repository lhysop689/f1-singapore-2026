"""Step 5: draw the five report figures into reports/figures/ (see src/plotting.py)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from src.plotting import make_all  # noqa: E402
from src.scoring import SCENARIOS  # noqa: E402


def main():
    scores = pd.read_csv(config.TABLES_DIR / "team_scores.csv", index_col="Team")
    ranks = pd.read_csv(config.TABLES_DIR / "robustness.csv", index_col="Team")
    ranks.columns = list(SCENARIOS)  # restore the two-line labels for the x-axis
    make_all(scores, ranks)
    for p in sorted(config.FIGURES_DIR.glob("*.png")):
        print("wrote", p.relative_to(config.ROOT))


if __name__ == "__main__":
    main()
