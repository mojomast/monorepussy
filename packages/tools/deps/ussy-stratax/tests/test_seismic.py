"""Tests for seismic analysis."""
import pytest
from strata.models import ProbeResult, VersionProbeResult
from strata.analysis.seismic import SeismicAnalyzer


def make_version_results(pass_patterns):
    """Create VersionProbeResult list from pass/fail patterns."""
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


class TestSeismicAnalyzer:
    def setup_method(self):
        self.analyzer = SeismicAnalyzer()

    def test_empty_results(self):
        report = self.analyzer.analyze_function("pkg", "fn", [])
        assert report.total_quakes == 0
        assert report.versions_scanned == 0
        assert report.quakes_per_version == 0.0
        assert report.hazard_level == "dormant"

    def test_no_quakes(self):
        results = make_version_results([
            [True, True],
            [True, True],
            [True, True],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.total_quakes == 0
        assert report.hazard_level == "dormant"

    def test_every_version_quake(self):
        # Every version changes = maximum quakes
        results = make_version_results([
            [True],
            [False],
            [True],
            [False],
            [True],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.total_quakes == 4  # 4 transitions across 5 versions
        assert report.hazard_level == "catastrophic"

    def test_few_quakes(self):
        results = make_version_results([
            [True, True],
            [True, True],
            [True, False],  # One change
            [True, False],
            [True, False],
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.total_quakes == 1
        assert report.hazard_level in ("dormant", "minor", "moderate")

    def test_recent_quakes_window(self):
        # Recent quakes (last 5 versions) should be counted
        results = make_version_results([
            [True],   # 0
            [True],   # 1
            [True],   # 2
            [True],   # 3
            [True],   # 4
            [True],   # 5
            [True],   # 6
            [False],  # 7 - recent
            [True],   # 8 - recent
            [False],  # 9 - recent
        ])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.versions_scanned == 10
        # Recent quakes in the last 5 versions
        assert report.recent_quakes >= 2

    def test_analyze_package(self):
        version_data = {
            "fn1": make_version_results([[True], [True], [True]]),
            "fn2": make_version_results([[True], [False], [True]]),
        }
        reports = self.analyzer.analyze_package("pkg", version_data)
        assert len(reports) == 2
        fn1 = next(r for r in reports if r.function == "fn1")
        fn2 = next(r for r in reports if r.function == "fn2")
        assert fn1.total_quakes == 0
        assert fn2.total_quakes == 2  # True→False, False→True

    def test_custom_recent_window(self):
        analyzer = SeismicAnalyzer(recent_window=3)
        results = make_version_results([
            [True],
            [False],
            [True],
            [False],
            [True],
        ])
        report = analyzer.analyze_function("pkg", "fn", results)
        # Only last 3 versions: [False], [True], [False]
        # Transitions: False→True, True→False = 2 recent quakes
        assert report.recent_quakes >= 2
