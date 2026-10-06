"""The five report figures (matplotlib + seaborn). Each is saved as a PNG in
reports/figures/ and answers one question:

  fig1  Who has the best Singapore profile, and which traits drive it?
  fig2  Where is each team strong or weak?
  fig3  How large are the measured gaps, and how certain?
  fig4  Does the ranking depend on our analysis choices?
  fig5  How is tyre wear measured? (worked example)
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

import config
from src.metrics import clean_stint_laps, load, stint_rows

TRAITS = list(config.METRICS)
TRAIT_COLORS = dict(zip(TRAITS, ["#1f77b4", "#ff7f0e", "#2ca02c"]))
SOURCE = (f"Source: FastF1 official timing data, {config.SEASON} rounds 1–{config.LAST_ROUND} "
          "(data cut-off before the Singapore GP, round 17).")


def setup_style():
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 10,
        "xtick.labelsize": 9.5, "ytick.labelsize": 9.5, "legend.fontsize": 9,
        "axes.edgecolor": "#888888", "grid.color": "#e3e3e3",
        "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def titles(fig, title, subtitle, note=SOURCE):
    fig.suptitle(title, x=0.01, y=1.0, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.955, subtitle, ha="left", va="top", fontsize=10, color="#444444")
    fig.text(0.01, -0.01, note, ha="left", va="top", fontsize=8, color="#666666")


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
    left = np.zeros(len(df))
    for t in TRAITS:
        part = df[f"{t}: score"].to_numpy() / len(TRAITS)
        ax.barh(df.index, part, left=left, color=TRAIT_COLORS[t], height=0.65,
                edgecolor="white", linewidth=1, label=t)
        left += part
    for y, (total, rank) in enumerate(zip(df["Overall score"], df["Overall rank"])):
        ax.text(total + 1, y, f"{total:.0f}", va="center", fontsize=10, fontweight="bold")
    ax.set_yticks(range(len(df)), [f"{r}. {t}" for t, r in zip(df.index, df["Overall rank"])])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Overall score (0–100): mean of the three trait scores")
    ax.grid(axis="y", visible=False)
    ax.legend(title="Contribution from", title_fontsize=9.5, loc="lower right", frameon=True)
    titles(fig, "Mercedes, Racing Bulls and Ferrari are almost level at the top; Cadillac trail far behind",
           "Overall Singapore-suitability score by team. Each bar is split into the share contributed by each trait.")
    save(fig, "fig1_overall_score.png")


# --- Figure 2: score heatmap ----------------------------------------------------------------

def fig2_heatmap(scores):
    cols = [f"{t}: score" for t in TRAITS] + ["Overall score"]
    data = scores[cols].copy()
    data.columns = ["Position\nretention", "Slow-corner\nspeed", "Tyre\nwear", "Overall"]
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    sns.heatmap(data, annot=True, fmt=".0f", cmap="Blues", vmin=0, vmax=100, linewidths=1,
                linecolor="white", cbar_kws={"label": "Score (0 = worst team, 100 = best team)"},
                annot_kws={"fontsize": 10}, ax=ax)
    ax.axvline(3, color="white", linewidth=6)
    ax.set_xlabel("Trait")
    ax.set_ylabel("Team (sorted by overall score)")
    ax.tick_params(axis="x", rotation=0)
    titles(fig, "Most leading teams have one weak trait",
           "Score on each trait. Racing Bulls and Red Bull are weak in slow corners, Ferrari in tyre wear.")
    save(fig, "fig2_score_heatmap.png", despine=False)


# --- Figure 3: measured values with uncertainty ------------------------------------------

def fig3_measured(scores):
    order = scores.sort_values("Overall score").index
    panels = {
        "Position retention": ("Places gained vs expected per race", "better →", 0, "0 = as expected from grid slot"),
        "Slow-corner speed": ("km/h behind the best team per slow corner", "← better", None, None),
        "Tyre wear": ("Lap time lost per lap of tyre age vs field (s/lap)", "← better", 0, "0 = field average"),
    }
    fig, axes = plt.subplots(1, 3, figsize=(13, 6), sharey=True)
    for ax, (t, (xlabel, better, ref, ref_label)) in zip(axes, panels.items()):
        v, se, n = (scores.loc[order, f"{t}: {k}"] for k in ("value", "se", "n"))
        ax.errorbar(v, range(len(order)), xerr=se, fmt="o", color=TRAIT_COLORS[t], ecolor="#555555",
                    elinewidth=1.2, capsize=3, markersize=7)
        if ref is not None:
            ax.axvline(ref, color="#333333", linewidth=1, linestyle="--", label=ref_label)
            ax.legend(loc="upper right", fontsize=8, frameon=True, handlelength=1.5)
        n_text = f"{int(n.min())}" if n.min() == n.max() else f"{int(n.min())}–{int(n.max())}"
        ax.set_title(f"{t}\n(n = {n_text} per team)", fontsize=10)
        ax.set_xlabel(xlabel)
        ax.text(0.98 if "→" in better else 0.02, 0.01, better, transform=ax.transAxes,
                ha="right" if "→" in better else "left", fontsize=9, color="#333333", style="italic")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(order)), order)
    axes[0].set_ylim(-0.6, len(order) - 0.1)
    titles(fig, "The measured gaps: clear at the extremes, small and uncertain in the midfield",
           "Team averages in real units. Error bars show ±1 standard error; overlapping bars mean the teams "
           "cannot be told apart on that trait.",
           SOURCE + "  n = races (retention), qualifying sessions (slow corners) or stints (tyre wear).")
    fig.subplots_adjust(top=0.84, wspace=0.08)
    save(fig, "fig3_measured_values.png")


# --- Figure 4: robustness -------------------------------------------------------------------

def fig4_robustness(ranks, colors):
    fig, ax = plt.subplots(figsize=(11, 6.5))
    xs = np.arange(len(ranks.columns))
    for team, row in ranks.iterrows():
        c = colors.get(team, "#777777")
        ax.plot(xs, row.values, color=c, linewidth=2.2, marker="o", markersize=7,
                markeredgecolor="white", markeredgewidth=1.2)
        ax.text(xs[0] - 0.12, row.values[0], team, ha="right", va="center", fontsize=9.5)
        ax.text(xs[-1] + 0.12, row.values[-1], team, ha="left", va="center", fontsize=9.5)
    ax.axvspan(-0.25, 0.25, color="#f0f0f0", zorder=0)
    ax.set_xticks(xs, ranks.columns)
    ax.set_yticks(range(1, len(ranks) + 1))
    ax.set_ylim(len(ranks) + 0.6, 0.4)
    ax.set_xlim(-1.6, len(xs) - 1 + 1.6)
    ax.set_ylabel("Overall rank (1 = best)")
    ax.set_xlabel("Analysis choice (shaded column = published result)")
    ax.grid(axis="x", visible=False)
    titles(fig, "The top three stay in the top four, and the bottom three stay bottom, under every alternative",
           "Overall rank when one analysis choice is changed at a time. Line colours are the official 2026 team colours.")
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


def fig5_tyre_example(colors):
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
        c = colors.get(s["Team"], "#777777")
        ax.scatter(x, y, color=c, s=28, edgecolor="white", linewidth=0.6, zorder=3)
        xs = np.array([x.min(), x.max()])
        ax.plot(xs, slope * xs + intercept, color=c, linewidth=2.2)
        handles.append(Line2D([0], [0], color=c, marker="o", linewidth=2.2,
                              label=f"{s['Team']} ({s['Driver']}): slope {slope:+.3f} s/lap"))
    gap = b["Slope"] - a["Slope"]
    ax.set_xlabel("Tyre age (laps)")
    ax.set_ylabel("Lap time (s)")
    ax.legend(handles=handles, loc="lower left", frameon=True)
    titles(fig, f"How tyre wear is measured: Cadillac lose {gap:.3f} s/lap more than Mercedes as tyres age",
           f"{a['EventName']}, {a['Compound'].title()} tyres, green-flag laps. Lines are least-squares fits. "
           f"Both cars speed up as fuel burns off;\nthe difference in slope is the tyre-wear gap "
           f"(season-average gap between these teams: {season_gap:.3f} s/lap).")
    fig.subplots_adjust(top=0.83)
    save(fig, "fig5_tyre_wear_example.png")


def make_all(scores, ranks, colors):
    setup_style()
    fig1_overall(scores)
    fig2_heatmap(scores)
    fig3_measured(scores)
    fig4_robustness(ranks, colors)
    fig5_tyre_example(colors)
