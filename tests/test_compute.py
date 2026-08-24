"""Hand-checkable percentile and position-group tests."""

import pandas as pd

from soccer_pizza_charts.compute import (
    POSITION_GROUP,
    comparison_pool,
    percentile_ranks,
    player_percentiles,
    position_group,
)


def test_position_group_mapping() -> None:
    assert position_group("Center Forward") == "Forward"
    assert position_group("Right Wing") == "Forward"
    assert position_group("Left Center Midfield") == "Midfielder"
    assert position_group("Left Back") == "Defender"
    assert position_group("Goalkeeper") == "Goalkeeper"
    assert position_group(None) is None
    # Every mapped label is one of the four groups.
    assert set(POSITION_GROUP.values()) <= {
        "Forward",
        "Midfielder",
        "Defender",
        "Goalkeeper",
    }


def test_percentile_ranks_higher_is_better() -> None:
    # Three distinct values: ranks 1/3, 2/3, 3/3 → 33.3, 66.7, 100.
    s = pd.Series([1.0, 2.0, 3.0], index=["low", "mid", "high"])
    ranks = percentile_ranks(s)
    assert abs(ranks["low"] - 100 / 3) < 1e-9
    assert abs(ranks["mid"] - 200 / 3) < 1e-9
    assert abs(ranks["high"] - 100.0) < 1e-9


def test_comparison_pool_minutes_and_group() -> None:
    table = pd.DataFrame(
        {
            "player": ["A", "B", "C"],
            "position": ["Center Forward", "Center Forward", "Left Back"],
            "minutes": [900, 899, 3000],
            "np_goals_per90": [1.0, 2.0, 0.1],
        }
    )
    pool = comparison_pool(table, group="Forward", min_minutes=900)
    assert list(pool["player"]) == ["A"]


def test_player_percentiles_uses_named_columns() -> None:
    pool = pd.DataFrame(
        {
            "player": ["Luis Alberto Suárez Díaz", "Other"],
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
    pct = player_percentiles(pool, "Luis Alberto Suárez Díaz")
    goals = pct.set_index("column").loc["np_goals_per90", "percentile"]
    pass_pct = pct.set_index("column").loc["pass_completion_pct", "percentile"]
    assert goals == 100.0
    assert pass_pct == 50.0  # 70 < 80 → lower percentile, higher-is-better
