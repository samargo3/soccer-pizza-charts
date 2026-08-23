# pipeline/

Python data pipeline. Code arrives in Phase 1–2, organized as:

- `ingest.py` — fetch StatsBomb open events (La Liga 2015/16) and cache to
  `data/events_la_liga_2015_16.parquet`. Re-runs skip per-match files already
  under `data/raw/statsbomb/events/`.
- `transform.py` — minutes, modal position, counting stats, per-90 from
  `data/events_la_liga_2015_16.parquet` → `data/player_season_la_liga_2015_16.parquet`.
  Stage 2 joins coordinate-derived progression metrics onto that table.
- `compute.py` — percentile ranks within a position group; pizza PNG in
  `outputs/`. Does not re-fetch or rebuild the player-season table.

See `.cursor/rules/100-python-pipeline.mdc` for conventions.
