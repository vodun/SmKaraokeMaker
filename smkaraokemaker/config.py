"""Конфигурация и контекст пайплайна."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from smkaraokemaker.models import Segment


class QualityProfile(str, Enum):
    """Профили качества выходного видео."""

    DRAFT = "draft"
    HIGH = "high"
    ULTRA = "ultra"

    @property
    def preset(self) -> str:
        return {"draft": "ultrafast", "high": "medium", "ultra": "slow"}[self.value]

    @property
    def crf(self) -> int:
        return {"draft": 28, "high": 18, "ultra": 14}[self.value]

    @property
    def audio_bitrate(self) -> str:
        return {"draft": "128k", "high": "192k", "ultra": "320k"}[self.value]


@dataclass
class KaraokeConfig:
    """Все настройки из CLI."""

    input_video: Path
    output_video: Path
    lang: str = "auto"
    model: str = "large-v3"
    font: Path | None = None
    font_size: int = 64
    color_active: str = "#FFD700"
    color_inactive: str = "#FFFFFF"
    color_done: str = "#AAAAAA"
    position: str = "bottom"
    separator: str = "demucs"
    lyrics: Path | None = None
    keep_temp: bool = False
    quality: QualityProfile = QualityProfile.HIGH
    verbose: bool = False


@dataclass
class PipelineContext:
    """Контекст, передаваемый между модулями пайплайна."""

    input_video: Path
    output_video: Path
    temp_dir: Path
    config: KaraokeConfig

    # Заполняется по мере выполнения
    audio_path: Path | None = None
    vocals_path: Path | None = None
    instrumental_path: Path | None = None
    transcript: list[Segment] = field(default_factory=list)
    subtitle_path: Path | None = None
