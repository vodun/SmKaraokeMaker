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
        # 2 сегмента: seg0 → Line1 (active) + Line2 (preview), seg1 → Line2 (active)
        assert len(dialogue_lines) == 3
        # Проверяем чередование стилей
        assert ",Line1," in dialogue_lines[0]  # seg0 active
        assert ",Line2," in dialogue_lines[1]  # seg1 preview
        assert ",Line2," in dialogue_lines[2]  # seg1 active

    def test_alternating_lines(self, tmp_path):
        """Проверка чередования строк: чётные на Line1, нечётные на Line2."""
        segments = [
            Segment(
                text=f"seg{i}",
                words=[Word(text=f"word{i}", start=i * 5.0, end=i * 5.0 + 3.0)],
                start=i * 5.0,
                end=i * 5.0 + 3.0,
            )
            for i in range(4)
        ]
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

        # 4 сегмента: каждый даёт active + preview (кроме последнего — только active)
        # seg0: Line1 active + Line2 preview = 2
        # seg1: Line2 active + Line1 preview = 2
        # seg2: Line1 active + Line2 preview = 2
        # seg3: Line2 active = 1
        assert len(dialogue_lines) == 7

        # Проверяем чередование: active стили
        active_styles = [l.split(",")[3] for l in dialogue_lines if "\\kf" in l]
        assert active_styles == ["Line1", "Line2", "Line1", "Line2"]

        # Проверяем preview стили
        preview_styles = [l.split(",")[3] for l in dialogue_lines if "\\kf" not in l]
        assert preview_styles == ["Line2", "Line1", "Line2"]

    def test_no_preview_across_long_gap(self, tmp_path):
        """Превью не показывается, если до следующего сегмента пауза >= 5 сек."""
        segments = [
            Segment(
                text="Первая строка",
                words=[Word(text="Первая", start=1.0, end=1.5),
                       Word(text="строка", start=1.6, end=2.0)],
                start=1.0, end=2.0,
            ),
            # Пауза 8 секунд
            Segment(
                text="После паузы",
                words=[Word(text="После", start=10.0, end=10.5),
                       Word(text="паузы", start=10.6, end=11.0)],
                start=10.0, end=11.0,
            ),
        ]
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
        dialogue_lines = [l for l in content.splitlines()
                          if l.startswith("Dialogue:") and ",Countdown," not in l]
        # seg0: active Line1, НЕТ превью (пауза 8 сек)
        # seg1: active Line2
        assert len(dialogue_lines) == 2
        assert ",Line1," in dialogue_lines[0]
        assert "\\kf" in dialogue_lines[0]
        assert ",Line2," in dialogue_lines[1]
        assert "\\kf" in dialogue_lines[1]

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
