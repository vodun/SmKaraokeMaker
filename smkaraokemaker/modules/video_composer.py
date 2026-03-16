"""Финальная сборка караоке-видео."""

from __future__ import annotations

import logging

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.utils.ffmpeg_utils import run_ffmpeg, FFmpegError

logger = logging.getLogger(__name__)


def compose_video(ctx: PipelineContext) -> PipelineContext:
    """Собрать финальное видео: оригинал + инструментал + субтитры."""
    if ctx.instrumental_path is None:
        raise RuntimeError("Инструментал не найден. Сначала выполните сепарацию.")

    quality = ctx.config.quality

    if ctx.has_video:
        # Видео на входе: берём видеопоток из оригинала
        args = [
            "-i", str(ctx.input_video),
            "-i", str(ctx.instrumental_path),
        ]

        if ctx.subtitle_path and ctx.subtitle_path.exists():
            args.extend(["-vf", f"ass=filename={ctx.subtitle_path}"])

        args.extend([
            "-map", "0:v",
            "-map", "1:a",
        ])
    else:
        # Аудио на входе: генерируем чёрный фон
        resolution = ctx.config.resolution
        args = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={resolution}:r=30",
            "-i", str(ctx.instrumental_path),
        ]

        if ctx.subtitle_path and ctx.subtitle_path.exists():
            args.extend(["-vf", f"ass=filename={ctx.subtitle_path}"])

        args.extend([
            "-map", "0:v",
            "-map", "1:a",
            "-shortest",
        ])

    args.extend([
        "-c:v", "libx264",
        "-preset", quality.preset,
        "-crf", str(quality.crf),
        "-c:a", "aac",
        "-b:a", quality.audio_bitrate,
        "-movflags", "+faststart",
        str(ctx.output_video),
    ])

    logger.info(
        "Сборка видео: quality=%s (preset=%s, crf=%d)",
        quality.value, quality.preset, quality.crf,
    )

    run_ffmpeg(args, verbose=ctx.config.verbose)

    if not ctx.output_video.exists():
        raise FFmpegError("FFmpeg не создал выходной видеофайл")

    size_mb = ctx.output_video.stat().st_size / (1024 * 1024)
    logger.info("Выходной файл: %s (%.1f МБ)", ctx.output_video, size_mb)

    return ctx
