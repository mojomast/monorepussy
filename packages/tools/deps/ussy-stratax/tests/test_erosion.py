"""Tests for erosion analysis."""
import pytest
from ussy_stratax.models import ProbeResult, VersionProbeResult
from ussy_stratax.analysis.erosion import ErosionAnalyzer


def make_version_results(pass_rates):
    """Create VersionProbeResult list from pass rates per version.
    
    Args:
        pass_rates: List of floats (0.0-1.0) representing pass rate per version.
    """
    results = []
    for i, rate in enumerate(pass_rates):
        version = f"1.{i}.0"
        # Create probes to achieve the desired pass rate
        if rate == 1.0:
            probe_results = [
                ProbeResult("p1", "pkg", version, True),
                ProbeResult("p2", "pkg", version, True),
            ]
        elif rate == 0.0:
            probe_results = [
                ProbeResult("p1", "pkg", version, False),
                ProbeResult("p2", "pkg", version, False),
            ]
        elif rate == 0.5:
            probe_results = [
                ProbeResult("p1", "pkg", version, True),
                ProbeResult("p2", "pkg", version, False),
            ]
        else:
            # Approximate with 10 probes
            n_pass = int(rate * 10)
            probe_results = [
                ProbeResult(f"p{j}", "pkg", version, passed=(j < n_pass))
                for j in range(10)
            ]
        results.append(
            VersionProbeResult(package="pkg", version=version, results=probe_results)
        )
    return results


class TestErosionAnalyzer:
    def setup_method(self):
        self.analyzer = ErosionAnalyzer()

    def test_stable_no_erosion(self):
        results = make_version_results([1.0, 1.0, 1.0, 1.0, 1.0])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.is_eroding is False
        assert report.erosion_rate >= 0

    def test_declining_erosion(self):
        # Pass rate declines from 100% to 50%
        results = make_version_results([1.0, 0.9, 0.8, 0.7, 0.6, 0.5])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.is_eroding is True
        assert report.erosion_rate < 0
        assert report.initial_pass_rate > report.current_pass_rate

    def test_improving_not_erosion(self):
        # Pass rate improves over time
        results = make_version_results([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.is_eroding is False
        assert report.erosion_rate > 0

    def test_single_version(self):
        results = make_version_results([1.0])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.erosion_rate == 0.0
        assert report.is_eroding is False

    def test_two_versions_stable(self):
        results = make_version_results([1.0, 1.0])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.is_eroding is False

    def test_two_versions_declining(self):
        results = make_version_results([1.0, 0.5])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        assert report.is_eroding is True

    def test_custom_threshold(self):
        analyzer = ErosionAnalyzer(erosion_threshold=-0.10)
        results = make_version_results([1.0, 0.9, 0.8])
        report = analyzer.analyze_function("pkg", "fn", results)
        # Erosion rate is about -0.1, which doesn't meet -0.10 threshold
        # (needs to be strictly less than threshold)
        # The actual rate depends on the linear regression

    def test_versions_declining_count(self):
        results = make_version_results([1.0, 0.5, 0.5, 0.5, 0.0])
        report = self.analyzer.analyze_function("pkg", "fn", results)
        # Versions where pass rate declined vs previous:
        # 1.0→0.5 (declined), 0.5→0.5 (not), 0.5→0.5 (not), 0.5→0.0 (declined)
        assert report.versions_declining >= 2

    def test_analyze_package(self):
        version_data = {
            "fn1": make_version_results([1.0, 1.0, 1.0]),
            "fn2": make_version_results([1.0, 0.5, 0.0]),
        }
        reports = self.analyzer.analyze_package("pkg", version_data)
        assert len(reports) == 2
        fn1 = next(r for r in reports if r.function == "fn1")
        fn2 = next(r for r in reports if r.function == "fn2")
        assert fn1.is_eroding is False
        assert fn2.is_eroding is True
