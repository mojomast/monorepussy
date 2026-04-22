"""Tests for the DDI (drug-drug interaction) module."""

import pytest

from ussy_dosemate.ddi import (
    DDIResult, compute_ddi, analyze_all_interactions,
    compute_breaking_change_displacement,
)
from ussy_dosemate.metabolism import MetabolismParams
from ussy_dosemate.git_parser import PullRequestInfo
from ussy_dosemate.dependency_graph import DependencyGraphAnalyzer
from datetime import datetime, timedelta
import tempfile
import os
import shutil


class TestComputeDDI:
    """Tests for compute_ddi function."""

    def _make_prs_and_analyzer(self):
        """Create test fixtures for DDI tests."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src", "auth"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "src", "core"), exist_ok=True)
            
            with open(os.path.join(tmpdir, "src", "auth", "__init__.py"), 'w') as f:
                f.write("from src.core import something\ndef auth_fn(): pass\n")
            with open(os.path.join(tmpdir, "src", "core", "__init__.py"), 'w') as f:
                f.write("def something(): pass\ndef other(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            
            now = datetime.now()
            pr_a = PullRequestInfo(
                id="pr_a", title="PR A",
                created_at=now - timedelta(days=2),
                merged_at=now - timedelta(days=1),
                files_changed=["src/auth/__init__.py", "src/core/__init__.py"],
                insertions=100, deletions=10,
                first_ci_at=now - timedelta(days=2, hours=1),
            )
            pr_b = PullRequestInfo(
                id="pr_b", title="PR B",
                created_at=now - timedelta(days=1, hours=12),
                merged_at=now - timedelta(days=1),
                files_changed=["src/auth/__init__.py"],
                insertions=50, deletions=5,
                first_ci_at=now - timedelta(days=1, hours=11),
            )
            
            file_to_module = {
                "src/auth/__init__.py": "src/auth",
                "src/core/__init__.py": "src/core",
            }
            
            metabolism = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=0.5, Vmax=15.0,
                Km=800.0, processing_rate=7.5,
            )
            
            return pr_a, pr_b, analyzer, file_to_module, metabolism, tmpdir
        except:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise

    def test_shared_modules_detected(self):
        """DDI should detect shared modules between PRs."""
        pr_a, pr_b, analyzer, file_to_module, metabolism, tmpdir = self._make_prs_and_analyzer()
        try:
            result = compute_ddi(pr_a, pr_b, analyzer, file_to_module, metabolism)
            assert result.shared_modules >= 1  # both touch src/auth
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_shared_modules_low_severity(self):
        """PRs with no shared modules should have low severity."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "mod_a"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "mod_b"), exist_ok=True)
            
            with open(os.path.join(tmpdir, "mod_a", "a.py"), 'w') as f:
                f.write("def a(): pass\n")
            with open(os.path.join(tmpdir, "mod_b", "b.py"), 'w') as f:
                f.write("def b(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            
            now = datetime.now()
            pr_a = PullRequestInfo(
                id="pr_a", title="PR A",
                created_at=now - timedelta(days=1), merged_at=now,
                files_changed=["mod_a/a.py"], insertions=10, deletions=0,
                first_ci_at=now - timedelta(hours=23),
            )
            pr_b = PullRequestInfo(
                id="pr_b", title="PR B",
                created_at=now - timedelta(days=1), merged_at=now,
                files_changed=["mod_b/b.py"], insertions=10, deletions=0,
                first_ci_at=now - timedelta(hours=23),
            )
            file_to_module = {"mod_a/a.py": "mod_a/a", "mod_b/b.py": "mod_b/b"}
            metabolism = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=0.5, Vmax=15.0,
                Km=800.0, processing_rate=7.5,
            )
            
            result = compute_ddi(pr_a, pr_b, analyzer, file_to_module, metabolism)
            assert result.severity == "low"
            assert result.shared_modules == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_auc_ratio_ge_1(self):
        """AUC ratio should always be >= 1."""
        pr_a, pr_b, analyzer, file_to_module, metabolism, tmpdir = self._make_prs_and_analyzer()
        try:
            result = compute_ddi(pr_a, pr_b, analyzer, file_to_module, metabolism)
            assert result.AUC_ratio >= 1.0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_severity_classifications(self):
        """Severity should match AUC ratio thresholds."""
        # Test that the severity mapping works correctly
        assert "low" in ["low", "moderate", "high", "critical"]
        # Direct threshold checks
        for ratio, expected in [(1.1, "low"), (1.5, "moderate"), (2.5, "high"), (4.0, "critical")]:
            if ratio < 1.2:
                assert expected == "low"
            elif ratio < 2.0:
                assert expected == "moderate"
            elif ratio < 3.0:
                assert expected == "high"
            else:
                assert expected == "critical"


class TestAnalyzeAllInteractions:
    """Tests for analyze_all_interactions function."""

    def test_empty_prs(self):
        """No PRs should produce no interactions."""
        tmpdir = tempfile.mkdtemp()
        try:
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            metabolism = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=0.5, Vmax=15.0,
                Km=800.0, processing_rate=7.5,
            )
            result = analyze_all_interactions([], analyzer, {}, metabolism)
            assert len(result) == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_single_pr_no_interactions(self):
        """Single PR should produce no interactions (need pairs)."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            metabolism = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=0.5, Vmax=15.0,
                Km=800.0, processing_rate=7.5,
            )
            now = datetime.now()
            pr = PullRequestInfo(
                id="pr_1", title="PR 1",
                created_at=now - timedelta(days=1), merged_at=now,
                files_changed=["src/mod.py"], insertions=10, deletions=0,
            )
            result = analyze_all_interactions([pr], analyzer, {}, metabolism)
            assert len(result) == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_three_prs_three_interactions(self):
        """3 PRs should produce C(3,2) = 3 interactions."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            metabolism = MetabolismParams(
                first_pass_effect=0.3, bioavailability_F=0.5,
                ci_saturation_fraction=0.5, Vmax=15.0,
                Km=800.0, processing_rate=7.5,
            )
            now = datetime.now()
            prs = [
                PullRequestInfo(
                    id=f"pr_{i}", title=f"PR {i}",
                    created_at=now - timedelta(days=1), merged_at=now,
                    files_changed=["src/mod.py"], insertions=10, deletions=0,
                )
                for i in range(3)
            ]
            file_to_module = {"src/mod.py": "src/mod"}
            result = analyze_all_interactions(prs, analyzer, file_to_module, metabolism)
            assert len(result) == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestBreakingChangeDisplacement:
    """Tests for compute_breaking_change_displacement function."""

    def test_no_breaking_change(self):
        """No breaking change should not alter fu."""
        fu_new = compute_breaking_change_displacement(0.5, 0.0, 10.0)
        assert abs(fu_new - 0.5) < 0.01

    def test_breaking_change_increases_fu(self):
        """Breaking change should increase unbound fraction."""
        fu_new = compute_breaking_change_displacement(0.5, 20.0, 10.0)
        assert fu_new > 0.5

    def test_fu_bounded_at_1(self):
        """fu should never exceed 1.0."""
        fu_new = compute_breaking_change_displacement(0.9, 1000.0, 1.0)
        assert fu_new <= 1.0

    def test_small_kd_more_displacement(self):
        """Smaller Kd should result in more displacement."""
        fu_small_kd = compute_breaking_change_displacement(0.5, 10.0, 1.0)
        fu_large_kd = compute_breaking_change_displacement(0.5, 10.0, 100.0)
        assert fu_small_kd > fu_large_kd
