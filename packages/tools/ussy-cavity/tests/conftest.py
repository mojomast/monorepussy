"""Shared test fixtures and configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ussy_cavity.topology import PipelineTopology


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_yaml_path() -> str:
    return str(FIXTURES_DIR / "simple_pipeline.yaml")


@pytest.fixture
def complex_yaml_path() -> str:
    return str(FIXTURES_DIR / "complex_pipeline.yaml")


@pytest.fixture
def simple_json_path() -> str:
    return str(FIXTURES_DIR / "simple_pipeline.json")


@pytest.fixture
def deadlock_timeseries_path() -> str:
    return str(FIXTURES_DIR / "timeseries_deadlock.json")


@pytest.fixture
def empty_timeseries_path() -> str:
    return str(FIXTURES_DIR / "timeseries_empty.json")


@pytest.fixture
def simple_topology(simple_yaml_path) -> PipelineTopology:
    return PipelineTopology.from_file(simple_yaml_path)


@pytest.fixture
def complex_topology(complex_yaml_path) -> PipelineTopology:
    return PipelineTopology.from_file(complex_yaml_path)


@pytest.fixture
def minimal_dict() -> dict[str, Any]:
    """A minimal pipeline dict for quick tests."""
    return {
        "stages": {
            "a": {"rate": 100, "buffer": 50, "depends_on": [], "locks": []},
            "b": {"rate": 50, "buffer": 20, "depends_on": ["a"], "locks": ["lock1"]},
        },
        "locks": {
            "lock1": {"type": "exclusive", "holders": ["b"]},
        },
    }


@pytest.fixture
def cyclic_dict() -> dict[str, Any]:
    """A pipeline dict with a potential circular dependency via locks."""
    return {
        "stages": {
            "worker_a": {"rate": 100, "buffer": 50, "depends_on": [], "locks": ["lock_x"]},
            "worker_b": {"rate": 100, "buffer": 50, "depends_on": [], "locks": ["lock_y"]},
        },
        "locks": {
            "lock_x": {"type": "exclusive", "holders": ["worker_a", "worker_b"]},
            "lock_y": {"type": "exclusive", "holders": ["worker_a", "worker_b"]},
        },
    }


@pytest.fixture
def sine_signal() -> np.ndarray:
    """A pure sine wave at 1 Hz, sampled at 100 Hz for 5 seconds."""
    fs = 100.0
    duration = 5.0
    t = np.arange(int(fs * duration)) / fs
    return np.sin(2.0 * np.pi * 1.0 * t)


@pytest.fixture
def beat_signal() -> np.ndarray:
    """A beat signal: sum of two close frequencies (10 Hz and 10.5 Hz)."""
    fs = 1000.0
    duration = 4.0
    t = np.arange(int(fs * duration)) / fs
    sig = np.sin(2.0 * np.pi * 10.0 * t) + np.sin(2.0 * np.pi * 10.5 * t)
    return sig


@pytest.fixture
def zero_signal() -> np.ndarray:
    """A zero-valued signal."""
    return np.zeros(100)


@pytest.fixture
def deadlock_wait_series() -> np.ndarray:
    """Simulated wait-duration signal showing persistent deadlock."""
    fs = 10.0
    n = 50
    t = np.arange(n) / fs
    # Persistent oscillation (standing wave)
    signal = 4.0 * np.sin(2.0 * np.pi * 1.0 * t) + 0.1 * np.random.randn(n)
    return np.abs(signal)
