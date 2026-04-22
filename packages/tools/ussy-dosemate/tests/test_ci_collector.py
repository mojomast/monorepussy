"""Tests for the CI collector module."""

import os
import tempfile
import shutil

import pytest

from ussy_dosemate.ci_collector import CICollector, CIMetrics
from ussy_dosemate.git_parser import GitHistoryParser


class TestCICollector:
    """Tests for CICollector."""

    def test_collect_from_real_repo(self, temp_repo):
        """Should collect CI metrics from a real repo."""
        parser = GitHistoryParser(temp_repo)
        collector = CICollector(parser)
        metrics = collector.collect()
        assert isinstance(metrics, CIMetrics)
        assert metrics.max_ci_capacity > 0
        assert metrics.half_saturation_size > 0

    def test_empty_repo_metrics(self):
        """Should handle empty repo gracefully."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.system(f'cd {tmpdir} && git init && git config user.email "t@t.com" && git config user.name "T"')
            parser = GitHistoryParser(tmpdir)
            collector = CICollector(parser)
            metrics = collector.collect()
            assert metrics.pr_arrival_rate == 0
            assert metrics.max_ci_capacity > 0  # defaults
        finally:
            shutil.rmtree(tmpdir)

    def test_default_vmax_reasonable(self):
        """Default Vmax should be reasonable (5-50 PRs/day)."""
        assert 5 <= CICollector.DEFAULT_VMAX <= 50

    def test_default_km_reasonable(self):
        """Default Km should be reasonable (100-5000 lines)."""
        assert 100 <= CICollector.DEFAULT_KM <= 5000

    def test_lint_pass_rate_bounded(self, temp_repo):
        """Lint pass rate should be in [0, 1]."""
        parser = GitHistoryParser(temp_repo)
        collector = CICollector(parser)
        metrics = collector.collect()
        assert 0.0 <= metrics.lint_pass_rate <= 1.0

    def test_review_survival_rate_bounded(self, temp_repo):
        """Review survival rate should be in [0, 1]."""
        parser = GitHistoryParser(temp_repo)
        collector = CICollector(parser)
        metrics = collector.collect()
        assert 0.0 <= metrics.review_survival_rate <= 1.0
