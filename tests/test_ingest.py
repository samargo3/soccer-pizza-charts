"""Unit tests for ingest helpers. No GitHub calls."""

import pandas as pd

from pipeline.ingest import nested_object_columns


def test_nested_object_columns_keeps_coordinate_lists_drops_dicts() -> None:
    df = pd.DataFrame(
        {
            "location": [[10.0, 20.0], [30.0, 40.0]],
            "related_events": [["abc"], ["def"]],
            "shot_freeze_frame": [[{"player": {"id": 1}}], None],
            "tactics": [{"formation": 433, "lineup": []}, None],
            "type": ["Shot", "Pass"],
        }
    )
    assert nested_object_columns(df) == ["shot_freeze_frame", "tactics"]
