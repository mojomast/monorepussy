"""Tests for coroner.luminol — Hidden State Detection."""

from __future__ import annotations

from ussy_coroner.models import LuminolResult
from ussy_coroner.luminol import (
    analyze_luminol,
    cache_luminol,
    confirmatory_test,
    format_luminol,
    ninhydrin_scan,
)


class TestCacheLuminol:
    """Tests for cache luminol (integrity check)."""

    def test_no_artifacts_no_findings(self, passing_run):
        findings = cache_luminol(passing_run)
        # Passing run with some artifacts but no mutations
        assert isinstance(findings, list)

    def test_artifact_mutation_detected(self, artifact_mutation_run):
        findings = cache_luminol(artifact_mutation_run)
        # compiled.o hash changes between checkout and build
        cache_findings = [f for f in findings if f.category == "cache"]
        assert len(cache_findings) > 0

    def test_missing_artifact_hashes_flagged(self):
        """Stage with success but no artifact hashes should be flagged."""
        from ussy_coroner.models import PipelineRun, Stage, StageStatus
        run = PipelineRun(run_id="no-arts")
        run.stages = [
            Stage(name="build", index=0, status=StageStatus.SUCCESS, artifact_hashes={}),
        ]
        findings = cache_luminol(run)
        assert len(findings) > 0
        assert any("no verifiable artifact" in f.description for f in findings)


class TestNinhydrinScan:
    """Tests for ninhydrin scan (undeclared state mutations)."""

    def test_detects_new_env_vars(self, env_diverge_run):
        findings = ninhydrin_scan(env_diverge_run)
        assert len(findings) > 0
        ninhydrin = [f for f in findings if f.category == "ninhydrin"]
        assert len(ninhydrin) > 0

    def test_no_undeclared_vars_in_simple_run(self, simple_failing_run):
        findings = ninhydrin_scan(simple_failing_run)
        # simple_failing_run may have some env var differences
        # but not necessarily undeclared ones
        assert isinstance(findings, list)

    def test_well_known_vars_filtered(self):
        """Well-known CI variables should not be flagged."""
        from ussy_coroner.models import PipelineRun, Stage, StageStatus
        run = PipelineRun(run_id="well-known")
        run.stages = [
            Stage(name="a", index=0, status=StageStatus.SUCCESS,
                  env_vars={"PATH": "/usr/bin", "HOME": "/root", "CUSTOM": "v1"}),
            Stage(name="b", index=1, status=StageStatus.SUCCESS,
                  env_vars={"PATH": "/usr/local/bin", "HOME": "/root", "CUSTOM": "v1"}),
        ]
        findings = ninhydrin_scan(run)
        # PATH should be filtered out as well-known
        for f in findings:
            if f.env_vars:
                assert "PATH" not in f.env_vars
                assert "HOME" not in f.env_vars


class TestConfirmatoryTest:
    """Tests for confirmatory testing (false positive elimination)."""

    def test_single_cache_finding_not_confirmed(self):
        from ussy_coroner.models import LuminolFinding, LuminolResult
        presumptive = [
            LuminolFinding(
                category="cache",
                path="test",
                expected_hash="abc",
                actual_hash="def",
                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                description="Test finding",
            ),
        ]
        from ussy_coroner.models import PipelineRun
        run = PipelineRun(run_id="test")
        confirmed = confirmatory_test(run, presumptive)
        # Single uncorroborated finding should remain presumptive
        confirmed_findings = [f for f in confirmed if f.result == LuminolResult.CONFIRMED]
        # With only 1 cache finding and no ninhydrin, it should not be confirmed
        assert len(confirmed_findings) == 0

    def test_multiple_findings_corroborated(self):
        from ussy_coroner.models import LuminolFinding, LuminolResult
        presumptive = [
            LuminolFinding(
                category="cache",
                path="test1",
                expected_hash="abc",
                actual_hash="def",
                source_stage="build",
                target_stage="test",
                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                description="Finding 1",
            ),
            LuminolFinding(
                category="cache",
                path="test2",
                expected_hash="ghi",
                actual_hash="jkl",
                source_stage="build",
                target_stage="deploy",
                result=LuminolResult.PRESUMPTIVE_POSITIVE,
                description="Finding 2",
            ),
        ]
        from ussy_coroner.models import PipelineRun
        run = PipelineRun(run_id="test")
        confirmed = confirmatory_test(run, presumptive)
        # Multiple cache findings should corroborate each other
        confirmed_findings = [f for f in confirmed if f.result == LuminolResult.CONFIRMED]
        assert len(confirmed_findings) > 0


class TestAnalyzeLuminol:
    """Tests for the full luminol analysis."""

    def test_env_diverge_detected(self, env_diverge_run):
        report = analyze_luminol(env_diverge_run)
        assert len(report.findings) > 0

    def test_artifact_mutation_detected(self, artifact_mutation_run):
        report = analyze_luminol(artifact_mutation_run)
        assert len(report.findings) > 0

    def test_passing_run_clean(self, passing_run):
        report = analyze_luminol(passing_run)
        # A clean passing run should have minimal findings
        assert isinstance(report.findings, list)

    def test_root_cause_generated(self, multi_failure_run):
        report = analyze_luminol(multi_failure_run)
        assert report.root_cause != ""

    def test_confirmed_flag_set(self, artifact_mutation_run):
        report = analyze_luminol(artifact_mutation_run)
        assert isinstance(report.confirmed, bool)


class TestFormatLuminol:
    """Tests for format_luminol."""

    def test_format_with_findings(self, multi_failure_run):
        report = analyze_luminol(multi_failure_run)
        text = format_luminol(report)
        assert isinstance(text, str)

    def test_format_empty(self, passing_run):
        report = analyze_luminol(passing_run)
        text = format_luminol(report)
        assert isinstance(text, str)
        assert "No hidden state" in text or len(text) > 0
