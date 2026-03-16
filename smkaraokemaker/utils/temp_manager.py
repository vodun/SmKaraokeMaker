"""Temporary file and cache management."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

HASH_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB for fast hashing


class TempManager:
    """Pipeline temporary file manager."""

    def __init__(self, input_file: Path, keep_temp: bool = False) -> None:
        self.input_file = input_file
        self.keep_temp = keep_temp
        self.input_hash = self._hash_file(input_file)
        self.temp_dir = Path(tempfile.gettempdir()) / f"smkaraokemaker_{self.input_hash[:8]}"
        self._state_file = self.temp_dir / "pipeline_state.json"
        self._state: dict = {}

    def __enter__(self) -> TempManager:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()
        logger.debug("Temp dir: %s (hash: %s)", self.temp_dir, self.input_hash)
        return self

    def __exit__(self, *args: object) -> None:
        if not self.keep_temp and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.debug("Cleaned up temp dir: %s", self.temp_dir)

    def get_path(self, name: str) -> Path:
        """Get path to a file in the temporary directory."""
        return self.temp_dir / name

    def is_step_done(self, step_name: str) -> bool:
        """Check if a step is completed (for caching)."""
        if self._state.get("input_hash") != self.input_hash:
            return False
        step = self._state.get("steps", {}).get(step_name, {})
        if not step.get("done"):
            return False
        output_file = step.get("output")
        if output_file and not Path(output_file).exists():
            return False
        return True

    def mark_step_done(self, step_name: str, output: Path | None = None) -> None:
        """Mark a step as completed."""
        self._state.setdefault("input_hash", self.input_hash)
        self._state.setdefault("steps", {})
        self._state["steps"][step_name] = {
            "done": True,
            "output": str(output) if output else None,
        }
        self._save_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                return json.loads(self._state_file.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_state(self) -> None:
        self._state_file.write_text(json.dumps(self._state, indent=2))

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA256 of the first 64 MB of the file for fast identification."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            data = f.read(HASH_CHUNK_SIZE)
            h.update(data)
        # Add file size for additional uniqueness
        h.update(str(path.stat().st_size).encode())
        return h.hexdigest()
