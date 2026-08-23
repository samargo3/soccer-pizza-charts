# Metrics dictionary

The single source of truth for every stat used in the charts. Before adding or
changing a metric anywhere in the pipeline, define it here first.

For each metric, record: what it means, where it comes from, which chart
category it belongs to, whether it's normalized per 90 minutes, and any notes on
edge cases (e.g. how it's handled for goalkeepers).

Source for this project is **StatsBomb open event data** (see
`docs/adr/0003-data-source-strategy.md`). Field names below are StatsBomb /
statsbombpy columns on the flattened event table.

## Chart categories

Pizza slices are grouped into categories. Proposed grouping (adjust as you go):

- **Defending** — tackles, interceptions, blocks, clearances, aerials won.
- **Possession** — touches, pass completion, progressive passes received.
- **Progression** — progressive carries, progressive passes, dribbles.
- **Attacking** — non-penalty goals, xG, shots, assists, xA.

## How percentiles work here

Each metric shown on the chart is converted to a **percentile rank within a peer
group** — by default, players in the same position group with a minimum minutes
threshold. A percentile of 90 means "better than 90% of comparable players on
this metric." The percentile, not the raw value, sets the slice length.

Minimum minutes threshold: **900 minutes**. Players below this are dropped
from the percentile pool so a handful of substitute appearances cannot
dominate per-90 rates. Chosen for this project (replacing the earlier 450
placeholder); roughly 10 full matches.

## Minutes

Minutes are not a StatsBomb column. Per match:

- Clock is **period + timestamp** (period-relative `HH:MM:SS.mmm`). Raw
  `minute` is not a single timeline: first-half stoppage can be 46+ while
  second-half kickoff resets to 45, so HT subs would be undercounted.
- Starters begin at 0. A starter is anyone who appears in events and is **not**
  a `substitution_replacement`. (Starting XI lineups lived in `tactics`, which
  was dropped at ingest; unused bench players never appear in events.)
- Players listed as `substitution_replacement` begin at that Substitution
  event's elapsed time.
- Players listed as `player` on a Substitution event (coming off) end there.
- Everyone else ends at the last **Half End** of the match.
- Season minutes = sum across matches.

**Known inaccuracy:** red cards / second yellows (`foul_committed_card`,
`bad_behaviour_card`) are not used as an off-time. A sent-off player is still
counted until match end, so that team's player-minutes run slightly above
11 × match length.

## Metric table

| Metric | Category | Per 90? | Source (StatsBomb) | Definition | Notes / edge cases |
|--------|----------|---------|--------------------|------------|--------------------|
| Non-penalty goals | Attacking | Yes | `type=Shot`, `shot_outcome=Goal`, `shot_type≠Penalty` | Goals excluding penalties | Free-kick goals count; penalty goals do not |
| npxG | Attacking | Yes | `shot_statsbomb_xg` on non-penalty shots | Sum of StatsBomb xG excluding penalties | Includes blocked / off-target shots; excludes `shot_type=Penalty` |
| Shots | Attacking | Yes | `type=Shot` | All shots, including penalties | |
| Assists | Attacking | Yes | `pass_goal_assist=True` | Passes tagged as the goal assist | Flag is True vs null, not True/False. Disjoint from `pass_shot_assist` in this dump |
| Key passes | Attacking | Yes | `pass_shot_assist=True` | Passes that assisted a shot but not a goal | Not a superset of assists here — the two flags do not overlap |
| Passes attempted | Possession | Yes | `type=Pass` | All pass events | |
| Passes completed | Possession | Yes | `type=Pass` and `pass_outcome` null | Completed passes | StatsBomb leaves `pass_outcome` null on a successful pass. Unsuccessful: Incomplete, Out, Pass Offside, Unknown, Injury Clearance |
| Pass completion % | Possession | No | completed / attempted | Already a rate — do not per-90 | |
| Tackles won | Defending | Yes | `type=Duel`, `duel_type=Tackle`, outcome in {Won, Success In Play, Success Out} | Successful tackle duels | `Aerial Lost` is a different `duel_type` and is not a tackle. Lost In Play / Lost Out are unsuccessful |
| Interceptions | Defending | Yes | `type=Interception` | All interception events | Count the event, not only `interception_outcome=Won` |
| Blocks | Defending | Yes | `type=Block` | All block events | The shot's `shot_outcome=Blocked` is the shooter, not the blocker |
| Progressive passes | Progression | Yes | **Project rule** on completed passes (see below) | Completed passes that cut distance-to-goal by ≥ 10 yards and do not start in the defensive third | Not a StatsBomb flag |
| Progressive carries | Progression | Yes | **Project rule** on carries (see below) | Carries that cut distance-to-goal by ≥ 10 yards and do not start in the defensive third | Uses `location` → `carry_end_location` |
| Successful dribbles | Progression | Yes | `type=Dribble`, `dribble_outcome=Complete` | Take-ons completed | StatsBomb flag, not the distance rule |

### Progressive actions (project definition — not a source flag)

StatsBomb does not tag passes or carries as progressive. These rules are **ours**.
They are a v1 distance-to-goal cutoff, not FBref/Opta (no “into the box”
exception, and the excluded zone is the defensive **third** at `x < 40`, not
FBref’s defending 40%).

Pitch: StatsBomb 120×80 yards. Opponent goal center **G = (120, 40)**. Events
are oriented so the team in possession attacks toward `x = 120`.

For an action with start `(x0, y0)` and end `(x1, y1)`:

```
d0 = hypot(120 - x0, 40 - y0)
d1 = hypot(120 - x1, 40 - y1)
progressive ⇔ (x0 ≥ 40) AND (d0 − d1 ≥ 10)
```

| Constant | Value | Meaning |
|----------|-------|---------|
| Goal | `(120, 40)` | Opponent goal center |
| Threshold | **10 yards** | Minimum reduction in Euclidean distance to G |
| Defensive third | start `x < 40` | **Excluded** — long clearances from one’s own third would otherwise count |

Applied to:

- **progressive_passes** — `type=Pass`, `pass_outcome` is null (completed),
  start = `location`, end = `pass_end_location`.
- **progressive_carries** — `type=Carry`, start = `location`, end =
  `carry_end_location`. Same 10-yard / defensive-third rule.

**Not applied to dribbles.** `successful_dribbles` is `type=Dribble` with
`dribble_outcome=Complete` (a StatsBomb outcome, independent of coordinates).

Not in this aggregation stage (still defined for later if we add them):

| Metric | Category | Per 90? | Source | Definition | Notes / edge cases |
|--------|----------|---------|--------|------------|--------------------|
| xA | Attacking | Yes | _not derived yet_ | Expected assists | StatsBomb has no ready-made xA on open data; do not invent |
| Touches | Possession | Yes | _not derived yet_ | | Not in this stage |
| Aerials won | Defending | Yes | _not derived yet_ | | `duel_type=Aerial Lost` is the loser only |

## Position

Each player is tagged with their **modal** `position` across all of their
events (excluding null and the rare `Substitute` label). This is the StatsBomb
event position string (e.g. `Center Forward`).

## Position groups

Percentiles are computed **within** a position group, not across the whole
league. Granular StatsBomb positions collapse to four groups:

| Group | StatsBomb `position` values |
|-------|-----------------------------|
| Forward | Center Forward, Left Center Forward, Right Center Forward, Left Wing, Right Wing |
| Midfielder | Center Attacking Midfield, Left/Right Midfield, Left/Right Center Midfield, Center/Left/Right Defensive Midfield |
| Defender | Left Back, Right Back, Left Center Back, Right Center Back |
| Goalkeeper | Goalkeeper |

Wings sit with Forwards: they are attacking wide players, not central
midfielders. Unmapped / null positions are excluded from every pool.

**This chart's pool:** Forwards with ≥ 900 minutes, La Liga 2015/16.

## Open questions

- How to handle players who changed position mid-season? (currently: modal)
- Should key passes include assists? In this feed the flags are disjoint.
- Finer peer groups (striker vs winger) if the Forward pool feels mixed.
