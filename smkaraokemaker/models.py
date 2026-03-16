"""Базовые модели данных SMKaraokeMaker."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Word(BaseModel):
    """Одно слово с таймингами."""

    text: str
    start: float  # секунды
    end: float  # секунды
    confidence: float = 1.0


class Segment(BaseModel):
    """Строка текста (группа слов) с общим таймингом."""

    text: str
    words: list[Word]
    start: float
    end: float


class SubtitleStyle(BaseModel):
    """Параметры стиля караоке-субтитров."""

    font_path: Path
    font_size: int = 64
    color_active: str = "#FFD700"
    color_inactive: str = "#FFFFFF"
    color_done: str = "#AAAAAA"
    outline_color: str = "#000000"
    outline_width: int = 3
    shadow_offset: tuple[int, int] = (2, 2)
    background_opacity: float = Field(default=0.0, ge=0.0, le=1.0)
    position: str = "bottom"  # top | center | bottom
    margin_bottom: int = 60
    max_width_ratio: float = Field(default=0.85, ge=0.1, le=1.0)
