"""Final karaoke video assembly."""

from __future__ import annotations

import logging

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.utils.ffmpeg_utils import run_ffmpeg, FFmpegError

logger = logging.getLogger(__name__)


def compose_video(ctx: PipelineContext) -> PipelineContext:
    """Assemble final video: original + instrumental + subtitles."""
    if ctx.instrumental_path is None:
        raise RuntimeError("Instrumental not found. Run vocal separation first.")

    quality = ctx.config.quality

    if ctx.has_video:
        # Video input: take video stream from original
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
        # Audio input: generate black background
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
        "Video assembly: quality=%s (preset=%s, crf=%d)",
        quality.value, quality.preset, quality.crf,
    )

    run_ffmpeg(args, verbose=ctx.config.verbose)

    if not ctx.output_video.exists():
        raise FFmpegError("FFmpeg did not create the output video file")

    size_mb = ctx.output_video.stat().st_size / (1024 * 1024)
    logger.info("Output file: %s (%.1f MB)", ctx.output_video, size_mb)

    return ctx
