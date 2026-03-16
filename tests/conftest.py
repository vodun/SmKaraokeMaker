"""Common test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_video() -> Path:
    """Path to test video file."""
    path = FIXTURES_DIR / "sample_short.mp4"
    if not path.exists():
        pytest.skip("Test video file not found: tests/fixtures/sample_short.mp4")
    return path
