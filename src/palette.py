"""The single colour palette used by every figure.

Rules
  Team identity  -> the official 2026 team colour (FastF1 `TeamColor`), always
                    paired with the team's name, because several are near-twins
                    (four blues, two greys, two reds).
  Trait          -> a shade of the team's own colour (full, mid, light).
  Score (0-100)  -> one neutral sequential ramp, light grey to carbon, so the
                    team colours stay the only saturated colours in any figure.
  Text, axes     -> carbon and greys; F1 red is reserved for highlights.
"""
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb

# Official 2026 team colours, as published in the FastF1 timing data
# (results `TeamColor`); tests/test_metrics.py checks they still match.
TEAM_COLORS = {
    "Mercedes": "#00D7B6",
    "Ferrari": "#ED1131",
    "McLaren": "#F47600",
    "Red Bull Racing": "#4781D7",
    "Racing Bulls": "#6C98FF",
    "Alpine": "#00A1E8",
    "Williams": "#1868DB",
    "Audi": "#F50537",
    "Aston Martin": "#229971",
    "Haas F1 Team": "#9C9FA2",
    "Cadillac": "#909090",
}

# Second team of each look-alike pair gets a different line style in line charts.
TEAM_LINESTYLE = {"Racing Bulls": "--", "Williams": ":", "Audi": "--", "Cadillac": "--"}

# Brand and chrome
F1_RED = "#E10600"
CARBON = "#15151E"        # titles, primary text
GREY_TEXT = "#5A5A66"     # subtitles, secondary text
GREY_NOTE = "#8A8A94"     # source notes
GRID = "#E6E6EA"
AXIS = "#B8B8C0"
REFERENCE = "#38383F"     # reference lines (zero, field average)
HIGHLIGHT_BG = "#FBEAEA"  # light F1-red wash for the published-result column

# Trait shades: share of the team colour kept (1 = full colour)
TRAIT_SHADE = {"Position retention": 1.0, "Slow-corner speed": 0.62, "Tyre wear": 0.32}

# Score ramp for the heatmap: 0 = near-white, 100 = carbon
SCORE_CMAP = LinearSegmentedColormap.from_list(
    "f1_score", ["#F5F5F7", "#CFD0D8", "#9294A3", "#55576A", CARBON])


def team_color(team):
    return TEAM_COLORS.get(team, GREY_NOTE)


def shade(color, keep):
    """Mix a colour with white: keep=1 returns the colour, keep=0 returns white."""
    r, g, b = to_rgb(color)
    return to_hex((1 - keep + keep * r, 1 - keep + keep * g, 1 - keep + keep * b))


def text_on(fill_value, threshold=50):
    """Ink colour for a number printed on a heatmap cell of the given score."""
    return "white" if fill_value >= threshold else CARBON
