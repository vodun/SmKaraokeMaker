"""Tests for validators."""

import pytest
from pathlib import Path

from smkaraokemaker.utils.validators import (
    ValidationError,
    validate_input_file,
    validate_ffmpeg_available,
    validate_disk_space,
    is_audio_only_format,
)


class TestValidateInputFile:
    def test_nonexistent_file(self, tmp_path):
        with pytest.raises(ValidationError, match="File not found"):
            validate_input_file(tmp_path / "nope.mp4")

    def test_directory_instead_of_file(self, tmp_path):
        with pytest.raises(ValidationError, match="Not a file"):
            validate_input_file(tmp_path)

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_bytes(b"fake")
        with pytest.raises(ValidationError, match="Unsupported format"):
            validate_input_file(f)

    def test_valid_mp4(self, tmp_path):
        f = tmp_path / "video.mp4"
        f.write_bytes(b"fake mp4")
        validate_input_file(f)  # should not raise

    def test_valid_mkv(self, tmp_path):
        f = tmp_path / "video.mkv"
        f.write_bytes(b"fake mkv")
        validate_input_file(f)

    def test_case_insensitive_extension(self, tmp_path):
        f = tmp_path / "video.MP4"
        f.write_bytes(b"fake")
        validate_input_file(f)

    def test_valid_mp3(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.write_bytes(b"fake mp3")
        validate_input_file(f)

    def test_valid_flac(self, tmp_path):
        f = tmp_path / "song.flac"
        f.write_bytes(b"fake flac")
        validate_input_file(f)

    def test_valid_wav(self, tmp_path):
        f = tmp_path / "song.wav"
        f.write_bytes(b"fake wav")
        validate_input_file(f)


class TestIsAudioOnlyFormat:
    def test_mp3_is_audio(self):
        assert is_audio_only_format(Path("song.mp3")) is True

    def test_flac_is_audio(self):
        assert is_audio_only_format(Path("song.flac")) is True

    def test_mp4_is_not_audio(self):
        assert is_audio_only_format(Path("video.mp4")) is False

    def test_mkv_is_not_audio(self):
        assert is_audio_only_format(Path("video.mkv")) is False


class TestValidateFFmpeg:
    def test_ffmpeg_missing(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        with pytest.raises(ValidationError, match="FFmpeg not found"):
            validate_ffmpeg_available()


class TestValidateDiskSpace:
    def test_enough_space(self, tmp_path):
        validate_disk_space(tmp_path, required_gb=0.001)

    def test_not_enough_space(self, tmp_path):
        with pytest.raises(ValidationError, match="Not enough disk space"):
            validate_disk_space(tmp_path, required_gb=999999)
