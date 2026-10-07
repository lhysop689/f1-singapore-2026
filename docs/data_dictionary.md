# Data dictionary

## Raw data: `data/raw/` (not in git; rebuilt by steps 1–2)

One parquet file per session table. `{rr}` is the two-digit round number; `{s}` is the session (`R` Grand Prix, `Q` Qualifying, `S` Sprint, `SQ` Sprint Qualifying).

| File | One row per | Columns used by the analysis |
|---|---|---|
| `schedule.parquet` | Round in scope | `RoundNumber`, `EventName`, `EventFormat` (`sprint_qualifying` = sprint weekend), `Session5DateUtc` |
| `{rr}_{s}_results.parquet` | Driver in a session | `TeamName`, `TeamColor`, `Abbreviation`, `GridPosition`, `ClassifiedPosition` (number, or `R` retired, `W` withdrawn, `D` disqualified), `Status`, `Q1`–`Q3` |
| `{rr}_{s}_laps.parquet` | Lap by a driver | `Team`, `Driver`, `LapNumber`, `LapTime`, `Stint`, `Compound`, `TyreLife` (laps on this set), `TrackStatus` (`1` = green flag), `PitInTime`, `PitOutTime`, `IsAccurate` |
| `{rr}_{Q\|SQ}_corners.parquet` | Corner × team × lap set | see below |

Every file also carries `Round` and `EventName`. Laps and results are FastF1's standard tables; see the [FastF1 docs](https://docs.fastf1.dev/core.html) for every column.

**Corner speeds** (built by `scripts/02_pull_corner_speeds.py`):

| Column | Meaning |
|---|---|
| `LapSet` | `Q1` = team's fastest lap in the first knockout round (used); `all` = fastest of the whole session (robustness check only) |
| `Team`, `Driver`, `LapTime`, `Compound` | The lap the reading comes from |
| `Corner` | Corner number from FastF1's circuit map (e.g. `7`, `12A`) |
| `ClosestM` | Closest distance (m) between the car's path and the corner marker |
| `Samples` | Telemetry samples within 60 m of the marker |
| `MinSpeed` | Lowest speed (km/h) in that window |
| `Frozen` | `True` if the speed channel stalled (3+ identical samples); such readings are dropped |

## Output tables: `reports/tables/` (in git)

### `team_scores.csv`: the published result, one row per team

For each trait (`Position retention`, `Slow-corner speed`, `Tyre wear`) there are five columns:

| Column suffix | Meaning |
|---|---|
| `: value` | Team average in real units: places vs expected, km/h behind best team, s/lap vs field |
| `: se` | Standard error of that average |
| `: n` | Observations averaged: driver-races, qualifying sessions or stints |
| `: rank` | 1 = best team on this trait |
| `: score` | 0–100 (min-max: best team = 100, worst = 0) |

Plus `Suitability score` (Singapore suitability score: mean of the three trait scores) and `Suitability rank`.

### `robustness.csv`: suitability rank under each alternative choice

One column per scenario: `Published (min-max)`, `Rank-based scoring`, `Z-score scoring`, `Without Sprints`, `Mixed-weather GPs included`, `Whole-session quali laps`. See [methodology §5](methodology.md#5-robustness).

### `data_coverage.csv`: one row per round, built by step 3

| Column | Meaning |
|---|---|
| `Sprint weekend` | Round has Sprint and Sprint Qualifying sessions |
| `GP laps` | Laps recorded in the Grand Prix |
| `Lap time present %` | Laps with a lap time |
| `Tyre info present %` | Laps with a known tyre compound |
| `Green-flag laps %` | Laps run entirely under green flag |
| `Wet tyres used` | Intermediate or wet tyres used: the race is excluded from tyre wear |
| `Classified finishers` | Drivers with an official finishing position |
| `Corner speeds (Q)` | Corner-speed file exists (`False` = no FastF1 corner map) |
