# ADR 0004 — Product direction: Argo FC Analytics

**Status:** Accepted (direction; several elements deliberately deferred)
**Date:** 2026-08-25

## Context

This project began as a learning vehicle: one player pizza chart, built to
understand a full data-to-visualization pipeline. It has since grown a
trustworthy event-data pipeline (tested `src/` package, versioned JSON contract,
themed rendering). The owner's actual goal is now explicit and larger:

> **Argo FC Analytics** — a maintained platform for soccer analytics,
> visualization, and analysis at the **player, team, and league** level, across
> the **top-5 European leagues** and **multiple seasons**.

This ADR records that direction while it is fresh, so foundations get built — or
deferred — deliberately rather than by drift. It captures intent, what already
scales, what is out of scope for now, and the key open risks. It is direction,
not a data contract; the schemas and keys for the deferred pieces get their own
ADRs when they are actually built.

## Decision

Adopt Argo FC Analytics as the north star, and:

1. Keep the **event-data-first foundation** (StatsBomb events → our own
   aggregation) as the core pattern. It is the one approach that yields player,
   team, *and* league metrics from a single source, on definitions we own.
2. Keep the current architecture — tested `src/` pipeline, `ingest → transform →
   compute`, versioned JSON contract, design tokens, the ADR habit. These scale
   to the larger vision unchanged.
3. Explicitly **scope** what the current foundation already supports vs. what is
   deferred (below), so single-season / single-position / single-competition
   scaffolding is never mistaken for the final model.
4. Treat **data sourcing for current top-5 leagues as an open, unresolved
   question and a gating risk** — to be researched before team/league features
   are built on an assumption about data we may not be able to obtain.

## Data granularity (framing for future work)

Three granularities, each implying a different source and a different class of
analysis:

- **Results / fixtures** — scores, dates, tables. Cheap and stable. Enables
  league tables over time, form, home/away splits, Elo-style ratings.
- **Match / shot level** — xG, shot maps, match aggregates. The sweet spot for
  team analysis: rolling xG trends, xG timelines, over/under-performance vs.
  results.
- **Event level** — every pass, carry, pressure. The current StatsBomb
  foundation; the deepest analysis, but free coverage of *current* top-5 seasons
  is essentially absent.

## Source landscape (as understood 2026-08; re-verify before relying on it)

- **FBref** — lost its Opta/Stats Perform feed in January 2026 (see ADR 0003).
  Now a historical archive, not a live advanced-stats source.
- **StatsBomb open data** — our event-level playground. Coverage is *selected*
  competitions (internationals, women's, select historical seasons), **not**
  current top-5 league seasons. Great for deep-dives, not for a "this weekend's
  matches" pipeline. Free tier is non-commercial with attribution (ADR 0003).
- **Understat** — the likely workhorse for current top-5 team/match xG and
  shot-level data (all five leagues). Requires scraping, which breaks regularly
  → a resilient, cached fetch layer is part of the design, not an afterthought.
- **football-data.co.uk / football-data.org** — rock-solid results/fixtures;
  a good stable spine other data joins onto.
- **Paid APIs** (API-Football, Sportmonks, StatsBomb paid, Opta) — the escape
  hatch. Free tiers are too limited to build on; this becomes a cost/licensing
  decision if the platform goes beyond personal/learning use.

## What already scales (keep building)

- The event-data foundation (teams = a different group-by; leagues = aggregations
  of the same events).
- The tested `src/` pipeline and the ingest → transform → compute split.
- The JSON contract with `schema_version` — lets the shape evolve (positions,
  teams, seasons) without breaking existing data.
- The design-tokens theme — one visual identity across every future chart type.
- The ADR habit — how a multi-league, multi-season platform stays comprehensible.

## Deferred (deliberately out of current scope)

- **Per-position peer groups + position-appropriate metric templates.**
  Cross-position comparison is not "forward metrics with worse numbers" — a
  center-back needs different slices. A genuine analytical phase.
- **Multi-league / multi-season data model.** League and season must become
  first-class dimensions/keys across ingest, storage, JSON, and file paths.
  Today `la_liga_2015_16` is a folder name; eventually it is a filterable,
  comparable dimension.
- **Team- and league-level entities and metrics** — effectively a star schema:
  matches / teams / seasons / leagues as dimensions, shot/stat facts hanging off
  them. Player pizza charts were one entity type; this is the dimensional model.
- **Cross-source entity resolution** — team/match/player identity across sources
  (a genuinely hard, and genuinely transferable, problem).
- **Incremental / scheduled loads** vs. one-shot historical fetches — overlaps
  the automation phase.

## Open risks

1. **Data availability (GATING).** Comprehensive, current, multi-season top-5
   data is not freely available post-Opta. Resolve via a dedicated sourcing
   research pass — paid tiers, providers, cost, licensing, terms of use — BEFORE
   building team/league features on it. Flagged here; not solved here.
2. **Scraper-maintenance posture.** Relying on Understat commits us to
   maintaining scrapers rather than consuming a stable API.
3. **Licensing for a maintained/published product.** StatsBomb open data is
   non-commercial with attribution (ADR 0003). A real product may require paid or
   otherwise-licensed data.

## Consequences

- Current work (86-forward batch export, player search UI) proceeds unchanged —
  it is a prerequisite either way.
- Future contributors and AI agents pointed at this repo inherit the full
  picture and the deferred list, which reduces drift.
- The data-sourcing risk is on the record as a gate, so team/league build-out
  cannot quietly start on a false assumption about available data.

## Notes

- Suggested first spike when platform work begins: a small **Understat** pull
  (one league, one season) into Parquet using the existing caching pattern, to
  test the shot-level schema and the real fragility of scraping. Reference only;
  not committed here.
- Re-verify the source landscape at the time of building — it has already shifted
  once this year (FBref/Opta), and it can shift again.
