# Singapore GP 2026 — Characteristic-Based Team Advantage

Scores each 2026 F1 team on three Singapore-relevant characteristics (quali-to-race position retention, low-speed sector pace, tyre degradation) using FastF1 season data. Pre-race scores are frozen on Oct 8, 2026, and compared with the actual Singapore GP result after Oct 11.

Work in progress. Method, decisions and limitations: [METHOD.md](METHOD.md).

## Setup
```
uv venv --python 3.13 .venv
uv pip install --link-mode=copy --python .venv\Scripts\python.exe fastf1 pandas pyarrow plotly kaleido jupyter
.venv\Scripts\python.exe scripts\pull_season.py        # saves data/raw/*.parquet (re-runnable)
.venv\Scripts\python.exe scripts\check_completeness.py # rounds x fields table
```
