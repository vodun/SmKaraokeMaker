"""Общие фикстуры для тестов."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_video() -> Path:
    """Путь к тестовому видеофайлу."""
    path = FIXTURES_DIR / "sample_short.mp4"
    if not path.exists():
        pytest.skip("Тестовый видеофайл не найден: tests/fixtures/sample_short.mp4")
    return path
