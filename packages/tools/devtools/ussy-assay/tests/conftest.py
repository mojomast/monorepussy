"""Test configuration and shared fixtures."""

import os
from pathlib import Path
from typing import Generator

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def business_file() -> Path:
    return FIXTURES_DIR / "sample_business.py"


@pytest.fixture
def mixed_file() -> Path:
    return FIXTURES_DIR / "sample_mixed.py"


@pytest.fixture
def slag_file() -> Path:
    return FIXTURES_DIR / "sample_slag.py"


@pytest.fixture
def validation_file() -> Path:
    return FIXTURES_DIR / "sample_validation.py"


@pytest.fixture
def tmp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory with sample files."""
    for name in ("sample_business.py", "sample_mixed.py", "sample_slag.py", "sample_validation.py"):
        src = FIXTURES_DIR / name
        dst = tmp_path / name
        dst.write_text(src.read_text(), encoding="utf-8")
    yield tmp_path
