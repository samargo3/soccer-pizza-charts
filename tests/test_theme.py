"""Theme loader: tokens come from config/theme.json, not from Python."""

from soccer_pizza_charts.theme import (
    THEME_PATH,
    category_color,
    category_entries,
    category_label,
    load_theme,
)


def test_theme_file_exists() -> None:
    assert THEME_PATH.is_file()


def test_load_theme_has_required_tokens() -> None:
    theme = load_theme()
    color = theme["color"]
    for key in (
        "background",
        "surface",
        "grid",
        "track",
        "text_primary",
        "text_secondary",
        "text_on_slice",
    ):
        assert color[key].startswith("#")
    assert list(theme["categories"]) == [
        "attacking",
        "possession_progression",
        "defending",
    ]
    assert theme["attribution"]["required_text"]
    assert "handle" in theme["brand"]


def test_category_entries_match_theme_file() -> None:
    theme = load_theme()
    entries = category_entries(theme)
    assert [row["key"] for row in entries] == [
        "attacking",
        "possession_progression",
        "defending",
    ]
    assert entries[0]["color"] == theme["categories"]["attacking"]["color"]
    assert category_label("defending", theme) == theme["categories"]["defending"]["label"]
    assert category_color("attacking", theme) == theme["categories"]["attacking"]["color"]
