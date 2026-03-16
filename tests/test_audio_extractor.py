"""Тесты для извлечения аудио."""

from pathlib import Path

import pytest

from smkaraokemaker.config import KaraokeConfig, PipelineContext
from smkaraokemaker.modules.audio_extractor import extract_audio
from smkaraokemaker.utils.ffmpeg_utils import FFmpegError, probe_media


def _make_ctx(input_video: Path, tmp_path: Path) -> PipelineContext:
    config = KaraokeConfig(
        input_video=input_video,
        output_video=tmp_path / "output.mp4",
    )
    return PipelineContext(
        input_video=input_video,
        output_video=config.output_video,
        temp_dir=tmp_path,
        config=config,
    )


class TestAudioExtractor:
    def test_extract_audio(self, sample_video, tmp_path):
        ctx = _make_ctx(sample_video, tmp_path)
        result = extract_audio(ctx)

        assert result.audio_path is not None
        assert result.audio_path.exists()
        assert result.audio_path.suffix == ".wav"

        # Проверяем метаданные
        info = probe_media(result.audio_path)
        assert info["duration"] > 0
        assert info["has_audio"]

    def test_output_is_pcm_wav(self, sample_video, tmp_path):
        ctx = _make_ctx(sample_video, tmp_path)
        result = extract_audio(ctx)

        # Файл должен быть WAV приличного размера (PCM несжатый)
        assert result.audio_path is not None
        size = result.audio_path.stat().st_size
        # 5 сек * 44100 * 2 каналов * 2 байт = ~882000 байт минимум
        assert size > 500_000
