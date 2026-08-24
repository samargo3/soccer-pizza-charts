"""Percentile ranks within a peer group, plus the pizza chart.

Reads the completed player-season table. Does not re-fetch events or
recompute counting / per-90 metrics. See docs/metrics.md.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from mplsoccer import PyPizza

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/soccer_pizza_charts -> repo root
DATA_DIR = REPO_ROOT / "data"
PLAYER_SEASON_PARQUET = DATA_DIR / "player_season_la_liga_2015_16.parquet"
OUTPUTS_DIR = REPO_ROOT / "outputs"
CHART_PATH = OUTPUTS_DIR / "luis_suarez_la_liga_2015_16.png"

# Matplotlib cache inside the repo so sandboxed runs don't need $HOME.
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

# Minutes floor for the comparison pool. Recorded in docs/metrics.md.
MIN_MINUTES = 900

PLAYER_NAME = "Luis Alberto Suárez Díaz"

# StatsBomb modal position → four pizza peer groups. Wings sit with Forwards
# (they are attacking wide players, not central midfielders).
POSITION_GROUP: dict[str, str] = {
    "Center Forward": "Forward",
    "Left Center Forward": "Forward",
    "Right Center Forward": "Forward",
    "Left Wing": "Forward",
    "Right Wing": "Forward",
    "Center Attacking Midfield": "Midfielder",
    "Left Midfield": "Midfielder",
    "Right Midfield": "Midfielder",
    "Left Center Midfield": "Midfielder",
    "Right Center Midfield": "Midfielder",
    "Center Defensive Midfield": "Midfielder",
    "Left Defensive Midfield": "Midfielder",
    "Right Defensive Midfield": "Midfielder",
    "Left Back": "Defender",
    "Right Back": "Defender",
    "Left Center Back": "Defender",
    "Right Center Back": "Defender",
    "Goalkeeper": "Goalkeeper",
}

PEER_GROUP = "Forward"

# Slice order for the pizza. Per-90 except pass completion % (already a rate).
# All twelve: higher is better — no inversion. docs/metrics.md.
PIZZA_METRICS: list[tuple[str, str, str]] = [
    # (column, chart label, category)
    ("np_goals_per90", "NP goals", "Attacking"),
    ("npxg_per90", "npxG", "Attacking"),
    ("shots_per90", "Shots", "Attacking"),
    ("assists_per90", "Assists", "Attacking"),
    ("key_passes_per90", "Key passes", "Attacking"),
    ("pass_completion_pct", "Pass %", "Possession/Progression"),
    ("progressive_passes_per90", "Prog. passes", "Possession/Progression"),
    ("progressive_carries_per90", "Prog. carries", "Possession/Progression"),
    ("successful_dribbles_per90", "Succ. dribbles", "Possession/Progression"),
    ("tackles_won_per90", "Tackles won", "Defending"),
    ("interceptions_per90", "Interceptions", "Defending"),
    ("blocks_per90", "Blocks", "Defending"),
]

CATEGORY_COLORS = {
    "Attacking": "#C0392B",
    "Possession/Progression": "#1E8449",
    "Defending": "#2471A3",
}


def position_group(position: object) -> str | None:
    """Map a StatsBomb position string to Forward / Midfielder / Defender / GK."""
    if position is None or (isinstance(position, float) and np.isnan(position)):
        return None
    return POSITION_GROUP.get(str(position))


def add_position_group(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    out["position_group"] = out["position"].map(position_group)
    return out


def comparison_pool(
    table: pd.DataFrame,
    group: str = PEER_GROUP,
    min_minutes: int = MIN_MINUTES,
) -> pd.DataFrame:
    """Players in `group` with at least `min_minutes`. docs/metrics.md."""
    tagged = add_position_group(table)
    return tagged.loc[
        tagged["position_group"].eq(group) & tagged["minutes"].ge(min_minutes)
    ].copy()


def percentile_ranks(series: pd.Series) -> pd.Series:
    """Percentile 0–100 within the series. Higher value → higher percentile.

    Average rank on ties. Scaled with pct=True so the maximum is 100.
    """
    return series.rank(method="average", pct=True) * 100.0


def player_percentiles(
    pool: pd.DataFrame,
    player_name: str,
    metrics: list[tuple[str, str, str]] = PIZZA_METRICS,
) -> pd.DataFrame:
    """One row per metric: raw value and percentile inside the pool."""
    rows: list[dict[str, object]] = []
    player = pool.loc[pool["player"].eq(player_name)]
    if player.empty:
        raise KeyError(f"{player_name!r} is not in the comparison pool")
    for column, label, category in metrics:
        ranks = percentile_ranks(pool[column])
        rows.append(
            {
                "metric": label,
                "column": column,
                "category": category,
                "value": float(player[column].iloc[0]),
                "percentile": float(ranks.loc[player.index[0]]),
            }
        )
    return pd.DataFrame(rows)


def render_pizza(
    percentiles: pd.DataFrame,
    player_name: str,
    minutes: float,
    pool_size: int,
    path: Path = CHART_PATH,
) -> Path:
    """Draw mplsoccer PyPizza and save PNG. Values are percentiles 0–100."""
    params = percentiles["metric"].tolist()
    values = [int(round(v)) for v in percentiles["percentile"].tolist()]
    slice_colors = [
        CATEGORY_COLORS[str(c)] for c in percentiles["category"].tolist()
    ]

    baker = PyPizza(
        params=params,
        background_color="#F7F7F5",
        straight_line_color="#B0B0B0",
        straight_line_lw=1,
        last_circle_lw=1,
        last_circle_color="#333333",
        other_circle_lw=1,
        other_circle_color="#D0D0D0",
        inner_circle_size=8,
    )
    fig, ax = baker.make_pizza(
        values,
        figsize=(10, 11),
        color_blank_space="same",
        slice_colors=slice_colors,
        value_colors=["#FFFFFF"] * len(values),
        value_bck_colors=slice_colors,
        blank_alpha=0.35,
        kwargs_slices=dict(edgecolor="#F7F7F5", zorder=2, linewidth=1),
        kwargs_params=dict(color="#222222", fontsize=11),
        kwargs_values=dict(
            color="#FFFFFF",
            fontsize=10,
            zorder=3,
            bbox=dict(edgecolor="#FFFFFF", boxstyle="round,pad=0.2", lw=0),
        ),
    )
    fig.suptitle(
        f"{player_name}\nLa Liga 2015/16  ·  Forward  ·  {minutes:,.0f} minutes",
        fontsize=16,
        fontweight="bold",
        color="#222222",
        y=0.98,
    )
    fig.text(
        0.5,
        0.935,
        f"Percentile rank vs {pool_size} Forwards with ≥ {MIN_MINUTES} minutes  ·  "
        "StatsBomb open data",
        ha="center",
        fontsize=10,
        color="#555555",
    )
    legend = [
        Patch(facecolor=CATEGORY_COLORS["Attacking"], label="Attacking"),
        Patch(
            facecolor=CATEGORY_COLORS["Possession/Progression"],
            label="Possession / Progression",
        ),
        Patch(facecolor=CATEGORY_COLORS["Defending"], label="Defending"),
    ]
    ax.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def main() -> None:
    table = pd.read_parquet(PLAYER_SEASON_PARQUET)
    pool = comparison_pool(table)
    print(f"comparison pool: {PEER_GROUP} with ≥ {MIN_MINUTES} minutes → {len(pool)} players")
    if PLAYER_NAME not in set(pool["player"]):
        raise KeyError(f"{PLAYER_NAME!r} missing from pool")

    pct = player_percentiles(pool, PLAYER_NAME)
    print("\n=== Luis Alberto Suárez Díaz percentiles (within Forward pool) ===")
    print(
        pct[["category", "metric", "value", "percentile"]].to_string(
            index=False,
            formatters={"value": "{:.3f}".format, "percentile": "{:.1f}".format},
        )
    )

    minutes = float(pool.loc[pool["player"].eq(PLAYER_NAME), "minutes"].iloc[0])
    path = render_pizza(pct, PLAYER_NAME, minutes, len(pool))
    print("\nsaved", path)


if __name__ == "__main__":
    main()
