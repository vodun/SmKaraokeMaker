"""FFmpeg wrappers."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """FFmpeg execution error."""


def run_ffmpeg(
    args: list[str],
    verbose: bool = False,
    progress_callback: Any | None = None,
) -> None:
    """Run FFmpeg with the specified arguments.

    Args:
        args: Arguments for ffmpeg (without 'ffmpeg' itself).
        verbose: Print full FFmpeg log.
        progress_callback: Called with (current_seconds, total_seconds) for progress.
    """
    cmd = ["ffmpeg", "-y", *args]
    logger.debug("FFmpeg command: %s", " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stderr_output = []
    assert process.stderr is not None
    for line in iter(process.stderr.readline, b""):
        text = line.decode("utf-8", errors="replace").strip()
        stderr_output.append(text)
        if verbose:
            logger.info("ffmpeg: %s", text)

        if progress_callback and "time=" in text:
            match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", text)
            if match:
                h, m, s, cs = (int(x) for x in match.groups())
                current = h * 3600 + m * 60 + s + cs / 100
                progress_callback(current)

    process.wait()
    if process.returncode != 0:
        error_text = "\n".join(stderr_output[-10:])
        raise FFmpegError(f"FFmpeg exited with code {process.returncode}:\n{error_text}")


def probe_media(path: Path) -> dict:
    """Get media file metadata via ffprobe.

    Returns:
        dict with keys: duration (float), width (int), height (int),
        fps (float), has_audio (bool), has_video (bool).
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"ffprobe could not read file: {path}") from e
    except FileNotFoundError:
        raise FFmpegError("ffprobe not found. Install: brew install ffmpeg")

    data = json.loads(result.stdout)

    info: dict[str, Any] = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "has_audio": False,
        "has_video": False,
    }

    if "format" in data:
        info["duration"] = float(data["format"].get("duration", 0))

    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and not info["has_video"]:
            info["has_video"] = True
            info["width"] = int(stream.get("width", 0))
            info["height"] = int(stream.get("height", 0))
            # Parse fps from r_frame_rate (e.g. "30000/1001")
            r_fps = stream.get("r_frame_rate", "0/1")
            if "/" in r_fps:
                num, den = r_fps.split("/")
                info["fps"] = float(num) / float(den) if float(den) else 0.0
            else:
                info["fps"] = float(r_fps)
        elif stream["codec_type"] == "audio":
            info["has_audio"] = True

    return info
