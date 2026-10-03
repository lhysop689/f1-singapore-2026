"""Builds notebooks/sanity.ipynb (hand checks for the metrics). Run, then execute with
jupyter nbconvert --to notebook --execute --inplace notebooks/sanity.ipynb
"""
from pathlib import Path

import nbformat as nbf

cells = [
    ("md", "# Sanity checks: metrics 1 and 2\n\nHand checks for `src/metrics.py`, plus both versions of each open decision so they can be compared. Definitions are in `METHOD.md`."),
    ("code", "import sys; sys.path.insert(0, '..')\nimport pandas as pd\nfrom src.metrics import load, retention_rows, retention, corner_deficit_rows, corner_deficit\npd.set_option('display.precision', 2)\nresults = load('results', {'R', 'S'})\ncorners = load('corners', {'Q', 'SQ'})\nprint(results.groupby(['SessionType'])['Round'].nunique().to_dict(), 'rounds by session type')"),

    ("md", "## Metric 1: position retention\n\n### Hand check: Azerbaijan GP (Round 15)\nExpected from the official result: Antonelli 16th → 5th (+11), Verstappen 8th → 2nd (+6), Piastri 3rd → 13th (−10). Retired cars (e.g. Norris, both Aston Martins) should be missing; Bottas was \"Retired\" but classified 16th, so he should be included."),
    ("code", "rows = retention_rows(results)\nrows[(rows['Round'] == 15) & (rows['Session'] == 'R')].sort_values('Finish')"),
    ("md", "### Hand check: one team computed by hand\nMercedes' net score should equal the plain average of its rows."),
    ("code", "merc = rows[rows['TeamName'] == 'Mercedes']\nprint('by hand:', round(merc['Gained'].mean(), 3), '| function:', round(retention(results).loc['Mercedes', 'score'], 3), '| n =', len(merc))"),
    ("md", "### Decision: how to count places\n- **net**: average places gained (gains and losses both count).\n- **lost**: average places lost (gains count as 0).\n- **adjusted**: places gained compared with the typical car starting from the same grid slot (slots pooled in pairs: P1–2, P3–4, ...).\n\nHigher is better in all three. Compare each with the team's average starting position: net and lost mostly track the grid (a car starting 20th can only gain, and gets promoted when cars ahead retire). Adjusted removes that built-in effect."),
    ("code", "comp = pd.DataFrame({m: retention(results, m)['score'] for m in ['net', 'lost', 'adjusted']})\ncomp['avg_grid'] = rows.groupby('TeamName')['GridPosition'].mean()\ncomp = comp.sort_values('adjusted', ascending=False)\nprint('Spearman correlation with average grid position:', comp.corr(method='spearman')['avg_grid'].round(2).drop('avg_grid').to_dict())\ncomp"),
    ("md", "### Expected places gained by starting slot\nThe baseline for **adjusted**: the average places gained by all drivers starting in each pair of grid slots, across every race and Sprint."),
    ("code", "rows.groupby((rows['GridPosition'] - 1) // 2 * 2 + 1)['Expected'].first().rename('expected gain').rename_axis('grid slots from').round(1)"),
    ("md", "### Sprints vs Grand Prix (net)\nDo teams behave differently in Sprints? (Sprints have about 22 rows per round vs about 22 per GP, but only 5 rounds.)"),
    ("code", "rows.pivot_table(index='TeamName', columns='SessionType', values='Gained', aggfunc='mean').sort_values('GP', ascending=False)"),

    ("md", "## Metric 2: slow-corner speed\n\n### Data quality: frozen speed readings\nThe 2026 speed channel sometimes stalls for up to ~1 s, holding one value (e.g. 305 km/h straight through a braking zone). Corner readings with 3+ identical consecutive speed samples are dropped, as are readings more than 30 km/h from the other teams at that corner. Corners are located by track-map position (X/Y), because FastF1's distance-along-lap drifts by up to ~3%.\n\nIf the dropped share is similar across teams, the cleaning doesn't favour anyone."),
    ("code", "from src.metrics import clean_corner_speeds\ncl = clean_corner_speeds(corners, 'Q1')\nprint(f\"dropped overall: {(~cl['Valid']).mean():.1%}\")\n(~cl['Valid']).groupby(cl['Team']).mean().mul(100).round(1).sort_values().rename('dropped %')"),
    ("md", "### Hand check: Azerbaijan qualifying, whole-session fastest lap\nThe Oct 3 test (before the cleaning) gave Mercedes 2.4 km/h behind the best team in each slow corner → Cadillac 8.5. The exact values change with the cleaning, but the order should be broadly similar: Mercedes near the front, Cadillac, Williams and Aston Martin near the back."),
    ("code", "dr_all = corner_deficit_rows(corners, 'all')\ndr_all[(dr_all['Round'] == 15)].sort_values('Deficit')[['Team', 'Deficit', 'SlowCorners', 'ValidCorners']]"),
    ("md", "### Slow corners found per session\nThe data picks the slow corners (median minimum speed below 120 km/h). Monza (Round 13) is a high-speed track, so few slow corners are expected there."),
    ("code", "dr_q1 = corner_deficit_rows(corners, 'Q1')\ndr_q1.drop_duplicates(['Round', 'Session'])[['Round', 'EventName', 'Session', 'SlowCorners']]"),
    ("md", "### Decision: fastest lap from Q1 only vs the whole session\n- **Q1**: every car runs it, all on the same tyre (Softs in Qualifying, Mediums in Sprint Qualifying), with similar track conditions.\n- **all**: each team's best lap overall. Top teams set it later in the session on a faster, rubbered-in track, and in Sprint Qualifying the final round switches to Softs, so top teams get a tyre advantage.\n\nLower deficit is better."),
    ("code", "cd = corner_deficit(corners, 'Q1').rename(columns={'score': 'Q1'}).join(corner_deficit(corners, 'all')['score'].rename('all'))\ncd['Q1_rank'] = cd['Q1'].rank().astype(int)\ncd['all_rank'] = cd['all'].rank().astype(int)\ncd"),
    ("md", "### Consistency across sessions (Q1)\nIs a team's deficit stable from track to track, or driven by one or two sessions?"),
    ("code", "dr_q1.pivot_table(index='Team', columns='Round', values='Deficit').round(1)"),
]

nb = nbf.v4.new_notebook()
nb["cells"] = [nbf.v4.new_markdown_cell(s) if t == "md" else nbf.v4.new_code_cell(s) for t, s in cells]
out = Path(__file__).with_name("sanity.ipynb")
nbf.write(nb, out)
print("wrote", out)
