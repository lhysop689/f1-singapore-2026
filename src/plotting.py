"""The five report figures (matplotlib + seaborn). Each is saved as a PNG in
reports/figures/ and answers one question:

  fig1  Who has the best Singapore profile, and which traits drive it?
  fig2  Where is each team strong or weak?
  fig3  How large are the measured gaps, and how certain?
  fig4  Does the ranking depend on our analysis choices?
  fig5  How is tyre wear measured? (worked example)

All colours come from src/palette.py.
"""
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

import config
from src import palette as pal
from src.metrics import clean_stint_laps, load, stint_rows

TRAITS = list(config.METRICS)
SOURCE = (f"Source: FastF1 official timing data, {config.SEASON} rounds 1–{config.LAST_ROUND} "
          "(data cut-off before the Singapore GP, round 17).")


def setup_style():
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "text.color": pal.CARBON, "axes.labelcolor": pal.CARBON,
        "xtick.color": pal.CARBON, "ytick.color": pal.CARBON,
        "axes.edgecolor": pal.AXIS, "grid.color": pal.GRID,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 10,
        "xtick.labelsize": 9.5, "ytick.labelsize": 9.5, "legend.fontsize": 9,
        "legend.edgecolor": pal.AXIS,
        "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white",
    })


def titles(fig, title, subtitle, note=SOURCE):
    fig.suptitle(title, x=0.01, y=1.0, ha="left", fontsize=13, fontweight="bold", color=pal.CARBON)
    fig.text(0.01, 0.955, subtitle, ha="left", va="top", fontsize=10, color=pal.GREY_TEXT)
    fig.text(0.01, -0.01, note, ha="left", va="top", fontsize=8, color=pal.GREY_NOTE)


def save(fig, name, despine=True):
    if despine:
        for ax in fig.axes:
            sns.despine(ax=ax)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES_DIR / name)
    plt.close(fig)


# --- Figure 1: overall score, split by trait --------------------------------------------

def fig1_overall(scores):
    df = scores.sort_values("Overall score")
    fig, ax = plt.subplots(figsize=(9, 6))
    for y, team in enumerate(df.index):
        left = 0.0
        for t in TRAITS:
            part = df.at[team, f"{t}: score"] / len(TRAITS)
            ax.barh(y, part, left=left, height=0.66, edgecolor="white", linewidth=1.2,
                    color=pal.shade(pal.team_color(team), pal.TRAIT_SHADE[t]))
            left += part
        ax.text(left + 1, y, f"{df.at[team, 'Overall score']:.0f}", va="center",
                fontsize=10, fontweight="bold", color=pal.CARBON)
    ax.set_yticks(range(len(df)), [f"{r}. {t}" for t, r in zip(df.index, df["Overall rank"])])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Overall score (0–100): mean of the three trait scores")
    ax.grid(axis="y", visible=False)
    legend = [Patch(facecolor=pal.shade(pal.GREY_TEXT, pal.TRAIT_SHADE[t]), edgecolor="white", label=t)
              for t in TRAITS]
    ax.legend(handles=legend, title="Bar segments (shade of team colour)", title_fontsize=9,
              loc="lower right", frameon=True)
    titles(fig, "Mercedes, Racing Bulls and Ferrari are almost level at the top; Cadillac trail far behind",
           "Overall Singapore-suitability score by team, in team colours. Each bar is split into the share "
           "contributed by each trait.")
    save(fig, "fig1_overall_score.png")


# --- Figure 2: score heatmap ----------------------------------------------------------------

def fig2_heatmap(scores):
    cols = [f"{t}: score" for t in TRAITS] + ["Overall score"]
    data = scores[cols].copy()
    data.columns = ["Position\nretention", "Slow-corner\nspeed", "Tyre\nwear", "Overall"]
    fig, ax = plt.subplots(figsize=(7.8, 6.5))
    sns.heatmap(data, annot=False, cmap=pal.SCORE_CMAP, vmin=0, vmax=100, linewidths=1.5,
                linecolor="white", cbar_kws={"label": "Score (0 = worst team, 100 = best team)"}, ax=ax)
    for i, team in enumerate(data.index):
        for j, col in enumerate(data.columns):
            v = data.iat[i, j]
            ax.text(j + 0.5, i + 0.5, f"{v:.0f}", ha="center", va="center", fontsize=10,
                    color=pal.text_on(v), fontweight="bold" if col == "Overall" else "normal")
        # team colour chip beside the name
        ax.add_patch(Rectangle((-0.2, i + 0.18), 0.12, 0.64, color=pal.team_color(team),
                               clip_on=False, transform=ax.transData))
    ax.axvline(3, color="white", linewidth=6)
    ax.tick_params(axis="y", pad=16)
    ax.set_xlabel("Trait")
    ax.set_ylabel("Team (sorted by overall score)")
    ax.tick_params(axis="x", rotation=0)
    titles(fig, "Most leading teams have one weak trait",
           "Score on each trait. Racing Bulls and Red Bull are weak in slow corners, Ferrari in tyre wear.")
    save(fig, "fig2_score_heatmap.png", despine=False)


# --- Figure 3: measured values with uncertainty ------------------------------------------

def fig3_measured(scores):
    order = scores.sort_values("Overall score").index
    colors = [pal.team_color(t) for t in order]
    panels = {
        "Position retention": ("Places gained vs expected per race", "better →", 0, "0 = as expected from grid slot"),
        "Slow-corner speed": ("km/h behind the best team per slow corner", "← better", None, None),
        "Tyre wear": ("Lap time lost per lap of tyre age vs field (s/lap)", "← better", 0, "0 = field average"),
    }
    fig, axes = plt.subplots(1, 3, figsize=(13, 6), sharey=True)
    for ax, (t, (xlabel, better, ref, ref_label)) in zip(axes, panels.items()):
        v, se, n = (scores.loc[order, f"{t}: {k}"] for k in ("value", "se", "n"))
        y = np.arange(len(order))
        ax.errorbar(v, y, xerr=se, fmt="none", ecolor=pal.GREY_TEXT, elinewidth=1.2, capsize=3, zorder=2)
        ax.scatter(v, y, c=colors, s=70, edgecolor="white", linewidth=1.2, zorder=3)
        if ref is not None:
            ax.axvline(ref, color=pal.REFERENCE, linewidth=1, linestyle="--", label=ref_label)
            ax.legend(loc="upper right", fontsize=8, frameon=True, handlelength=1.5)
        n_text = f"{int(n.min())}" if n.min() == n.max() else f"{int(n.min())}–{int(n.max())}"
        ax.set_title(f"{t}\n(n = {n_text} per team)", fontsize=10, color=pal.CARBON)
        ax.set_xlabel(xlabel)
        right = "→" in better
        ax.text(0.98 if right else 0.02, 0.01, better, transform=ax.transAxes,
                ha="right" if right else "left", fontsize=9, color=pal.GREY_TEXT, style="italic")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(order)), order)
    axes[0].set_ylim(-0.6, len(order) - 0.1)
    titles(fig, "The measured gaps: clear at the extremes, small and uncertain in the midfield",
           "Team averages in real units, dots in team colours. Error bars show ±1 standard error; overlapping "
           "bars mean the teams cannot be told apart on that trait.",
           SOURCE + "  n = races (retention), qualifying sessions (slow corners) or stints (tyre wear).")
    fig.subplots_adjust(top=0.84, wspace=0.08)
    save(fig, "fig3_measured_values.png")


# --- Figure 4: robustness -------------------------------------------------------------------

def fig4_robustness(ranks):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    xs = np.arange(len(ranks.columns))
    ax.axvspan(-0.25, 0.25, color=pal.HIGHLIGHT_BG, zorder=0)
    for team, row in ranks.iterrows():
        ax.plot(xs, row.values, color=pal.team_color(team), linestyle=pal.TEAM_LINESTYLE.get(team, "-"),
                linewidth=2.2, marker="o", markersize=7, markeredgecolor="white", markeredgewidth=1.2)
        ax.text(xs[0] - 0.12, row.values[0], team, ha="right", va="center", fontsize=9.5)
        ax.text(xs[-1] + 0.12, row.values[-1], team, ha="left", va="center", fontsize=9.5)
    ax.set_xticks(xs, ranks.columns)
    ax.get_xticklabels()[0].set_color(pal.F1_RED)
    ax.get_xticklabels()[0].set_fontweight("bold")
    ax.set_yticks(range(1, len(ranks) + 1))
    ax.set_ylim(len(ranks) + 0.6, 0.4)
    ax.set_xlim(-1.6, len(xs) - 1 + 1.6)
    ax.set_ylabel("Overall rank (1 = best)")
    ax.set_xlabel("Analysis choice (shaded column = published result)")
    ax.grid(axis="x", visible=False)
    titles(fig, "The top three stay in the top four, and the bottom three stay bottom, under every alternative",
           "Overall rank when one analysis choice is changed at a time. Lines in team colours; "
           "dashed or dotted lines separate teams with similar colours.")
    save(fig, "fig4_robustness.png")


# --- Figure 5: worked example of the tyre-wear measurement ----------------------------

def representative_pair(stints, team_a="Mercedes", team_b="Cadillac"):
    """GP stints (15+ laps, same race and compound, within 5 laps in length)
    whose slope gap is closest to the two teams' season-average gap. Single
    stints are noisy, so an arbitrary pair can even point the opposite way."""
    season = stints.groupby("Team")["RelSlope"].mean()
    target = season[team_b] - season[team_a]
    long = stints[(stints["Session"] == "R") & (stints["Laps"] >= 15)]
    best = None
    for _, g in long.groupby(["Round", "Compound"]):
        for _, sa in g[g["Team"] == team_a].iterrows():
            for _, sb in g[g["Team"] == team_b].iterrows():
                if abs(sa["Laps"] - sb["Laps"]) > 5:
                    continue
                miss = abs((sb["Slope"] - sa["Slope"]) - target)
                if best is None or miss < best[0]:
                    best = (miss, sa, sb)
    return best[1], best[2], target


def fig5_tyre_example():
    laps = load("laps", {"R", "S"})
    stints, clean = stint_rows(laps), clean_stint_laps(laps)
    a, b, season_gap = representative_pair(stints)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    handles = []
    for s in (a, b):
        g = clean[(clean["Round"] == s["Round"]) & (clean["Session"] == s["Session"])
                  & (clean["Driver"] == s["Driver"]) & (clean["Stint"] == s["Stint"])]
        x, y = g["TyreLife"].to_numpy(float), g["LapS"].to_numpy()
        slope, intercept = np.polyfit(x, y, 1)
        c = pal.team_color(s["Team"])
        ax.scatter(x, y, color=c, s=30, edgecolor="white", linewidth=0.6, zorder=3)
        xs = np.array([x.min(), x.max()])
        ax.plot(xs, slope * xs + intercept, color=c, linewidth=2.2)
        handles.append(Line2D([0], [0], color=c, marker="o", linewidth=2.2,
                              label=f"{s['Team']} ({s['Driver']}): slope {slope:+.3f} s/lap"))
    gap = b["Slope"] - a["Slope"]
    ax.set_xlabel("Tyre age (laps)")
    ax.set_ylabel("Lap time (s)")
    ax.legend(handles=handles, loc="lower left", frameon=True)
    titles(fig, f"How tyre wear is measured: Cadillac lose {gap:.3f} s/lap more than Mercedes as tyres age",
           f"{a['EventName']}, {a['Compound'].title()} tyres, green-flag laps, in team colours. Lines are "
           f"least-squares fits. Both cars speed up as fuel burns off;\nthe difference in slope is the "
           f"tyre-wear gap (season-average gap between these teams: {season_gap:.3f} s/lap).")
    fig.subplots_adjust(top=0.83)
    save(fig, "fig5_tyre_wear_example.png")


def make_all(scores, ranks):
    setup_style()
    fig1_overall(scores)
    fig2_heatmap(scores)
    fig3_measured(scores)
    fig4_robustness(ranks)
    fig5_tyre_example()
