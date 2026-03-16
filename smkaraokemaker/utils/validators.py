"""Input data validation."""

from __future__ import annotations

import shutil
from pathlib import Path


SUPPORTED_VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".aiff"}
SUPPORTED_FORMATS = SUPPORTED_VIDEO_FORMATS | SUPPORTED_AUDIO_FORMATS


def is_audio_only_format(path: Path) -> bool:
    """Check if the file is an audio-only format (no video)."""
    return path.suffix.lower() in SUPPORTED_AUDIO_FORMATS


class ValidationError(Exception):
    """Input data validation error."""


def validate_input_file(path: Path) -> None:
    """Check that the input file exists and has a supported format."""
    if not path.exists():
        raise ValidationError(f"File not found: {path}")
    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        formats = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ValidationError(
            f"Unsupported format '{path.suffix}'. "
            f"Supported video: {', '.join(sorted(SUPPORTED_VIDEO_FORMATS))}; "
            f"audio: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )


def validate_ffmpeg_available() -> None:
    """Check that FFmpeg is installed and available in PATH."""
    if shutil.which("ffmpeg") is None:
        raise ValidationError(
            "FFmpeg not found. Install: brew install ffmpeg"
        )


def validate_disk_space(path: Path, required_gb: float = 2.0) -> None:
    """Check for sufficient free disk space."""
    target = path if path.is_dir() else path.parent
    if not target.exists():
        target = Path.home()
    stat = shutil.disk_usage(target)
    free_gb = stat.free / (1024 ** 3)
    if free_gb < required_gb:
        raise ValidationError(
            f"Not enough disk space: {free_gb:.1f} GB free, "
            f"minimum {required_gb:.1f} GB required"
        )
