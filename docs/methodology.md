# Methodology

This document defines every number in the project. The settings it refers to live in [`config.py`](../config.py), and the code in [`src/metrics.py`](../src/metrics.py) and [`src/scoring.py`](../src/scoring.py). It is frozen with the scores in the `pre-race-snapshot` release on Oct 8, 2026, before the first Singapore session.

**Contents:**
1. [Question and scope](#1-question-and-scope)
2. [Data](#2-data)
3. [Metrics](#3-metrics)
4. [Scoring](#4-scoring)
5. [Robustness](#5-robustness)
6. [Pre-registered post-race test](#6-pre-registered-post-race-test)
7. [Limitations](#7-limitations)
8. [Decision log](#8-decision-log)

---

## 1. Question and scope

**Question:** based on their 2026 season so far, which teams have the strongest profile for the Singapore Grand Prix (Marina Bay, Oct 9–11, 2026)?

**What the analysis is:**
- **Descriptive.** Each team is scored on three traits that Singapore rewards; it is not a race prediction model.
- **Team-level.** Both drivers share the car, and the traits mostly come from the car.
- **Under an information cutoff.** Only data from rounds 1–16, all completed before Singapore (round 17), is used. The scores are frozen publicly before the event and then tested against the actual result (section 6).

**Why these three traits:**

| Singapore characteristic | Trait scored |
|---|---|
| Narrow street circuit, walls close by, very hard to overtake | Position retention |
| 19 mostly slow corners, short straights | Slow-corner speed |
| Hot, humid night race over about 62 laps | Tyre wear |

---

## 2. Data

| Item | Detail |
|---|---|
| Source | Official F1 timing data via [FastF1](https://docs.fastf1.dev) 3.8 |
| Rounds | 2026 rounds 1–16. Round 16 is the "Bahrain Grand Prix" held in Kuala Lumpur on Oct 4 |
| Sessions | Grand Prix (R) and Qualifying (Q) every round; Sprint (S) and Sprint Qualifying (SQ) at rounds 2, 4, 5, 9, 12. Practice is not used: teams don't show true pace there |
| Telemetry | Car speed and X/Y position for each team's fastest qualifying lap (slow-corner metric only) |
| Pre-2026 data | Not used: the 2026 rules changed the cars completely |

Every table is described in [`data_dictionary.md`](data_dictionary.md). The per-round coverage check is `reports/tables/data_coverage.csv`.

---

## 3. Metrics

Each metric is computed per observation and then averaged per team. The **standard error** (SE) of that average is reported alongside, to show how precisely it is known. Sprints are handled exactly like Grands Prix: each metric compares teams only **within the same session** (and, for tyre wear, the same tyre compound), so differences between the two formats cancel out.

### 3.1 Position retention: does the team hold its place in races?

```
Places gained          = grid position − finishing position          (per driver, per race)
Expected places gained = average places gained by all drivers starting
                         in the same pair of grid slots (P1–2, P3–4, …), all races
Position retention     = Places gained − Expected places gained
Team score             = mean over the team's driver-races
```
**Sign convention:**
- **Positive:** the team gains more places than a typical car starting where it started (better).
- **Zero:** as expected from its grid slot.

**Included:** classified finishers in every Grand Prix and Sprint (24–40 driver-races per team). A car marked "retired" that still covered 90% of the distance is classified, so it is included.

**Why grid-adjusted:** raw places gained mostly measures where a team starts. A car starting 20th can only gain, and moves up whenever cars ahead retire; a car on pole can only lose. Raw places gained correlates 0.87 (Spearman) with a team's average grid position; the adjusted version removes that built-in effect.

**What it reflects:** race-day execution as a whole, not one skill:
- race pace relative to qualifying pace
- starts
- pit stops
- strategy
- staying out of trouble

**Why Sprints count:** with no required pit stop, a Sprint is almost purely a test of holding position, the closest 2026 equivalent to Singapore's own Sprint.

### 3.2 Slow-corner speed: how fast is the car through slow corners?

```
Corner minimum speed = lowest telemetry speed while the car is within 60 m of a corner marker
                       (on the team's fastest lap of Q1 / SQ1)
Slow corner          = corner whose median minimum speed across teams is below 120 km/h
Session deficit      = mean over slow corners of (fastest team's speed − team's speed)
Team score           = mean session deficit
```
**Sign convention:**
- **Zero:** the fastest team at every slow corner.
- **Larger values:** slower through slow corners (worse).

**Included:** 18 qualifying sessions (13 Qualifying + 5 Sprint Qualifying); 17–18 per team. Excluded:
- Madrid (R14) and Kuala Lumpur (R16): FastF1 has no corner map for these tracks.
- Austria (R8): only 2 slow corners, below the 3-corner minimum.

**Why Q1 / SQ1 laps:** all 22 cars run that round, on the same tyre (Softs in Qualifying, Mediums in Sprint Qualifying) and in similar track conditions. Later rounds favour teams that reach them, because the track gains grip, and in Sprint Qualifying the final round switches to Softs.

**Why minimum corner speed, not sector times:** a sector mixes straights with corners, so a strong engine can hide a car that is weak in slow corners.

**What drives it (mostly the car):**
- mechanical grip on a bumpy surface
- low-speed downforce
- agility into tight corners
- traction out of them

**Telemetry cleaning:** two 2026 data problems found during the build.
1. **Distance drift.** FastF1's distance along the lap is integrated from speed and drifts by up to ~3%, enough to place a "corner" reading on the next straight. Corners are therefore located by X/Y track position.
2. **Frozen readings.** The speed channel sometimes stalls for up to ~1 s, holding one value (e.g. 305 km/h through a braking zone). Readings with 3 or more identical consecutive samples are dropped: about 8% of slow-corner readings, spread evenly across teams (5–11% each).

After both fixes:
- Readings more than 30 km/h from the corner median are dropped.
- A corner is used only with at least 8 valid team readings.
- A session is used only with at least 3 slow corners.

### 3.3 Tyre wear: how fast does the car slow down as its tyres age?

```
Stint slope    = least-squares slope of lap time (s) against tyre age (laps), one stint
Tyre wear      = Stint slope − average slope of all stints in the same session on the same compound
Team score     = mean over the team's stints
```
**Sign convention:**
- **Negative:** the car loses less time as its tyres age than the field (better).
- **Zero:** field average.

**Included laps:**
- green-flag only
- not lap 1
- not pit in/out laps
- timed accurately (FastF1 `IsAccurate`)
- dry tyres
- within 107% of the stint median

**Included stints:** at least 8 laps, with at least 3 stints on that compound in that session. That gives 718 stints, 55–74 per team.

**Excluded races:** the mixed-weather Grands Prix in Canada (R5) and Kuala Lumpur (R16). A drying track gets faster lap by lap, which disguises wear.

**Why compare with the field:** the car burns fuel and gets lighter through a stint, so raw slopes are near zero or negative. Fuel burn affects every car similarly, so comparing with the field in the same session and compound removes it. [Figure 5](../reports/figures/fig5_tyre_wear_example.png) shows a worked example.

**Why wear differs although every team has identical Pirelli tyres:** each car works the same tyres differently.
1. **Aerodynamics:** more grip means less sliding, and sliding scrubs rubber.
2. **Suspension and weight balance:** an overloaded tyre wears first.
3. **Heat management:** tyres grip only within a temperature window; overheating costs grip, especially in hot races.
4. **Driving style:** smooth inputs wear tyres less.

Tyre strategy (which tyres to use and when to pit) is a set of team decisions and is not scored.

---

## 4. Scoring

```
Trait score   = 100 × (team value − worst team value) / (best team value − worst team value)
Overall score = mean of the three trait scores (equal weights)
```
The best team on each trait scores 100, the worst 0, and the rest in proportion to their measured value.

**Why min-max:** it is as easy to explain as ranks and keeps the size of the gaps. Ranks would put Mercedes 10 points clear of 2nd, while the measurements show the top three almost level (76, 74, 74).

**Why equal weights:** there is no defensible basis for ranking one trait above another for Singapore, so the neutral choice is stated openly.

**Limitations:**
- Scores are relative to this season's best and worst team. One extreme team squeezes the rest together: Cadillac's tyre wear is far worse than anyone else's, which pushes most teams into the 50–100 range on that trait.
- Small midfield gaps may be noise. [Figure 3](../reports/figures/fig3_measured_values.png) shows each measurement with its ±1 SE.

**How much of each trait's spread is real.** This is the estimated share of the between-team spread that is signal rather than measurement noise:

| Trait | Real signal |
|---|---|
| Slow-corner speed | ~76% |
| Position retention | ~55% |
| Tyre wear | ~39% |

**Overlap between traits:** Spearman correlations between the three traits are 0.32–0.52, so each adds information and the overall score does not count one trait twice.

---

## 5. Robustness

Each analysis choice was changed one at a time and the overall ranking recomputed (`reports/tables/robustness.csv`, [Figure 4](../reports/figures/fig4_robustness.png)):

| Alternative | What changes |
|---|---|
| Rank-based scoring | 1st = 100, 2nd = 90, … instead of min-max |
| Z-score scoring | Distance from the average team, in standard deviations |
| Without Sprints | Grand Prix and Qualifying sessions only |
| Mixed-weather GPs included | Canada and Kuala Lumpur kept in tyre wear |
| Whole-session qualifying laps | Each team's fastest lap of the whole session, not Q1 / SQ1 |

**Result:**
- **Mercedes, Racing Bulls and Ferrari finish in the top 4 under every alternative.**
- **Williams, Aston Martin and Cadillac finish in the bottom 3 under every alternative.**
- The order within the top group, and the middle five (McLaren, Audi, Red Bull, Alpine, Haas), depends on the choices made. The middle five should be read as a group, not as a precise order.

---

## 6. Pre-registered post-race test

Written before the race. Results will be reported whatever they show.

- **Team result** for each Singapore session (Sprint on Oct 10, Grand Prix on Oct 11): the mean finishing position of the team's two cars, with a non-classified car counted as 22nd.
- **Test A:** Spearman rank correlation between the pre-race overall score and the team result, separately for the Sprint and the Grand Prix.
- **Test B:** each trait recomputed on the Singapore sessions alone, correlated with that trait's pre-race score.

With 11 teams and one race weekend this is a directional check: |ρ| needs to be about 0.6 before it means much. A weak match would not prove the method wrong, and a strong one would not prove it right.

---

## 7. Limitations

**Data:**
- Only 16 rounds, under brand-new 2026 rules. Early-season races count the same as recent ones, although teams develop quickly.
- New 2026 telemetry (battery deployment, active-aero states) is not in the public feed.
- Pit-lane starts can't be identified: every starter has a grid slot from 1 to 22.

**Measurement:**
- Tyre wear is the noisiest trait. A driver deliberately saving tyres produces flat lap times, which can make a slow car look gentle on its tyres.
- Position retention partly reflects overall race pace. It also ignores reliability, because retirements are excluded.
- Minimum corner speed does not capture acceleration out of the corner.

**Scope:**
- Safety cars (frequent at Singapore), night and heat effects, and Singapore's first Sprint weekend are not scored.
- Team-level scores hide driver differences. Most teammates are close (median gap 0.7 qualifying places), but some pairings are lopsided; at those teams the stronger driver can finish well above the team average:

  | Team | Qualifying head-to-head | Average qualifying gap |
  |---|---|---|
  | Alpine | Gasly 12–4 Colapinto | 2.6 places |
  | Red Bull | Verstappen 12–3 Hadjar | 2.2 places |
  | Williams | Sainz 12–3 Albon | 1.6 places |
  | Aston Martin | Alonso 12–2 Stroll | 1.4 places |

  Team scores also include substitute or swapped drivers (Lawson raced for both Red Bull and Racing Bulls; Tsunoda for Racing Bulls).

---

## 8. Decision log

| Date | Decision | Alternatives considered |
|---|---|---|
| Oct 2 | Three traits, team-level, 2026 data only, publish before the race and test afterwards | Up to 7 traits; prediction model |
| Oct 3 | Slow-corner speed from telemetry corner speeds | Qualifying sector times (mix straights and corners) |
| Oct 3 | Include Sprints in all three traits | Grand Prix only |
| Oct 3 | Exclude Madrid (R14) from slow-corner speed: no corner map | Detect corners from the speed trace (inconsistent with other tracks) |
| Oct 4 | Locate corners by X/Y; drop frozen speed readings | Distance along lap (drifts) |
| Oct 5 | Exclude mixed-weather GPs (R5, R16) from tyre wear; R16 also has no corner map | Include them (tested in section 5) |
| Oct 6 | Grid-adjusted position retention | Raw places gained; places lost only (both track grid position) |
| Oct 6 | Q1 / SQ1 laps for slow-corner speed | Whole-session fastest lap (tested in section 5) |
| Oct 6 | Min-max scoring, equal weights | Rank, z-score, uncertainty-shrunk scores (tested in section 5) |
