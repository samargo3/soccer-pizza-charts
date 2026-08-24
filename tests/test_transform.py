"""Hand-checkable transform tests. No GitHub, no season Parquet required."""

import pandas as pd

from soccer_pizza_charts.transform import (
    TACKLE_WON_OUTCOMES,
    add_per90,
    counting_metrics,
    derive_minutes,
    is_progressive_action,
    progression_metrics,
)


def _event(**kwargs: object) -> dict:
    row = {
        "match_id": 1,
        "type": "Pass",
        "player": None,
        "player_id": None,
        "team": "Home",
        "team_id": 1,
        "position": "Center Forward",
        "period": 1,
        "minute": 0,
        "second": 0,
        "timestamp": "00:00:00.000",
        "shot_outcome": None,
        "shot_type": None,
        "shot_statsbomb_xg": None,
        "pass_outcome": None,
        "pass_goal_assist": None,
        "pass_shot_assist": None,
        "duel_type": None,
        "duel_outcome": None,
        "interception_outcome": None,
        "substitution_replacement": None,
        "substitution_replacement_id": None,
        "location": None,
        "pass_end_location": None,
        "carry_end_location": None,
        "dribble_outcome": None,
    }
    row.update(kwargs)
    return row


def _one_match_with_ht_sub() -> pd.DataFrame:
    """11 Home starters, P11 off at HT, P12 on. Each half is 45:00 → 90 min.

    Paper minutes: P1–P10 = 90, P11 = 45, P12 = 45. Team sum = 11 × 90.
    """
    rows = [
        _event(type="Half End", period=1, timestamp="00:45:00.000", minute=45),
        _event(type="Half End", period=2, timestamp="00:45:00.000", minute=90),
    ]
    for i in range(1, 12):
        rows.append(
            _event(
                type="Pass",
                player=f"P{i}",
                player_id=float(i),
                timestamp="00:01:00.000",
                minute=1,
            )
        )
    rows.append(
        _event(
            type="Substitution",
            player="P11",
            player_id=11.0,
            substitution_replacement="P12",
            substitution_replacement_id=12.0,
            period=2,
            minute=45,
            timestamp="00:00:00.000",
        )
    )
    rows.append(
        _event(
            type="Pass",
            player="P12",
            player_id=12.0,
            period=2,
            minute=46,
            timestamp="00:01:00.000",
        )
    )
    return pd.DataFrame(rows)


def test_derive_minutes_exact_values() -> None:
    minutes = derive_minutes(_one_match_with_ht_sub()).set_index("player_id")["minutes"]
    assert minutes.loc[1.0] == 90.0
    assert minutes.loc[11.0] == 45.0
    assert minutes.loc[12.0] == 45.0


def test_team_minutes_equal_11_times_match_length() -> None:
    minutes = derive_minutes(_one_match_with_ht_sub())
    match_length_min = minutes["match_end"].iloc[0] / 60.0
    assert match_length_min == 90.0
    team_sum = minutes.loc[minutes["team"] == "Home", "minutes"].sum()
    assert abs(team_sum - 11 * match_length_min) < 1e-6


def test_progression_forward_pass_counts_backward_does_not() -> None:
    events = pd.DataFrame(
        [
            _event(
                type="Pass",
                player="A",
                player_id=1.0,
                location=[50.0, 40.0],
                pass_end_location=[70.0, 40.0],
                pass_outcome=None,
            ),
            _event(
                type="Pass",
                player="B",
                player_id=2.0,
                location=[70.0, 40.0],
                pass_end_location=[50.0, 40.0],
                pass_outcome=None,
            ),
        ]
    )
    prog = progression_metrics(events, threshold=10).set_index("player_id")
    assert prog.loc[1.0, "progressive_passes"] == 1
    assert prog.loc[2.0, "progressive_passes"] == 0


def test_np_goals_exclude_penalties_and_pass_completion() -> None:
    rows = [
        _event(
            type="Shot",
            player="A",
            player_id=1.0,
            shot_outcome="Goal",
            shot_type="Open Play",
            shot_statsbomb_xg=0.4,
        ),
        _event(
            type="Shot",
            player="A",
            player_id=1.0,
            shot_outcome="Goal",
            shot_type="Penalty",
            shot_statsbomb_xg=0.76,
        ),
        _event(type="Pass", player="A", player_id=1.0, pass_outcome=None),
        _event(type="Pass", player="A", player_id=1.0, pass_outcome="Incomplete"),
        _event(
            type="Duel",
            player="A",
            player_id=1.0,
            duel_type="Tackle",
            duel_outcome="Won",
        ),
        _event(
            type="Duel",
            player="A",
            player_id=1.0,
            duel_type="Tackle",
            duel_outcome="Lost In Play",
        ),
    ]
    totals = counting_metrics(pd.DataFrame(rows)).set_index("player_id").loc[1.0]
    assert totals["np_goals"] == 1
    assert totals["shots"] == 2
    assert abs(totals["npxg"] - 0.4) < 1e-9
    assert totals["passes_attempted"] == 2
    assert totals["passes_completed"] == 1
    assert totals["tackles_won"] == 1
    assert "Lost In Play" not in TACKLE_WON_OUTCOMES


def test_per90_and_pass_pct_not_per90() -> None:
    table = pd.DataFrame(
        {
            "minutes": [90.0],
            "np_goals": [1],
            "npxg": [0.5],
            "shots": [2],
            "assists": [0],
            "key_passes": [1],
            "passes_attempted": [10],
            "passes_completed": [8],
            "tackles_won": [0],
            "interceptions": [0],
            "blocks": [0],
        }
    )
    out = add_per90(table)
    assert out.loc[0, "np_goals_per90"] == 1.0
    assert out.loc[0, "pass_completion_pct"] == 80.0
    assert "pass_completion_pct_per90" not in out.columns


def test_progressive_distance_rule_defensive_third() -> None:
    starts = pd.Series([[50.0, 40.0], [50.0, 40.0], [20.0, 40.0], [50.0, 40.0]])
    ends = pd.Series([[70.0, 40.0], [55.0, 40.0], [100.0, 40.0], [60.0, 40.0]])
    got = is_progressive_action(starts, ends, threshold=10)
    assert list(got) == [True, False, False, True]
