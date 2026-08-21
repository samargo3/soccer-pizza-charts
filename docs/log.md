# Dev log

A running, informal log of what was done, what broke, and what was learned.
Newest entries at the top. This is for your future self — keep it low-effort.

---

## 2025-08-20 — Phase 0: scaffold

- Created the repo structure: `pipeline/`, `data/`, `docs/`, `.cursor/rules/`.
- Wrote the README, `.gitignore` (Python + Node), and three Cursor project rules
  (project context, python pipeline, frontend).
- Started the metrics dictionary (`docs/metrics.md`) and two ADRs (record-
  decisions; DuckDB + static JSON).
- Next: Phase 1 — pull FBref data with `soccerdata` and produce one correct
  static pizza chart in a notebook.
