"""Tests for relay chain module."""

import math
import pytest

from telegrapha.models import Hop, Route
from telegrapha.relay_chain import (
    compute_required_per_hop,
    compute_series_reliability,
    find_weakest_link,
    compute_parallel_reliability,
    analyze_relay_chain,
    format_relay_chain_report,
    relay_chain_to_dict,
)


class TestComputeRequiredPerHop:
    """Tests for per-hop reliability budget computation."""

    def test_single_hop(self):
        assert compute_required_per_hop(0.999, 1) == pytest.approx(0.999)

    def test_two_hops(self):
        result = compute_required_per_hop(0.999, 2)
        expected = 0.999 ** 0.5
        assert result == pytest.approx(expected)

    def test_three_hops(self):
        result = compute_required_per_hop(0.999, 3)
        expected = 0.999 ** (1/3)
        assert result == pytest.approx(expected)

    def test_zero_hops(self):
        assert compute_required_per_hop(0.999, 0) == 0.999

    def test_high_sla(self):
        result = compute_required_per_hop(0.99999, 5)
        assert result > 0.99999  # Per-hop must be higher than end-to-end


class TestComputeSeriesReliability:
    """Tests for series reliability computation."""

    def test_perfect_reliability(self):
        route = Route(name="perfect", hops=[
            Hop(name="h1", reliability=1.0),
            Hop(name="h2", reliability=1.0),
        ])
        assert compute_series_reliability(route) == 1.0

    def test_single_hop(self, single_hop_route):
        result = compute_series_reliability(single_hop_route)
        assert result == pytest.approx(0.998)

    def test_multiplicative(self, high_reliability_route):
        result = compute_series_reliability(high_reliability_route)
        expected = 0.9999 ** 3
        assert result == pytest.approx(expected)

    def test_empty_route(self, empty_route):
        assert compute_series_reliability(empty_route) == 1.0


class TestFindWeakestLink:
    """Tests for weakest link identification."""

    def test_mixed_reliability(self, mixed_reliability_route):
        weakest = find_weakest_link(mixed_reliability_route)
        assert weakest is not None
        assert weakest.name == "auth"

    def test_empty_route(self, empty_route):
        assert find_weakest_link(empty_route) is None

    def test_uniform_reliability(self, high_reliability_route):
        weakest = find_weakest_link(high_reliability_route)
        assert weakest is not None
        assert weakest.reliability == 0.9999


class TestComputeParallelReliability:
    """Tests for parallel reliability computation."""

    def test_single_path(self):
        result = compute_parallel_reliability([0.99])
        assert result == pytest.approx(0.99)

    def test_two_paths(self):
        result = compute_parallel_reliability([0.99, 0.99])
        expected = 1 - (1 - 0.99) ** 2
        assert result == pytest.approx(expected)

    def test_perfect_reliability(self):
        result = compute_parallel_reliability([1.0, 0.5])
        assert result == pytest.approx(1.0)

    def test_no_paths(self):
        result = compute_parallel_reliability([])
        assert result == pytest.approx(0.0)


class TestAnalyzeRelayChain:
    """Tests for full relay chain analysis."""

    def test_meets_sla(self, high_reliability_route):
        result = analyze_relay_chain(high_reliability_route, target_sla=0.999)
        assert result.meets_sla is True

    def test_does_not_meet_sla(self, mixed_reliability_route):
        result = analyze_relay_chain(mixed_reliability_route, target_sla=0.9999)
        assert result.meets_sla is False

    def test_weakest_link_identified(self, mixed_reliability_route):
        result = analyze_relay_chain(mixed_reliability_route, target_sla=0.9999)
        assert result.weakest_link == "auth"

    def test_recommendations_generated(self, mixed_reliability_route):
        result = analyze_relay_chain(mixed_reliability_route, target_sla=0.9999)
        assert len(result.recommendations) > 0

    def test_alternate_path(self, mixed_reliability_route):
        result = analyze_relay_chain(
            mixed_reliability_route,
            target_sla=0.9999,
            alternate_path_reliability=0.99995,
        )
        assert any("alternate" in r.lower() or "parallel" in r.lower()
                    for r in result.recommendations)

    def test_simple_route_analysis(self, simple_route):
        result = analyze_relay_chain(simple_route, target_sla=0.999)
        # The simple route has reliabilities 0.9999, 0.9995, 0.9998, 0.999
        expected = 0.9999 * 0.9995 * 0.9998 * 0.999
        assert result.actual_reliability == pytest.approx(expected, rel=1e-6)


class TestFormatReport:
    """Tests for report formatting."""

    def test_report_contains_route(self, high_reliability_route):
        result = analyze_relay_chain(high_reliability_route, target_sla=0.999)
        report = format_relay_chain_report(result)
        assert "high-rel-route" in report

    def test_report_contains_sla_status(self, mixed_reliability_route):
        result = analyze_relay_chain(mixed_reliability_route, target_sla=0.9999)
        report = format_relay_chain_report(result)
        assert "SLA" in report


class TestRelayChainToDict:
    """Tests for JSON serialization."""

    def test_dict_has_required_keys(self, high_reliability_route):
        result = analyze_relay_chain(high_reliability_route, target_sla=0.999)
        data = relay_chain_to_dict(result)
        assert "route" in data
        assert "target_sla" in data
        assert "meets_sla" in data
        assert "hops" in data
