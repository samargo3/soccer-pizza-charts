# Dev log

A running, informal log of what was done, what broke, and what was learned.
Newest entries at the top. This is for your future self — keep it low-effort.

---

## 2026-08-24 — Phase 2 step 3B: deduct red-card minutes

- Sending-off (`Red Card` or `Second Yellow` on `foul_committed_card` or
  `bad_behaviour_card`) now ends that player's interval. Yellow cards do not.
  Team minutes on a sending-off match sit below 11 × length. Suárez unchanged.
  See `docs/metrics.md`.

## 2026-08-24 — Phase 2 step 3A: key passes include assists

- `key_passes` is now `pass_shot_assist` OR `pass_goal_assist`. StatsBomb
  tags them exclusively; the union is the conventional key-pass definition.
  Assists stay goal-assists only. See `docs/metrics.md`.

## 2026-08-24 — Phase 2 step 2b: JSON schema_version 2

- Metadata only: `higher_is_better` on each metric, top-level `categories`
  (colors match the pizza), `generated_at`, `data_source`. Percentiles unchanged.
- Path is now `outputs/json/v2/...`. Contract documented in `docs/schema.md`.

## 2026-08-24 — Phase 2 step 2: percentiles + player JSON export

- Percentile math was already in `compute.py` (pandas `rank(method="average", pct=True)*100`, Forward pool, ≥900 minutes, 12 higher-is-better per-90 slices). Kept it.
- The Phase 1 notebook never computed percentiles; `compute.py` is the source of truth. Aligned `PIZZA_METRICS` column names to the player-season parquet (`np_goals_per90`, `key_passes_per90`, …).
- New JSON: `export_player_json` (pure dict) + `write_player_json` → `outputs/json/v1/la_liga_2015_16/<player>.json`. Schema version 1, one file per player. Did not change chart rendering.

## 2026-08-24 — Phase 2 step 1b: move pipeline into src-layout package

- Moved `ingest.py` / `transform.py` / `compute.py` from `pipeline/` into
  `src/soccer_pizza_charts/`. Kept the existing implementations (not empty
  stubs) so ingest/compute tests stay green. Replaced the uv hello-world
  `main()` with a one-line package docstring.
- Imports are now `from soccer_pizza_charts.transform import ...`. Removed
  the pytest `pythonpath=["."]` shim; package is installed editable via uv.
- Deleted `pipeline/`. Conceptual ingest → transform → compute split is
  unchanged; only the folder path moved.

## 2026-08-23 — Phase 2 step 1: extract transform into tested module

- (Superseded by step 1b.) Transform lived in `pipeline/` with a pytest
  pythonpath shim; the installed package was still the uv hello-world stub.
- Public API: `derive_minutes`, `assign_positions`, `counting_metrics`,
  `progression_metrics(threshold=10)`, `build_player_season`. Same definitions
  as Phase 1 (no key-pass / red-card changes).
- `uv run pytest -q`: 11 passed. Rebuilt Suárez row matches the cached table
  (37 np goals, 23.73 npxG, 15 assists, 3273.20 minutes, 71/75/50 progression).

## 2026-08-22 — Phase 1 complete: Suárez pizza from StatsBomb events

- Data-source saga: FBref lost its Opta advanced feed (Jan 2026), removing
  xG/progression; Understat was blocked by TLS on this network. Pivoted to
  StatsBomb open event data via statsbombpy. See ADR 0003.
- Cached La Liga 2015/16: 380/380 matches, 1.29M events → Parquet (140 MB, gitignored).
- Built player-season table from raw events: minutes derived from period+timestamp
  + substitutions (validated at 11×match length), modal position, 12 metrics, per-90.
- Defined progressive passes/carries from coordinates ourselves (10-yd-to-goal
  rule, def third excluded) — documented in metrics.md. Top-5 progressors
  (Kroos, Modrić, fullbacks) validated the logic.
- Percentiles within Forward pool (86 players, ≥900 min). Suárez attacking 95–99th,
  defending/progression low — correct box-striker shape.
- Output: outputs/luis_suarez_la_liga_2015_16.png.
- Known limits to revisit in Phase 2: red-card minutes not deducted (~15 players);
  key_passes excludes assists (StatsBomb non-overlap).
- Next: Phase 2 — refactor notebook into `src/soccer_pizza_charts/` modules + pytest.

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

- `src/soccer_pizza_charts/transform.py` reads the event Parquet only (no re-fetch).
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

- Created the repo structure: `pipeline/` (later moved to
  `src/soccer_pizza_charts/`), `data/`, `docs/`, `.cursor/rules/`.
- Wrote the README, `.gitignore` (Python + Node), and three Cursor project rules
  (project context, python pipeline, frontend).
- Started the metrics dictionary (`docs/metrics.md`) and two ADRs (record-
  decisions; DuckDB + static JSON).
- Next: Phase 1 — pull FBref data with `soccerdata` and produce one correct
  static pizza chart in a notebook.
