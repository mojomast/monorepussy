"""Pytest configuration and shared fixtures."""

import os
import json
import tempfile
import pytest
from pathlib import Path

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")
SAMPLE_CODE_DIR = os.path.join(FIXTURES_DIR, "sample_code")


@pytest.fixture
def god_class_path():
    """Path to the god class fixture file."""
    return os.path.join(SAMPLE_CODE_DIR, "god_class_module.py")


@pytest.fixture
def clean_module_path():
    """Path to the clean module fixture file."""
    return os.path.join(SAMPLE_CODE_DIR, "clean_module.py")


@pytest.fixture
def sample_code_dir():
    """Path to the sample code directory."""
    return SAMPLE_CODE_DIR


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file with given content."""
    files = []

    def _create(content: str, filename: str = "temp_module.py") -> str:
        tmpdir = tempfile.mkdtemp()
        fpath = os.path.join(tmpdir, filename)
        with open(fpath, "w") as f:
            f.write(content)
        files.append(fpath)
        return fpath

    yield _create

    # Cleanup
    for f in files:
        try:
            os.remove(f)
        except OSError:
            pass


@pytest.fixture
def temp_project():
    """Create a temporary project directory structure."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Cleanup is handled by OS for temp dirs


@pytest.fixture
def calibration_data():
    """Sample calibration data for testing."""
    return [
        {"delta_K": 5.0, "growth_rate": 0.05},
        {"delta_K": 10.0, "growth_rate": 0.25},
        {"delta_K": 15.0, "growth_rate": 0.80},
        {"delta_K": 20.0, "growth_rate": 1.50},
        {"delta_K": 25.0, "growth_rate": 3.20},
        {"delta_K": 30.0, "growth_rate": 6.00},
        {"delta_K": 35.0, "growth_rate": 12.00},
        {"delta_K": 40.0, "growth_rate": 25.00},
    ]


@pytest.fixture
def calibration_json_file(calibration_data, tmp_path):
    """Create a JSON file with calibration data."""
    fpath = tmp_path / "calibration_data.json"
    with open(fpath, "w") as f:
        json.dump(calibration_data, f)
    return str(fpath)
