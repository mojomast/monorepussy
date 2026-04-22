"""Tests for cyclone.detect — cyclone detection and tracking."""

import pytest

from cyclone.detect import (
    detect_cyclones,
    track_cyclone,
    format_detection,
    _find_affected_stages,
)
from cyclone.models import (
    CycloneCategory,
    CycloneDetection,
    PipelineStage,
    PipelineTopology,
    VorticityReading,
)


@pytest.fixture
def stormy_topology():
    """Create a topology with stormy conditions."""
    topo = PipelineTopology()
    topo.add_stage(PipelineStage(
        name="ingest", forward_rate=5000.0, reprocessing_rate=50.0,
        queue_depth=200, consumer_count=4, error_rate=10.0,
        dlq_depth=100, base_retry_rate=5.0,
    ))
    topo.add_stage(PipelineStage(
        name="enrich", forward_rate=2000.0, reprocessing_rate=800.0,
        queue_depth=5000, consumer_count=2, error_rate=200.0,
        dlq_depth=12433, base_retry_rate=20.0,
    ))
    topo.add_stage(PipelineStage(
        name="sink", forward_rate=5000.0, reprocessing_rate=30.0,
        queue_depth=100, consumer_count=4, error_rate=5.0,
        dlq_depth=50, base_retry_rate=2.0,
    ))
    topo.add_edge("ingest", "enrich")
    topo.add_edge("enrich", "sink")
    # CISK cycle: enrich → enrich
    topo.add_retry_edge("enrich", "enrich", 1.8)
    return topo


@pytest.fixture
def calm_topology():
    """Create a topology with calm conditions."""
    topo = PipelineTopology()
    topo.add_stage(PipelineStage(
        name="source", forward_rate=10000.0, reprocessing_rate=5.0,
        queue_depth=50, consumer_count=8, error_rate=1.0,
    ))
    topo.add_stage(PipelineStage(
        name="sink", forward_rate=9900.0, reprocessing_rate=3.0,
        queue_depth=30, consumer_count=4, error_rate=0.5,
    ))
    topo.add_edge("source", "sink")
    return topo


class TestDetectCyclones:
    def test_detects_stormy_stage(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field
        from cyclone.cisk import detect_cisk

        cycles, gains = detect_cisk(stormy_topology)
        readings = compute_vorticity_field(stormy_topology)
        detections = detect_cyclones(stormy_topology, readings=readings, cisk_cycles=cycles, cycle_gains=gains)

        # The enrich stage should be detected as having elevated vorticity
        enrich_names = [d.center_stage for d in detections]
        assert "enrich" in enrich_names

    def test_calm_pipeline_no_cyclones(self, calm_topology):
        detections = detect_cyclones(calm_topology)
        # Calm pipeline should have no or very few cyclones
        assert len(detections) == 0

    def test_cyclone_has_id(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field

        readings = compute_vorticity_field(stormy_topology)
        # Only detect where vorticity is above threshold
        detections = detect_cyclones(stormy_topology, readings=readings)
        for d in detections:
            assert len(d.id) == 8  # MD5 hash truncated to 8 chars

    def test_cyclone_has_category(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field

        readings = compute_vorticity_field(stormy_topology)
        detections = detect_cyclones(stormy_topology, readings=readings)
        for d in detections:
            assert isinstance(d.category, CycloneCategory)

    def test_cyclone_with_cisk_upgrade(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field
        from cyclone.cisk import detect_cisk

        cycles, gains = detect_cisk(stormy_topology)
        readings = compute_vorticity_field(stormy_topology)
        detections = detect_cyclones(stormy_topology, readings=readings, cisk_cycles=cycles, cycle_gains=gains)

        # Check enrich stage detection includes CISK info
        enrich_detections = [d for d in detections if d.center_stage == "enrich"]
        if enrich_detections:
            d = enrich_detections[0]
            # If CISK is detected, it should be in the detection
            if d.cisk_cycle:
                assert d.cycle_gain > 0

    def test_detection_timestamp(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field

        readings = compute_vorticity_field(stormy_topology)
        detections = detect_cyclones(stormy_topology, readings=readings)
        for d in detections:
            assert d.timestamp.tzinfo is not None


class TestFindAffectedStages:
    def test_finds_nearby_stages(self, stormy_topology):
        from cyclone.vorticity import compute_vorticity_field
        readings = compute_vorticity_field(stormy_topology)
        affected = _find_affected_stages("enrich", stormy_topology, readings)
        assert "enrich" in affected


class TestTrackCyclone:
    def test_find_existing_cyclone(self):
        d = CycloneDetection(
            id="abc12345",
            center_stage="test",
            category=CycloneCategory.STORM,
            vorticity=1.0,
        )
        result = track_cyclone([d], "abc12345")
        assert result is d

    def test_missing_cyclone(self):
        result = track_cyclone([], "nonexistent")
        assert result is None


class TestFormatDetection:
    def test_format_with_cyclones(self):
        detections = [
            CycloneDetection(
                id="abc12345",
                center_stage="enrich",
                category=CycloneCategory.SEVERE_STORM,
                vorticity=2.1,
                stages_affected=["enrich", "route"],
            )
        ]
        output = format_detection(detections)
        assert "enrich" in output
        assert "Severe Storm" in output

    def test_format_no_cyclones(self):
        output = format_detection([])
        assert "calm" in output.lower()

    def test_format_with_cisk_info(self):
        detections = [
            CycloneDetection(
                id="abc12345",
                center_stage="enrich",
                category=CycloneCategory.SEVERE_STORM,
                vorticity=2.1,
                cisk_cycle=["enrich", "error", "retry"],
                cycle_gain=1.8,
                dlq_depth=12433,
            )
        ]
        output = format_detection(detections)
        assert "CISK" in output
        assert "1.80x" in output
        assert "12,433" in output
