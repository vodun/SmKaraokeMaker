"""Pipeline configuration and context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from smkaraokemaker.models import Segment


class QualityProfile(str, Enum):
    """Output video quality profiles."""

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
    """All settings from CLI."""

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
    resolution: str = "1280x720"
    verbose: bool = False


@dataclass
class PipelineContext:
    """Context passed between pipeline modules."""

    input_video: Path
    output_video: Path
    temp_dir: Path
    config: KaraokeConfig

    has_video: bool = True  # False when input is an audio file

    # Populated during execution
    audio_path: Path | None = None
    vocals_path: Path | None = None
    instrumental_path: Path | None = None
    transcript: list[Segment] = field(default_factory=list)
    subtitle_path: Path | None = None
