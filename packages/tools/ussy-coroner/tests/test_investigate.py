"""Tests for coroner.investigate — Full Forensic Investigation."""

from __future__ import annotations

from coroner.investigate import investigate
from coroner.models import Investigation, VelocityClass


class TestInvestigate:
    """Tests for the full forensic investigation."""

    def test_investigation_returns_result(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert isinstance(inv, Investigation)
        assert inv.run_id == "test-run-1"

    def test_investigation_has_traces(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.trace_result is not None
        assert len(inv.trace_result.forward_traces) > 0

    def test_investigation_has_spatter(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.spatter_result is not None
        assert len(inv.spatter_result.stains) > 0

    def test_investigation_has_luminol(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.luminol_report is not None

    def test_investigation_has_custody(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.custody_chain is not None
        assert len(inv.custody_chain.entries) == 3

    def test_investigation_has_summary(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.summary != ""

    def test_investigation_confidence(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert 0.0 <= inv.confidence <= 1.0

    def test_investigation_timestamp_utc(self, simple_failing_run):
        inv = investigate(simple_failing_run)
        assert inv.timestamp.tzinfo is not None

    def test_investigation_with_comparison(self, simple_failing_run, build_38_run):
        inv = investigate(simple_failing_run, compare_runs=[build_38_run])
        assert len(inv.striation_matches) > 0
        assert inv.custody_comparison is not None

    def test_passing_run_investigation(self, passing_run):
        inv = investigate(passing_run)
        assert inv.run_id == "passing-run"
        assert len(inv.spatter_result.stains) == 0

    def test_multi_failure_investigation(self, multi_failure_run):
        inv = investigate(multi_failure_run)
        assert len(inv.spatter_result.stains) >= 2
        assert inv.confidence > 0

    def test_investigation_no_bidirectional(self, simple_failing_run):
        inv = investigate(simple_failing_run, bidirectional=False)
        assert len(inv.trace_result.reverse_traces) == 0


class TestInvestigationReport:
    """Tests for investigation report generation."""

    def test_report_generation(self, simple_failing_run):
        from coroner.report import generate_report
        inv = investigate(simple_failing_run)
        report = generate_report(inv)
        assert "AUTOPSY REPORT" in report
        assert "EXECUTIVE SUMMARY" in report
        assert "TRACE EVIDENCE" in report
        assert "ERROR SPATTER" in report
        assert "LUMINOL" in report
        assert "CHAIN OF CUSTODY" in report

    def test_report_with_striation(self, simple_failing_run, build_38_run):
        from coroner.report import generate_report
        inv = investigate(simple_failing_run, compare_runs=[build_38_run])
        report = generate_report(inv)
        assert "STRIATION" in report

    def test_report_format_complete(self, multi_failure_run):
        from coroner.report import generate_report
        inv = investigate(multi_failure_run)
        report = generate_report(inv)
        assert "END OF AUTOPSY REPORT" in report
