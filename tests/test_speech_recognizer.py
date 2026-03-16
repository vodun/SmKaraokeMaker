"""Тесты для группировки слов (без ML-моделей)."""

from smkaraokemaker.models import Word
from smkaraokemaker.modules.speech_recognizer import _group_words_into_segments


def _make_words(timings: list[tuple[float, float]]) -> list[Word]:
    return [
        Word(text=f"word{i}", start=s, end=e)
        for i, (s, e) in enumerate(timings)
    ]


class TestGroupWords:
    def test_single_word(self):
        words = _make_words([(0.0, 0.5)])
        segments = _group_words_into_segments(words)
        assert len(segments) == 1
        assert len(segments[0].words) == 1

    def test_split_by_pause(self):
        # 3 слова, пауза, 3 слова
        words = _make_words([
            (0.0, 0.3), (0.35, 0.6), (0.65, 1.0),
            (2.0, 2.3), (2.35, 2.6), (2.65, 3.0),
        ])
        segments = _group_words_into_segments(words)
        assert len(segments) == 2
        assert len(segments[0].words) == 3
        assert len(segments[1].words) == 3

    def test_split_by_max_words(self):
        # 12 слов подряд без пауз → должно разбиться
        words = _make_words([(i * 0.3, i * 0.3 + 0.25) for i in range(12)])
        segments = _group_words_into_segments(words)
        assert len(segments) >= 2
        for seg in segments:
            assert len(seg.words) <= 8

    def test_segment_timing(self):
        words = _make_words([(1.0, 1.5), (1.6, 2.0), (2.1, 2.5)])
        segments = _group_words_into_segments(words)
        assert segments[0].start == 1.0
        assert segments[0].end == 2.5

    def test_empty_list(self):
        assert _group_words_into_segments([]) == []
