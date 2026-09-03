# STATUS — Argo FC Analytics

**Last updated:** 2026-09-02
**Priority:** SECONDARY. Active but deprioritized behind prediction-engine. Personal / portfolio. Pick up when prediction-engine is between phases.
**Branch:** `main` <!-- VERIFY -->

## Current phase

Phases 0–4 — COMPLETE

Scaffold + ADRs + dev log, pizza chart pipeline from StatsBomb event data, tested `src`-layout Python package with JSON contract (schema v3), interactive React/D3 app on Vercel, CI via GitHub Actions (tests + manual-trigger data refresh).

Phase 5 — branding integration. Partially done outside the repo. See In flight.

## In flight

Brand assets exist but are not in the repo. The "1b Broadsheet" kit was generated in a Claude session on 2026-08-31 — mark (dark/light), full + compact wordmarks, horizontal lockups, favicon set (SVG / 512 / 180 Apple touch / 32), 1200×630 OG card, 21 files plus README and the matplotlib build script. Delivered as a zip.

<!-- VERIFY: did the zip get committed, or is it still sitting in Downloads? If it's still in Downloads this is the single most losable piece of work across either repo — it exists in no version-controlled place. -->

Two known follow-ups were flagged and not yet done:

1. Draft palette in `docs/branding/theme.broadsheet.draft.json` not yet reconciled with canonical tokens in `config/theme.json`.
2. Build script not yet landed under `scripts/branding/` — assets are not currently reproducible from tokens.

## Next action

Land the branding kit in the repo on a `phase-5-branding` branch: commit assets, fold the build script into `scripts/branding/`, reconcile the draft palette into `config/theme.json` so the matplotlib renderer and the web app stay on one token source.

## Blockers & open questions

- Current-season data availability is an unresolved gating risk for the multi-league vision. StatsBomb open data is historical; nothing has replaced it for live seasons. Understat is the planned source but unvalidated.
- Does the favicon/OG wiring into the Vercel app happen in the same phase or a follow-on?

## Recent decisions

- **ADR 0004** — Product vision recorded, including what scales vs. what is deliberately deferred. Read this before proposing expansion.
- **ADR 0003** — StatsBomb open data adopted as primary source after FBref lost its Opta/Stats Perform feed (Jan 2026), eliminating xG and progressive metrics site-wide.
- **ADR 0002** — DuckDB/Parquet internally, static JSON for serving.

## Deliberately deferred

<!-- All of this is from ADR 0004's deferred list plus later backlog. Do not propose any of it as next work without saying it's deferred and asking if that still holds. -->

- Team- and match-level analysis (Understat as primary xG/shot source)
- Elo-style team ratings
- xG differential and race/timeline charts; shot maps
- Multi-league expansion across top-5 with live data sources
- Continuous sample-size confidence weighting (refinement to the current binary 900-minute threshold)
- Folding the PL predictor into this platform — rejected; it lives in prediction-engine

## Cold-start notes

- **Stack:** Python `src`-layout package (`src/soccer_pizza_charts/`), `statsbombpy`, DuckDB/Parquet, `pytest`. Web: Vite + React + TypeScript + D3, Vercel with auto-deploy on push to `main`.
- **Verify current state:** `pytest` green, then check the JSON index manifest for exported player count (86 forwards, ≥900 min, La Liga 2015/16).
- **Data:** ~380 match event files, ~1.29M events, ~140MB Parquet cached locally and gitignored. Not in the repo — a fresh clone has to re-fetch.
- **Gotchas:**
  - First push on a new branch must be `git push -u origin <branch-name>`. Plain `git push` on an untracked branch has caused confusion three times.
  - `main` is branch-protected; tests CI must pass before merge.
  - `config/theme.json` is the single source of truth for design tokens — serves both the matplotlib PNG renderer and the web app. Don't fork the palette.
  - Metric definitions are project-owned and documented (progressive pass/carry 10-yard rule; key passes = shot-assists ∪ goal-assists). Changing one moves percentiles materially — redefining key passes moved Suárez 66th → 81st.
- **Related repo:** prediction-engine (Salesforce DX) — PRIMARY. Shares football-data.org and the ADR 0001 conceptual framework only. Deliberately separate.
