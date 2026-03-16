"""Работа со шрифтами."""

from __future__ import annotations

from pathlib import Path


def get_default_font() -> Path:
    """Вернуть путь к встроенному шрифту NotoSans-Bold.ttf."""
    font_path = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Bold.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Встроенный шрифт не найден: {font_path}")
    return font_path
