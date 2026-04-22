"""Tests for gamut.models module."""

import pytest
from datetime import datetime, timezone

from gamut.models import (
    BoundaryReport,
    ClippingResult,
    ClippingRisk,
    FieldType,
    FieldProfile,
    PipelineDAG,
    PipelineEdge,
    RenderingIntent,
    SampleReport,
    SampleValue,
    StageProfile,
    TypeGamut,
)


class TestTypeGamut:
    """Tests for TypeGamut dataclass."""

    def test_creation_basic(self):
        g = TypeGamut(system="test", type_name="INT", field_type=FieldType.INTEGER)
        assert g.system == "test"
        assert g.type_name == "INT"
        assert g.field_type == FieldType.INTEGER
        assert g.nullable is True  # default

    def test_creation_full(self):
        g = TypeGamut(
            system="postgresql",
            type_name="NUMERIC(38,18)",
            field_type=FieldType.DECIMAL,
            min_value=-1e20,
            max_value=1e20,
            precision=38,
            scale=18,
            charset=None,
            max_length=None,
            timezone_aware=None,
            tz_precision=None,
            nullable=False,
        )
        assert g.precision == 38
        assert g.scale == 18
        assert g.nullable is False

    def test_frozen(self):
        g = TypeGamut(system="test", type_name="INT", field_type=FieldType.INTEGER)
        with pytest.raises(AttributeError):
            g.system = "other"

    def test_equality(self):
        g1 = TypeGamut(system="test", type_name="INT", field_type=FieldType.INTEGER)
        g2 = TypeGamut(system="test", type_name="INT", field_type=FieldType.INTEGER)
        assert g1 == g2

    def test_inequality(self):
        g1 = TypeGamut(system="test", type_name="INT", field_type=FieldType.INTEGER)
        g2 = TypeGamut(system="test", type_name="BIGINT", field_type=FieldType.INTEGER)
        assert g1 != g2


class TestFieldProfile:
    """Tests for FieldProfile."""

    def test_creation(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        fp = FieldProfile(name="id", gamut=g, source_type_raw="INT")
        assert fp.name == "id"
        assert fp.gamut.system == "pg"

    def test_default_source_type(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        fp = FieldProfile(name="id", gamut=g)
        assert fp.source_type_raw == ""


class TestStageProfile:
    """Tests for StageProfile."""

    def test_creation(self):
        sp = StageProfile(name="test_stage", system="postgresql")
        assert sp.name == "test_stage"
        assert sp.system == "postgresql"
        assert sp.fields == []
        assert sp.timestamp.tzinfo is not None

    def test_field_names(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        sp = StageProfile(
            name="stage",
            system="pg",
            fields=[
                FieldProfile(name="a", gamut=g),
                FieldProfile(name="b", gamut=g),
            ],
        )
        assert sp.field_names() == ["a", "b"]

    def test_get_field(self):
        g = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER)
        sp = StageProfile(
            name="stage",
            system="pg",
            fields=[FieldProfile(name="a", gamut=g)],
        )
        assert sp.get_field("a") is not None
        assert sp.get_field("z") is None


class TestClippingResult:
    """Tests for ClippingResult."""

    def test_no_clipping(self):
        cr = ClippingResult(
            field_name="test",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="INT", field_type=FieldType.INTEGER),
            risk=ClippingRisk.NONE,
            delta_e=0.0,
        )
        assert not cr.is_clipping

    def test_is_clipping(self):
        cr = ClippingResult(
            field_name="test",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="INT", field_type=FieldType.INTEGER),
            risk=ClippingRisk.HIGH,
            delta_e=10.0,
        )
        assert cr.is_clipping


class TestBoundaryReport:
    """Tests for BoundaryReport."""

    def test_empty_report(self):
        br = BoundaryReport(source_stage="a", dest_stage="b")
        assert br.clipping_count == 0
        assert br.critical_count == 0
        assert br.max_delta_e == 0.0

    def test_with_results(self):
        cr1 = ClippingResult(
            field_name="f1",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="SMALLINT", field_type=FieldType.INTEGER),
            risk=ClippingRisk.HIGH,
            delta_e=15.0,
        )
        cr2 = ClippingResult(
            field_name="f2",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="INT", field_type=FieldType.INTEGER),
            risk=ClippingRisk.NONE,
            delta_e=0.0,
        )
        br = BoundaryReport(source_stage="a", dest_stage="b", results=[cr1, cr2])
        assert br.clipping_count == 1
        assert br.critical_count == 0
        assert br.max_delta_e == 15.0

    def test_get_clipping_results(self):
        cr = ClippingResult(
            field_name="f1",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="INT", field_type=FieldType.INTEGER),
            risk=ClippingRisk.MEDIUM,
            delta_e=3.0,
        )
        br = BoundaryReport(source_stage="a", dest_stage="b", results=[cr])
        assert len(br.get_clipping_results()) == 1


class TestPipelineDAG:
    """Tests for PipelineDAG."""

    def test_creation(self):
        dag = PipelineDAG(name="test")
        assert dag.name == "test"
        assert len(dag.stages) == 0

    def test_add_stage(self, postgres_stage):
        dag = PipelineDAG(name="test")
        dag.add_stage(postgres_stage)
        assert "pg_source" in dag.stages

    def test_add_edge(self, postgres_stage, json_stage):
        dag = PipelineDAG(name="test")
        dag.add_stage(postgres_stage)
        dag.add_stage(json_stage)
        dag.add_edge("pg_source", "json_api", "export")
        assert len(dag.edges) == 1
        assert dag.edges[0].label == "export"

    def test_boundary_pairs(self, postgres_stage, json_stage):
        dag = PipelineDAG(name="test")
        dag.add_stage(postgres_stage)
        dag.add_stage(json_stage)
        dag.add_edge("pg_source", "json_api")
        pairs = dag.boundary_pairs()
        assert len(pairs) == 1
        assert pairs[0][0].name == "pg_source"
        assert pairs[0][1].name == "json_api"

    def test_boundary_pairs_missing_stage(self, postgres_stage):
        dag = PipelineDAG(name="test")
        dag.add_stage(postgres_stage)
        dag.add_edge("pg_source", "nonexistent")
        pairs = dag.boundary_pairs()
        assert len(pairs) == 0


class TestSampleReport:
    """Tests for SampleReport."""

    def test_empty_report(self):
        sr = SampleReport(source_stage="a", dest_stage="b")
        assert sr.total_count == 0
        assert sr.clipped_count == 0
        assert sr.clipped_pct == 0.0

    def test_with_samples(self):
        samples = [
            SampleValue(field_name="f1", value=1, stage="b", is_clipped=False),
            SampleValue(field_name="f2", value=2, stage="b", is_clipped=True),
            SampleValue(field_name="f1", value=3, stage="b", is_clipped=True),
        ]
        sr = SampleReport(source_stage="a", dest_stage="b", samples=samples)
        assert sr.total_count == 3
        assert sr.clipped_count == 2
        assert sr.clipped_pct == pytest.approx(66.666, rel=1e-2)

    def test_clipped_by_field(self):
        samples = [
            SampleValue(field_name="f1", value=1, stage="b", is_clipped=True),
            SampleValue(field_name="f2", value=2, stage="b", is_clipped=True),
            SampleValue(field_name="f1", value=3, stage="b", is_clipped=True),
        ]
        sr = SampleReport(source_stage="a", dest_stage="b", samples=samples)
        by_field = sr.clipped_by_field()
        assert by_field["f1"] == 2
        assert by_field["f2"] == 1


class TestEnums:
    """Tests for enum values."""

    def test_rendering_intent_values(self):
        assert RenderingIntent.PERCEPTUAL.value == "perceptual"
        assert RenderingIntent.ABSOLUTE_COLORIMETRIC.value == "absolute_colorimetric"
        assert RenderingIntent.SATURATION.value == "saturation"

    def test_clipping_risk_values(self):
        assert ClippingRisk.NONE.value == "none"
        assert ClippingRisk.LOW.value == "low"
        assert ClippingRisk.MEDIUM.value == "medium"
        assert ClippingRisk.HIGH.value == "high"
        assert ClippingRisk.CRITICAL.value == "critical"

    def test_field_type_values(self):
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.TIMESTAMP.value == "timestamp"
        assert FieldType.STRING.value == "string"

    def test_timezone_aware_timestamps(self):
        """All datetime.now() calls should use timezone.utc."""
        sp = StageProfile(name="test", system="test")
        assert sp.timestamp.tzinfo is not None
