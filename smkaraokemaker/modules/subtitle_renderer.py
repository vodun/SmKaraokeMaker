"""Karaoke subtitle generation in ASS format."""

from __future__ import annotations

import logging
from pathlib import Path

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.models import Segment, SubtitleStyle
from smkaraokemaker.utils.fonts import get_default_font

logger = logging.getLogger(__name__)

# Position to ASS Alignment mapping
POSITION_ALIGNMENT = {
    "bottom": 2,
    "center": 5,
    "top": 8,
}

COUNTDOWN_THRESHOLD = 5.0  # Pause in seconds after which a countdown is inserted
COUNTDOWN_DURATION = 3  # Number of countdown seconds (3, 2, 1)

# Spacing between the two subtitle lines (px at PlayResY=1080)
LINE_SPACING = 20


def render_subtitles(ctx: PipelineContext) -> PipelineContext:
    """Generate karaoke subtitles from recognized text."""
    if not ctx.transcript:
        logger.warning("No recognized text — subtitles will not be created.")
        ctx.subtitle_path = None
        return ctx

    font_path = ctx.config.font or get_default_font()
    style = SubtitleStyle(
        font_path=font_path,
        font_size=ctx.config.font_size,
        color_active=ctx.config.color_active,
        color_inactive=ctx.config.color_inactive,
        color_done=ctx.config.color_done,
        position=ctx.config.position,
    )

    # Determine resolution for PlayRes in ASS
    parts = ctx.config.resolution.split("x")
    play_res = (int(parts[0]), int(parts[1]))

    ass_path = ctx.temp_dir / "karaoke.ass"
    _generate_ass(ctx.transcript, style, ass_path, play_res=play_res)

    ctx.subtitle_path = ass_path
    logger.info("ASS subtitles: %d lines → %s", len(ctx.transcript), ass_path)
    return ctx


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert #RRGGBB to ASS format &H00BBGGRR (BGR, no alpha)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}"


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS format: H:MM:SS.CC."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _build_karaoke_text(segment: Segment) -> str:
    """Build text with \\kf karaoke tags for a segment."""
    karaoke_parts = []
    for word in segment.words:
        duration_cs = max(1, int(round((word.end - word.start) * 100)))
        karaoke_parts.append(f"{{\\kf{duration_cs}}}{word.text}")
    return " ".join(karaoke_parts)


def _build_done_text(segment: Segment, done_color: str) -> str:
    """Build text for an already sung line (all in done color)."""
    ass_color = _hex_to_ass_color(done_color)
    words = " ".join(w.text for w in segment.words)
    return f"{{\\c{ass_color}}}{words}"


def _generate_ass(
    segments: list[Segment],
    style: SubtitleStyle,
    output: Path,
    play_res: tuple[int, int] = (1920, 1080),
) -> None:
    """Generate ASS file with two-line karaoke display.

    Line alternation logic:
    - Even segments (0, 2, 4...) always on Line1 (upper line)
    - Odd segments (1, 3, 5...) always on Line2 (lower line)
    - When the active segment is being sung, the other line shows
      a preview of the next segment
    - Text never jumps between lines
    """
    alignment = POSITION_ALIGNMENT.get(style.position, 2)
    font_name = style.font_path.stem

    # ASS colors
    active_color = _hex_to_ass_color(style.color_active)
    inactive_color = _hex_to_ass_color(style.color_inactive)
    outline_color = _hex_to_ass_color(style.outline_color)

    # Margins for two lines: upper line higher, lower line lower
    margin_line1 = style.margin_bottom + style.font_size + LINE_SPACING
    margin_line2 = style.margin_bottom

    # Countdown font size — 2x larger
    countdown_font_size = style.font_size * 2

    lines = [
        "[Script Info]",
        "Title: SMKaraokeMaker",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {play_res[0]}",
        f"PlayResY: {play_res[1]}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # Line 1 (upper) — active with karaoke
        f"Style: Line1,{font_name},{style.font_size},{inactive_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},"
        f"{style.shadow_offset[0]},{alignment},40,40,{margin_line1},1",
        # Line 2 (lower) — preview of next line
        f"Style: Line2,{font_name},{style.font_size},{inactive_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},"
        f"{style.shadow_offset[0]},{alignment},40,40,{margin_line2},1",
        # Countdown — centered on screen
        f"Style: Countdown,{font_name},{countdown_font_size},{active_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,4,2,5,40,40,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    prev_end = 0.0

    for i, segment in enumerate(segments):
        next_segment = segments[i + 1] if i + 1 < len(segments) else None

        # Alternation: even segments → Line1, odd → Line2
        if i % 2 == 0:
            active_style = "Line1"
            preview_style = "Line2"
        else:
            active_style = "Line2"
            preview_style = "Line1"

        # Countdown 3-2-1 if pause before segment > 5 sec
        gap = segment.start - prev_end
        if gap >= COUNTDOWN_THRESHOLD:
            countdown_start = segment.start - COUNTDOWN_DURATION
            for n in range(COUNTDOWN_DURATION, 0, -1):
                t_start = _seconds_to_ass_time(countdown_start + (COUNTDOWN_DURATION - n))
                t_end = _seconds_to_ass_time(countdown_start + (COUNTDOWN_DURATION - n) + 1.0)
                fade = r"{\fad(200,200)}"
                lines.append(
                    f"Dialogue: 1,{t_start},{t_end},Countdown,,0,0,0,,{fade}{n}"
                )

        ass_start = _seconds_to_ass_time(segment.start)
        ass_end = _seconds_to_ass_time(segment.end)

        # Active line with karaoke fill
        karaoke_text = _build_karaoke_text(segment)
        lines.append(f"Dialogue: 0,{ass_start},{ass_end},{active_style},,0,0,0,,{karaoke_text}")

        # Preview of the next segment on the other line
        # Don't show preview if there's a long pause before the next segment
        if next_segment:
            next_gap = next_segment.start - segment.end
            if next_gap < COUNTDOWN_THRESHOLD:
                preview_text = " ".join(w.text for w in next_segment.words)
                lines.append(
                    f"Dialogue: 0,{ass_start},{ass_end},{preview_style},,0,0,0,,{preview_text}"
                )

        prev_end = segment.end

    output.write_text("\n".join(lines), encoding="utf-8")
