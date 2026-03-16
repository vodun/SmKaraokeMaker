"""Тесты для базовых моделей данных."""

from pathlib import Path

from smkaraokemaker.models import Word, Segment, SubtitleStyle


class TestWord:
    def test_create_word(self):
        w = Word(text="привет", start=1.0, end=1.5, confidence=0.95)
        assert w.text == "привет"
        assert w.start == 1.0
        assert w.end == 1.5
        assert w.confidence == 0.95

    def test_default_confidence(self):
        w = Word(text="мир", start=2.0, end=2.3)
        assert w.confidence == 1.0


class TestSegment:
    def test_create_segment(self):
        words = [
            Word(text="Я", start=1.0, end=1.1),
            Word(text="помню", start=1.2, end=1.5),
            Word(text="чудное", start=1.6, end=2.0),
            Word(text="мгновенье", start=2.1, end=2.8),
        ]
        seg = Segment(
            text="Я помню чудное мгновенье",
            words=words,
            start=1.0,
            end=2.8,
        )
        assert len(seg.words) == 4
        assert seg.start == 1.0
        assert seg.end == 2.8

    def test_segment_serialization(self):
        words = [Word(text="test", start=0.0, end=0.5)]
        seg = Segment(text="test", words=words, start=0.0, end=0.5)
        data = seg.model_dump()
        assert data["text"] == "test"
        assert len(data["words"]) == 1
        restored = Segment.model_validate(data)
        assert restored == seg


class TestSubtitleStyle:
    def test_defaults(self):
        style = SubtitleStyle(font_path=Path("/tmp/font.ttf"))
        assert style.font_size == 48
        assert style.color_active == "#FFD700"
        assert style.color_inactive == "#FFFFFF"
        assert style.color_done == "#AAAAAA"
        assert style.position == "bottom"

    def test_custom_colors(self):
        style = SubtitleStyle(
            font_path=Path("/tmp/font.ttf"),
            color_active="#FF0000",
            color_inactive="#00FF00",
            font_size=64,
        )
        assert style.color_active == "#FF0000"
        assert style.font_size == 64
