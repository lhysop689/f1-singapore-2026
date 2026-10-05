"""Example of the tyre-degradation measurement: one Mercedes and one Cadillac
stint from the same race on the same compound, lap time vs tyre age with the
fitted slope. Writes outputs/example_stint.{html,png}.

Usage: python scripts/example_stint.py
"""
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.metrics import clean_stint_laps, load, stint_rows  # noqa: E402

OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
TEAMS = {"Mercedes": "#2a78d6", "Cadillac": "#eb6834"}  # categorical slots 1, 2
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def pick_pair(stints):
    """A representative pair: GP stints of 15+ laps, one per team, same race and
    compound, within 5 laps of each other in length, whose slope gap is closest
    to the two teams' season-average gap. Single stints are noisy, so an
    arbitrary pair can even point the opposite way."""
    a_team, b_team = TEAMS
    season = stints.groupby("Team")["RelSlope"].mean()
    target = season[b_team] - season[a_team]
    long = stints[(stints["Session"] == "R") & (stints["Laps"] >= 15)]
    best = None
    for _, g in long.groupby(["Round", "Compound"]):
        for _, sa in g[g["Team"] == a_team].iterrows():
            for _, sb in g[g["Team"] == b_team].iterrows():
                if abs(sa["Laps"] - sb["Laps"]) > 5:
                    continue
                miss = abs((sb["Slope"] - sa["Slope"]) - target)
                if best is None or miss < best[0]:
                    best = (miss, sa, sb)
    return best[1], best[2], target


def main():
    laps = load("laps", {"R", "S"})
    stints = stint_rows(laps)
    clean = clean_stint_laps(laps)
    *pair, season_gap = pick_pair(stints)
    event, compound = pair[0]["EventName"], pair[0]["Compound"].title()

    fig = go.Figure()
    for s in pair:
        g = clean[(clean["Round"] == s["Round"]) & (clean["Session"] == s["Session"])
                  & (clean["Driver"] == s["Driver"]) & (clean["Stint"] == s["Stint"])]
        color = TEAMS[s["Team"]]
        x = g["TyreLife"].to_numpy(float)
        slope, intercept = np.polyfit(x, g["LapS"], 1)
        name = f"{s['Team']} ({s['Driver']})"
        fig.add_trace(go.Scatter(
            x=x, y=g["LapS"], mode="markers", name=name, legendgroup=name,
            marker=dict(size=8, color=color, line=dict(width=2, color=SURFACE)),
            hovertemplate=f"{name}<br>Tyre age %{{x:.0f}} laps<br>Lap time %{{y:.3f}} s<extra></extra>"))
        xs = np.array([x.min(), x.max()])
        fig.add_trace(go.Scatter(
            x=xs, y=slope * xs + intercept, mode="lines", legendgroup=name, showlegend=False,
            line=dict(width=2, color=color), hoverinfo="skip"))
        fig.add_annotation(x=xs[1], y=slope * xs[1] + intercept, xanchor="left", xshift=8,
                           text=f"{s['Team']}: {slope:+.3f} s/lap", showarrow=False,
                           font=dict(color=INK_2, size=12))

    rel = pair[1]["Slope"] - pair[0]["Slope"]
    fig.update_layout(
        title=dict(text=f"{event}, {compound} tyres: Cadillac loses {rel:.3f} s/lap more than Mercedes as tyres age"
                        f"<br><sup>A typical pair: the season-average gap between the teams is {season_gap:.3f} s/lap. "
                        "Green-flag laps only; each dot is one lap; lines are straight-line fits</sup>",
                   font=dict(color=INK, size=15)),
        font=dict(family=FONT, color=INK_2, size=12),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        xaxis=dict(title="Tyre age (laps)", gridcolor=GRID, linecolor=AXIS, zeroline=False),
        yaxis=dict(title="Lap time (s)", gridcolor=GRID, linecolor=AXIS, zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=INK_2)),
        margin=dict(l=60, r=170, t=90, b=50), width=900, height=500,
    )
    fig.write_html(OUT / "example_stint.html", include_plotlyjs="cdn")
    fig.write_image(OUT / "example_stint.png", scale=2)
    print(f"R{pair[0]['Round']} {event} {compound}: "
          + " | ".join(f"{s['Team']} {s['Driver']} stint {int(s['Stint'])} {s['Laps']} laps slope {s['Slope']:+.4f}" for s in pair))


if __name__ == "__main__":
    main()
