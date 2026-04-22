"""Tests for gamut.analyzer module."""

import pytest

from gamut.models import (
    ClippingRisk,
    FieldType,
    FieldProfile,
    RenderingIntent,
    TypeGamut,
)
from gamut.analyzer import (
    analyze_boundary,
    analyze_field,
    analyze_pipeline,
    classify_risk,
    classify_rendering_intent,
    compute_delta_e,
    generate_clipped_examples,
)
from gamut.profiler import profile_stage


class TestComputeDeltaE:
    """Tests for Delta E computation."""

    def test_identical_types_no_loss(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-2147483648, max_value=2147483647, precision=10, scale=0)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-2147483648, max_value=2147483647, precision=10, scale=0)
        de = compute_delta_e(src, dst)
        assert de == 0.0

    def test_numeric_range_loss(self):
        src = TypeGamut(system="pg", type_name="BIGINT", field_type=FieldType.INTEGER,
                        min_value=-9.22e18, max_value=9.22e18, precision=19, scale=0)
        dst = TypeGamut(system="pg", type_name="SMALLINT", field_type=FieldType.INTEGER,
                        min_value=-32768, max_value=32767, precision=5, scale=0)
        de = compute_delta_e(src, dst)
        assert de > 0.0  # Significant range loss

    def test_timezone_loss(self):
        src = TypeGamut(system="pg", type_name="TIMESTAMPTZ", field_type=FieldType.TIMESTAMP,
                        timezone_aware=True, tz_precision=6)
        dst = TypeGamut(system="bq", type_name="DATETIME", field_type=FieldType.TIMESTAMP,
                        timezone_aware=False, tz_precision=6)
        de = compute_delta_e(src, dst)
        # Timezone loss should contribute significantly
        assert de >= 25.0  # At least _WEIGHT_TIMEZONE * 1.0 * 100

    def test_precision_loss(self):
        src = TypeGamut(system="pg", type_name="NUMERIC(38,18)", field_type=FieldType.DECIMAL,
                        min_value=-1e20, max_value=1e20, precision=38, scale=18)
        dst = TypeGamut(system="bq", type_name="NUMERIC(38,9)", field_type=FieldType.DECIMAL,
                        min_value=-1e29, max_value=1e29, precision=38, scale=9)
        de = compute_delta_e(src, dst)
        assert de > 0.0  # Scale loss: 18 -> 9

    def test_no_loss_unbounded_dest(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-100, max_value=100, precision=3, scale=0)
        dst = TypeGamut(system="json", type_name="number", field_type=FieldType.FLOAT,
                        min_value=-1.7e308, max_value=1.7e308, precision=15, scale=None)
        de = compute_delta_e(src, dst)
        assert de == 0.0  # Destination is wider

    def test_nullable_loss(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=True)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=False)
        de = compute_delta_e(src, dst)
        assert de > 0.0  # Nullable loss

    def test_delta_e_capped_at_100(self):
        # Extreme case: total loss
        src = TypeGamut(system="pg", type_name="NUMERIC", field_type=FieldType.DECIMAL,
                        min_value=-1e20, max_value=1e20, precision=38, scale=18,
                        timezone_aware=True, nullable=True)
        dst = TypeGamut(system="pg", type_name="SMALLINT", field_type=FieldType.INTEGER,
                        min_value=-32768, max_value=32767, precision=5, scale=0,
                        nullable=False)
        de = compute_delta_e(src, dst)
        assert de <= 100.0


class TestClassifyRisk:
    """Tests for risk classification."""

    def test_none(self):
        assert classify_risk(0.0) == ClippingRisk.NONE

    def test_low(self):
        assert classify_risk(0.5) == ClippingRisk.LOW

    def test_medium(self):
        assert classify_risk(3.0) == ClippingRisk.MEDIUM

    def test_high(self):
        assert classify_risk(15.0) == ClippingRisk.HIGH

    def test_critical(self):
        assert classify_risk(25.0) == ClippingRisk.CRITICAL

    def test_boundary_values(self):
        assert classify_risk(0.99) == ClippingRisk.LOW
        assert classify_risk(1.0) == ClippingRisk.MEDIUM
        assert classify_risk(4.99) == ClippingRisk.MEDIUM
        assert classify_risk(5.0) == ClippingRisk.HIGH
        assert classify_risk(19.99) == ClippingRisk.HIGH
        assert classify_risk(20.0) == ClippingRisk.CRITICAL


class TestClassifyRenderingIntent:
    """Tests for rendering intent classification."""

    def test_nullable_violation_is_absolute(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=True)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=False)
        assert classify_rendering_intent(src, dst) == RenderingIntent.ABSOLUTE_COLORIMETRIC

    def test_string_truncation_is_saturation(self):
        src = TypeGamut(system="pg", type_name="VARCHAR(500)", field_type=FieldType.STRING,
                        max_length=500)
        dst = TypeGamut(system="pg", type_name="VARCHAR(100)", field_type=FieldType.STRING,
                        max_length=100)
        assert classify_rendering_intent(src, dst) == RenderingIntent.SATURATION

    def test_timezone_drop_is_saturation(self):
        src = TypeGamut(system="pg", type_name="TIMESTAMPTZ", field_type=FieldType.TIMESTAMP,
                        timezone_aware=True)
        dst = TypeGamut(system="bq", type_name="DATETIME", field_type=FieldType.TIMESTAMP,
                        timezone_aware=False)
        assert classify_rendering_intent(src, dst) == RenderingIntent.SATURATION

    def test_numeric_conversion_is_perceptual(self):
        src = TypeGamut(system="pg", type_name="NUMERIC(38,18)", field_type=FieldType.DECIMAL,
                        precision=38, scale=18)
        dst = TypeGamut(system="json", type_name="number", field_type=FieldType.FLOAT,
                        precision=15)
        assert classify_rendering_intent(src, dst) == RenderingIntent.PERCEPTUAL


class TestGenerateClippedExamples:
    """Tests for clipped example generation."""

    def test_numeric_range_clipping(self):
        src = TypeGamut(system="pg", type_name="BIGINT", field_type=FieldType.INTEGER,
                        min_value=-9.22e18, max_value=9.22e18)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-2147483648, max_value=2147483647)
        examples = generate_clipped_examples(src, dst)
        assert any("exceeds dest max" in e or "below dest min" in e for e in examples)

    def test_timezone_clipping(self):
        src = TypeGamut(system="pg", type_name="TIMESTAMPTZ", field_type=FieldType.TIMESTAMP,
                        timezone_aware=True)
        dst = TypeGamut(system="bq", type_name="DATETIME", field_type=FieldType.TIMESTAMP,
                        timezone_aware=False)
        examples = generate_clipped_examples(src, dst)
        assert any("timezone" in e.lower() for e in examples)

    def test_nullable_violation(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=True)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER, nullable=False)
        examples = generate_clipped_examples(src, dst)
        assert any("NULL" in e for e in examples)

    def test_precision_loss(self):
        src = TypeGamut(system="pg", type_name="NUMERIC(38,18)", field_type=FieldType.DECIMAL,
                        precision=38, scale=18)
        dst = TypeGamut(system="bq", type_name="NUMERIC(38,9)", field_type=FieldType.DECIMAL,
                        precision=38, scale=9)
        examples = generate_clipped_examples(src, dst)
        assert any("scale loss" in e for e in examples)

    def test_no_clipping_no_examples(self):
        src = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-100, max_value=100, precision=3, scale=0)
        dst = TypeGamut(system="pg", type_name="INT", field_type=FieldType.INTEGER,
                        min_value=-32768, max_value=32767, precision=5, scale=0)
        examples = generate_clipped_examples(src, dst)
        assert len(examples) == 0


class TestAnalyzeBoundary:
    """Tests for analyze_boundary function."""

    def test_postgres_to_json(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        assert report.source_stage == "pg_source"
        assert report.dest_stage == "json_api"
        assert len(report.results) >= 5

    def test_clipping_fields_detected(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        # NUMERIC(38,18) → JSON number should be detected as clipping
        clipping_fields = [r for r in report.results if r.is_clipping]
        assert len(clipping_fields) > 0

    def test_missing_field_in_dest(self):
        src = profile_stage("postgresql", "src", {"id": {"type": "INTEGER"}})
        dst = profile_stage("postgresql", "dst", {})  # No fields
        report = analyze_boundary(src, dst)
        assert report.critical_count >= 1
        # Missing field should be critical
        assert any(r.risk == ClippingRisk.CRITICAL for r in report.results)

    def test_added_field_in_dest(self):
        src = profile_stage("postgresql", "src", {"id": {"type": "INTEGER"}})
        dst = profile_stage("postgresql", "dst", {
            "id": {"type": "INTEGER"},
            "extra": {"type": "TEXT"},
        })
        report = analyze_boundary(src, dst)
        # Added field should have no risk
        extra_result = [r for r in report.results if r.field_name == "extra"]
        assert len(extra_result) == 1
        assert extra_result[0].risk == ClippingRisk.NONE


class TestAnalyzePipeline:
    """Tests for analyze_pipeline function."""

    def test_three_stage_pipeline(self, sample_dag):
        reports = analyze_pipeline(sample_dag)
        assert len(reports) == 2  # Two edges = two boundaries

    def test_report_has_clipping(self, sample_dag):
        reports = analyze_pipeline(sample_dag)
        # At least one boundary should have clipping
        total_clipping = sum(r.clipping_count for r in reports)
        assert total_clipping > 0

    def test_pipeline_from_file(self, sample_pipeline_json):
        from gamut.profiler import dag_from_json
        dag = dag_from_json(sample_pipeline_json)
        reports = analyze_pipeline(dag)
        assert len(reports) == 2
