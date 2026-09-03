"""Cache-aware refresh: skip StatsBomb when the events Parquet already exists."""

from pathlib import Path

import pandas as pd

from soccer_pizza_charts.pipeline import ensure_events


def test_ensure_events_uses_cache_when_parquet_exists(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "events.parquet"
    cache.write_bytes(b"placeholder")
    called = {"ingest": False}

    def fake_load(path: Path = cache) -> pd.DataFrame:
        assert path == cache
        return pd.DataFrame({"player": ["A"]})

    def fake_ingest(**_kwargs: object):
        called["ingest"] = True
        raise AssertionError("must not fetch when cache exists")

    monkeypatch.setattr("soccer_pizza_charts.pipeline.load_events", fake_load)
    monkeypatch.setattr(
        "soccer_pizza_charts.pipeline.ingest_season_events", fake_ingest
    )
    out = ensure_events(parquet_path=cache)
    assert list(out["player"]) == ["A"]
    assert called["ingest"] is False


def test_ensure_events_fetches_when_cache_missing(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "missing.parquet"
    events = pd.DataFrame({"match_id": [1], "player": ["A"]})

    def fake_ingest(*, parquet_path: Path, **_kwargs: object):
        assert parquet_path == cache
        return events, [], ["tactics"]

    monkeypatch.setattr(
        "soccer_pizza_charts.pipeline.ingest_season_events", fake_ingest
    )
    out = ensure_events(parquet_path=cache)
    assert len(out) == 1
    assert out.loc[0, "match_id"] == 1
