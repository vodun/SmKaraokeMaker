"""Font utilities."""

from __future__ import annotations

from pathlib import Path


def get_default_font() -> Path:
    """Return the path to the bundled NotoSans-Bold.ttf font."""
    font_path = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Bold.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Bundled font not found: {font_path}")
    return font_path
