"""Hand checks of the metrics against known 2026 results, run with `pytest`.

These need the downloaded data in data/raw/ (run step 1 first); they are
skipped otherwise.
"""
import numpy as np
import pandas as pd
import pytest

import config
from src.metrics import (clean_stint_laps, corner_deficit_rows, load, retention_rows,
                         stint_rows)
from src.scoring import team_scores

pytestmark = pytest.mark.skipif(not (config.RAW_DIR / "15_R_results.parquet").exists(),
                                reason="data/raw not downloaded")


@pytest.fixture(scope="module")
def results():
    return load("results", {"R", "S"})


@pytest.fixture(scope="module")
def laps():
    return load("laps", {"R", "S"})


# --- Position retention: Azerbaijan GP (round 15), checked against the official result

def azerbaijan(results):
    rows = retention_rows(results)
    return rows[(rows["Round"] == 15) & (rows["Session"] == "R")].set_index("Abbreviation")


def test_places_gained_match_official_result(results):
    az = azerbaijan(results)
    assert az.loc["ANT", "Gained"] == 11   # Antonelli 16th -> 5th
    assert az.loc["VER", "Gained"] == 6    # Verstappen 8th -> 2nd
    assert az.loc["PIA", "Gained"] == -10  # Piastri 3rd -> 13th


def test_classified_retiree_kept_and_retirements_dropped(results):
    az = azerbaijan(results)
    assert "BOT" in az.index                       # "Retired" but classified 16th
    assert not {"NOR", "ALO", "STR"} & set(az.index)  # retired, not classified


def test_expected_gain_removes_grid_bias(results):
    rows = retention_rows(results)
    # by construction, the adjusted metric averages zero within every grid band
    band = (rows["GridPosition"] - 1) // config.GRID_BAND
    assert rows.groupby(band)["VsExpected"].mean().abs().max() < 1e-9


# --- Slow-corner speed --------------------------------------------------------------------

def test_corner_deficits_are_relative_to_best_team():
    rows = corner_deficit_rows(load("corners", {"Q", "SQ"}))
    assert (rows["Deficit"] >= 0).all()
    assert rows["Deficit"].max() < 25          # no physically implausible gaps after cleaning
    assert (rows["SlowCorners"] >= config.MIN_SLOW_CORNERS).all()
    assert rows["Round"].isin([14, 16]).sum() == 0   # no corner map for Madrid, Kuala Lumpur


# --- Tyre wear ------------------------------------------------------------------------------

def test_stint_slope_matches_least_squares_by_hand(laps):
    st = stint_rows(laps)
    row = st.sort_values("Laps", ascending=False).iloc[0]
    clean = clean_stint_laps(laps)
    g = clean[(clean["Round"] == row["Round"]) & (clean["Session"] == row["Session"])
              & (clean["Driver"] == row["Driver"]) & (clean["Stint"] == row["Stint"])]
    x, y = g["TyreLife"].to_numpy(float), g["LapS"].to_numpy()
    by_hand = ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum()
    assert row["Slope"] == pytest.approx(by_hand)


def test_tyre_wear_uses_only_dry_green_flag_laps(laps):
    clean = clean_stint_laps(laps)
    assert set(clean["Compound"]) <= set(config.DRY_COMPOUNDS)
    assert (clean["TrackStatus"].astype(str) == "1").all()
    assert not ((clean["Session"] == "R") & clean["Round"].isin(config.MIXED_WEATHER_GP_ROUNDS)).any()


def test_relative_slopes_average_zero_within_each_field(laps):
    st = stint_rows(laps)
    means = st.groupby(["Round", "Session", "Compound"])["RelSlope"].mean()
    assert np.allclose(means, 0)


# --- Scoring ----------------------------------------------------------------------------------

def test_scores_span_0_to_100_and_overall_is_the_mean():
    s = team_scores()
    traits = [f"{t}: score" for t in config.METRICS]
    for col in traits:
        assert s[col].min() == pytest.approx(0) and s[col].max() == pytest.approx(100)
    assert np.allclose(s["Suitability score"], s[traits].mean(axis=1))
    assert len(s) == 11


def test_palette_matches_official_team_colours(results):
    from src.palette import TEAM_COLORS
    latest = results[(results["Session"] == "R") & (results["Round"] == results["Round"].max())]
    official = {t: f"#{c}".upper() for t, c in zip(latest["TeamName"], latest["TeamColor"])}
    assert {t: c.upper() for t, c in TEAM_COLORS.items()} == official
