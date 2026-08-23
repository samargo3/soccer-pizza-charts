"""Player-season aggregates from cached StatsBomb events.

Domain logic lives here: minutes, modal position, counting stats, per-90.
See docs/metrics.md. No percentiles.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
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

# Columns this stage needs. Confirmed against the 114-col La Liga 2015/16 cache.
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


def player_match_minutes(events: pd.DataFrame) -> pd.DataFrame:
    """Minutes played per player per match.

    Starters begin at 0 (anyone who appears in events and is not a
    substitution_replacement). Replacements begin at the Substitution event
    clock. Players named as `player` on a Substitution event end there;
    everyone else ends at the last Half End. Starting XI lineups are not in
    the cache (tactics was dropped), so unused substitutes who never appear
    in events are invisible — they played 0 minutes anyway.

    Red-card early exits are NOT applied: a sent-off player still runs to
    match end. That slightly inflates team minutes. See docs/metrics.md.
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


def validate_team_minutes(match_minutes: pd.DataFrame, n_matches: int = 3) -> pd.DataFrame:
    """Sum of player-minutes per team vs 11 × match length (seconds/60)."""
    sample_ids = (
        match_minutes["match_id"].drop_duplicates().head(n_matches).tolist()
    )
    sample = match_minutes[match_minutes["match_id"].isin(sample_ids)]
    match_length = sample.groupby("match_id")["match_end"].first() / 60.0
    summed = (
        sample.groupby(["match_id", "team"], as_index=False)["minutes"]
        .sum()
        .rename(columns={"minutes": "team_player_minutes"})
    )
    summed["match_length_min"] = summed["match_id"].map(match_length)
    summed["expected_11x"] = 11.0 * summed["match_length_min"]
    summed["ratio"] = summed["team_player_minutes"] / summed["expected_11x"]
    return summed.sort_values(["match_id", "team"])


def modal_position(events: pd.DataFrame) -> pd.DataFrame:
    """Each player's most common non-null position across their events."""
    pos = events.dropna(subset=["player_id", "position"])
    pos = pos[pos["position"] != "Substitute"]
    mode = (
        pos.groupby(["player_id", "position"], as_index=False)
        .size()
        .sort_values(["player_id", "size", "position"], ascending=[True, False, True])
        .drop_duplicates("player_id")
        [["player_id", "position"]]
    )
    return mode


def player_season_totals(events: pd.DataFrame) -> pd.DataFrame:
    """Season counting stats per player. Definitions: docs/metrics.md."""
    is_shot = events["type"].eq("Shot")
    is_penalty = events["shot_type"].eq("Penalty")
    is_pass = events["type"].eq("Pass")
    # Completed pass: StatsBomb leaves pass_outcome null. Incomplete / Out /
    # Pass Offside / Unknown / Injury Clearance are unsuccessful.
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
    totals = (
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
    return totals


def add_per90(table: pd.DataFrame) -> pd.DataFrame:
    """Per-90 rates for counting metrics; pass completion % stays a rate."""
    out = table.copy()
    minutes = out["minutes"]
    for col in COUNT_METRICS:
        out[f"{col}_per90"] = np.where(
            minutes > 0, out[col] * 90.0 / minutes, np.nan
        )
    out["pass_completion_pct"] = np.where(
        out["passes_attempted"] > 0,
        100.0 * out["passes_completed"] / out["passes_attempted"],
        np.nan,
    )
    return out


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


def is_progressive_action(start: pd.Series, end: pd.Series) -> np.ndarray:
    """True where the action cuts distance to (120, 40) by ≥ 10 yards and
    does not start in the defensive third (x < 40). docs/metrics.md.
    """
    x0, y0 = _xy_columns(start)
    x1, y1 = _xy_columns(end)
    d0 = np.hypot(GOAL_X - x0, GOAL_Y - y0)
    d1 = np.hypot(GOAL_X - x1, GOAL_Y - y1)
    valid = np.isfinite(d0) & np.isfinite(d1)
    return valid & (x0 >= DEFENSIVE_THIRD_MAX_X) & (
        (d0 - d1) >= PROGRESSIVE_DISTANCE_YARDS
    )


def player_progression_totals(events: pd.DataFrame) -> pd.DataFrame:
    """Season progressive-pass, progressive-carry, and completed-dribble counts.

    Passes/carries use the project distance-to-goal rule. Dribbles use
    dribble_outcome=Complete. docs/metrics.md.
    """
    is_completed_pass = events["type"].eq("Pass") & events["pass_outcome"].isna()
    is_carry = events["type"].eq("Carry")
    prog_pass = np.zeros(len(events), dtype=bool)
    prog_carry = np.zeros(len(events), dtype=bool)
    if is_completed_pass.any():
        prog_pass[is_completed_pass.to_numpy()] = is_progressive_action(
            events.loc[is_completed_pass, "location"],
            events.loc[is_completed_pass, "pass_end_location"],
        )
    if is_carry.any():
        prog_carry[is_carry.to_numpy()] = is_progressive_action(
            events.loc[is_carry, "location"],
            events.loc[is_carry, "carry_end_location"],
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


def attach_progression_metrics(
    events: pd.DataFrame, player_season: pd.DataFrame
) -> pd.DataFrame:
    """Join progression totals + per-90 onto an existing player-season table.

    Does not recompute stage-1 metrics. Per-90 uses the table's minutes column.
    """
    extra = [c for c in PROGRESSION_METRICS if c in player_season.columns]
    extra += [f"{c}_per90" for c in PROGRESSION_METRICS if f"{c}_per90" in player_season.columns]
    base = player_season.drop(columns=extra) if extra else player_season.copy()

    prog = player_progression_totals(events)
    out = base.merge(prog, on="player_id", how="left")
    for col in PROGRESSION_METRICS:
        out[col] = out[col].fillna(0)
        out[f"{col}_per90"] = np.where(
            out["minutes"] > 0, out[col] * 90.0 / out["minutes"], np.nan
        )
    return out


def build_player_season_table(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (player-season table, minutes-validation sample)."""
    match_minutes = player_match_minutes(events)
    validation = validate_team_minutes(match_minutes)
    season_minutes = (
        match_minutes.groupby("player_id", as_index=False)
        .agg(player=("player", "first"), minutes=("minutes", "sum"))
    )
    totals = player_season_totals(events)
    positions = modal_position(events)
    table = (
        season_minutes.merge(positions, on="player_id", how="left")
        .merge(totals.drop(columns=["player"]), on="player_id", how="left")
    )
    for col in COUNT_METRICS:
        table[col] = table[col].fillna(0)
    table = add_per90(table)
    col_order = (
        ["player", "player_id", "position", "minutes"]
        + COUNT_METRICS
        + ["pass_completion_pct"]
        + [f"{c}_per90" for c in COUNT_METRICS]
    )
    return table[col_order], validation


def load_events(path: Path = EVENTS_PARQUET) -> pd.DataFrame:
    import pyarrow.parquet as pq

    schema_names = pq.read_schema(path).names
    missing = [c for c in REQUIRED_COLUMNS if c not in schema_names]
    if missing:
        raise KeyError(f"Cached events missing columns: {missing}")
    return pd.read_parquet(path)


def confirm_columns(events: pd.DataFrame) -> None:
    """Print the exact flags this stage uses. Run before aggregating."""
    print("=== column confirmation ===")
    for col in REQUIRED_COLUMNS:
        print(f"  {col}: present, dtype={events[col].dtype}")
    print("shot_outcome values:", sorted(events["shot_outcome"].dropna().unique().tolist()))
    print("shot_type values:", sorted(events["shot_type"].dropna().unique().tolist()))
    print("pass_outcome values:", sorted(events["pass_outcome"].dropna().unique().tolist()))
    print("duel_type values:", sorted(events["duel_type"].dropna().unique().tolist()))
    print("duel_outcome values:", sorted(events["duel_outcome"].dropna().unique().tolist()))
    print(
        "interception_outcome values:",
        sorted(events["interception_outcome"].dropna().unique().tolist()),
    )
    print(
        "pass_goal_assist unique:",
        events["pass_goal_assist"].value_counts(dropna=False).to_dict(),
    )
    print(
        "pass_shot_assist unique:",
        events["pass_shot_assist"].value_counts(dropna=False).to_dict(),
    )
    sxi = events[events["type"] == "Starting XI"]
    print(
        "Starting XI rows:",
        len(sxi),
        "player non-null:",
        int(sxi["player"].notna().sum()),
        "(lineups lived in dropped tactics column)",
    )


def main() -> None:
    """Stage 2: attach progression columns onto the existing player-season table."""
    if not PLAYER_SEASON_PARQUET.exists():
        raise FileNotFoundError(
            f"Stage-1 table missing: {PLAYER_SEASON_PARQUET}. Run stage 1 first."
        )
    events = load_events()
    for col in ("location", "pass_end_location", "carry_end_location", "dribble_outcome"):
        if col not in events.columns:
            raise KeyError(f"Cached events missing {col}")
    table = pd.read_parquet(PLAYER_SEASON_PARQUET)
    stage1_cols = [
        c
        for c in table.columns
        if c not in PROGRESSION_METRICS
        and not any(c == f"{m}_per90" for m in PROGRESSION_METRICS)
    ]
    out = attach_progression_metrics(events, table[stage1_cols])
    out.to_parquet(PLAYER_SEASON_PARQUET, engine="pyarrow", index=False)

    suarez = out[out["player"] == "Luis Alberto Suárez Díaz"]
    print("=== Luis Alberto Suárez Díaz (progression) ===")
    cols = (
        ["player", "position", "minutes"]
        + PROGRESSION_METRICS
        + [f"{c}_per90" for c in PROGRESSION_METRICS]
    )
    print(suarez[cols].iloc[0].to_string())

    qualified = out[out["minutes"] >= 900].sort_values(
        "progressive_passes_per90", ascending=False
    )
    print("\n=== top 5 progressive_passes_per90 (min 900 minutes) ===")
    print(
        qualified[
            ["player", "position", "minutes", "progressive_passes", "progressive_passes_per90"]
        ]
        .head(5)
        .to_string(index=False)
    )
    print("\ntable shape:", out.shape)
    print("wrote", PLAYER_SEASON_PARQUET)


if __name__ == "__main__":
    main()
