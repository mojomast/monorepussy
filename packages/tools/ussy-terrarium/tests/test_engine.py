"""Tests for TerrariumEngine and HealthScore."""

import json

import pytest

from terrarium.engine import TerrariumEngine
from terrarium.health import HealthScore
from terrarium.adapters.base import BaseAdapter
from terrarium.ecosystem.model import OrganismHealthState


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    STUB_MODE = True

    def __init__(self, name, states):
        super().__init__()
        self.name = name
        self._states = states

    def load(self):
        return self._states


class TestHealthScore:
    def test_default_values(self):
        h = HealthScore()
        assert h.overall == 1.0
        assert h.fatigue == 1.0
        assert h.epidemic == 1.0

    def test_to_dict(self):
        h = HealthScore(overall=0.75, fatigue=0.5)
        d = h.to_dict()
        assert d["overall"] == 0.75
        assert d["fatigue"] == 0.5
        assert d["epidemic"] == 1.0


class TestTerrariumEngine:
    def test_collect_empty(self):
        engine = TerrariumEngine([])
        result = engine.collect()
        assert result == {}

    def test_collect_with_adapters(self):
        adapter = MockAdapter(
            "fatigue",
            {
                "src/a.py": OrganismHealthState(path="src/a.py", crack_intensity=0.5),
            },
        )
        engine = TerrariumEngine([adapter])
        result = engine.collect()
        assert "fatigue" in result
        assert result["fatigue"]["count"] == 1
        assert result["fatigue"]["states"]["src/a.py"]["crack_intensity"] == 0.5

    def test_score_perfect_health(self):
        adapter = MockAdapter(
            "fatigue",
            {
                "src/a.py": OrganismHealthState(path="src/a.py"),
            },
        )
        engine = TerrariumEngine([adapter])
        engine.collect()
        score = engine.score()
        assert score.overall == 1.0
        assert score.fatigue == 1.0

    def test_score_with_damage(self):
        adapters = [
            MockAdapter(
                "fatigue",
                {
                    "src/a.py": OrganismHealthState(
                        path="src/a.py", crack_intensity=0.5
                    ),
                },
            ),
            MockAdapter(
                "endemic",
                {
                    "src/a.py": OrganismHealthState(
                        path="src/a.py", infection_state="I"
                    ),
                },
            ),
            MockAdapter(
                "sentinel",
                {
                    "src/a.py": OrganismHealthState(
                        path="src/a.py", anomaly_active=True
                    ),
                },
            ),
        ]
        engine = TerrariumEngine(adapters)
        engine.collect()
        score = engine.score()
        assert score.fatigue == 0.5
        assert score.epidemic == 0.0
        assert score.anomaly == 0.0
        assert 0.0 < score.overall < 1.0

    def test_to_json(self):
        adapter = MockAdapter(
            "fatigue",
            {
                "src/a.py": OrganismHealthState(path="src/a.py", crack_intensity=0.2),
            },
        )
        engine = TerrariumEngine([adapter])
        engine.collect()
        json_str = engine.to_json()
        data = json.loads(json_str)
        assert "health" in data
        assert "adapters" in data
        assert data["health"]["fatigue"] == 0.8

    def test_score_missing_adapter(self):
        engine = TerrariumEngine([])
        engine.collect()
        score = engine.score()
        assert score.overall == 1.0

    def test_score_churn_from_churnmap(self):
        adapters = [
            MockAdapter(
                "churnmap",
                {
                    "src/a.py": OrganismHealthState(
                        path="src/a.py", territory_id="core-auth"
                    ),
                    "src/b.py": OrganismHealthState(path="src/b.py", territory_id=""),
                    "src/c.py": OrganismHealthState(path="src/c.py", territory_id=None),
                },
            ),
        ]
        engine = TerrariumEngine(adapters)
        engine.collect()
        score = engine.score()
        # 1 of 3 files is churning (has territory_id)
        assert score.churn == pytest.approx(1.0 - (1 / 3), abs=0.01)

    def test_collect_skips_unavailable_adapter(self):
        class UnavailableAdapter(BaseAdapter):
            name = "unavailable"
            data_path = None
            STUB_MODE = False

            def load(self):
                return {}

        engine = TerrariumEngine([UnavailableAdapter()])
        result = engine.collect()
        assert "unavailable" in result
        assert result["unavailable"]["error"] == "adapter not available"
        assert result["unavailable"]["stub"] is True
