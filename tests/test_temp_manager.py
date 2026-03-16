"""Tests for temporary file manager."""

from pathlib import Path

from smkaraokemaker.utils.temp_manager import TempManager


class TestTempManager:
    def test_creates_temp_dir(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"fake video content")

        with TempManager(fake_input) as tm:
            assert tm.temp_dir.exists()
            assert tm.temp_dir.is_dir()

    def test_cleanup_on_exit(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"fake video content")

        with TempManager(fake_input) as tm:
            temp_dir = tm.temp_dir
            # Create a file inside
            (temp_dir / "test.txt").write_text("hello")
        # After exiting the context, the directory should be deleted
        assert not temp_dir.exists()

    def test_keep_temp(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"fake video content")

        with TempManager(fake_input, keep_temp=True) as tm:
            temp_dir = tm.temp_dir
        assert temp_dir.exists()
        # Clean up manually
        import shutil
        shutil.rmtree(temp_dir)

    def test_get_path(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"fake video content")

        with TempManager(fake_input) as tm:
            p = tm.get_path("vocals.wav")
            assert p.parent == tm.temp_dir
            assert p.name == "vocals.wav"

    def test_step_caching(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"fake video content")

        with TempManager(fake_input, keep_temp=True) as tm:
            temp_dir = tm.temp_dir
            assert not tm.is_step_done("extract_audio")

            output = tm.get_path("audio.wav")
            output.write_bytes(b"audio data")
            tm.mark_step_done("extract_audio", output)
            assert tm.is_step_done("extract_audio")

        # Reopen — cache should persist
        with TempManager(fake_input, keep_temp=True) as tm2:
            assert tm2.is_step_done("extract_audio")

        import shutil
        shutil.rmtree(temp_dir)

    def test_same_hash_same_dir(self, tmp_path):
        fake_input = tmp_path / "input.mp4"
        fake_input.write_bytes(b"same content")

        tm1 = TempManager(fake_input)
        tm2 = TempManager(fake_input)
        assert tm1.temp_dir == tm2.temp_dir

    def test_different_files_different_hash(self, tmp_path):
        f1 = tmp_path / "a.mp4"
        f1.write_bytes(b"content A")
        f2 = tmp_path / "b.mp4"
        f2.write_bytes(b"content B")

        tm1 = TempManager(f1)
        tm2 = TempManager(f2)
        assert tm1.input_hash != tm2.input_hash
