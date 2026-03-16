"""Audio track extraction from media files."""

from __future__ import annotations

import logging

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.utils.ffmpeg_utils import run_ffmpeg, probe_media, FFmpegError

logger = logging.getLogger(__name__)


def extract_audio(ctx: PipelineContext) -> PipelineContext:
    """Extract audio from media file to WAV (PCM 16-bit, 44100 Hz, stereo)."""
    output_path = ctx.temp_dir / "audio_full.wav"

    # Check for audio track presence
    info = probe_media(ctx.input_video)
    if not info["has_audio"]:
        raise FFmpegError(f"File does not contain an audio track: {ctx.input_video}")

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

    # Validation: file created and has non-zero duration
    if not output_path.exists():
        raise FFmpegError("FFmpeg did not create the output audio file")

    out_info = probe_media(output_path)
    if out_info["duration"] <= 0:
        raise FFmpegError("Extracted audio has zero duration")

    logger.info("Audio extracted: %.1f sec, %s", out_info["duration"], output_path)
    ctx.audio_path = output_path
    return ctx
