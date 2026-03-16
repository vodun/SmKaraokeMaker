"""Генерация караоке-субтитров в формате ASS."""

from __future__ import annotations

import logging
from pathlib import Path

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.models import Segment, SubtitleStyle
from smkaraokemaker.utils.fonts import get_default_font

logger = logging.getLogger(__name__)

# Маппинг позиции на ASS Alignment
POSITION_ALIGNMENT = {
    "bottom": 2,
    "center": 5,
    "top": 8,
}


def render_subtitles(ctx: PipelineContext) -> PipelineContext:
    """Сгенерировать караоке-субтитры из распознанного текста."""
    if not ctx.transcript:
        logger.warning("Нет распознанного текста — субтитры не будут созданы.")
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

    ass_path = ctx.temp_dir / "karaoke.ass"
    _generate_ass(ctx.transcript, style, ass_path)

    ctx.subtitle_path = ass_path
    logger.info("ASS-субтитры: %d строк → %s", len(ctx.transcript), ass_path)
    return ctx


def _hex_to_ass_color(hex_color: str) -> str:
    """Конвертировать #RRGGBB в ASS-формат &H00BBGGRR (BGR, без альфы)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}"


def _seconds_to_ass_time(seconds: float) -> str:
    """Конвертировать секунды в формат ASS: H:MM:SS.CC."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _generate_ass(segments: list[Segment], style: SubtitleStyle, output: Path) -> None:
    """Генерация ASS-файла с караоке-тегами \\kf."""
    alignment = POSITION_ALIGNMENT.get(style.position, 2)
    font_name = style.font_path.stem  # Имя шрифта из файла

    # ASS цвета
    active_color = _hex_to_ass_color(style.color_active)
    inactive_color = _hex_to_ass_color(style.color_inactive)
    outline_color = _hex_to_ass_color(style.outline_color)

    lines = [
        "[Script Info]",
        "Title: SMKaraokeMaker",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Karaoke,{font_name},{style.font_size},{inactive_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},"
        f"{style.shadow_offset[0]},{alignment},40,40,{style.margin_bottom},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for segment in segments:
        start = _seconds_to_ass_time(segment.start)
        end = _seconds_to_ass_time(segment.end)

        # Строим текст с караоке-тегами \kf
        karaoke_parts = []
        for word in segment.words:
            # Длительность слова в сотых секунды
            duration_cs = max(1, int(round((word.end - word.start) * 100)))
            karaoke_parts.append(f"{{\\kf{duration_cs}}}{word.text}")

        text = " ".join(karaoke_parts)
        lines.append(f"Dialogue: 0,{start},{end},Karaoke,,0,0,0,,{text}")

    output.write_text("\n".join(lines), encoding="utf-8")
