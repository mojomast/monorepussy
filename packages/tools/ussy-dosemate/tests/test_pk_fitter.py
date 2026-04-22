"""Tests for the PK Fitter module (integration tests)."""

import json
import os
import tempfile
import shutil

import pytest

from ussy_dosemate.pk_fitter import PKModelFitter, report_to_dict, ChangePK, PKReport
from ussy_dosemate.absorption import compute_absorption
from ussy_dosemate.distribution import compute_distribution
from ussy_dosemate.excretion import compute_excretion
from ussy_dosemate.metabolism import compute_metabolism
from ussy_dosemate.ci_collector import CIMetrics


class TestPKModelFitter:
    """Integration tests for PKModelFitter."""

    def test_analyze_returns_report(self, temp_repo):
        """analyze() should return a PKReport."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        assert isinstance(report, PKReport)

    def test_report_has_change_pk(self, temp_repo):
        """Report should have change_pk entries."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        # May or may not have PRs depending on merge commits
        assert isinstance(report.change_pk, dict)

    def test_report_has_interactions(self, temp_repo):
        """Report should have interactions list."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        assert isinstance(report.interactions, list)

    def test_report_has_steady_state(self, temp_repo):
        """Report should have steady-state params."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        assert report.steady_state is not None

    def test_report_has_dose_plan(self, temp_repo):
        """Report should have dose plan."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        assert report.dose_plan is not None


class TestReportToDict:
    """Tests for report_to_dict serialization."""

    def test_serializable(self, temp_repo):
        """Output should be JSON-serializable."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        data = report_to_dict(report)
        # Should not raise
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_has_required_keys(self, temp_repo):
        """Output should have all required top-level keys."""
        fitter = PKModelFitter(temp_repo)
        report = fitter.analyze()
        data = report_to_dict(report)
        assert "change_pk" in data
        assert "interactions" in data
        assert "steady_state" in data
        assert "dose_plan" in data


class TestPropertyInvariants:
    """Property-based invariants that should always hold."""

    def test_half_life_always_positive(self):
        """Half-life should always be > 0."""
        from ussy_dosemate.distribution import DistributionParams
        from ussy_dosemate.excretion import compute_excretion
        
        for Vd in [1, 5, 10, 50, 100]:
            dist = DistributionParams(
                Vd=Vd, Kp=1.0, fu=0.5,
                total_dependent_modules=Vd,
                central_compartment_size=max(Vd // 5, 1),
                peripheral_compartment_size=Vd - max(Vd // 5, 1),
            )
            result = compute_excretion(dist)
            assert result.t_half > 0

    def test_bioavailability_0_to_1(self):
        """Bioavailability should always be in [0, 1]."""
        for f_abs in [0.1, 0.5, 0.9]:
            for f_lint in [0.7, 0.85, 0.95]:
                for f_review in [0.6, 0.78, 0.9]:
                    ci = CIMetrics(
                        pr_arrival_rate=5.0, max_ci_capacity=15.0,
                        half_saturation_size=800.0, ci_thoroughness=5.0,
                        avg_pr_size_lines=200.0, avg_review_time_hours=24.0,
                        merge_rate=0.8, lint_pass_rate=f_lint,
                        review_survival_rate=f_review,
                    )
                    result = compute_metabolism(ci, fraction_absorbed=f_abs)
                    assert 0.0 <= result.bioavailability_F <= 1.0

    def test_vd_always_positive(self):
        """Vd should always be > 0."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            from ussy_dosemate.dependency_graph import DependencyGraphAnalyzer
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            
            for files in [[], ["src/mod.py"], ["src/mod.py", "nonexistent.py"]]:
                result = compute_distribution(
                    files, analyzer, {"src/mod.py": "src/mod"},
                )
                assert result.Vd > 0
        finally:
            shutil.rmtree(tmpdir)

    def test_accumulation_factor_ge_1(self):
        """Accumulation factor R should always be >= 1."""
        from ussy_dosemate.excretion import ExcretionParams
        from ussy_dosemate.steady_state import compute_steady_state
        
        for ke in [0.001, 0.01, 0.1, 1.0, 10.0]:
            for tau in [0.5, 1.0, 2.0, 4.0]:
                excretion = ExcretionParams(CL=ke, ke=ke, t_half=0.693 / ke)
                result = compute_steady_state(0.5, 10.0, ke, excretion, tau)
                assert result.accumulation_factor_R >= 1.0
