"""Player-season aggregates from cached StatsBomb events.

Pure transforms take a DataFrame and return a DataFrame. I/O stays at the
edges (load / save). Definitions: docs/metrics.md. No percentiles.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/soccer_pizza_charts -> repo root
DATA_DIR = REPO_ROOT / "data"
EVENTS_PARQUET = DATA_DIR / "events_la_liga_2015_16.parquet"
PLAYER_SEASON_PARQUET = DATA_DIR / "player_season_la_liga_2015_16.parquet"

# Pitch / progression — project definition, not a StatsBomb flag.
# See docs/metrics.md "Progressive actions (project definition)".
GOAL_X = 120.0
GOAL_Y = 40.0
PROGRESSIVE_DISTANCE_YARDS = 10.0
DEFENSIVE_THIRD_MAX_X = 40.0  # start x < 40 is excluded

PROGRESSION_METRICS = [
    "progressive_passes",
    "progressive_carries",
    "successful_dribbles",
]

REQUIRED_COLUMNS = [
    "match_id",
    "type",
    "player",
    "player_id",
    "team",
    "team_id",
    "position",
    "period",
    "minute",
    "second",
    "timestamp",
    "shot_outcome",
    "shot_type",
    "shot_statsbomb_xg",
    "pass_outcome",
    "pass_goal_assist",
    "pass_shot_assist",
    "duel_type",
    "duel_outcome",
    "interception_outcome",
    "substitution_replacement",
    "substitution_replacement_id",
]

# StatsBomb tackle duels: "Won" plus the two Success* outcomes are successful
# tackles; Lost In Play / Lost Out are not. Aerial Lost is a separate duel_type
# with no outcome (not a tackle). See docs/metrics.md.
TACKLE_WON_OUTCOMES = ("Won", "Success In Play", "Success Out")

COUNT_METRICS = [
    "np_goals",
    "npxg",
    "shots",
    "assists",
    "key_passes",
    "passes_attempted",
    "passes_completed",
    "tackles_won",
    "interceptions",
    "blocks",
]


def timestamp_to_seconds(timestamp: str) -> float:
    """Parse StatsBomb period-relative timestamp (HH:MM:SS.mmm) to seconds."""
    hours, minutes, seconds = str(timestamp).split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def add_elapsed_seconds(events: pd.DataFrame) -> pd.DataFrame:
    """Add match-elapsed seconds using period + timestamp, not raw `minute`.

    StatsBomb `minute` jumps backward at kickoff of the second half (45) while
    first-half stoppage can already be 46–50. Half-time substitutions would be
    undercounted if we used `minute` as a single clock. Timestamp is
    period-relative; we add the first-half Half End length for period 2.
    See docs/metrics.md (Minutes).
    """
    out = events.copy()
    out["_ts"] = out["timestamp"].map(timestamp_to_seconds)
    half_end = out[out["type"] == "Half End"]
    first_half = (
        half_end.loc[half_end["period"] == 1]
        .groupby("match_id")["_ts"]
        .max()
        .rename("_first_half")
    )
    second_half = (
        half_end.loc[half_end["period"] == 2]
        .groupby("match_id")["_ts"]
        .max()
        .rename("_second_half")
    )
    lengths = pd.concat([first_half, second_half], axis=1)
    out = out.merge(lengths, left_on="match_id", right_index=True, how="left")
    out["_elapsed"] = np.where(
        out["period"].eq(1),
        out["_ts"],
        out["_first_half"] + out["_ts"],
    )
    out["_match_end"] = out["_first_half"] + out["_second_half"]
    return out


def derive_minutes(events: pd.DataFrame) -> pd.DataFrame:
    """Minutes played per player per match. docs/metrics.md (Minutes).

    Starters begin at 0 (anyone in events who is not a substitution_replacement).
    Replacements begin at the Substitution clock. The `player` on a Substitution
    event ends there; everyone else ends at the last Half End.

    Red-card early exits are not applied — a sent-off player still runs to
    match end.
    """
    timed = add_elapsed_seconds(events)

    appearances = (
        timed.dropna(subset=["player_id"])
        .groupby(["match_id", "player_id"], as_index=False)
        .agg(
            player=("player", "first"),
            team=("team", "first"),
            team_id=("team_id", "first"),
            match_end=("_match_end", "first"),
        )
    )

    subs = timed[timed["type"] == "Substitution"]
    on_times = (
        subs.dropna(subset=["substitution_replacement_id"])
        .groupby(["match_id", "substitution_replacement_id"], as_index=False)
        .agg(on_elapsed=("_elapsed", "min"))
        .rename(columns={"substitution_replacement_id": "player_id"})
    )
    off_times = (
        subs.dropna(subset=["player_id"])
        .groupby(["match_id", "player_id"], as_index=False)
        .agg(off_elapsed=("_elapsed", "min"))
    )

    minutes = appearances.merge(on_times, on=["match_id", "player_id"], how="left")
    minutes = minutes.merge(off_times, on=["match_id", "player_id"], how="left")
    minutes["on_elapsed"] = minutes["on_elapsed"].fillna(0.0)
    minutes["off_elapsed"] = minutes["off_elapsed"].fillna(minutes["match_end"])
    minutes["minutes"] = (
        (minutes["off_elapsed"] - minutes["on_elapsed"]).clip(lower=0.0) / 60.0
    )
    return minutes[
        ["match_id", "player_id", "player", "team", "team_id", "minutes", "match_end"]
    ]


def assign_positions(events: pd.DataFrame) -> pd.DataFrame:
    """Modal non-null position per player. docs/metrics.md (Position)."""
    pos = events.dropna(subset=["player_id", "position"])
    pos = pos[pos["position"] != "Substitute"]
    return (
        pos.groupby(["player_id", "position"], as_index=False)
        .size()
        .sort_values(["player_id", "size", "position"], ascending=[True, False, True])
        .drop_duplicates("player_id")
        [["player_id", "position"]]
    )


def counting_metrics(events: pd.DataFrame) -> pd.DataFrame:
    """Season totals for the stage-1 counting metrics. docs/metrics.md."""
    is_shot = events["type"].eq("Shot")
    is_penalty = events["shot_type"].eq("Penalty")
    is_pass = events["type"].eq("Pass")
    # Completed pass: StatsBomb leaves pass_outcome null.
    pass_completed = is_pass & events["pass_outcome"].isna()

    flags = pd.DataFrame(
        {
            "player_id": events["player_id"],
            "player": events["player"],
            "np_goals": is_shot
            & events["shot_outcome"].eq("Goal")
            & ~is_penalty,
            "npxg": np.where(is_shot & ~is_penalty, events["shot_statsbomb_xg"], 0.0),
            "shots": is_shot,
            "assists": events["pass_goal_assist"].eq(True),
            "key_passes": events["pass_shot_assist"].eq(True),
            "passes_attempted": is_pass,
            "passes_completed": pass_completed,
            "tackles_won": events["type"].eq("Duel")
            & events["duel_type"].eq("Tackle")
            & events["duel_outcome"].isin(TACKLE_WON_OUTCOMES),
            "interceptions": events["type"].eq("Interception"),
            "blocks": events["type"].eq("Block"),
        }
    )
    return (
        flags.dropna(subset=["player_id"])
        .groupby("player_id", as_index=False)
        .agg(
            player=("player", "first"),
            np_goals=("np_goals", "sum"),
            npxg=("npxg", "sum"),
            shots=("shots", "sum"),
            assists=("assists", "sum"),
            key_passes=("key_passes", "sum"),
            passes_attempted=("passes_attempted", "sum"),
            passes_completed=("passes_completed", "sum"),
            tackles_won=("tackles_won", "sum"),
            interceptions=("interceptions", "sum"),
            blocks=("blocks", "sum"),
        )
    )


def _xy_columns(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Unpack [x, y] lists/arrays (possibly length-3) to float columns."""
    values = series.to_numpy()
    x = np.empty(len(values), dtype=float)
    y = np.empty(len(values), dtype=float)
    for i, point in enumerate(values):
        try:
            x[i] = float(point[0])
            y[i] = float(point[1])
        except (TypeError, ValueError, IndexError):
            x[i] = np.nan
            y[i] = np.nan
    return x, y


def is_progressive_action(
    start: pd.Series,
    end: pd.Series,
    threshold: float = PROGRESSIVE_DISTANCE_YARDS,
) -> np.ndarray:
    """True if distance to (120, 40) falls by ≥ threshold yards and start x ≥ 40.

    Project rule, not a StatsBomb flag. docs/metrics.md.
    """
    x0, y0 = _xy_columns(start)
    x1, y1 = _xy_columns(end)
    d0 = np.hypot(GOAL_X - x0, GOAL_Y - y0)
    d1 = np.hypot(GOAL_X - x1, GOAL_Y - y1)
    valid = np.isfinite(d0) & np.isfinite(d1)
    return valid & (x0 >= DEFENSIVE_THIRD_MAX_X) & ((d0 - d1) >= threshold)


def progression_metrics(
    events: pd.DataFrame, threshold: float = PROGRESSIVE_DISTANCE_YARDS
) -> pd.DataFrame:
    """Season progressive-pass, progressive-carry, and completed-dribble counts.

    Passes/carries use the project distance-to-goal rule with `threshold`
    (default 10 yards); defensive-third starts (x < 40) are excluded.
    Dribbles use dribble_outcome=Complete. docs/metrics.md.
    """
    is_completed_pass = events["type"].eq("Pass") & events["pass_outcome"].isna()
    is_carry = events["type"].eq("Carry")
    prog_pass = np.zeros(len(events), dtype=bool)
    prog_carry = np.zeros(len(events), dtype=bool)
    if is_completed_pass.any():
        prog_pass[is_completed_pass.to_numpy()] = is_progressive_action(
            events.loc[is_completed_pass, "location"],
            events.loc[is_completed_pass, "pass_end_location"],
            threshold=threshold,
        )
    if is_carry.any():
        prog_carry[is_carry.to_numpy()] = is_progressive_action(
            events.loc[is_carry, "location"],
            events.loc[is_carry, "carry_end_location"],
            threshold=threshold,
        )
    flags = pd.DataFrame(
        {
            "player_id": events["player_id"],
            "progressive_passes": prog_pass,
            "progressive_carries": prog_carry,
            "successful_dribbles": events["type"].eq("Dribble")
            & events["dribble_outcome"].eq("Complete"),
        }
    )
    return (
        flags.dropna(subset=["player_id"])
        .groupby("player_id", as_index=False)
        .sum(numeric_only=True)
    )


def add_per90(table: pd.DataFrame) -> pd.DataFrame:
    """Per-90 rates for counting and progression metrics; pass % stays a rate."""
    out = table.copy()
    minutes = out["minutes"]
    rate_cols = [c for c in COUNT_METRICS + PROGRESSION_METRICS if c in out.columns]
    for col in rate_cols:
        out[f"{col}_per90"] = np.where(
            minutes > 0, out[col] * 90.0 / minutes, np.nan
        )
    if "passes_attempted" in out.columns and "passes_completed" in out.columns:
        out["pass_completion_pct"] = np.where(
            out["passes_attempted"] > 0,
            100.0 * out["passes_completed"] / out["passes_attempted"],
            np.nan,
        )
    return out


def build_player_season(events: pd.DataFrame) -> pd.DataFrame:
    """Orchestrate minutes, position, counting, and progression; add per-90.

    Pure function: no file I/O. docs/metrics.md.
    """
    match_minutes = derive_minutes(events)
    season_minutes = (
        match_minutes.groupby("player_id", as_index=False)
        .agg(player=("player", "first"), minutes=("minutes", "sum"))
    )
    table = (
        season_minutes.merge(assign_positions(events), on="player_id", how="left")
        .merge(counting_metrics(events).drop(columns=["player"]), on="player_id", how="left")
        .merge(progression_metrics(events), on="player_id", how="left")
    )
    for col in COUNT_METRICS + PROGRESSION_METRICS:
        table[col] = table[col].fillna(0)
    table = add_per90(table)
    col_order = (
        ["player", "player_id", "position", "minutes"]
        + COUNT_METRICS
        + ["pass_completion_pct"]
        + [f"{c}_per90" for c in COUNT_METRICS]
        + PROGRESSION_METRICS
        + [f"{c}_per90" for c in PROGRESSION_METRICS]
    )
    return table[col_order]


def load_events(path: Path = EVENTS_PARQUET) -> pd.DataFrame:
    """I/O edge: read the cached events Parquet."""
    import pyarrow.parquet as pq

    schema_names = pq.read_schema(path).names
    missing = [c for c in REQUIRED_COLUMNS if c not in schema_names]
    if missing:
        raise KeyError(f"Cached events missing columns: {missing}")
    return pd.read_parquet(path)


def main() -> None:
    """Rebuild the player-season Parquet from the cached events file."""
    events = load_events()
    table = build_player_season(events)
    PLAYER_SEASON_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(PLAYER_SEASON_PARQUET, engine="pyarrow", index=False)
    print("table shape:", table.shape)
    print("wrote", PLAYER_SEASON_PARQUET)


if __name__ == "__main__":
    main()
