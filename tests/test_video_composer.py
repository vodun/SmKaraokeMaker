"""Тесты для сборки видео."""

from pathlib import Path

import pytest

from smkaraokemaker.config import KaraokeConfig, PipelineContext, QualityProfile
from smkaraokemaker.modules.video_composer import compose_video
from smkaraokemaker.utils.ffmpeg_utils import probe_media


class TestVideoComposer:
    def test_compose_with_ass(self, sample_video, tmp_path):
        # Сначала извлечём аудио как «инструментал»
        from smkaraokemaker.modules.audio_extractor import extract_audio

        config = KaraokeConfig(
            input_video=sample_video,
            output_video=tmp_path / "karaoke_out.mp4",
            quality=QualityProfile.DRAFT,
        )
        ctx = PipelineContext(
            input_video=sample_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
        )
        ctx = extract_audio(ctx)
        # Используем полное аудио как инструментал (тест без реальной сепарации)
        ctx.instrumental_path = ctx.audio_path

        # Создаём минимальный ASS-файл
        ass_path = tmp_path / "karaoke.ass"
        ass_path.write_text(
            "[Script Info]\nTitle: Test\nScriptType: v4.00+\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
            "0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\\kf100}Test {\\kf100}line\n"
        )
        ctx.subtitle_path = ass_path

        result = compose_video(ctx)
        assert result.output_video.exists()

        info = probe_media(result.output_video)
        assert info["has_video"]
        assert info["has_audio"]
        assert info["duration"] > 0

    def test_compose_audio_only(self, sample_video, tmp_path):
        """Тест сборки видео из аудио-входа (чёрный фон)."""
        from smkaraokemaker.modules.audio_extractor import extract_audio

        config = KaraokeConfig(
            input_video=sample_video,
            output_video=tmp_path / "karaoke_audio.mp4",
            quality=QualityProfile.DRAFT,
            resolution="1280x720",
        )
        ctx = PipelineContext(
            input_video=sample_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
            has_video=False,  # Эмулируем аудио-вход
        )
        ctx = extract_audio(ctx)
        ctx.instrumental_path = ctx.audio_path

        result = compose_video(ctx)
        assert result.output_video.exists()

        info = probe_media(result.output_video)
        assert info["has_video"]
        assert info["has_audio"]
        assert info["width"] == 1280
        assert info["height"] == 720

    def test_missing_instrumental_raises(self, sample_video, tmp_path):
        config = KaraokeConfig(
            input_video=sample_video,
            output_video=tmp_path / "out.mp4",
        )
        ctx = PipelineContext(
            input_video=sample_video,
            output_video=config.output_video,
            temp_dir=tmp_path,
            config=config,
        )
        with pytest.raises(RuntimeError, match="Инструментал не найден"):
            compose_video(ctx)
