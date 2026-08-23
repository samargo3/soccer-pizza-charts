# ADR 0003 — Data source strategy: build on StatsBomb open event data

**Status:** Accepted
**Date:** 2026-08-22

## Context

The project needs player statistics rich enough to build "pizza" percentile
charts across attacking, progression, possession, and defending. The original
plan assumed FBref (via soccerdata) as the source. Two things changed that:

1. **FBref lost its advanced-stats feed.** On 20 January 2026, Sports Reference
   (which operates FBref) removed all advanced statistics after its data
   provider, Stats Perform / Opta, terminated access. Everything Opta-derived —
   xG, npxG, xAG, progressive carries and passes, and the possession/passing
   detail — is gone from FBref for everyone. What remains is basic counting
   stats only (goals, assists, shots, tackles, interceptions, minutes, cards).
   We verified this empirically: both the single-league and the Big 5 Combined
   standard tables now return the stripped set, with no xG anywhere.

2. **The tabular alternatives each cover only half, and one was unreachable.**
   Understat still provides xG/xA/shots/key passes but has no defensive or
   possession data, and the dev machine could not complete a TLS handshake to
   understat.com. FBref (basic) + Understat (xG) could in principle be joined,
   but only via fragile cross-source player-name matching, and even combined
   they cannot supply progressive carries/passes, pass %, or touches from a
   free source post-Opta.

Separately, a stated goal of the project is to learn the full data stack in
order to apply the pattern elsewhere (e.g. business analytics), not just to
consume pre-aggregated tables.

## Decision

Build on **StatsBomb open data** (event-level) via the `statsbombpy` client,
read directly from the `hudl/open-data` GitHub repository (no credentials, no
scraping). Compute all chart metrics ourselves by aggregating raw events —
StatsBomb attaches its own xG to each shot, and progression, possession, and
defending metrics are derived from the event stream.

First working target: **La Liga 2015/16** (competition_id 11, season_id 27),
charting **Luis Suárez** as the sanity-check subject (a two-sided outlier: elite
finishing and elite creation that season).

Existing FBref caches are retained in case tabular data is useful later.

## Consequences

**Easier / better**
- One self-sufficient source: no cross-source name matching, and the full
  four-category chart (attacking, progression, possession, defending) is
  achievable again.
- Served from GitHub, so access is robust — no Cloudflare, no scraping, no TLS
  handshake problems.
- Recovers the metrics FBref's Opta loss removed, for covered competitions.
- Aggregating events into player-season metrics is the deeper, more transferable
  skill (raw records → engineered metrics ≈ transactions/logs → business KPIs).

**Harder / limits**
- **Coverage:** the free set is selected competitions, NOT current top-5 league
  seasons. "Current season" charts are out of scope for this source and would
  need a different or paid provider later.
- **Weight:** we process thousands of events per match; a season is ~380 match
  files. Caching the consolidated result to Parquet is essential.
- **Minutes must be derived** from the starting XI plus substitution events —
  there is no minutes column. Per-90 rates depend on getting this right.
- **Licensing:** the open data is free for research and public use *with
  attribution* to StatsBomb (state the source, use their logo when publishing).
  It is not licensed for commercial use — a commercial product would need
  StatsBomb's paid data. (Not legal advice; see the repo's LICENSE.pdf.)

## Notes

- StatsBomb stores full legal player names (e.g. Suárez is not "Luis Suárez").
  Name strings must be confirmed from the data, not assumed.
- Superseded parts of ADR 0002 (DuckDB/Parquet, static JSON) still hold; only
  the upstream source changes.
