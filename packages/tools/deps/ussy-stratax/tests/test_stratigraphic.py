"""Tests for stratigraphic analysis (integration)."""
import pytest
from ussy_stratax.models import ProbeResult, VersionProbeResult
from ussy_stratax.analysis.stratigraphic import StratigraphicAnalyzer


def make_version_results(version_data):
    """Create version results from a dict of {version: [pass/fail list]}."""
    results = []
    for version, passes in version_data.items():
        probe_results = [
            ProbeResult(f"probe_{j}", "pkg", version, passed=p)
            for j, p in enumerate(passes)
        ]
        results.append(
            VersionProbeResult(package="pkg", version=version, results=probe_results)
        )
    return results


class TestStratigraphicAnalyzer:
    def setup_method(self):
        self.analyzer = StratigraphicAnalyzer()

    def test_stable_package(self):
        version_data = {
            "func_a": make_version_results({
                "1.0.0": [True, True],
                "1.1.0": [True, True],
                "1.2.0": [True, True],
                "1.3.0": [True, True],
                "1.4.0": [True, True],
            }),
            "func_b": make_version_results({
                "1.0.0": [True],
                "1.1.0": [True],
                "1.2.0": [True],
                "1.3.0": [True],
                "1.4.0": [True],
            }),
        }
        column = self.analyzer.analyze("pkg", version_data)
        assert column.package == "pkg"
        assert len(column.bedrock_reports) == 2
        # Without dates, 5 stable versions = "stable" tier (85), not "bedrock" (90+)
        assert all(r.stability_tier in ("bedrock", "stable") for r in column.bedrock_reports)
        assert len(column.fault_lines) == 0
        assert not any(e.is_eroding for e in column.erosion_reports)

    def test_mixed_stability(self):
        version_data = {
            "bedrock_fn": make_version_results({
                "1.0.0": [True],
                "1.1.0": [True],
                "1.2.0": [True],
                "1.3.0": [True],
                "1.4.0": [True],
            }),
            "volatile_fn": make_version_results({
                "1.0.0": [True],
                "1.1.0": [False],
                "1.2.0": [True],
                "1.3.0": [False],
                "1.4.0": [True],
            }),
        }
        column = self.analyzer.analyze("pkg", version_data)
        assert len(column.bedrock_reports) == 2
        # Should have fault lines between bedrock and volatile
        assert len(column.fault_lines) >= 1
        # bedrock_fn should have higher score than volatile_fn
        bedrock_fn = next(r for r in column.bedrock_reports if r.function == "bedrock_fn")
        volatile_fn = next(r for r in column.bedrock_reports if r.function == "volatile_fn")
        assert bedrock_fn.bedrock_score > volatile_fn.bedrock_score

    def test_eroding_function(self):
        version_data = {
            "declining_fn": make_version_results({
                "1.0.0": [True, True],
                "1.1.0": [True, True],
                "1.2.0": [True, False],
                "1.3.0": [True, False],
                "1.4.0": [False, False],
            }),
        }
        column = self.analyzer.analyze("pkg", version_data)
        erosion = next(e for e in column.erosion_reports if e.function == "declining_fn")
        assert erosion.is_eroding is True

    def test_bedrock_reports_sorted_by_score(self):
        version_data = {
            "mid_fn": make_version_results({
                "1.0.0": [True],
                "1.1.0": [True],
                "1.2.0": [False],
            }),
            "top_fn": make_version_results({
                "1.0.0": [True],
                "1.1.0": [True],
                "1.2.0": [True],
            }),
            "low_fn": make_version_results({
                "1.0.0": [True],
                "1.1.0": [False],
                "1.2.0": [False],
            }),
        }
        column = self.analyzer.analyze("pkg", version_data)
        scores = [r.bedrock_score for r in column.bedrock_reports]
        assert scores == sorted(scores, reverse=True)

    def test_custom_parameters(self):
        analyzer = StratigraphicAnalyzer(
            stability_threshold=0.90,
            recent_window=3,
            score_gap_threshold=30.0,
            erosion_threshold=-0.05,
        )
        version_data = {
            "fn1": make_version_results({
                "1.0.0": [True],
                "1.1.0": [True],
                "1.2.0": [True],
            }),
        }
        column = analyzer.analyze("pkg", version_data)
        assert len(column.bedrock_reports) == 1
