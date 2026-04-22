"""Tests for bedrock analysis."""
import pytest
from ussy_stratax.models import ProbeResult, VersionProbeResult, BedrockReport
from ussy_stratax.analysis.bedrock import BedrockAnalyzer


def make_version_results(pass_patterns):
    """Create VersionProbeResult list from pass/fail patterns.
    
    Args:
        pass_patterns: List of lists of booleans. Each inner list is
            [probe1_passed, probe2_passed, ...] for one version.
    """
    results = []
    for i, pattern in enumerate(pass_patterns):
        version = f"1.{i}.0"
        probe_results = [
            ProbeResult(f"probe_{j}", "pkg", version, passed=p)
            for j, p in enumerate(pattern)
        ]
        results.append(
            VersionProbeResult(package="pkg", version=version, results=probe_results)
        )
    return results


class TestBedrockAnalyzer:
    def setup_method(self):
        self.analyzer = BedrockAnalyzer()

    def test_empty_version_results(self):
        report = self.analyzer.analyze_function("pkg", "fn", [])
        assert report.bedrock_score == 0.0
        assert report.versions_stable == 0
        assert report.versions_total == 0
        assert report.stability_tier == "deprecated"

    def test_all_stable_versions(self):
        # 5 versions, all probes pass every time
        results = make_version_results([
            [True, True],
            [True, True],
            [True, True],
            [True, True],
            [True, True],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.bedrock_score >= 80  # 85 without dates, 90+ with dates
        assert report.stability_tier in ("bedrock", "stable")
        assert report.versions_stable == 5
        assert report.versions_total == 5

    def test_all_unstable_versions(self):
        # Alternating pass/fail — very unstable
        results = make_version_results([
            [True, False],
            [False, True],
            [True, False],
            [False, True],
            [True, False],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.bedrock_score < 50

    def test_gradually_stabilizing(self):
        # Starts unstable, becomes stable
        results = make_version_results([
            [True, False],
            [False, True],
            [True, True],
            [True, True],
            [True, True],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        # Should have moderate score — some stable, some not
        assert 30 < report.bedrock_score < 90
        # Last 3 are all stable
        assert report.versions_stable >= 3

    def test_with_version_dates(self):
        results = make_version_results([
            [True, True],
            [True, True],
            [True, True],
        ])
        dates = {
            "1.0.0": "2021-01-01T00:00:00Z",
            "1.1.0": "2022-01-01T00:00:00Z",
            "1.2.0": "2023-01-01T00:00:00Z",
        }
        report = self.analyzer.analyze_function("pkg", "fn", results, dates)
        assert report.years_stable > 0
        assert report.bedrock_score >= 90  # All stable

    def test_analyze_package(self):
        version_data = {
            "func1": make_version_results([[True], [True], [True]]),
            "func2": make_version_results([[True], [False], [True]]),
        }
        reports = self.analyzer.analyze_package("pkg", version_data)
        assert len(reports) == 2
        # func1 is more stable than func2
        func1_report = next(r for r in reports if r.function == "func1")
        func2_report = next(r for r in reports if r.function == "func2")
        assert func1_report.bedrock_score > func2_report.bedrock_score

    def test_single_version(self):
        results = make_version_results([[True, True]])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.versions_total == 1
        assert report.versions_stable == 1
        # With only one version, no transitions = high consistency
        assert report.bedrock_score > 50

    def test_consecutive_stable_from_end(self):
        # Last 3 stable, first 2 not
        results = make_version_results([
            [True, False],
            [False, True],
            [True, True],
            [True, True],
            [True, True],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        # Should be stable because recent versions are consistent
        assert report.versions_stable >= 3
