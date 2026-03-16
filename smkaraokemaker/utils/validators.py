"""Валидация входных данных."""

from __future__ import annotations

import shutil
from pathlib import Path


SUPPORTED_VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".aiff"}
SUPPORTED_FORMATS = SUPPORTED_VIDEO_FORMATS | SUPPORTED_AUDIO_FORMATS


def is_audio_only_format(path: Path) -> bool:
    """Проверить, является ли файл аудиоформатом (без видео)."""
    return path.suffix.lower() in SUPPORTED_AUDIO_FORMATS


class ValidationError(Exception):
    """Ошибка валидации входных данных."""


def validate_input_file(path: Path) -> None:
    """Проверить, что входной файл существует и имеет поддерживаемый формат."""
    if not path.exists():
        raise ValidationError(f"Файл не найден: {path}")
    if not path.is_file():
        raise ValidationError(f"Не является файлом: {path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        formats = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ValidationError(
            f"Неподдерживаемый формат '{path.suffix}'. "
            f"Поддерживаемые видео: {', '.join(sorted(SUPPORTED_VIDEO_FORMATS))}; "
            f"аудио: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )


def validate_ffmpeg_available() -> None:
    """Проверить, что FFmpeg установлен и доступен в PATH."""
    if shutil.which("ffmpeg") is None:
        raise ValidationError(
            "FFmpeg не найден. Установите: brew install ffmpeg"
        )


def validate_disk_space(path: Path, required_gb: float = 2.0) -> None:
    """Проверить наличие свободного места на диске."""
    target = path if path.is_dir() else path.parent
    if not target.exists():
        target = Path.home()
    stat = shutil.disk_usage(target)
    free_gb = stat.free / (1024 ** 3)
    if free_gb < required_gb:
        raise ValidationError(
            f"Недостаточно места на диске: {free_gb:.1f} ГБ свободно, "
            f"требуется минимум {required_gb:.1f} ГБ"
        )
