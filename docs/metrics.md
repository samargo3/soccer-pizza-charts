# Metrics dictionary

The single source of truth for every stat used in the charts. Before adding or
changing a metric anywhere in the pipeline, define it here first.

For each metric, record: what it means, where it comes from, which chart
category it belongs to, whether it's normalized per 90 minutes, and any notes on
edge cases (e.g. how it's handled for goalkeepers).

## Chart categories

Pizza slices are grouped into categories. Proposed grouping (adjust as you go):

- **Defending** — tackles, interceptions, blocks, clearances, aerials won.
- **Possession** — touches, pass completion, progressive passes received.
- **Progression** — progressive carries, progressive passes, dribbles.
- **Attacking** — non-penalty goals, xG, shots, assists, xA.

## How percentiles work here

Each metric shown on a chart is converted to a **percentile rank within a peer
group** — by default, players in the same position group with a minimum minutes
threshold. A percentile of 90 means "better than 90% of comparable players on
this metric." The percentile, not the raw value, sets the slice length.

Minimum minutes threshold: _TBD (e.g. 450 minutes)_ — decide and record here.

## Metric table

| Metric | Category | Per 90? | Source (FBref field) | Definition | Notes / edge cases |
|--------|----------|---------|----------------------|------------|--------------------|
| Non-penalty goals | Attacking | Yes | `goals` − `pens_made` | Goals excluding penalties | |
| npxG | Attacking | Yes | `npxg` | Non-penalty expected goals | |
| Assists | Attacking | Yes | `assists` | | |
| xA | Attacking | Yes | `xg_assist` | Expected assists | |
| Shots | Attacking | Yes | `shots` | Total shots | |
| Progressive carries | Progression | Yes | `progressive_carries` | Carries toward opp. goal | |
| Progressive passes | Progression | Yes | `progressive_passes` | Passes toward opp. goal | |
| Successful dribbles | Progression | Yes | `take_ons_won` | | |
| Pass completion % | Possession | No | `passes_pct` | Already a rate — do not per-90 | Rate, not a count |
| Touches | Possession | Yes | `touches` | | |
| Tackles won | Defending | Yes | `tackles_won` | | |
| Interceptions | Defending | Yes | `interceptions` | | |
| Blocks | Defending | Yes | `blocks` | | |
| Aerials won | Defending | Yes | `aerials_won` | | |

> The source field names above are illustrative — verify them against what
> `soccerdata` actually returns in Phase 1 and correct this table.

## Position groups

Percentile peer groups are based on position. Proposed groups: _forwards,
attacking midfielders, central midfielders, fullbacks, center backs,
goalkeepers_. Record the exact mapping once decided.

## Open questions

- Final minutes threshold?
- How to handle players who changed position mid-season?
- Which season(s) and competition(s) form the comparison pool?
