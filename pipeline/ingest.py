"""Fetch StatsBomb open-data events and cache them to Parquet.

This stage is deliberately dumb: download, concatenate, drop nested columns
that Parquet cannot store, write the cache. No cleaning, per-90 rates, or
percentiles.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
from statsbombpy import sb
from statsbombpy.api_client import NoAuthWarning

# La Liga 2015/16 — first working target (docs/adr/0003-data-source-strategy.md).
COMPETITION_ID = 11
SEASON_ID = 27

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
EVENTS_PARQUET = DATA_DIR / "events_la_liga_2015_16.parquet"
MATCH_CACHE_DIR = DATA_DIR / "raw" / "statsbomb" / "events"
DROPPED_COLUMNS_PATH = DATA_DIR / "raw" / "statsbomb" / "dropped_columns.txt"

PROGRESS_EVERY = 50


def nested_object_columns(df: pd.DataFrame, sample: int = 200) -> list[str]:
    """Return columns whose values are dicts or lists of dicts.

    Coordinate lists (location, pass_end_location, …) are lists of numbers and
    are kept. List-of-dict / dict columns (shot_freeze_frame, tactics, …) do
    not serialize cleanly to Parquet and are not needed for a pizza chart.
    """
    dropped: list[str] = []
    for col in df.columns:
        for value in df[col].dropna().head(sample):
            if isinstance(value, dict):
                dropped.append(col)
                break
            if isinstance(value, list) and value and isinstance(value[0], dict):
                dropped.append(col)
                break
    return dropped


def drop_nested_object_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Drop dict / list-of-dict columns. Returns (frame, dropped names)."""
    dropped = nested_object_columns(df)
    if not dropped:
        return df, []
    return df.drop(columns=dropped), dropped


def write_parquet_or_name_offender(df: pd.DataFrame, path: Path) -> None:
    """Write Parquet; if pyarrow errors, name the offending column and raise."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, engine="pyarrow", index=False)
        return
    except Exception as exc:
        offender = _first_unserializable_column(df)
        if offender is None:
            raise RuntimeError(f"Parquet write failed; could not isolate a column: {exc}") from exc
        raise TypeError(
            f"Column {offender!r} cannot serialize to Parquet: {exc}"
        ) from exc


def _first_unserializable_column(df: pd.DataFrame) -> str | None:
    probe = Path("/tmp/soccer_pizza_charts_col_probe.parquet")
    for col in df.columns:
        try:
            df[[col]].to_parquet(probe, engine="pyarrow", index=False)
        except Exception:
            return col
    return None


def fetch_events_with_retry(match_id: int) -> pd.DataFrame:
    """Call sb.events; retry once on failure, then re-raise."""
    try:
        events = sb.events(match_id=match_id)
    except Exception as exc:
        print(f"  retry match_id={match_id} after {type(exc).__name__}: {exc}")
        events = sb.events(match_id=match_id)
    events = events.copy()
    events["match_id"] = int(match_id)
    return events


def load_matches(competition_id: int = COMPETITION_ID, season_id: int = SEASON_ID) -> pd.DataFrame:
    """Return the season match list (one row per match)."""
    return sb.matches(competition_id=competition_id, season_id=season_id)


def ingest_season_events(
    competition_id: int = COMPETITION_ID,
    season_id: int = SEASON_ID,
    parquet_path: Path = EVENTS_PARQUET,
) -> tuple[pd.DataFrame, list[int], list[str]]:
    """Fetch every match's events, cache to Parquet, return (events, failed_ids, dropped_cols).

    Per-match Parquet files under MATCH_CACHE_DIR let a later run skip GitHub
    fetches that already succeeded.
    """
    warnings.filterwarnings("ignore", category=NoAuthWarning)

    matches = load_matches(competition_id, season_id)
    match_ids = [int(mid) for mid in matches["match_id"].tolist()]
    print(f"matches: {len(match_ids)} (competition_id={competition_id}, season_id={season_id})")

    MATCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    failed: list[int] = []
    dropped_union: set[str] = set()

    for i, match_id in enumerate(match_ids, start=1):
        cache_path = MATCH_CACHE_DIR / f"{match_id}.parquet"
        try:
            if cache_path.exists():
                frame = pd.read_parquet(cache_path)
            else:
                raw = fetch_events_with_retry(match_id)
                frame, dropped = drop_nested_object_columns(raw)
                dropped_union.update(dropped)
                write_parquet_or_name_offender(frame, cache_path)
            frames.append(frame)
        except Exception as exc:
            print(f"  FAILED match_id={match_id}: {type(exc).__name__}: {exc}")
            failed.append(match_id)

        if i % PROGRESS_EVERY == 0 or i == len(match_ids):
            print(
                f"progress {i}/{len(match_ids)} "
                f"(ok={len(frames)} failed={len(failed)})"
            )

    if not frames:
        raise RuntimeError("No match events were fetched; nothing to cache.")

    events = pd.concat(frames, ignore_index=True, sort=False)
    # Re-scan the concatenated frame in case a column only appears later
    # and is dict-typed on some matches.
    events, extra_dropped = drop_nested_object_columns(events)
    dropped_union.update(extra_dropped)
    if dropped_union:
        DROPPED_COLUMNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        DROPPED_COLUMNS_PATH.write_text("\n".join(sorted(dropped_union)) + "\n")
    elif DROPPED_COLUMNS_PATH.exists():
        dropped_union.update(
            line.strip()
            for line in DROPPED_COLUMNS_PATH.read_text().splitlines()
            if line.strip()
        )

    print(f"concatenated events: {len(events):,} rows × {len(events.columns)} columns")
    write_parquet_or_name_offender(events, parquet_path)
    print(f"wrote {parquet_path}")

    verify = pd.read_parquet(parquet_path)
    if len(verify) != len(events):
        raise RuntimeError(
            f"Parquet round-trip row count mismatch: wrote {len(events)}, read {len(verify)}"
        )
    print(f"parquet round-trip ok: {len(verify):,} rows")

    return events, failed, sorted(dropped_union)


def inspect_cached_events(events: pd.DataFrame) -> None:
    """Print schema, Suárez identity, and one shot / one pass example. No aggregation."""
    print("\n=== columns ===")
    for col in events.columns:
        print(f"  {col}")

    print("\n=== type value counts ===")
    print(events["type"].value_counts().to_string())

    suarez = events[events["player"].fillna("").str.contains("Suárez", regex=False)]
    names = sorted(suarez["player"].dropna().unique().tolist())
    print("\n=== Suárez name search ===")
    print("exact player-name strings:", names)
    for name in names:
        n = int((events["player"] == name).sum())
        print(f"  {name!r}: {n:,} events")

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 120)

    shots = events[events["type"] == "Shot"]
    passes = events[events["type"] == "Pass"]
    print("\n=== example SHOT (highlight location, shot_statsbomb_xg) ===")
    shot = shots.iloc[0]
    print(shot.to_string())
    print(f"\n  >> location = {shot['location']!r}")
    print(f"  >> shot_statsbomb_xg = {shot['shot_statsbomb_xg']!r}")

    print("\n=== example PASS (highlight location, pass_end_location) ===")
    pas = passes.iloc[0]
    print(pas.to_string())
    print(f"\n  >> location = {pas['location']!r}")
    print(f"  >> pass_end_location = {pas['pass_end_location']!r}")


def main() -> None:
    print("credentials were not supplied; statsbombpy uses open data only (expected).")
    events, failed, dropped = ingest_season_events()
    print(f"\nsucceeded: {events['match_id'].nunique()} matches")
    print(f"failed match_ids: {failed if failed else '(none)'}")
    print(f"dropped nested columns: {dropped}")
    inspect_cached_events(events)


if __name__ == "__main__":
    main()
