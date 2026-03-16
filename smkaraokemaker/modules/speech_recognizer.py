"""Speech recognition with word-level timestamps."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from smkaraokemaker.config import PipelineContext
from smkaraokemaker.models import Word, Segment

logger = logging.getLogger(__name__)

# Word grouping parameters
MAX_WORDS_PER_LINE = 6
MIN_WORDS_PER_LINE = 2
PAUSE_THRESHOLD = 0.5  # seconds — pause threshold for line break
FORCE_BREAK_THRESHOLD = 2.0  # seconds — always break segment on gaps this large
MIN_CONFIDENCE = 0.3


def recognize_speech(ctx: PipelineContext) -> PipelineContext:
    """Recognize words from the vocal track with word-level timestamps."""
    if ctx.vocals_path is None:
        raise RuntimeError("Vocal track not found. Run vocal separation first.")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Install: pip install 'smkaraokemaker[ml]'"
        )

    model_size = ctx.config.model
    lang = ctx.config.lang if ctx.config.lang != "auto" else None

    logger.info("Loading Whisper model: %s", model_size)
    model = WhisperModel(model_size, device="auto", compute_type="auto")

    logger.info("Transcription: %s", ctx.vocals_path)
    segments_iter, info = model.transcribe(
        str(ctx.vocals_path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,
    )

    logger.info("Detected language: %s (probability %.2f)", info.language, info.language_probability)

    # Collect all words
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
        logger.warning("Failed to recognize text. Try --lyrics for manual lyrics.")
        ctx.transcript = []
        return ctx

    # Group words into lines
    segments = _group_words_into_segments(all_words)
    ctx.transcript = segments

    # Save to JSON
    transcript_path = ctx.temp_dir / "transcript.json"
    data = [seg.model_dump() for seg in segments]
    transcript_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("Recognized %d lines, %d words → %s", len(segments), len(all_words), transcript_path)

    return ctx


def _group_words_into_segments(words: list[Word]) -> list[Segment]:
    """Group words into lines by pauses and maximum length."""
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

        force_break = gap >= FORCE_BREAK_THRESHOLD
        if should_break and (len(current_words) >= MIN_WORDS_PER_LINE or force_break):
            segments.append(_make_segment(current_words))
            current_words = [word]
        else:
            current_words.append(word)

    # Last group
    if current_words:
        segments.append(_make_segment(current_words))

    return segments


def _make_segment(words: list[Word]) -> Segment:
    """Create a Segment from a list of words."""
    text = " ".join(w.text for w in words)
    return Segment(
        text=text,
        words=words,
        start=words[0].start,
        end=words[-1].end,
    )
