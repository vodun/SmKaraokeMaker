"""Распознавание речи с пословными таймингами."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.models import Word, Segment

logger = logging.getLogger(__name__)

# Параметры группировки слов в строки
MAX_WORDS_PER_LINE = 8
MIN_WORDS_PER_LINE = 3
PAUSE_THRESHOLD = 0.5  # секунды — пауза для разрыва строки
MIN_CONFIDENCE = 0.3


def recognize_speech(ctx: PipelineContext) -> PipelineContext:
    """Распознать слова из вокальной дорожки с word-level timestamps."""
    if ctx.vocals_path is None:
        raise RuntimeError("Вокальная дорожка не найдена. Сначала выполните сепарацию.")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper не установлен. Установите: pip install 'smkaraokemaker[ml]'"
        )

    model_size = ctx.config.model
    lang = ctx.config.lang if ctx.config.lang != "auto" else None

    logger.info("Загрузка модели Whisper: %s", model_size)
    model = WhisperModel(model_size, device="auto", compute_type="auto")

    logger.info("Транскрипция: %s", ctx.vocals_path)
    segments_iter, info = model.transcribe(
        str(ctx.vocals_path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,
    )

    logger.info("Обнаружен язык: %s (вероятность %.2f)", info.language, info.language_probability)

    # Собираем все слова
    all_words: list[Word] = []
    for seg in segments_iter:
        if seg.words is None:
            continue
        for w in seg.words:
            if w.probability >= MIN_CONFIDENCE:
                all_words.append(
                    Word(
                        text=w.word.strip(),
                        start=round(w.start, 3),
                        end=round(w.end, 3),
                        confidence=round(w.probability, 3),
                    )
                )

    if not all_words:
        logger.warning("Не удалось распознать текст. Попробуйте --lyrics для ручного текста.")
        ctx.transcript = []
        return ctx

    # Группировка слов в строки
    segments = _group_words_into_segments(all_words)
    ctx.transcript = segments

    # Сохраняем в JSON
    transcript_path = ctx.temp_dir / "transcript.json"
    data = [seg.model_dump() for seg in segments]
    transcript_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("Распознано %d строк, %d слов → %s", len(segments), len(all_words), transcript_path)

    return ctx


def _group_words_into_segments(words: list[Word]) -> list[Segment]:
    """Группировка слов в строки по паузам и максимальной длине."""
    if not words:
        return []

    segments: list[Segment] = []
    current_words: list[Word] = [words[0]]

    for prev, word in zip(words, words[1:]):
        gap = word.start - prev.end
        should_break = (
            gap >= PAUSE_THRESHOLD
            or len(current_words) >= MAX_WORDS_PER_LINE
        )

        if should_break and len(current_words) >= MIN_WORDS_PER_LINE:
            segments.append(_make_segment(current_words))
            current_words = [word]
        else:
            current_words.append(word)

    # Последняя группа
    if current_words:
        segments.append(_make_segment(current_words))

    return segments


def _make_segment(words: list[Word]) -> Segment:
    """Создать Segment из списка слов."""
    text = " ".join(w.text for w in words)
    return Segment(
        text=text,
        words=words,
        start=words[0].start,
        end=words[-1].end,
    )
