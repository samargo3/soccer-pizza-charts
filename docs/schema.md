# Player-chart JSON schema

The pipeline writes **one JSON file per player**. The UI reads these files;
it never recomputes percentiles. Metric definitions stay in `docs/metrics.md`.
This document is only the file shape.

Current version: **`schema_version` 2**. Path:

`outputs/json/v{schema_version}/{league}_{season}/{player}.json`

Example: `outputs/json/v2/la_liga_2015_16/luis_alberto_suarez_diaz.json`.

## Schema 2

```json
{
  "schema_version": 2,
  "generated_at": "2026-08-24T22:00:00+00:00",
  "data_source": {
    "provider": "StatsBomb open data",
    "library": "statsbombpy",
    "version": "1.22.0"
  },
  "player": {
    "name": "Luis Alberto Suárez Díaz",
    "position": "Center Forward",
    "position_group": "Forward",
    "minutes": 3273.20
  },
  "competition": { "league": "La Liga", "season": "2015/16" },
  "peer_group": {
    "position_group": "Forward",
    "min_minutes": 900,
    "n_players": 86,
    "description": "Forwards with at least 900 minutes, La Liga 2015/16"
  },
  "categories": [
    { "key": "attacking", "label": "Attacking", "color": "#C0392B" },
    { "key": "possession_progression", "label": "Possession/Progression", "color": "#1E8449" },
    { "key": "defending", "label": "Defending", "color": "#2471A3" }
  ],
  "metrics": [
    {
      "metric": "np_goals_per90",
      "label": "NP goals",
      "category": "Attacking",
      "value_per90": 1.017,
      "percentile": 98.84,
      "higher_is_better": true
    }
  ]
}
```

| Field | Notes |
|-------|--------|
| `generated_at` | UTC ISO-8601 timestamp of the export, not of the season. |
| `data_source.version` | Installed `statsbombpy` version at export time. |
| `categories` | Ordered display groups. `color` matches the Phase 1 pizza. `label` is what `metrics[].category` stores. |
| `metrics` | 12 slices in pizza order. `metric` is the column id. `value_per90` is the per-90 rate except pass completion % (already a rate). |
| `higher_is_better` | Direction for the UI. All 12 are `true` today; do not hardcode that. |

## History

- **1** — player, competition, peer group, 12 metrics (`value_per90` + `percentile`).
- **2** — `higher_is_better` on each metric; top-level `categories`, `generated_at`, `data_source`. Numbers unchanged.
