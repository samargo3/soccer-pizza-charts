# Soccer Pizza Charts

An end-to-end data project: pull soccer player statistics, compute percentile
rankings, and render interactive "pizza" (radar-style) charts for players and
teams. Built as a learning project to understand the full data-to-visualization
pipeline, with the longer-term goal of applying the same pattern to other
domains (e.g. business analytics).

## The idea in one line

Raw stats come in once, get progressively refined through a Python pipeline,
land as simple JSON files, and a web UI reads those files to draw the charts.
The UI never talks to the data source directly — that separation is the whole
point.

## Architecture

```
Data source        →  Pipeline (Python)           →  Serving      →  UI
FBref via              ingest → transform →            static          React + D3
soccerdata             compute (percentiles)           JSON            pizza charts
                                                                        ▲
                              GitHub Actions re-runs the pipeline ──────┘
                              weekly and redeploys the UI
```

- **Ingest** — fetch from the data source, cache raw files, never re-download.
- **Transform** — clean the data, convert to per-90 rates, tag positions.
- **Compute** — turn clean stats into percentile ranks within peer groups.
- **Serving** — export the computed table as static JSON, one file per league.
- **UI** — a React app where D3 draws each slice; slice length = percentile.
- **Automation** — a scheduled GitHub Actions workflow keeps data fresh.

## Tech stack

| Layer     | Tools                                             |
|-----------|---------------------------------------------------|
| Data      | Python 3.12+, `soccerdata`, `pandas`, `duckdb`, `pyarrow` |
| Charts    | `mplsoccer` (PyPizza) for the static reference chart |
| UI        | Vite, React, TypeScript, `d3`                     |
| Testing   | `pytest`                                          |
| Automation| GitHub Actions                                    |
| Tooling   | Cursor, git, GitHub                               |

## Repo structure

```
.
├── README.md              You are here
├── .gitignore
├── .cursor/rules/         Project rules Cursor loads automatically (.mdc)
├── docs/
│   ├── metrics.md         Data dictionary — every stat and how it's computed
│   ├── log.md             Running dev log
│   └── adr/               Architecture Decision Records (the "why")
├── src/soccer_pizza_charts/   Installed package: ingest / transform / compute
├── web/                   Vite + React + TypeScript UI (Phase 3)
└── data/                  Local data cache — NOT committed to git
```

Pipeline modules live in `src/soccer_pizza_charts/` (import as
`soccer_pizza_charts.transform`, etc.):

- `ingest.py` — fetch StatsBomb open events (La Liga 2015/16) and cache to
  `data/events_la_liga_2015_16.parquet`. Re-runs skip per-match files already
  under `data/raw/statsbomb/events/`.
- `transform.py` — pure functions (`derive_minutes`, `assign_positions`,
  `counting_metrics`, `progression_metrics`, `build_player_season`) plus I/O
  at the edges. Reads the events Parquet, writes
  `data/player_season_la_liga_2015_16.parquet`.
- `compute.py` — percentile ranks within a position group; pizza PNG in
  `outputs/`. Does not re-fetch or rebuild the player-season table.

## Getting started

> This is a Phase 0 scaffold. The pipeline and UI are built in later phases.

1. Clone the repo and open it in Cursor.
2. (Phase 1+) Create a Python environment and install dependencies.
3. Read `docs/metrics.md` before touching any stat calculations.
4. Read the ADRs in `docs/adr/` to understand the key decisions.

## Roadmap

- **Phase 0** — Scaffold: repo, docs, Cursor rules. ← *current*
- **Phase 1** — One correct static pizza chart in a notebook.
- **Phase 2** — Refactor into a real pipeline with tests.
- **Phase 3** — Interactive React + D3 UI.
- **Phase 4** — GitHub Actions automation + CI.
- **Phase 5** — Write up how the pattern generalizes to business analytics.

## A note on data sources

Statistics are sourced from FBref (via the `soccerdata` library). Respect the
source's terms of use and rate limits — the ingest layer caches aggressively so
we fetch each thing only once.
