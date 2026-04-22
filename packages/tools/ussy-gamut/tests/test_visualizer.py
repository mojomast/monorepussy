"""Tests for gamut.visualizer module."""

import pytest

from gamut.analyzer import analyze_boundary
from gamut.models import (
    BoundaryReport,
    ClippingResult,
    ClippingRisk,
    FieldType,
    RenderingIntent,
    TypeGamut,
)
from gamut.profiler import profile_stage
from gamut.visualizer import (
    render_boundary_comparison,
    render_field_detail,
    render_gamut_diagram,
    render_pipeline_overview,
)


class TestRenderGamutDiagram:
    """Tests for gamut diagram rendering."""

    def test_no_clipping(self):
        report = BoundaryReport(source_stage="a", dest_stage="b")
        output = render_gamut_diagram(report)
        assert "no clipping" in output.lower() or "in-gamut" in output.lower()

    def test_with_clipping(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        output = render_gamut_diagram(report)
        assert "Gamut Diagram" in output
        assert "Legend" in output
        assert "Fields:" in output

    def test_custom_dimensions(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        output = render_gamut_diagram(report, width=30, height=10)
        assert "Gamut Diagram" in output

    def test_field_labels_present(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        output = render_gamut_diagram(report)
        # Should contain field names from the boundary
        for field in postgres_stage.fields:
            if any(r.is_clipping and r.field_name == field.name for r in report.results):
                assert field.name in output


class TestRenderPipelineOverview:
    """Tests for pipeline overview rendering."""

    def test_basic_overview(self, sample_dag):
        from gamut.analyzer import analyze_pipeline
        reports = analyze_pipeline(sample_dag)
        output = render_pipeline_overview(reports, sample_dag)
        assert "Pipeline: test_pipeline" in output
        assert "Stages:" in output

    def test_boundary_summary(self, sample_dag):
        from gamut.analyzer import analyze_pipeline
        reports = analyze_pipeline(sample_dag)
        output = render_pipeline_overview(reports, sample_dag)
        assert "Boundary:" in output
        assert "Clipping fields" in output

    def test_empty_reports(self, sample_dag):
        output = render_pipeline_overview([], sample_dag)
        assert "Pipeline: test_pipeline" in output


class TestRenderFieldDetail:
    """Tests for field detail rendering."""

    def test_basic_detail(self):
        cr = ClippingResult(
            field_name="amount",
            source_gamut=TypeGamut(
                system="postgresql", type_name="NUMERIC(38,18)",
                field_type=FieldType.DECIMAL, precision=38, scale=18,
            ),
            dest_gamut=TypeGamut(
                system="json", type_name="number",
                field_type=FieldType.FLOAT, precision=15,
            ),
            risk=ClippingRisk.HIGH,
            delta_e=12.5,
            rendering_intent=RenderingIntent.PERCEPTUAL,
            clipped_examples=["scale loss: 18 → 15 decimal places"],
        )
        output = render_field_detail(cr)
        assert "Field: amount" in output
        assert "NUMERIC(38,18)" in output
        assert "number" in output
        assert "ΔE" in output

    def test_no_examples(self):
        cr = ClippingResult(
            field_name="test",
            source_gamut=TypeGamut(system="a", type_name="INT", field_type=FieldType.INTEGER),
            dest_gamut=TypeGamut(system="b", type_name="INT", field_type=FieldType.INTEGER),
        )
        output = render_field_detail(cr)
        assert "Field: test" in output


class TestRenderBoundaryComparison:
    """Tests for boundary comparison table rendering."""

    def test_comparison_table(self, postgres_stage, json_stage):
        report = analyze_boundary(postgres_stage, json_stage)
        output = render_boundary_comparison(postgres_stage, json_stage, report)
        assert "Stage Comparison" in output
        assert "Field" in output
        assert "Source Type" in output
        assert "Dest Type" in output
