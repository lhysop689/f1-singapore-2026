# Singapore GP 2026: Which Teams Are Built for Marina Bay?

Marina Bay rewards a particular set of car traits: holding track position on a circuit where overtaking is very hard, speed through slow corners, and tyres that last in heat and humidity. This project measures those traits for every 2026 Formula 1 team from official timing and telemetry data. It combines them into a **Singapore suitability score** before the race, then tests whether the best-suited teams outperform their usual level when the season reaches Singapore.

> **Research question:** which 2026 teams have the car traits that Marina Bay rewards, and do those teams outperform their usual level at the Singapore Grand Prix?

| At a glance | |
|---|---|
| Season scope | 2026 rounds 1–16: 16 Grands Prix, 5 Sprints, with their qualifying sessions. Singapore is round 17 (Oct 9–11) |
| Teams | 11 |
| Data analysed | 20,527 race laps · 718 tyre stints · 386 driver-races · 3,333 telemetry corner readings |
| Data source | [FastF1](https://docs.fastf1.dev) (official F1 timing data) |
| Scores frozen | Oct 9, 2026, before the first Singapore session (Practice 1, 08:30 UTC): GitHub Release [`pre-race-snapshot`](../../releases/tag/pre-race-snapshot) |

---

## Key findings

1. **Mercedes (76), Racing Bulls (74) and Ferrari (74) are the best suited to Marina Bay, and almost level.** They stay in the top 4 under every alternative analysis choice tested.
2. **Racing Bulls are the second-best suited team despite being fifth in the championship.** They have the best position retention on the grid and the second-lowest tyre wear. Their sister team Red Bull, fourth in the championship, ranks sixth: similar slow-corner speed, but it loses places in Sprints.
3. **Most leading teams have one weak trait.**
   - Racing Bulls and Red Bull: slow corners.
   - Ferrari: tyre wear.
   - Mercedes and McLaren are the only teams scoring above 60 on all three traits.
4. **Cadillac (2), Aston Martin (29) and Williams (29) are the least suited.** They stay bottom 3 under every alternative.
5. **The midfield is not clearly separated.** McLaren, Audi, Red Bull, Alpine and Haas sit within measurement uncertainty of each other.

<p align="center"><img src="reports/figures/fig1_suitability_score.png" width="85%"></p>
<p align="center"><img src="reports/figures/fig2_score_heatmap.png" width="70%"></p>

---

## The three traits

Each trait is measured relative to the rest of the field, so together they describe how well a car fits Singapore's demands.

| Trait | Why Marina Bay rewards it | Measured as | Better |
|---|---|---|---|
| **Position retention** | Narrow, walled street circuit where overtaking is very hard | Places gained in each Grand Prix and Sprint, compared with the average car starting from the same grid slots | Higher |
| **Slow-corner speed** | 19 mostly slow corners, short straights | Minimum telemetry speed at every corner under 120 km/h on each team's fastest Q1 / SQ1 lap, as km/h behind the best team | Lower |
| **Tyre wear** | Hot, humid, ~62-lap race | Lap time lost per lap of tyre age in each stint, compared with the field on the same tyre in the same session | Lower |

**Singapore suitability score:** on each trait the best team scores 100, the worst 0, and the rest in proportion to their measured value. The suitability score is the equal-weight average of the three.

Full definitions, formulas, sign conventions and every data decision are in [docs/methodology.md](docs/methodology.md).

---

## How certain are these results?

**Figure 3** shows the measurements behind the scores in real units, with ±1 standard-error bars. The extremes are clear; most midfield gaps overlap. Slow-corner speed is the most precise trait, and tyre wear the noisiest.

<p align="center"><img src="reports/figures/fig3_measured_values.png" width="100%"></p>

**Figure 4** changes one analysis choice at a time: the scoring method, including Sprints or not, including mixed-weather races, and which qualifying laps are used. The top three and bottom three hold under every alternative.

<p align="center"><img src="reports/figures/fig4_robustness.png" width="90%"></p>

**Figure 5** is a worked example of the tyre-wear measurement: a typical Mercedes stint against a typical Cadillac stint. [View figure](reports/figures/fig5_tyre_wear_example.png).

---

## The test at Singapore

Fixed before the race ([methodology §6](docs/methodology.md#6-pre-registered-test)):

- **Over-performance:** each team's 2026 average finishing position minus its finishing position at Singapore (both cars averaged). A positive value means the team did better than usual.
- **Test:** Spearman rank correlation between the suitability score and over-performance, computed separately for the Singapore Sprint (Oct 10) and the Grand Prix (Oct 11).
- **Reading the result:** a positive correlation means the best-suited teams beat their usual level.

*Results will be added after Oct 11.*

---

## Limitations

- **Small sample.** Only 16 rounds under brand-new 2026 rules, with early-season races weighted the same as recent ones.
- **Noise.** Tyre wear is noisy: a driver saving tyres can make a slow car look gentle on them.
- **What position retention captures.** It partly reflects overall race pace, and it ignores reliability because retirements are excluded.
- **Not scored:** safety cars, night and heat effects, and Singapore's first Sprint weekend.
- **Team-level only.** Scores hide driver differences; Gasly/Colapinto and Verstappen/Hadjar are the most lopsided pairings.
- **One race weekend.** With 11 teams, the test is directional rather than conclusive.

---

## Repository structure

```text
f1-singapore-2026/
├── README.md
├── config.py                  every setting: rounds, thresholds, exclusions
├── run_pipeline.py            runs steps 1–5 in order
├── requirements.txt
├── scripts/
│   ├── 01_pull_sessions.py        download laps and results (FastF1)
│   ├── 02_pull_corner_speeds.py   corner speeds from qualifying telemetry
│   ├── 03_check_data.py           per-round coverage check
│   ├── 04_compute_scores.py       traits → suitability scores, robustness table
│   └── 05_make_figures.py         the five figures
├── src/
│   ├── metrics.py             the three trait definitions
│   ├── scoring.py             min-max scoring and robustness scenarios
│   ├── palette.py             one colour palette: official team colours + neutral greys
│   └── plotting.py            figures (matplotlib + seaborn)
├── tests/test_metrics.py      hand checks against known 2026 results
├── notebooks/sanity_checks.ipynb  the checks behind each analysis decision
├── docs/
│   ├── methodology.md         definitions, decisions, limitations
│   └── data_dictionary.md     every table and column
└── reports/
    ├── figures/               fig1–fig5 (PNG)
    └── tables/                team_scores.csv · robustness.csv · data_coverage.csv
```

Downloaded data (`data/`) and the FastF1 cache (`cache/`) are not in git; step 1 rebuilds them.

---

## Reproduce

Requires Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run_pipeline.py          # first run downloads ~1.2 GB of FastF1 data
.venv\Scripts\python.exe -m pytest                # 9 hand checks
```

`python run_pipeline.py --skip-pull` rebuilds every table and figure from already-downloaded data. Changing a value in `config.py` and re-running reproduces the analysis under that setting.

---

## Data and trademark notice

Timing and telemetry data come from the public F1 live-timing feed via [FastF1](https://github.com/theOehrly/Fast-F1). This is an independent portfolio project, not affiliated with or endorsed by Formula 1, the FIA, or any team. Formula 1, F1, team names and related marks belong to their respective owners.
