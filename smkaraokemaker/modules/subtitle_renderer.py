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

COUNTDOWN_THRESHOLD = 5.0  # Пауза в секундах, после которой вставляется обратный отсчёт
COUNTDOWN_DURATION = 3  # Количество секунд обратного отсчёта (3, 2, 1)

# Отступ между двумя строками субтитров (px при PlayResY=1080)
LINE_SPACING = 20


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


def _build_karaoke_text(segment: Segment) -> str:
    """Построить текст с караоке-тегами \\kf для сегмента."""
    karaoke_parts = []
    for word in segment.words:
        duration_cs = max(1, int(round((word.end - word.start) * 100)))
        karaoke_parts.append(f"{{\\kf{duration_cs}}}{word.text}")
    return " ".join(karaoke_parts)


def _build_done_text(segment: Segment, done_color: str) -> str:
    """Построить текст уже спетой строки (весь в цвете done)."""
    ass_color = _hex_to_ass_color(done_color)
    words = " ".join(w.text for w in segment.words)
    return f"{{\\c{ass_color}}}{words}"


def _generate_ass(segments: list[Segment], style: SubtitleStyle, output: Path) -> None:
    """Генерация ASS-файла с двухстрочным караоке-отображением.

    Логика:
    - Строка 1 (верхняя) — текущая активная строка с караоке-заливкой
    - Строка 2 (нижняя) — следующая строка (предпросмотр, белым цветом)
    - Когда строка 1 допета, строка 2 становится строкой 1 (активной),
      а на строку 2 выводится следующий текст
    """
    alignment = POSITION_ALIGNMENT.get(style.position, 2)
    font_name = style.font_path.stem

    # ASS цвета
    active_color = _hex_to_ass_color(style.color_active)
    inactive_color = _hex_to_ass_color(style.color_inactive)
    outline_color = _hex_to_ass_color(style.outline_color)

    # Отступы для двух строк: верхняя строка выше, нижняя ниже
    margin_line1 = style.margin_bottom + style.font_size + LINE_SPACING
    margin_line2 = style.margin_bottom

    # Размер шрифта для обратного отсчёта — в 2 раза крупнее
    countdown_font_size = style.font_size * 2

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
        # Строка 1 (верхняя) — активная с караоке
        f"Style: Line1,{font_name},{style.font_size},{inactive_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},"
        f"{style.shadow_offset[0]},{alignment},40,40,{margin_line1},1",
        # Строка 2 (нижняя) — предпросмотр следующей строки
        f"Style: Line2,{font_name},{style.font_size},{inactive_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{style.outline_width},"
        f"{style.shadow_offset[0]},{alignment},40,40,{margin_line2},1",
        # Обратный отсчёт — по центру экрана
        f"Style: Countdown,{font_name},{countdown_font_size},{active_color},{active_color},"
        f"{outline_color},&H80000000,1,0,0,0,100,100,0,0,1,4,2,5,40,40,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    prev_end = 0.0

    for i, segment in enumerate(segments):
        next_segment = segments[i + 1] if i + 1 < len(segments) else None

        # Обратный отсчёт 3-2-1, если пауза перед сегментом > 5 сек
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

        # Строка 1 — текущая активная строка с караоке-заливкой
        karaoke_text = _build_karaoke_text(segment)
        lines.append(f"Dialogue: 0,{ass_start},{ass_end},Line1,,0,0,0,,{karaoke_text}")

        # Строка 2 — предпросмотр следующей строки (показывается пока поётся текущая)
        if next_segment:
            preview_text = " ".join(w.text for w in next_segment.words)
            lines.append(
                f"Dialogue: 0,{ass_start},{ass_end},Line2,,0,0,0,,{preview_text}"
            )

        prev_end = segment.end

    output.write_text("\n".join(lines), encoding="utf-8")
