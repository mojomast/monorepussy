"""Tests for cyclone.vorticity — vorticity computation."""

import os

import pytest

from ussy_cyclone.models import (
    CycloneCategory,
    PipelineStage,
    PipelineTopology,
)
from ussy_cyclone.vorticity import (
    compute_stage_vorticity,
    compute_vorticity_field,
    compute_vorticity_change,
    format_vorticity,
)


@pytest.fixture
def simple_topology():
    """Create a simple linear pipeline topology."""
    topo = PipelineTopology()
    topo.add_stage(PipelineStage(
        name="ingest", forward_rate=5000.0, reprocessing_rate=50.0,
        queue_depth=200, consumer_count=4, base_retry_rate=5.0,
    ))
    topo.add_stage(PipelineStage(
        name="process", forward_rate=4000.0, reprocessing_rate=200.0,
        queue_depth=500, consumer_count=3, base_retry_rate=10.0,
    ))
    topo.add_stage(PipelineStage(
        name="enrich", forward_rate=2000.0, reprocessing_rate=800.0,
        queue_depth=5000, consumer_count=2, base_retry_rate=20.0,
    ))
    topo.add_edge("ingest", "process")
    topo.add_edge("process", "enrich")
    return topo


@pytest.fixture
def hurricane_topology():
    """Load the hurricane pipeline fixture."""
    from ussy_cyclone.models import topology_from_json
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    return topology_from_json(os.path.join(fixtures_dir, "hurricane_pipeline.json"))


class TestComputeStageVorticity:
    def test_isolated_stage_zero_reprocessing(self):
        stage = PipelineStage(name="solo", forward_rate=100.0, reprocessing_rate=0.0)
        reading = compute_stage_vorticity(stage)
        assert reading.stage_name == "solo"
        # No reprocessing, no neighbors → vorticity is zero
        assert reading.zeta == 0.0

    def test_isolated_stage_with_reprocessing(self):
        stage = PipelineStage(name="solo", forward_rate=100.0, reprocessing_rate=10.0)
        reading = compute_stage_vorticity(stage)
        assert reading.stage_name == "solo"
        # Intrinsic rotation from reprocessing even without neighbors
        assert reading.zeta > 0.0

    def test_stage_with_downstream(self):
        stage = PipelineStage(name="a", forward_rate=100.0, reprocessing_rate=10.0)
        downstream = [PipelineStage(name="b", forward_rate=50.0, reprocessing_rate=50.0)]
        reading = compute_stage_vorticity(stage, downstream_stages=downstream)
        # ∂v/∂x = 50 - 10 = 40
        assert reading.zeta != 0.0

    def test_stage_with_upstream(self):
        stage = PipelineStage(name="b", forward_rate=50.0, reprocessing_rate=50.0)
        upstream = [PipelineStage(name="a", forward_rate=100.0, reprocessing_rate=10.0)]
        reading = compute_stage_vorticity(stage, upstream_stages=upstream)
        assert reading.zeta != 0.0

    def test_absolute_vorticity(self):
        stage = PipelineStage(
            name="test", forward_rate=100.0, reprocessing_rate=10.0,
            base_retry_rate=5.0,
        )
        downstream = [PipelineStage(name="b", forward_rate=100.0, reprocessing_rate=20.0)]
        reading = compute_stage_vorticity(stage, downstream_stages=downstream)
        # η = ζ + f
        assert reading.absolute_vorticity == pytest.approx(reading.zeta + 5.0)

    def test_divergence_computed(self):
        stage = PipelineStage(name="a", forward_rate=100.0, reprocessing_rate=10.0)
        downstream = [PipelineStage(name="b", forward_rate=200.0, reprocessing_rate=50.0)]
        reading = compute_stage_vorticity(stage, downstream_stages=downstream)
        # With downstream having higher rates, divergence should be computed
        assert isinstance(reading.divergence, float)

    def test_pv_computed(self):
        stage = PipelineStage(name="a", forward_rate=100.0, reprocessing_rate=10.0,
                              queue_depth=100, base_retry_rate=5.0)
        downstream = [PipelineStage(name="b", forward_rate=200.0, reprocessing_rate=50.0)]
        reading = compute_stage_vorticity(stage, downstream_stages=downstream)
        # PV = η / H
        assert reading.pv == pytest.approx(reading.absolute_vorticity / 100)

    def test_category_assigned(self):
        stage = PipelineStage(name="a", forward_rate=100.0, reprocessing_rate=10.0)
        reading = compute_stage_vorticity(stage)
        assert isinstance(reading.category, CycloneCategory)


class TestComputeVorticityField:
    def test_all_stages_computed(self, simple_topology):
        readings = compute_vorticity_field(simple_topology)
        assert len(readings) == 3
        assert "ingest" in readings
        assert "process" in readings
        assert "enrich" in readings

    def test_vorticity_values(self, simple_topology):
        readings = compute_vorticity_field(simple_topology)
        # The enrich stage has much higher reprocessing, should have notable vorticity
        assert readings["enrich"].zeta != 0.0

    def test_hurricane_high_vorticity(self, hurricane_topology):
        readings = compute_vorticity_field(hurricane_topology)
        # All stages in hurricane pipeline have high reprocessing
        high_vorticity = [name for name, r in readings.items() if r.zeta > 0.5]
        assert len(high_vorticity) > 0


class TestComputeVorticityChange:
    def test_change_computed(self):
        from ussy_cyclone.models import VorticityReading
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        current = {
            "a": VorticityReading(stage_name="a", zeta=1.5, timestamp=now),
            "b": VorticityReading(stage_name="b", zeta=0.8, timestamp=now),
        }
        previous = {
            "a": VorticityReading(stage_name="a", zeta=1.0, timestamp=now),
            "b": VorticityReading(stage_name="b", zeta=0.8, timestamp=now),
        }

        changes = compute_vorticity_change(current, previous)
        assert changes["a"] == pytest.approx(0.5)
        assert changes["b"] == pytest.approx(0.0)

    def test_missing_stage(self):
        from ussy_cyclone.models import VorticityReading
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        current = {
            "a": VorticityReading(stage_name="a", zeta=1.0, timestamp=now),
        }
        previous = {}

        changes = compute_vorticity_change(current, previous)
        assert "a" not in changes


class TestFormatVorticity:
    def test_format_produces_output(self, simple_topology):
        readings = compute_vorticity_field(simple_topology)
        output = format_vorticity(readings)
        assert "CYCLONE" in output
        assert "ingest" in output

    def test_format_empty(self):
        output = format_vorticity({})
        assert "CYCLONE" in output
