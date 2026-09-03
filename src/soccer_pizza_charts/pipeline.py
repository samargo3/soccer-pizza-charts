"""End-to-end data refresh: ingest → transform → compute → JSON export.

Cache-aware: uses the events Parquet when it exists; otherwise fetches
StatsBomb open data (no credentials). See docs/metrics.md.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from soccer_pizza_charts.compute import (
    MIN_MINUTES,
    PEER_GROUP,
    comparison_pool,
    write_peer_group_json,
)
from soccer_pizza_charts.ingest import EVENTS_PARQUET, ingest_season_events
from soccer_pizza_charts.transform import (
    PLAYER_SEASON_PARQUET,
    build_player_season,
    load_events,
)


def ensure_events(parquet_path: Path = EVENTS_PARQUET) -> pd.DataFrame:
    """Return season events: cache hit, or a fresh StatsBomb fetch."""
    if parquet_path.exists():
        print(f"using cached events: {parquet_path}")
        return load_events(parquet_path)
    print(
        "no events cache; fetching StatsBomb open data "
        "(credentials were not supplied — expected for open data)."
    )
    events, failed, dropped = ingest_season_events(parquet_path=parquet_path)
    print(f"succeeded: {events['match_id'].nunique()} matches")
    print(f"failed match_ids: {failed if failed else '(none)'}")
    print(f"dropped nested columns: {dropped}")
    return events


def refresh() -> dict[str, object]:
    """Run ingest → transform → percentile export for the Forward pool."""
    print("=== refresh: ingest ===")
    events = ensure_events()
    print(f"events: {len(events):,} rows")

    print("=== refresh: transform ===")
    table = build_player_season(events)
    PLAYER_SEASON_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(PLAYER_SEASON_PARQUET, engine="pyarrow", index=False)
    print(f"player-season table: {table.shape[0]} players → {PLAYER_SEASON_PARQUET}")

    print("=== refresh: compute + export ===")
    pool = comparison_pool(table)
    print(f"comparison pool: {PEER_GROUP} with ≥ {MIN_MINUTES} minutes → {len(pool)} players")
    player_paths, manifest_path = write_peer_group_json(pool)
    print(f"exported {len(player_paths)} player JSON files")
    print(f"wrote {manifest_path}")
    print(
        f"=== refresh done: {len(player_paths)} players, "
        f"{len(player_paths) + 1} files under {manifest_path.parent} ==="
    )
    return {
        "n_players": len(player_paths),
        "n_files": len(player_paths) + 1,
        "manifest": manifest_path,
        "player_paths": player_paths,
    }


def main() -> None:
    refresh()
