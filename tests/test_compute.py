"""Hand-checkable percentile, peer-group, and JSON-export tests."""

from __future__ import annotations

from datetime import datetime
import json

import pandas as pd
import pytest

from soccer_pizza_charts.compute import (
    LEAGUE,
    MIN_MINUTES,
    PEER_GROUP,
    PIZZA_METRICS,
    PLAYER_NAME,
    PLAYER_SEASON_PARQUET,
    POSITION_GROUP,
    SEASON,
    build_peer_group,
    comparison_pool,
    compute_percentiles,
    export_player_json,
    percentile_ranks,
    player_percentiles,
    position_group,
    write_player_json,
)

SUAREZ = "Luis Alberto Suárez Díaz"


def test_position_group_mapping() -> None:
    assert position_group("Center Forward") == "Forward"
    assert position_group("Right Wing") == "Forward"
    assert position_group("Left Center Midfield") == "Midfielder"
    assert position_group("Left Back") == "Defender"
    assert position_group("Goalkeeper") == "Goalkeeper"
    assert position_group(None) is None
    assert set(POSITION_GROUP.values()) <= {
        "Forward",
        "Midfielder",
        "Defender",
        "Goalkeeper",
    }


def test_percentile_ranks_higher_is_better() -> None:
    # pandas rank(pct=True)*100: n=3 → 33.3, 66.7, 100. Max is always 100.
    # The middle value is not 50 under this definition (Phase 1 formula).
    s = pd.Series([1.0, 2.0, 3.0], index=["low", "mid", "high"])
    ranks = percentile_ranks(s)
    assert abs(ranks["low"] - 100 / 3) < 1e-9
    assert abs(ranks["mid"] - 200 / 3) < 1e-9
    assert abs(ranks["high"] - 100.0) < 1e-9


def test_compute_percentiles_max_is_100_on_two_players() -> None:
    # Two players: lower → 50th, higher → 100th (the "~50 / 100" case).
    table = pd.DataFrame(
        {
            "player": ["low", "high"],
            "np_goals_per90": [1.0, 2.0],
        }
    )
    ranked = compute_percentiles(
        table, metrics=[("np_goals_per90", "NP goals", "Attacking")]
    )
    by_player = ranked.set_index("player")["np_goals_per90_percentile"]
    assert by_player["high"] == 100.0
    assert by_player["low"] == 50.0


def test_build_peer_group_minutes_and_group() -> None:
    table = pd.DataFrame(
        {
            "player": ["A", "B", "C"],
            "position": ["Center Forward", "Center Forward", "Left Back"],
            "minutes": [900, 899, 3000],
            "np_goals_per90": [1.0, 2.0, 0.1],
        }
    )
    pool = build_peer_group(table, position_group="Forward", min_minutes=900)
    assert list(pool["player"]) == ["A"]
    alias = comparison_pool(table, group="Forward", min_minutes=900)
    assert list(alias["player"]) == ["A"]


def _two_player_pool() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player": [SUAREZ, "Other"],
            "position": ["Center Forward", "Right Wing"],
            "minutes": [3273.2, 2000.0],
            "np_goals_per90": [2.0, 1.0],
            "npxg_per90": [1.0, 1.0],
            "shots_per90": [4.0, 3.0],
            "assists_per90": [0.5, 0.4],
            "key_passes_per90": [1.0, 0.5],
            "pass_completion_pct": [70.0, 80.0],
            "progressive_passes_per90": [2.0, 5.0],
            "progressive_carries_per90": [2.0, 1.0],
            "successful_dribbles_per90": [1.0, 1.5],
            "tackles_won_per90": [0.4, 0.8],
            "interceptions_per90": [0.2, 0.3],
            "blocks_per90": [0.7, 0.6],
        }
    )


def test_player_percentiles_uses_named_columns() -> None:
    pool = _two_player_pool()
    pct = player_percentiles(pool, SUAREZ)
    goals = pct.set_index("column").loc["np_goals_per90", "percentile"]
    pass_pct = pct.set_index("column").loc["pass_completion_pct", "percentile"]
    assert goals == 100.0
    assert pass_pct == 50.0  # 70 < 80 → lower percentile, higher-is-better


def test_export_player_json_shape_order_and_values() -> None:
    pool = _two_player_pool()
    pct = player_percentiles(pool, SUAREZ)
    payload = export_player_json(
        pct,
        player_name=SUAREZ,
        position_group="Forward",
        minutes=3273.2,
        league=LEAGUE,
        season=SEASON,
        min_minutes=MIN_MINUTES,
        peer_group_size=len(pool),
        position="Center Forward",
    )
    assert set(payload) >= {
        "schema_version",
        "generated_at",
        "data_source",
        "player",
        "competition",
        "peer_group",
        "categories",
        "metrics",
    }
    assert payload["schema_version"] == 2
    datetime.fromisoformat(str(payload["generated_at"]))
    player = payload["player"]
    assert isinstance(player, dict)
    assert set(player) >= {"name", "position_group", "minutes"}
    competition = payload["competition"]
    assert isinstance(competition, dict)
    assert set(competition) >= {"league", "season"}
    peer = payload["peer_group"]
    assert isinstance(peer, dict)
    assert set(peer) >= {"position_group", "min_minutes", "description"}

    categories = payload["categories"]
    assert isinstance(categories, list)
    category_labels = {item["label"] for item in categories}
    assert category_labels == {"Attacking", "Possession/Progression", "Defending"}
    assert [item["key"] for item in categories] == [
        "attacking",
        "possession_progression",
        "defending",
    ]

    metrics = payload["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == 12
    expected_ids = [column for column, _label, _category in PIZZA_METRICS]
    assert [row["metric"] for row in metrics] == expected_ids
    for row in metrics:
        assert set(row) >= {
            "metric",
            "category",
            "value_per90",
            "percentile",
            "higher_is_better",
        }
        assert row["higher_is_better"] is True

    by_column = pct.set_index("column")
    for row in metrics:
        computed = by_column.loc[row["metric"]]
        assert row["value_per90"] == pytest.approx(float(computed["value"]))
        assert row["percentile"] == pytest.approx(float(computed["percentile"]))
        assert row["category"] == computed["category"]


def test_write_player_json(tmp_path) -> None:
    pool = _two_player_pool()
    pct = player_percentiles(pool, SUAREZ)
    payload = export_player_json(
        pct,
        player_name=SUAREZ,
        position_group="Forward",
        minutes=3273.2,
        league=LEAGUE,
        season=SEASON,
        min_minutes=MIN_MINUTES,
        peer_group_size=2,
        position="Center Forward",
    )
    path = tmp_path / "player.json"
    written = write_player_json(payload, path)
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 2
    assert loaded["player"]["name"] == SUAREZ
    assert len(loaded["metrics"]) == 12


@pytest.mark.skipif(
    not PLAYER_SEASON_PARQUET.exists(),
    reason="cached player-season parquet is not present",
)
def test_export_suarez_json_matches_computed_table() -> None:
    table = pd.read_parquet(PLAYER_SEASON_PARQUET)
    pool = build_peer_group(table, position_group=PEER_GROUP, min_minutes=MIN_MINUTES)
    pct = player_percentiles(pool, PLAYER_NAME)
    row = pool.loc[pool["player"].eq(PLAYER_NAME)].iloc[0]
    payload = export_player_json(
        pct,
        player_name=PLAYER_NAME,
        position_group=PEER_GROUP,
        minutes=float(row["minutes"]),
        league=LEAGUE,
        season=SEASON,
        min_minutes=MIN_MINUTES,
        peer_group_size=len(pool),
        position=str(row["position"]),
    )
    assert len(payload["metrics"]) == 12
    assert payload["schema_version"] == 2
    datetime.fromisoformat(str(payload["generated_at"]))
    assert {item["label"] for item in payload["categories"]} == {
        "Attacking",
        "Possession/Progression",
        "Defending",
    }
    by_column = pct.set_index("column")
    for metric_row in payload["metrics"]:
        computed = by_column.loc[metric_row["metric"]]
        assert metric_row["percentile"] == pytest.approx(float(computed["percentile"]))
        assert metric_row["value_per90"] == pytest.approx(float(computed["value"]))
        assert metric_row["higher_is_better"] is True
