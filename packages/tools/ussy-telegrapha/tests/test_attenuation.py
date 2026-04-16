"""Tests for attenuation module."""

import math
import pytest

from telegrapha.models import Hop, Route
from telegrapha.attenuation import (
    compute_fidelity,
    check_distortionless,
    find_loading_coil_position,
    analyze_attenuation,
    format_attenuation_report,
    attenuation_to_dict,
    DEFAULT_FIDELITY_THRESHOLD,
)


class TestComputeFidelity:
    """Tests for compute_fidelity function."""

    def test_perfect_fidelity_no_degradation(self):
        route = Route(name="perfect", hops=[
            Hop(name="h1", degradation=0.0),
            Hop(name="h2", degradation=0.0),
        ])
        assert compute_fidelity(route) == 1.0

    def test_single_hop_degradation(self):
        route = Route(name="single", hops=[
            Hop(name="h1", degradation=0.05),
        ])
        assert compute_fidelity(route) == pytest.approx(0.95)

    def test_multiplicative_decay(self):
        route = Route(name="multi", hops=[
            Hop(name="h1", degradation=0.01),
            Hop(name="h2", degradation=0.02),
            Hop(name="h3", degradation=0.03),
        ])
        expected = (1 - 0.01) * (1 - 0.02) * (1 - 0.03)
        assert compute_fidelity(route) == pytest.approx(expected)

    def test_full_degradation(self):
        route = Route(name="dead", hops=[
            Hop(name="h1", degradation=1.0),
        ])
        assert compute_fidelity(route) == pytest.approx(0.0)

    def test_empty_route_fidelity(self):
        route = Route(name="empty", hops=[])
        assert compute_fidelity(route) == 1.0

    def test_simple_route_fixture(self, simple_route):
        fidelity = compute_fidelity(simple_route)
        expected = (1 - 0.005) * (1 - 0.030) * (1 - 0.020) * (1 - 0.040)
        assert fidelity == pytest.approx(expected, rel=1e-6)


class TestCheckDistortionless:
    """Tests for the Heaviside condition check."""

    def test_distortionless_route(self, distortionless_route):
        assert check_distortionless(distortionless_route) is True

    def test_distorted_route(self, distorted_route):
        assert check_distortionless(distorted_route) is False

    def test_custom_tolerance(self, distorted_route):
        # With very large tolerance, even distorted routes pass
        assert check_distortionless(distorted_route, tolerance=1.0) is True

    def test_no_ser_deser_data(self, simple_route):
        # Without ser/deser data, difference is 0, so distortionless
        assert check_distortionless(simple_route) is True


class TestFindLoadingCoilPosition:
    """Tests for loading coil position finder."""

    def test_no_coil_needed(self):
        route = Route(name="healthy", hops=[
            Hop(name="h1", degradation=0.01),
            Hop(name="h2", degradation=0.01),
        ])
        assert find_loading_coil_position(route, threshold=0.90) is None

    def test_coil_needed(self, simple_route):
        # With 4 hops at 0.005, 0.03, 0.02, 0.04, fidelity drops below 0.90
        pos = find_loading_coil_position(simple_route, threshold=0.95)
        assert pos is not None
        assert pos >= 1


class TestAnalyzeAttenuation:
    """Tests for full attenuation analysis."""

    def test_simple_route_analysis(self, simple_route):
        result = analyze_attenuation(simple_route)
        assert result.fidelity < 1.0
        assert result.cumulative_degradation > 0
        assert len(result.route.hops) == 4

    def test_below_threshold_warning(self, simple_route):
        result = analyze_attenuation(simple_route, threshold=0.95)
        assert len(result.warnings) > 0
        assert any("threshold" in w.lower() for w in result.warnings)

    def test_above_threshold_no_warning(self):
        route = Route(name="good", hops=[
            Hop(name="h1", degradation=0.001),
            Hop(name="h2", degradation=0.001),
        ])
        result = analyze_attenuation(route, threshold=0.90)
        assert not any("threshold" in w.lower() for w in result.warnings)

    def test_high_degradation_recommendations(self, simple_route):
        result = analyze_attenuation(simple_route)
        # hop2 (0.03) and hop4 (0.04) should generate recommendations
        assert len(result.recommendations) > 0

    def test_empty_route(self, empty_route):
        result = analyze_attenuation(empty_route)
        assert result.fidelity == 1.0
        assert result.cumulative_degradation == 0.0

    def test_distortionless_route(self, distortionless_route):
        result = analyze_attenuation(distortionless_route)
        assert result.is_distortionless is True

    def test_distorted_route(self, distorted_route):
        result = analyze_attenuation(distorted_route)
        assert result.is_distortionless is False


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_contains_route_info(self, simple_route):
        result = analyze_attenuation(simple_route)
        report = format_attenuation_report(result)
        assert "test-route" in report
        assert "4 hops" in report

    def test_report_contains_fidelity(self, simple_route):
        result = analyze_attenuation(simple_route)
        report = format_attenuation_report(result)
        assert "Fidelity at sink:" in report

    def test_report_json_serializable(self, simple_route):
        import json
        result = analyze_attenuation(simple_route)
        data = attenuation_to_dict(result)
        # Should not raise
        json_str = json.dumps(data)
        assert json_str


class TestAttenuationToDict:
    """Tests for JSON serialization."""

    def test_dict_has_required_keys(self, simple_route):
        result = analyze_attenuation(simple_route)
        data = attenuation_to_dict(result)
        assert "route" in data
        assert "hop_count" in data
        assert "fidelity" in data
        assert "is_distortionless" in data
        assert "warnings" in data
        assert "recommendations" in data
        assert "hops" in data
