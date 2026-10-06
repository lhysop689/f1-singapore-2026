"""The two published charts, built from outputs/scores.csv:
  outputs/heatmap.{html,png}        teams x traits, min-max score in each cell
  outputs/team_profiles.{html,png}  each team's score on the three traits

Usage: python scripts/score.py && python scripts/charts.py
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

TRAITS = ["Position retention", "Slow-corner speed", "Tyre wear"]
UNITS = {"Position retention": "places vs expected", "Slow-corner speed": "km/h behind best",
         "Tyre wear": "s/lap vs field"}
FMT = {"Position retention": "{:+.2f}", "Slow-corner speed": "{:.1f}", "Tyre wear": "{:+.3f}"}
BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
             "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
SERIES = {"Position retention": ("#2a78d6", "circle"),   # categorical slots 1-3,
          "Slow-corner speed": ("#eb6834", "diamond"),   # with a shape each as the
          "Tyre wear": ("#1baf7a", "square")}            # secondary encoding
INK, INK_2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
SUBTITLE = "2026 rounds 1–16 (Grands Prix and Sprints). On each trait, best team = 100, worst = 0"


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def base_layout(fig, title, height):
    fig.update_layout(
        title=dict(text=f"{title}<br><sup>{SUBTITLE}</sup>", font=dict(color=INK, size=16), x=0, xref="paper"),
        font=dict(family=FONT, color=INK_2, size=13),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        width=820, height=height, margin=dict(l=130, r=30, t=100, b=50),
    )


def heatmap(df):
    teams = df.index.tolist()
    cols = TRAITS + [" ", "Overall"]  # " " = spacer column setting Overall apart
    z, text, hover = [], [], []
    for t in teams:
        zr, tr, hr = [], [], []
        for c in cols:
            if c == " ":
                zr.append(None); tr.append(""); hr.append("")
            elif c == "Overall":
                zr.append(df.at[t, "Overall score"])
                tr.append(f"<b>{df.at[t, 'Overall score']:.0f}</b>")
                hr.append(f"{t}<br>Overall: {df.at[t, 'Overall score']:.0f} / 100 "
                          f"({ordinal(int(df.at[t, 'Overall rank']))})")
            else:
                zr.append(df.at[t, f"{c} score"])
                tr.append(f"{df.at[t, f'{c} score']:.0f}")
                hr.append(f"{t}<br>{c}: {df.at[t, f'{c} score']:.0f} / 100 "
                          f"({ordinal(int(df.at[t, f'{c} rank']))})<br>"
                          f"{FMT[c].format(df.at[t, f'{c} raw'])} {UNITS[c]}")
        z.append(zr); text.append(tr); hover.append(hr)
    n = len(BLUE_RAMP) - 1
    fig = go.Figure(go.Heatmap(
        z=z, x=cols, y=teams, text=text, texttemplate="%{text}", hovertext=hover, hoverinfo="text",
        colorscale=[[i / n, c] for i, c in enumerate(BLUE_RAMP)], zmin=0, zmax=100,
        xgap=2, ygap=2, showscale=False,
        textfont=dict(size=13),
    ))
    # ink on light cells, white on dark cells
    for i, t in enumerate(teams):
        for j, c in enumerate(cols):
            v = z[i][j]
            if v is not None:
                fig.add_annotation(x=c, y=t, text=text[i][j], showarrow=False,
                                   font=dict(size=13, color="#ffffff" if v >= 55 else INK))
    fig.update_traces(texttemplate=None)
    base_layout(fig, "Mercedes, Racing Bulls and Ferrari are almost level at the top; Cadillac trail far behind", 560)
    fig.update_xaxes(side="top", tickfont=dict(color=INK, size=13), showgrid=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK, size=13), showgrid=False)
    fig.add_annotation(text="Darker = better. Overall = equal-weight average of the three. "
                            "Small midfield gaps, especially in tyre wear, may be noise.",
                       xref="paper", yref="paper", x=0, y=-0.07, showarrow=False, xanchor="left",
                       font=dict(color=MUTED, size=12))
    return fig


def team_profiles(df):
    teams = df.index.tolist()
    ys = list(range(len(teams)))
    offset = {c: d for c, d in zip(TRAITS, (-0.27, 0, 0.27))}  # dodge so tied ranks don't hide each other
    fig = go.Figure()
    # a hairline per team spanning its weakest to strongest trait: long line = uneven profile
    for y, t in zip(ys, teams):
        vals = [df.at[t, f"{c} score"] for c in TRAITS]
        fig.add_trace(go.Scatter(x=[min(vals), max(vals)], y=[y, y], mode="lines",
                                 line=dict(color=AXIS, width=2), hoverinfo="skip", showlegend=False))
    for c in TRAITS:
        color, symbol = SERIES[c]
        fig.add_trace(go.Scatter(
            x=df[f"{c} score"], y=[y + offset[c] for y in ys], mode="markers", name=c,
            marker=dict(size=11, color=color, symbol=symbol, line=dict(width=2, color=SURFACE)),
            customdata=[[t, FMT[c].format(df.at[t, f"{c} raw"]), ordinal(int(df.at[t, f"{c} rank"]))]
                        for t in teams],
            hovertemplate=f"%{{customdata[0]}}<br>{c}: %{{x:.0f}} / 100 (%{{customdata[2]}})"
                          f"<br>%{{customdata[1]}} {UNITS[c]}<extra></extra>"))
    base_layout(fig, "Most leading teams have one weak trait; Mercedes and McLaren are the all-rounders", 680)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(color=INK_2)),
                      margin=dict(t=120))
    fig.update_xaxes(title="Score (0 = worst team on that trait, 100 = best)", range=[-4, 104], dtick=20,
                     gridcolor=GRID, linecolor=AXIS, zeroline=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK, size=13), showgrid=False,
                     tickmode="array", tickvals=ys, ticktext=teams, zeroline=False)
    return fig


def main():
    df = pd.read_csv(OUT / "scores.csv", index_col="Team")
    for name, fig in [("heatmap", heatmap(df)), ("team_profiles", team_profiles(df))]:
        fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn")
        fig.write_image(OUT / f"{name}.png", scale=2)
        print("wrote", name)


if __name__ == "__main__":
    main()
