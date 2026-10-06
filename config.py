"""Every setting the analysis depends on, in one place.

Changing a value here and re-running `python run_pipeline.py --skip-pull`
reproduces every table and figure under the new setting. The reasoning for
each value is in docs/methodology.md.
"""
from pathlib import Path

# --- Paths --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache"                  # FastF1 download cache (not in git)
RAW_DIR = ROOT / "data" / "raw"             # one parquet file per session table (not in git)
TABLES_DIR = ROOT / "reports" / "tables"
FIGURES_DIR = ROOT / "reports" / "figures"

# --- Scope --------------------------------------------------------------------
SEASON = 2026
LAST_ROUND = 16                             # information cutoff: rounds completed before Singapore (R17)
SESSIONS = ["R", "Q"]                       # Grand Prix, Qualifying: every round
SPRINT_SESSIONS = ["S", "SQ"]               # Sprint, Sprint Qualifying: sprint weekends only
DRY_COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]

# --- Metric 1: position retention ----------------------------------------------
GRID_BAND = 2                               # grid slots pooled per band for the expected-gain baseline

# --- Metric 2: slow-corner speed -----------------------------------------------
CORNER_LAP_SET = "Q1"                       # fastest lap from Q1 / SQ1 only (same tyre, all 22 cars)
SLOW_CORNER_KMH = 120                       # a corner is "slow" if the median minimum speed is below this
CORNER_RADIUS_M = 60                        # telemetry within this distance of the corner marker
FROZEN_RUN = 3                              # identical consecutive speed samples = stalled reading, dropped
MAX_OFF_MEDIAN_KMH = 30                     # readings this far from the corner median are dropped
MIN_TEAMS_PER_CORNER = 8                    # corner used only with this many valid team readings
MIN_SLOW_CORNERS = 3                        # session used only with this many slow corners

# --- Metric 3: tyre wear -------------------------------------------------------
MIXED_WEATHER_GP_ROUNDS = [5, 16]           # Canada, Kuala Lumpur: intermediates used; excluded
MAX_LAP_RATIO = 1.07                        # laps slower than 107% of the stint median are dropped
MIN_STINT_LAPS = 8                          # shorter stints are dropped
MIN_FIELD_STINTS = 3                        # session-compound groups need this many stints for a field average

# --- Scoring --------------------------------------------------------------------
# metric name -> (higher raw value is better?, unit shown in tables and figures)
METRICS = {
    "Position retention": (True, "places vs expected"),
    "Slow-corner speed": (False, "km/h behind best team"),
    "Tyre wear": (False, "s/lap vs field"),
}
