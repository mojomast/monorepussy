"""Tests for ussyverse adapter integrations."""

import json
import os
from typing import Dict

import pytest

from terrarium.adapters.base import BaseAdapter
from terrarium.adapters.fatigue import FatigueAdapter
from terrarium.adapters.endemic import EndemicAdapter
from terrarium.adapters.sentinel import SentinelAdapter
from terrarium.adapters import load_adapters, merge_health_states
from terrarium.ecosystem.model import OrganismHealthState


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestFatigueAdapter:
    """Unit tests for the fatigueussy adapter."""

    def test_load_maps_stress_intensity_to_crack_intensity(self):
        path = os.path.join(FIXTURES_DIR, "fatigue.json")
        adapter = FatigueAdapter(data_path=path)
        states = adapter.load()

        assert len(states) == 3
        assert "src/auth.py" in states
        assert "src/utils.py" in states
        assert "src/main.py" in states

    def test_crack_intensity_normalized(self):
        path = os.path.join(FIXTURES_DIR, "fatigue.json")
        adapter = FatigueAdapter(data_path=path)
        states = adapter.load()

        # auth.py has highest K (150), so crack_intensity should be highest
        auth_state = states["src/auth.py"]
        assert auth_state.crack_intensity > 0.9
        assert auth_state.crack_intensity <= 1.0

        # utils.py has K=20, moderate intensity
        utils_state = states["src/utils.py"]
        assert 0.1 < utils_state.crack_intensity < 0.2

        # main.py has K=5, low intensity
        main_state = states["src/main.py"]
        assert main_state.crack_intensity < 0.1

    def test_delta_k_boosts_crack_intensity(self):
        path = os.path.join(FIXTURES_DIR, "fatigue.json")
        adapter = FatigueAdapter(data_path=path)
        states = adapter.load()

        # auth.py has delta_K=10, main.py has delta_K=2
        auth_state = states["src/auth.py"]
        main_state = states["src/main.py"]

        # Both should get a growth boost, auth.py more so
        assert auth_state.crack_intensity > 0.9
        assert main_state.crack_intensity > 0.03

    def test_vitality_inverse_to_crack(self):
        path = os.path.join(FIXTURES_DIR, "fatigue.json")
        adapter = FatigueAdapter(data_path=path)
        states = adapter.load()

        assert states["src/auth.py"].vitality < states["src/utils.py"].vitality
        assert states["src/utils.py"].vitality < 1.0

    def test_empty_data_returns_empty(self):
        adapter = FatigueAdapter(data_path=None)
        assert adapter.load() == {}

    def test_missing_stress_intensities_returns_empty(self):
        path = os.path.join(FIXTURES_DIR, "fatigue.json")
        # Write temp file without stress_intensities
        with open(path, "r") as f:
            data = json.load(f)
        data.pop("stress_intensities")
        tmp_path = os.path.join(FIXTURES_DIR, "_tmp_fatigue_empty.json")
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        try:
            adapter = FatigueAdapter(data_path=tmp_path)
            assert adapter.load() == {}
        finally:
            os.remove(tmp_path)


class TestEndemicAdapter:
    """Unit tests for the endemicussy adapter."""

    def test_load_modules_list_format(self):
        path = os.path.join(FIXTURES_DIR, "endemic.json")
        adapter = EndemicAdapter(data_path=path)
        states = adapter.load()

        assert len(states) == 3
        assert states["src/auth.py"].infection_state == "I"
        assert states["src/utils.py"].infection_state == "S"
        assert states["src/main.py"].infection_state == "R"

    def test_load_flat_mapping_format(self):
        flat_data = {
            "src/a.py": {"compartment": "E"},
            "src/b.py": {"compartment": "I"},
        }
        tmp_path = os.path.join(FIXTURES_DIR, "_tmp_endemic_flat.json")
        with open(tmp_path, "w") as f:
            json.dump(flat_data, f)
        try:
            adapter = EndemicAdapter(data_path=tmp_path)
            states = adapter.load()
            assert states["src/a.py"].infection_state == "E"
            assert states["src/b.py"].infection_state == "I"
        finally:
            os.remove(tmp_path)

    def test_vitality_by_state(self):
        path = os.path.join(FIXTURES_DIR, "endemic.json")
        adapter = EndemicAdapter(data_path=path)
        states = adapter.load()

        assert states["src/auth.py"].vitality == 0.3  # I
        assert states["src/utils.py"].vitality == 1.0  # S
        assert states["src/main.py"].vitality == 0.8  # R

    def test_invalid_state_defaults_to_s(self):
        data = {"modules": [{"path": "src/x.py", "compartment": "X"}]}
        tmp_path = os.path.join(FIXTURES_DIR, "_tmp_endemic_bad.json")
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        try:
            adapter = EndemicAdapter(data_path=tmp_path)
            states = adapter.load()
            assert states["src/x.py"].infection_state == "S"
        finally:
            os.remove(tmp_path)

    def test_empty_data_returns_empty(self):
        adapter = EndemicAdapter(data_path=None)
        assert adapter.load() == {}


class TestSentinelAdapter:
    """Unit tests for the sentinelussy adapter."""

    def test_load_files_format(self):
        path = os.path.join(FIXTURES_DIR, "sentinel.json")
        adapter = SentinelAdapter(data_path=path)
        states = adapter.load()

        assert len(states) == 3
        assert states["src/auth.py"].anomaly_active is True
        assert states["src/utils.py"].anomaly_active is False
        # main.py has only detectors with fp_rate > 0.5, so it is suppressed
        assert states["src/main.py"].anomaly_active is False

    def test_suppress_high_false_positive_rate(self):
        path = os.path.join(FIXTURES_DIR, "sentinel.json")
        adapter = SentinelAdapter(data_path=path)
        states = adapter.load()

        # main.py has only detectors with fp_rate > 0.5, so should be suppressed
        assert states["src/main.py"].anomaly_active is False
        assert states["src/main.py"].vitality > 0.9

    def test_vitality_inverse_to_anomaly_score(self):
        path = os.path.join(FIXTURES_DIR, "sentinel.json")
        adapter = SentinelAdapter(data_path=path)
        states = adapter.load()

        assert states["src/auth.py"].vitality == 1.0 - 0.73
        assert states["src/utils.py"].vitality == 1.0 - 0.15

    def test_load_detections_list_format(self):
        data = {
            "detections": [
                {
                    "source_file": "src/a.py",
                    "strength": 0.6,
                    "false_positive_rate": 0.1,
                },
                {
                    "source_file": "src/a.py",
                    "strength": 0.3,
                    "false_positive_rate": 0.1,
                },
            ]
        }
        tmp_path = os.path.join(FIXTURES_DIR, "_tmp_sentinel_det.json")
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        try:
            adapter = SentinelAdapter(data_path=tmp_path)
            states = adapter.load()
            assert states["src/a.py"].anomaly_active is True
            assert states["src/a.py"].vitality == 1.0 - 0.6
        finally:
            os.remove(tmp_path)

    def test_empty_data_returns_empty(self):
        adapter = SentinelAdapter(data_path=None)
        assert adapter.load() == {}


class TestAdapterIntegration:
    """Integration tests loading all three adapters simultaneously."""

    def test_merge_health_states_all_three(self):
        fatigue_path = os.path.join(FIXTURES_DIR, "fatigue.json")
        endemic_path = os.path.join(FIXTURES_DIR, "endemic.json")
        sentinel_path = os.path.join(FIXTURES_DIR, "sentinel.json")

        adapters = load_adapters(
            fatigue_data=fatigue_path,
            endemic_data=endemic_path,
            sentinel_data=sentinel_path,
        )

        assert len(adapters) == 3
        merged = merge_health_states(adapters)

        # All three files should be present
        assert "src/auth.py" in merged
        assert "src/utils.py" in merged
        assert "src/main.py" in merged

        # auth.py: high crack + infected + anomaly
        auth = merged["src/auth.py"]
        assert auth.crack_intensity > 0.9
        assert auth.infection_state == "I"
        assert auth.anomaly_active is True
        assert auth.vitality < 1.0

        # utils.py: low crack + susceptible + no anomaly
        utils = merged["src/utils.py"]
        assert 0.0 < utils.crack_intensity < 0.2
        assert utils.infection_state == "S"
        assert utils.anomaly_active is False

        # main.py: low crack + recovered + suppressed anomaly
        main = merged["src/main.py"]
        assert main.crack_intensity < 0.1
        assert main.infection_state == "R"
        assert main.anomaly_active is False  # suppressed by high fp rate

    def test_merge_prioritizes_worst_vitality(self):
        """When multiple adapters report vitality, the lowest (worst) wins."""
        tmp_path1 = os.path.join(FIXTURES_DIR, "_tmp_merge1.json")
        tmp_path2 = os.path.join(FIXTURES_DIR, "_tmp_merge2.json")

        with open(tmp_path1, "w") as f:
            json.dump({"modules": [{"path": "src/x.py", "compartment": "S"}]}, f)
        with open(tmp_path2, "w") as f:
            json.dump(
                {
                    "files": {
                        "src/x.py": {
                            "anomaly_score": 0.5,
                            "is_anomalous": True,
                            "detections": [{"false_positive_rate": 0.1}],
                        }
                    }
                },
                f,
            )

        try:
            adapters = load_adapters(
                endemic_data=tmp_path1,
                sentinel_data=tmp_path2,
            )
            merged = merge_health_states(adapters)
            # endemic S = vitality 1.0, sentinel 0.5 = vitality 0.5
            assert merged["src/x.py"].vitality == 0.5
        finally:
            os.remove(tmp_path1)
            os.remove(tmp_path2)

    def test_graceful_degradation_no_adapters(self):
        adapters = load_adapters()
        assert adapters == []
        merged = merge_health_states(adapters)
        assert merged == {}

    def test_partial_adapters(self):
        fatigue_path = os.path.join(FIXTURES_DIR, "fatigue.json")
        adapters = load_adapters(fatigue_data=fatigue_path)
        assert len(adapters) == 1
        merged = merge_health_states(adapters)
        assert len(merged) == 3
        assert all(s.crack_intensity > 0 for s in merged.values())
        assert all(s.infection_state == "S" for s in merged.values())
        assert all(s.anomaly_active is False for s in merged.values())
