"""Тесты для валидаторов."""

import pytest
from pathlib import Path

from smkaraokemaker.utils.validators import (
    ValidationError,
    validate_input_file,
    validate_ffmpeg_available,
    validate_disk_space,
)


class TestValidateInputFile:
    def test_nonexistent_file(self, tmp_path):
        with pytest.raises(ValidationError, match="Файл не найден"):
            validate_input_file(tmp_path / "nope.mp4")

    def test_directory_instead_of_file(self, tmp_path):
        with pytest.raises(ValidationError, match="Не является файлом"):
            validate_input_file(tmp_path)

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "audio.mp3"
        f.write_bytes(b"fake")
        with pytest.raises(ValidationError, match="Неподдерживаемый формат"):
            validate_input_file(f)

    def test_valid_mp4(self, tmp_path):
        f = tmp_path / "video.mp4"
        f.write_bytes(b"fake mp4")
        validate_input_file(f)  # не должен бросать исключение

    def test_valid_mkv(self, tmp_path):
        f = tmp_path / "video.mkv"
        f.write_bytes(b"fake mkv")
        validate_input_file(f)

    def test_case_insensitive_extension(self, tmp_path):
        f = tmp_path / "video.MP4"
        f.write_bytes(b"fake")
        validate_input_file(f)


class TestValidateFFmpeg:
    def test_ffmpeg_missing(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        with pytest.raises(ValidationError, match="FFmpeg не найден"):
            validate_ffmpeg_available()


class TestValidateDiskSpace:
    def test_enough_space(self, tmp_path):
        validate_disk_space(tmp_path, required_gb=0.001)

    def test_not_enough_space(self, tmp_path):
        with pytest.raises(ValidationError, match="Недостаточно места"):
            validate_disk_space(tmp_path, required_gb=999999)
