"""Извлечение аудиодорожки из видеофайла."""

from __future__ import annotations

import logging

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.utils.ffmpeg_utils import run_ffmpeg, probe_media, FFmpegError

logger = logging.getLogger(__name__)


def extract_audio(ctx: PipelineContext) -> PipelineContext:
    """Извлечь аудио из видео в WAV (PCM 16-bit, 44100 Hz, stereo)."""
    output_path = ctx.temp_dir / "audio_full.wav"

    # Проверяем наличие аудиодорожки
    info = probe_media(ctx.input_video)
    if not info["has_audio"]:
        raise FFmpegError(f"Видеофайл не содержит аудиодорожки: {ctx.input_video}")

    run_ffmpeg(
        [
            "-i", str(ctx.input_video),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            str(output_path),
        ],
        verbose=ctx.config.verbose,
    )

    # Валидация: файл создан и имеет ненулевую длительность
    if not output_path.exists():
        raise FFmpegError("FFmpeg не создал выходной аудиофайл")

    out_info = probe_media(output_path)
    if out_info["duration"] <= 0:
        raise FFmpegError("Извлечённое аудио имеет нулевую длительность")

    logger.info("Аудио извлечено: %.1f сек, %s", out_info["duration"], output_path)
    ctx.audio_path = output_path
    return ctx
