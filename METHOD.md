# Method

> **Draft (updated Oct 5, 2026).** The open decisions listed at the end are settled by Oct 6. This file is frozen with the scores in the `pre-race-snapshot` release on Oct 8, before the first Singapore session.

## Question

Based on their 2026 season so far, which teams have the strongest profile for the Singapore Grand Prix (Marina Bay, Oct 9–11, 2026)?

This is a **descriptive** analysis, not a race prediction. It scores each team on three traits that Singapore rewards, then tests those scores against the actual Singapore results.

## Data

- **Source:** official F1 timing data via the [FastF1](https://docs.fastf1.dev) Python library.
- **Rounds:** every 2026 round completed before Singapore, i.e. rounds 1–16 (Round 16 is the "Bahrain Grand Prix" held in Kuala Lumpur on Oct 4).
- **Sessions:** Qualifying and Grand Prix for every round; Sprint Qualifying and Sprint for the sprint weekends (rounds 2, 4, 5, 9, 12). Practice is not used, because teams don't show their true pace there.
- **Unit of analysis:** the team. Both drivers share the car, and averaging both doubles the data.
- **Pre-2026 data** is used only to describe the circuit, never to score teams, because the 2026 rules changed the cars completely.

## Metric 1: Position retention

**Definition.** For each classified driver in each Grand Prix and Sprint, places gained = `GridPosition − ClassifiedPosition`.

That is then compared with the **expected** places gained: the average for all drivers who started from the same pair of grid slots (P1–2, P3–4, ...) across the season. The team score is the mean of (places gained − expected), over all of its driver-sessions. Higher is better.

**Why it matters for Singapore.**
- The track is narrow, lined with walls and has few overtaking spots. The race order tends to follow the starting order, and lost places are rarely regained.
- The metric captures **race-day execution**: how well a team turns its qualifying position into a finish. That reflects:
  - race pace relative to qualifying pace
  - clean starts
  - pit stop speed
  - strategy calls
  - staying out of trouble
- Sprints are included because a Sprint has no required pit stop, so it is almost purely a test of holding position. That is the closest 2026 equivalent to Singapore's own Sprint.

**Caveats.**
- Raw places gained is structurally biased by starting position. A car starting near the back can only gain, and is promoted whenever cars ahead retire; a car on pole can only lose. Raw net places gained correlates 0.94 (Spearman) with a team's average grid position. The adjusted version compares each driver with the average places gained from the same grid slot (slots pooled in pairs) to remove this.
- The 2026 results give every starter a grid slot from 1 to 22, so pit-lane starts cannot be identified separately. They appear at the back of the grid.
- Counting only finishers ignores reliability, so a team that retires often is not penalised here.

## Metric 2: Slow-corner speed

**Definition.** In each Qualifying and Sprint Qualifying session, take each team's fastest lap **from the first knockout round (Q1 / SQ1)**. Every car runs that round, on the same tyre (Softs in Qualifying, Mediums in Sprint Qualifying) and in similar track conditions. Measure the car's minimum telemetry speed while it is within 60 m of each corner marker.
- **Slow corners** are those where the median minimum speed across teams is below 120 km/h. The data picks them; there is no hand-picked list.
- **Session score:** the team's average km/h deficit to the best team across those corners.
- Sessions with fewer than 3 slow corners are excluded. No qualifying session in 2026 so far was wet.
- **Team score:** the mean deficit across sessions (lower is better).

**Why it matters for Singapore.**
- Singapore is a slow street circuit with 19 corners and short straights, so most lap time is won or lost in slow corners.
- Slow-corner speed is mostly a property of the car:
  1. **Mechanical grip:** the suspension keeps the tyres pressed onto a bumpy surface.
  2. **Low-speed downforce:** aerodynamic grip that still helps at low speed.
  3. **Agility:** how willingly the car turns into tight corners.
  4. **Traction:** putting power down on the way out, including how 2026 electric power is delivered.
- **Why qualifying:** every car is at maximum effort, on low fuel and with no traffic, so it is the cleanest like-for-like comparison.
- **Why minimum corner speed rather than sector times:** a sector mixes straights with corners, so a strong engine can hide a weak slow-corner car.

**Caveats.**
- Speed is sampled about 4 times per second, so a single corner's minimum can be off by 1–2 km/h. Averaging over many corners and sessions smooths this out.
- Minimum speed does not capture how quickly a car accelerates out of a corner.
- **Telemetry cleaning:**
  - **Corner location:** corners are found by track-map position (X/Y), not by distance along the lap. FastF1's distance is integrated from speed and drifts by up to ~3% per lap, enough to put a "corner" reading on the following straight.
  - **Frozen readings:** the 2026 speed channel sometimes stalls for up to about 1 second, holding one value (for example 305 km/h through a braking zone). Corner readings with 3 or more identical consecutive speed samples are dropped. This is about 8% of slow-corner readings, spread evenly across teams (5–11%).
  - **Outliers:** readings more than 30 km/h from the median of the other teams at that corner are dropped.
  - **Coverage:** a corner is used only if at least 8 teams have valid readings.
- Two qualifying sessions are excluded because FastF1's corner map for those tracks is unavailable (car telemetry exists): Round 14 (the new Madrid circuit) and Round 16 (Kuala Lumpur). The metric uses the remaining 18 sessions.
- The choice of Q1 laps matters for some teams. Using each team's fastest lap of the whole session instead moves Audi from 3rd to 7th, for example. Q1 was chosen because whole-session laps mix tyre types in Sprint Qualifying and favour teams that reach the later, faster-track rounds.

## Metric 3: Tyre degradation

**Definition.** For each Grand Prix and Sprint stint, keep laps that are:
- green-flag only
- not pit in/out laps and not lap 1
- marked accurate by FastF1
- within 107% of the stint median

Keep stints of at least 8 laps on dry tyres. The two mixed-weather Grands Prix are excluded: Canada (Round 5) and Kuala Lumpur (Round 16, wet start). A drying track gets faster lap by lap, which disguises tyre wear. The compound must also have at least 3 stints in that session for a field average to be meaningful.

Fit a straight line of lap time (s) against tyre age (laps); its slope is the seconds lost per lap of wear. Subtract the field-average slope for the same session and tyre compound. The team score is the mean relative slope (lower is better).

**Why it matters for Singapore.** It is a hot, humid, 62-lap race, which punishes tyre wear. Low wear lets a team stop fewer times, extend a stint, or react to a safety car.

**Why wear differs when every team has identical Pirelli tyres.** Each car works the same tyres differently:
1. **Aerodynamics (downforce):** more grip means less sliding, and sliding is what scrubs rubber off. *(car)*
2. **Suspension and weight balance:** how the load is spread across the four tyres; an overloaded tyre wears first. *(car)*
3. **Heat management:** tyres grip only within a temperature window. Cars that overheat them lose grip quickly, especially in hot races. *(car, plus driver)*
4. **Driving style:** smooth braking, steering and throttle wear tyres less. *(driver)*

Strategy (which tyres to use and when to pit) is a set of team decisions and is not scored.

**Caveats.**
- Burning fuel makes the car faster during a stint, which partly hides wear. This affects all teams similarly, so rankings hold.
- A driver deliberately saving tyres produces flat lap times. That can make a slow car look gentle on its tyres.
- **Precision:** single stints are noisy. Each team's score averages 55–74 stints, with a standard error of about 0.005–0.013 s/lap.
  - **The ends of the ranking are clear:** Mercedes and Racing Bulls are best, Cadillac worst, in every variant tested.
  - **The midfield is not:** teams differ by less than their uncertainty, so midfield ranks on this metric should not be over-read.

## Sprints vs Grand Prix sessions

Data for both is pulled the same way; only the session code differs. Each metric compares teams **within the same session** (and, for tyres, the same compound), so format differences cancel out:

| Metric | Grand Prix weekend | Sprint session |
|---|---|---|
| Position retention | Qualifying grid → GP finish | Sprint Qualifying grid → Sprint finish; one more race, with fewer laps to gain or lose places |
| Slow-corner speed | Qualifying (mostly Soft tyres) | Sprint Qualifying (mostly Medium tyres); compared within the session, so the tyre difference cancels |
| Tyre degradation | 2–3 stints, mixed tyres, heavy fuel at the start | One stint of about 17–24 laps, mostly Mediums, lighter fuel; compared within the session and compound |

As a sensitivity check, the scores were recomputed without Sprints:
- **Retention and slow-corner speed:** no team's rank moved by more than 1 place, except Aston Martin in slow-corner speed (9th → 11th).
- **Tyre degradation:** the top 3 and bottom 3 stayed the same teams. Midfield ranks moved by up to 3 places (Williams 5th → 8th).

## Scoring

Each metric is scaled 0–100 across the 11 teams (100 = best). The composite score is the equal-weight mean of the three.

## Pre-registered post-race test

Written before the race. Results are reported whatever they show.

- **Team result** for each Singapore session (Sprint on Oct 10, Grand Prix on Oct 11): the mean finishing position of the team's two cars, with a non-classified car counted as 22nd.
- **Test A:** Spearman rank correlation between the pre-race composite score and the team result, for each session.
- **Test B:** recompute each metric on the Singapore sessions alone, and correlate it with that metric's pre-race score.

With only 11 teams this is a directional check: |ρ| needs to be about 0.6 before it means much.

## Known limitations

- Rounds 1–16 only, under brand-new 2026 rules.
- Scores describe the season so far and are not a prediction.
- Safety cars, night conditions and Singapore's first Sprint weekend are not scored.
- New 2026 telemetry (battery deployment, active-aero states) is not in the public feed.
- Team-level scores hide differences between the two drivers.

## Open decisions (settled by Oct 6)

- [x] Retention: grid-adjusted places gained (Oct 5), chosen over net and places-lost, which mostly track grid position
- [x] Slow-corner speed: fastest lap from Q1 / SQ1 only (Oct 5)
- [ ] Scoring: min-max vs rank scaling; equal weights
