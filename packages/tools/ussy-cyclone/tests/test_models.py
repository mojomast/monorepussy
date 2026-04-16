"""Tests for cyclone.models — core data models."""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from cyclone.models import (
    CycloneCategory,
    CycloneDetection,
    ForecastStep,
    PipelineStage,
    PipelineTopology,
    StabilityReading,
    VelocityField,
    VorticityReading,
    classify_vorticity,
    topology_from_dict,
    topology_from_json,
)


# ── VelocityField ─────────────────────────────────────────────


class TestVelocityField:
    def test_speed(self):
        vf = VelocityField(u=3.0, v=4.0)
        assert vf.speed == pytest.approx(5.0)

    def test_angle(self):
        import math
        vf = VelocityField(u=1.0, v=0.0)
        assert vf.angle == pytest.approx(0.0)
        vf2 = VelocityField(u=0.0, v=1.0)
        assert vf2.angle == pytest.approx(math.pi / 2)

    def test_reprocessing_ratio_zero(self):
        vf = VelocityField(u=0.0, v=0.0)
        assert vf.reprocessing_ratio == 0.0

    def test_reprocessing_ratio_normal(self):
        vf = VelocityField(u=80.0, v=20.0)
        assert vf.reprocessing_ratio == pytest.approx(0.2)

    def test_speed_zero(self):
        vf = VelocityField(u=0.0, v=0.0)
        assert vf.speed == 0.0


# ── CycloneCategory ───────────────────────────────────────────


class TestCycloneCategory:
    def test_labels(self):
        assert CycloneCategory.CALM.label == "Calm"
        assert CycloneCategory.DEPRESSION.label == "Depression"
        assert CycloneCategory.STORM.label == "Storm"
        assert CycloneCategory.SEVERE_STORM.label == "Severe Storm"
        assert CycloneCategory.CYCLONE.label == "Cyclone"
        assert CycloneCategory.HURRICANE.label == "Hurricane"

    def test_emojis(self):
        assert CycloneCategory.CALM.emoji == "🌤️"
        assert CycloneCategory.HURRICANE.emoji == "☄️"

    def test_ordering(self):
        assert CycloneCategory.CALM < CycloneCategory.DEPRESSION
        assert CycloneCategory.HURRICANE > CycloneCategory.STORM

    def test_value(self):
        assert CycloneCategory.CYCLONE.value == 4


# ── PipelineStage ─────────────────────────────────────────────


class TestPipelineStage:
    def test_velocity_field_created(self):
        stage = PipelineStage(name="test", forward_rate=100.0, reprocessing_rate=10.0)
        assert stage.velocity.u == 100.0
        assert stage.velocity.v == 10.0

    def test_total_throughput(self):
        stage = PipelineStage(name="test", forward_rate=100.0, reprocessing_rate=20.0)
        assert stage.total_throughput == 120.0

    def test_reprocessing_fraction(self):
        stage = PipelineStage(name="test", forward_rate=80.0, reprocessing_rate=20.0)
        # reprocessing_fraction = reprocessing / total_throughput = 20 / 100 = 0.2
        assert stage.reprocessing_fraction == pytest.approx(0.2)

    def test_reprocessing_fraction_zero(self):
        stage = PipelineStage(name="test", forward_rate=0.0, reprocessing_rate=0.0)
        assert stage.reprocessing_fraction == 0.0

    def test_coriolis_parameter_explicit(self):
        stage = PipelineStage(name="test", base_retry_rate=5.0)
        assert stage.coriolis_parameter == 5.0

    def test_coriolis_parameter_inferred(self):
        stage = PipelineStage(name="test", reprocessing_rate=100.0, base_retry_rate=0.0)
        assert stage.coriolis_parameter == pytest.approx(10.0)

    def test_load_variance(self):
        stage = PipelineStage(name="test", queue_depth=200, consumer_count=4)
        assert stage.load_variance == 50.0

    def test_defaults(self):
        stage = PipelineStage(name="test")
        assert stage.stage_type == "generic"
        assert stage.consumer_count == 1
        assert stage.dlq_depth == 0


# ── VorticityReading ──────────────────────────────────────────


class TestVorticityReading:
    def test_basic_reading(self):
        r = VorticityReading(stage_name="test", zeta=1.5)
        assert r.zeta == 1.5
        assert r.absolute_vorticity == 0.0

    def test_timestamp_is_timezone_aware(self):
        r = VorticityReading(stage_name="test", zeta=0.0)
        assert r.timestamp.tzinfo is not None


# ── PipelineTopology ──────────────────────────────────────────


class TestPipelineTopology:
    def test_add_stage(self):
        topo = PipelineTopology()
        stage = PipelineStage(name="ingest")
        topo.add_stage(stage)
        assert "ingest" in topo.stages

    def test_add_edge(self):
        topo = PipelineTopology()
        topo.add_edge("a", "b")
        assert ("a", "b") in topo.edges

    def test_add_retry_edge(self):
        topo = PipelineTopology()
        topo.add_retry_edge("a", "b", 1.5)
        assert ("a", "b", 1.5) in topo.retry_edges

    def test_get_stage(self):
        topo = PipelineTopology()
        stage = PipelineStage(name="ingest")
        topo.add_stage(stage)
        assert topo.get_stage("ingest") is stage
        assert topo.get_stage("missing") is None

    def test_stage_names(self):
        topo = PipelineTopology()
        topo.add_stage(PipelineStage(name="a"))
        topo.add_stage(PipelineStage(name="b"))
        assert set(topo.stage_names) == {"a", "b"}

    def test_downstream(self):
        topo = PipelineTopology()
        topo.add_stage(PipelineStage(name="a"))
        topo.add_stage(PipelineStage(name="b"))
        topo.add_edge("a", "b")
        assert topo.downstream["a"] == ["b"]
        assert topo.downstream["b"] == []

    def test_upstream(self):
        topo = PipelineTopology()
        topo.add_stage(PipelineStage(name="a"))
        topo.add_stage(PipelineStage(name="b"))
        topo.add_edge("a", "b")
        assert topo.upstream["b"] == ["a"]
        assert topo.upstream["a"] == []


# ── CycloneDetection ──────────────────────────────────────────


class TestCycloneDetection:
    def test_severity_label(self):
        d = CycloneDetection(
            id="test-001",
            center_stage="enrich",
            category=CycloneCategory.SEVERE_STORM,
            vorticity=2.1,
        )
        assert d.severity_label == "Cat-3 Severe Storm"

    def test_is_active_default(self):
        d = CycloneDetection(
            id="test-001",
            center_stage="enrich",
            category=CycloneCategory.STORM,
            vorticity=1.0,
        )
        assert d.is_active is True


# ── StabilityReading ──────────────────────────────────────────


class TestStabilityReading:
    def test_unstable_detection(self):
        r = StabilityReading(
            boundary="a → b",
            richardson_number=0.1,
            throughput_gradient=100.0,
            load_stability=10.0,
        )
        assert r.is_unstable is True

    def test_stable_detection(self):
        r = StabilityReading(
            boundary="a → b",
            richardson_number=1.0,
            throughput_gradient=10.0,
            load_stability=10.0,
        )
        assert r.is_unstable is False

    def test_exactly_critical(self):
        r = StabilityReading(
            boundary="a → b",
            richardson_number=0.25,
            throughput_gradient=10.0,
            load_stability=5.0,
        )
        assert r.is_unstable is False  # Not strictly less than

    def test_explicit_unstable_overrides(self):
        r = StabilityReading(
            boundary="a → b",
            richardson_number=1.0,
            throughput_gradient=10.0,
            load_stability=10.0,
            is_unstable=True,
        )
        assert r.is_unstable is True


# ── classify_vorticity ────────────────────────────────────────


class TestClassifyVorticity:
    def test_calm(self):
        assert classify_vorticity(0.0, 0.0) == CycloneCategory.CALM

    def test_negative_vorticity_calm(self):
        assert classify_vorticity(-1.0, 0.0) == CycloneCategory.CALM

    def test_depression(self):
        assert classify_vorticity(0.3, 0.02) == CycloneCategory.DEPRESSION

    def test_storm(self):
        assert classify_vorticity(0.8, 0.10) == CycloneCategory.STORM

    def test_severe_storm(self):
        assert classify_vorticity(1.5, 0.20) == CycloneCategory.SEVERE_STORM

    def test_cyclone(self):
        assert classify_vorticity(2.5, 0.40) == CycloneCategory.CYCLONE

    def test_hurricane(self):
        assert classify_vorticity(4.0, 0.60) == CycloneCategory.HURRICANE


# ── topology_from_dict / topology_from_json ───────────────────


class TestTopologyLoading:
    @pytest.fixture
    def pipeline_dict(self):
        return {
            "stages": [
                {
                    "name": "ingest",
                    "type": "kafka",
                    "forward_rate": 1000.0,
                    "reprocessing_rate": 50.0,
                    "queue_depth": 100,
                    "consumer_count": 3,
                    "error_rate": 10.0,
                    "dlq_depth": 50,
                    "base_retry_rate": 5.0,
                },
                {
                    "name": "process",
                    "type": "generic",
                    "forward_rate": 900.0,
                    "reprocessing_rate": 100.0,
                    "queue_depth": 200,
                    "consumer_count": 2,
                },
            ],
            "edges": [["ingest", "process"]],
            "retry_edges": [["process", "ingest", 1.5]],
        }

    def test_from_dict(self, pipeline_dict):
        topo = topology_from_dict(pipeline_dict)
        assert len(topo.stages) == 2
        assert "ingest" in topo.stages
        assert "process" in topo.stages
        assert topo.stages["ingest"].stage_type == "kafka"
        assert topo.stages["process"].consumer_count == 2

    def test_from_dict_edges(self, pipeline_dict):
        topo = topology_from_dict(pipeline_dict)
        assert ("ingest", "process") in topo.edges
        assert ("process", "ingest", 1.5) in topo.retry_edges

    def test_from_json_file(self, pipeline_dict):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(pipeline_dict, f)
            f.flush()
            path = f.name

        try:
            topo = topology_from_json(path)
            assert len(topo.stages) == 2
        finally:
            os.unlink(path)

    def test_from_dict_empty(self):
        topo = topology_from_dict({})
        assert len(topo.stages) == 0
        assert len(topo.edges) == 0

    def test_from_dict_missing_optional_fields(self):
        data = {"stages": [{"name": "minimal"}]}
        topo = topology_from_dict(data)
        stage = topo.stages["minimal"]
        assert stage.stage_type == "generic"
        assert stage.forward_rate == 0.0


# ── ForecastStep ──────────────────────────────────────────────


class TestForecastStep:
    def test_creation(self):
        step = ForecastStep(
            timestamp=datetime.now(timezone.utc),
            stage_vorticities={"a": 0.5, "b": 1.2},
            stage_categories={"a": CycloneCategory.DEPRESSION, "b": CycloneCategory.STORM},
            cyclone_count=1,
        )
        assert step.cyclone_count == 1
        assert "a" in step.stage_vorticities
