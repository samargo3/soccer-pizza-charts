"""Percentile ranks within a peer group, pizza chart, and player JSON export.

Reads the completed player-season table. Does not re-fetch events or
recompute counting / per-90 metrics. See docs/metrics.md.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from mplsoccer import PyPizza

from soccer_pizza_charts.theme import category_color, category_entries, category_label, load_theme

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/soccer_pizza_charts -> repo root
DATA_DIR = REPO_ROOT / "data"
PLAYER_SEASON_PARQUET = DATA_DIR / "player_season_la_liga_2015_16.parquet"
OUTPUTS_DIR = REPO_ROOT / "outputs"
CHART_PATH = OUTPUTS_DIR / "luis_suarez_la_liga_2015_16.png"
DARK_CHART_PATH = OUTPUTS_DIR / "luis_suarez_la_liga_2015_16_dark.png"
JSON_DIR = OUTPUTS_DIR / "json"

# Matplotlib cache inside the repo so sandboxed runs don't need $HOME.
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

# Minutes floor for the comparison pool. Recorded in docs/metrics.md.
MIN_MINUTES = 900
SCHEMA_VERSION = 3
LEAGUE = "La Liga"
SEASON = "2015/16"

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
# Third field is the theme category key (config/theme.json). docs/metrics.md.
PIZZA_METRICS: list[tuple[str, str, str]] = [
    # (column, chart label, category_key)
    ("np_goals_per90", "NP goals", "attacking"),
    ("npxg_per90", "npxG", "attacking"),
    ("shots_per90", "Shots", "attacking"),
    ("assists_per90", "Assists", "attacking"),
    ("key_passes_per90", "Key passes", "attacking"),
    ("pass_completion_pct", "Pass %", "possession_progression"),
    ("progressive_passes_per90", "Prog. passes", "possession_progression"),
    ("progressive_carries_per90", "Prog. carries", "possession_progression"),
    ("successful_dribbles_per90", "Succ. dribbles", "possession_progression"),
    ("tackles_won_per90", "Tackles won", "defending"),
    ("interceptions_per90", "Interceptions", "defending"),
    ("blocks_per90", "Blocks", "defending"),
]

DATA_SOURCE_PROVIDER = "StatsBomb open data"
DATA_SOURCE_LIBRARY = "statsbombpy"


def position_group(position: object) -> str | None:
    """Map a StatsBomb position string to Forward / Midfielder / Defender / GK."""
    if position is None or (isinstance(position, float) and np.isnan(position)):
        return None
    return POSITION_GROUP.get(str(position))


def add_position_group(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    out["position_group"] = out["position"].map(position_group)
    return out


def build_peer_group(
    table: pd.DataFrame,
    position_group: str = PEER_GROUP,
    min_minutes: int = MIN_MINUTES,
) -> pd.DataFrame:
    """Players in `position_group` with at least `min_minutes`. docs/metrics.md."""
    tagged = add_position_group(table)
    return tagged.loc[
        tagged["position_group"].eq(position_group) & tagged["minutes"].ge(min_minutes)
    ].copy()


def comparison_pool(
    table: pd.DataFrame,
    group: str = PEER_GROUP,
    min_minutes: int = MIN_MINUTES,
) -> pd.DataFrame:
    """Alias for build_peer_group (Phase 1 name)."""
    return build_peer_group(table, position_group=group, min_minutes=min_minutes)


def percentile_ranks(series: pd.Series) -> pd.Series:
    """Percentile 0–100 within the series. Higher value → higher percentile.

    Average rank on ties. Scaled with pct=True so the maximum is 100.
    """
    return series.rank(method="average", pct=True) * 100.0


def compute_percentiles(
    table: pd.DataFrame,
    metrics: list[tuple[str, str, str]] = PIZZA_METRICS,
) -> pd.DataFrame:
    """Percentile rank (0–100) of each metric, ranked within `table`.

    `table` should already be the peer group (see build_peer_group). Uses
    per-90 columns; pass_completion_pct is already a rate. All 12 metrics
    are higher-is-better. docs/metrics.md.
    """
    out = table.copy()
    for column, _label, _category in metrics:
        out[f"{column}_percentile"] = percentile_ranks(out[column])
    return out


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
    ranked = compute_percentiles(pool, metrics)
    idx = player.index[0]
    for column, label, category_key in metrics:
        rows.append(
            {
                "metric": label,
                "column": column,
                "category": category_label(category_key),
                "category_key": category_key,
                "value": float(player[column].iloc[0]),
                "percentile": float(ranked.loc[idx, f"{column}_percentile"]),
            }
        )
    return pd.DataFrame(rows)


def _slug(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def unique_slugs(names: list[str]) -> list[str]:
    """Lowercased, ASCII-folded, underscore-joined slugs. Collisions get _2, _3, …"""
    used: set[str] = set()
    out: list[str] = []
    for name in names:
        base = _slug(name)
        slug = base
        n = 2
        while slug in used:
            slug = f"{base}_{n}"
            n += 1
        used.add(slug)
        out.append(slug)
    return out


def json_competition_dir(
    league: str = LEAGUE,
    season: str = SEASON,
    schema_version: int = SCHEMA_VERSION,
) -> Path:
    return JSON_DIR / f"v{schema_version}" / f"{_slug(league)}_{_slug(season)}"


def player_json_path(
    player_name: str,
    league: str = LEAGUE,
    season: str = SEASON,
    schema_version: int = SCHEMA_VERSION,
) -> Path:
    """Versioned path: outputs/json/v{n}/{league}_{season}/{player}.json."""
    return (
        JSON_DIR
        / f"v{schema_version}"
        / f"{_slug(league)}_{_slug(season)}"
        / f"{_slug(player_name)}.json"
    )


def export_player_json(
    percentiles: pd.DataFrame,
    *,
    player_name: str,
    position_group: str,
    minutes: float,
    league: str,
    season: str,
    min_minutes: int,
    peer_group_size: int,
    position: str | None = None,
    schema_version: int = SCHEMA_VERSION,
    generated_at: str | None = None,
) -> dict[str, object]:
    """One player's chart as a dict. No file I/O. See docs/schema.md.

    JSON shape (schema_version 3) — one file describes one player's pizza.
    Percentile / value_per90 numbers are unchanged from schema 2. Category
    colors come from config/theme.json. See docs/schema.md.
    """
    slices: list[dict[str, object]] = []
    for row in percentiles.itertuples(index=False):
        slices.append(
            {
                "metric": row.column,
                "label": row.metric,
                "category": row.category,
                "category_key": row.category_key,
                "value_per90": float(row.value),
                "percentile": float(row.percentile),
                # All 12 pizza metrics are higher-is-better today. The UI
                # must read this flag, not assume direction. docs/metrics.md.
                "higher_is_better": True,
            }
        )
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "data_source": {
            "provider": DATA_SOURCE_PROVIDER,
            "library": DATA_SOURCE_LIBRARY,
            "version": pkg_version(DATA_SOURCE_LIBRARY),
        },
        "player": {
            "name": player_name,
            "position": position,
            "position_group": position_group,
            "minutes": float(minutes),
        },
        "competition": {
            "league": league,
            "season": season,
        },
        "peer_group": {
            "position_group": position_group,
            "min_minutes": int(min_minutes),
            "n_players": int(peer_group_size),
            "description": (
                f"{position_group}s with at least {min_minutes} minutes, "
                f"{league} {season}"
            ),
        },
        "categories": category_entries(),
        "metrics": slices,
    }


def write_player_json(payload: dict[str, object], path: Path | None = None) -> Path:
    """Thin writer. Default path is player_json_path from payload metadata."""
    if path is None:
        player = payload["player"]
        competition = payload["competition"]
        assert isinstance(player, dict)
        assert isinstance(competition, dict)
        path = player_json_path(
            str(player["name"]),
            league=str(competition["league"]),
            season=str(competition["season"]),
            schema_version=int(payload["schema_version"]),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def search_manifest(
    players: list[dict[str, object]],
    *,
    league: str,
    season: str,
    schema_version: int = SCHEMA_VERSION,
) -> dict[str, object]:
    """UI search index. Players sorted by name. No percentile math."""
    return {
        "schema_version": schema_version,
        "competition": {"league": league, "season": season},
        "players": sorted(players, key=lambda row: str(row["name"])),
    }


def write_peer_group_json(
    pool: pd.DataFrame,
    *,
    peer_group: str = PEER_GROUP,
    league: str = LEAGUE,
    season: str = SEASON,
    min_minutes: int = MIN_MINUTES,
    schema_version: int = SCHEMA_VERSION,
    out_dir: Path | None = None,
) -> tuple[list[Path], Path]:
    """One v3 JSON per player in `pool`, plus index.json. Same peer group for all.

    Percentiles are ranked within this pool (docs/metrics.md). Existing files for
    the same player keep their generated_at so a re-export of an unchanged row
    stays byte-identical (Suárez).
    """
    dest = out_dir if out_dir is not None else json_competition_dir(
        league, season, schema_version
    )
    dest.mkdir(parents=True, exist_ok=True)

    names = pool["player"].astype(str).tolist()
    slugs = unique_slugs(names)
    batch_generated_at = datetime.now(timezone.utc).isoformat()
    peer_group_size = len(pool)
    written: list[Path] = []
    entries: list[dict[str, object]] = []

    for (_, row), slug in zip(pool.iterrows(), slugs, strict=True):
        player_name = str(row["player"])
        path = dest / f"{slug}.json"
        generated_at = batch_generated_at
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_player = existing.get("player")
            if (
                isinstance(existing_player, dict)
                and existing_player.get("name") == player_name
            ):
                generated_at = str(existing["generated_at"])
        pct = player_percentiles(pool, player_name)
        payload = export_player_json(
            pct,
            player_name=player_name,
            position_group=peer_group,
            minutes=float(row["minutes"]),
            league=league,
            season=season,
            min_minutes=min_minutes,
            peer_group_size=peer_group_size,
            position=str(row["position"]),
            schema_version=schema_version,
            generated_at=generated_at,
        )
        written.append(write_player_json(payload, path))
        entries.append(
            {
                "name": player_name,
                "slug": slug,
                "position": str(row["position"]),
                "minutes": float(row["minutes"]),
            }
        )

    manifest = search_manifest(
        entries, league=league, season=season, schema_version=schema_version
    )
    manifest_path = dest / "index.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return written, manifest_path


def render_pizza(
    percentiles: pd.DataFrame,
    player_name: str,
    minutes: float,
    pool_size: int,
    path: Path = DARK_CHART_PATH,
) -> Path:
    """Draw a dark-theme pizza from config/theme.json. Values are percentiles 0–100."""
    theme = load_theme()
    colors = theme["color"]
    type_tokens = theme["typography"]
    brand = theme["brand"]
    family = str(type_tokens["family"])
    title_size = int(type_tokens["title_size"])
    subtitle_size = int(type_tokens["subtitle_size"])
    slice_label_size = int(type_tokens["slice_label_size"])
    bg = str(colors["background"])
    grid = str(colors["grid"])
    track = str(colors["track"])
    text_primary = str(colors["text_primary"])
    text_secondary = str(colors["text_secondary"])
    text_on_slice = str(colors["text_on_slice"])

    params = percentiles["metric"].tolist()
    values = [int(round(v)) for v in percentiles["percentile"].tolist()]
    slice_colors = [
        category_color(str(key), theme) for key in percentiles["category_key"].tolist()
    ]

    baker = PyPizza(
        params=params,
        background_color=bg,
        straight_line_color=grid,
        straight_line_lw=1,
        last_circle_lw=1,
        last_circle_color=grid,
        other_circle_lw=1,
        other_circle_color=grid,
        inner_circle_size=8,
    )
    fig, ax = baker.make_pizza(
        values,
        figsize=(10, 13),
        color_blank_space=[track] * len(values),
        slice_colors=slice_colors,
        value_colors=[text_on_slice] * len(values),
        value_bck_colors=slice_colors,
        blank_alpha=1.0,
        kwargs_slices=dict(edgecolor=bg, zorder=2, linewidth=1),
        kwargs_params=dict(
            color=text_primary, fontsize=slice_label_size, fontfamily=family
        ),
        kwargs_values=dict(
            color=text_on_slice,
            fontsize=slice_label_size,
            fontfamily=family,
            zorder=3,
            bbox=dict(
                edgecolor=bg,
                boxstyle="round,pad=0.2",
                lw=0,
            ),
        ),
    )
    fig.set_facecolor(bg)
    ax.set_facecolor(bg)
    # Room above the pizza for title + subtitle (they used to overlap) and
    # room below for the legend + attribution.
    fig.subplots_adjust(left=0.06, right=0.94, top=0.78, bottom=0.20)

    fig.text(
        0.5,
        0.97,
        player_name,
        ha="center",
        va="top",
        fontsize=title_size,
        fontweight=str(type_tokens["title_weight"]),
        fontfamily=family,
        color=text_primary,
    )
    fig.text(
        0.5,
        0.915,
        f"{LEAGUE} {SEASON}  ·  {PEER_GROUP}  ·  {minutes:,.0f} minutes",
        ha="center",
        va="top",
        fontsize=subtitle_size,
        fontfamily=family,
        color=text_secondary,
    )
    fig.text(
        0.5,
        0.875,
        f"Percentile rank vs {pool_size} Forwards with ≥ {MIN_MINUTES} minutes",
        ha="center",
        va="top",
        fontsize=subtitle_size,
        fontfamily=family,
        color=text_secondary,
    )

    legend = [
        Patch(facecolor=category_color(key, theme), label=category_label(key, theme))
        for key in theme["categories"]
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.09),
        ncol=3,
        frameon=False,
        fontsize=subtitle_size,
        labelcolor=text_primary,
        prop={"family": family, "size": subtitle_size},
    )
    fig.text(
        0.5,
        0.045,
        str(theme["attribution"]["required_text"]),
        ha="center",
        va="bottom",
        fontsize=9,
        fontfamily=family,
        color=text_secondary,
    )
    if brand.get("show"):
        fig.text(
            0.97,
            0.02,
            str(brand["handle"]),
            ha="right",
            va="bottom",
            fontsize=8,
            fontfamily=family,
            color=text_secondary,
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
    player_paths, manifest_path = write_peer_group_json(pool)
    print(f"\nwrote {len(player_paths)} player JSON files")
    print("wrote", manifest_path)

    path = render_pizza(pct, PLAYER_NAME, minutes, len(pool), path=DARK_CHART_PATH)
    print("\nsaved", path)


if __name__ == "__main__":
    main()
