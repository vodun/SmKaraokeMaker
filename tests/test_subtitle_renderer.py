"""Тесты для генерации ASS-субтитров."""

from pathlib import Path

from smkaraokemaker.config import KaraokeConfig, PipelineContext
from smkaraokemaker.models import Word, Segment
from smkaraokemaker.modules.subtitle_renderer import (
    render_subtitles,
    _hex_to_ass_color,
    _seconds_to_ass_time,
)


def _make_segments() -> list[Segment]:
    return [
        Segment(
            text="Я помню чудное мгновенье",
            words=[
                Word(text="Я", start=1.0, end=1.2),
                Word(text="помню", start=1.3, end=1.7),
                Word(text="чудное", start=1.8, end=2.3),
                Word(text="мгновенье", start=2.4, end=3.2),
            ],
            start=1.0,
            end=3.2,
        ),
        Segment(
            text="Передо мной явилась ты",
            words=[
                Word(text="Передо", start=4.0, end=4.5),
                Word(text="мной", start=4.6, end=4.9),
                Word(text="явилась", start=5.0, end=5.6),
                Word(text="ты", start=5.7, end=6.0),
            ],
            start=4.0,
            end=6.0,
        ),
    ]


class TestHexToAssColor:
    def test_gold(self):
        assert _hex_to_ass_color("#FFD700") == "&H0000D7FF"

    def test_white(self):
        assert _hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"

    def test_black(self):
        assert _hex_to_ass_color("#000000") == "&H00000000"

    def test_red(self):
        assert _hex_to_ass_color("#FF0000") == "&H000000FF"


class TestSecondsToAssTime:
    def test_zero(self):
        assert _seconds_to_ass_time(0.0) == "0:00:00.00"

    def test_simple(self):
        assert _seconds_to_ass_time(65.5) == "0:01:05.50"

    def test_hours(self):
        assert _seconds_to_ass_time(3661.25) == "1:01:01.25"


class TestRenderSubtitles:
    def test_generates_ass_file(self, tmp_path):
        segments = _make_segments()
        config = KaraokeConfig(
            input_video=Path("/fake/input.mp4"),
            output_video=Path("/fake/output.mp4"),
        )
        ctx = PipelineContext(
            input_video=config.input_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
            transcript=segments,
        )
        result = render_subtitles(ctx)

        assert result.subtitle_path is not None
        assert result.subtitle_path.exists()

        content = result.subtitle_path.read_text()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "\\kf" in content

    def test_dialogue_count(self, tmp_path):
        segments = _make_segments()
        config = KaraokeConfig(
            input_video=Path("/fake/input.mp4"),
            output_video=Path("/fake/output.mp4"),
        )
        ctx = PipelineContext(
            input_video=config.input_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
            transcript=segments,
        )
        result = render_subtitles(ctx)
        content = result.subtitle_path.read_text()
        dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
        # 2 сегмента: каждый даёт Line1, плюс первый даёт Line2 (preview следующего)
        assert len(dialogue_lines) == 3

    def test_empty_transcript(self, tmp_path):
        config = KaraokeConfig(
            input_video=Path("/fake/input.mp4"),
            output_video=Path("/fake/output.mp4"),
        )
        ctx = PipelineContext(
            input_video=config.input_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
            transcript=[],
        )
        result = render_subtitles(ctx)
        assert result.subtitle_path is None
