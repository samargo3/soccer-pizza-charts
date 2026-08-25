"""Visual identity tokens. Single source of truth: config/theme.json."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_PATH = REPO_ROOT / "config" / "theme.json"


def load_theme(path: Path | None = None) -> dict:
    """Read the theme JSON. No colors are defined in Python."""
    theme_path = path or THEME_PATH
    return json.loads(theme_path.read_text(encoding="utf-8"))


def category_entries(theme: dict | None = None) -> list[dict[str, str]]:
    """Ordered {key, label, color} rows for JSON export and the legend."""
    payload = theme if theme is not None else load_theme()
    return [
        {"key": key, "label": str(meta["label"]), "color": str(meta["color"])}
        for key, meta in payload["categories"].items()
    ]


def category_label(key: str, theme: dict | None = None) -> str:
    payload = theme if theme is not None else load_theme()
    return str(payload["categories"][key]["label"])


def category_color(key: str, theme: dict | None = None) -> str:
    payload = theme if theme is not None else load_theme()
    return str(payload["categories"][key]["color"])
