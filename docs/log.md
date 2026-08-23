# Dev log

A running, informal log of what was done, what broke, and what was learned.
Newest entries at the top. This is for your future self — keep it low-effort.

---

## 2026-08-23 — Phase 1: percentiles + pizza

- Peer group: Forwards (CF / LCF / RCF / LW / RW) with ≥ 900 minutes → 86
  players. Threshold recorded in `docs/metrics.md`.
- Suárez attacking percentiles 95–99 except key passes (66). Progression
  31–51, defending 7–20 — box-striker shape vs a pool that includes wingers.
- Chart: `outputs/luis_suarez_la_liga_2015_16.png` (mplsoccer PyPizza).

## 2026-08-22 — Phase 1: progressive passes/carries (project rule)

- v1: action is progressive if start x ≥ 40 and Euclidean distance to (120, 40)
  drops by ≥ 10 yards. Documented in `docs/metrics.md` as a project choice.
- Successful dribbles = `dribble_outcome=Complete` (source flag, not the rule).
- Joined onto existing player-season table without recomputing stage 1.
- Top prog. passes/90 (900+ min): Kroos, Damián Suárez, Marcelo, Dani Alves,
  Modrić — looks like real progressors. Suárez: 71 / 75 / 50 (pass/carry/dribble).

## 2026-08-22 — Phase 1: player-season aggregates (no percentiles)

- `pipeline/transform.py` reads the event Parquet only (no re-fetch).
- Minutes from period+timestamp and Substitution on/off; 11×match-length
  invariant holds exactly on sampled matches. Red cards are a known individual-
  minutes overcount (team sum still 11× because we do not clock the dismissed
  player off).
- Modal StatsBomb `position`; counting stats + per-90. Pass completion % is a
  rate. Cached `data/player_season_la_liga_2015_16.parquet` (539 players).
- Suárez (`Luis Alberto Suárez Díaz`): 3273 min, 37 np goals, 23.7 npxG, 15
  assists. Stopped before percentiles / chart.

## 2026-08-22 — Phase 1: StatsBomb event cache (La Liga 2015/16)

- Fetched all 380 matches via `statsbombpy` (`sb.matches` + `sb.events`).
  0 failures after one-retry-and-continue. ~1.30M events.
- Dropped nested columns before Parquet: `50_50`, `shot_freeze_frame`, `tactics`.
  Coordinate lists (`location`, `pass_end_location`, `shot_end_location`) kept.
  Added `pyarrow` for the write.
- Cache: `data/events_la_liga_2015_16.parquet` (140 MB) plus per-match files
  under `data/raw/statsbomb/events/` so we never re-hit GitHub for a match
  that already succeeded.
- Subject string is `Luis Alberto Suárez Díaz` (4,985 events). Several other
  players contain "Suárez" (Isco, Denis Suárez, Damián Suárez, …) — match on
  the full legal name, not a substring.
- Stopped at inspect. No aggregation / per-90 / percentiles / chart.

---

## 2025-08-20 — Phase 0: scaffold

- Created the repo structure: `pipeline/`, `data/`, `docs/`, `.cursor/rules/`.
- Wrote the README, `.gitignore` (Python + Node), and three Cursor project rules
  (project context, python pipeline, frontend).
- Started the metrics dictionary (`docs/metrics.md`) and two ADRs (record-
  decisions; DuckDB + static JSON).
- Next: Phase 1 — pull FBref data with `soccerdata` and produce one correct
  static pizza chart in a notebook.
