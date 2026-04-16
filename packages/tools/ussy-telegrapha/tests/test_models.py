"""Tests for the models module."""

import pytest

from telegrapha.models import (
    Hop, Route, PipelineTopology,
    AttenuationResult, RelayChainResult,
    CapacityResult, PrecedenceClass, PrecedenceResult,
    HammingResult, DLQEntry, DLOResult,
)


class TestHop:
    """Tests for Hop dataclass."""

    def test_default_values(self):
        hop = Hop(name="test")
        assert hop.degradation == 0.0
        assert hop.reliability == 1.0
        assert hop.details == ""
        assert hop.serialization_degradation == 0.0
        assert hop.deserialization_degradation == 0.0


class TestRoute:
    """Tests for Route dataclass."""

    def test_hop_count(self, simple_route):
        assert simple_route.hop_count == 4

    def test_empty_route(self, empty_route):
        assert empty_route.hop_count == 0

    def test_end_to_end_fidelity(self, simple_route):
        expected = (1 - 0.005) * (1 - 0.030) * (1 - 0.020) * (1 - 0.040)
        assert simple_route.end_to_end_fidelity == pytest.approx(expected, rel=1e-6)

    def test_end_to_end_reliability(self, simple_route):
        expected = 0.9999 * 0.9995 * 0.9998 * 0.999
        assert simple_route.end_to_end_reliability == pytest.approx(expected, rel=1e-6)

    def test_perfect_fidelity(self):
        route = Route(name="perfect", hops=[Hop(name="h1")])
        assert route.end_to_end_fidelity == 1.0

    def test_perfect_reliability(self):
        route = Route(name="perfect", hops=[Hop(name="h1", reliability=1.0)])
        assert route.end_to_end_reliability == 1.0


class TestPipelineTopology:
    """Tests for PipelineTopology dataclass."""

    def test_default_values(self):
        topo = PipelineTopology()
        assert topo.name == ""
        assert topo.routes == []
        assert topo.loaded_at != ""

    def test_with_data(self):
        topo = PipelineTopology(name="test", routes=[Route(name="r1")])
        assert topo.name == "test"
        assert len(topo.routes) == 1


class TestAttenuationResult:
    """Tests for AttenuationResult dataclass."""

    def test_post_init_computes_fidelity(self, simple_route):
        result = AttenuationResult(route=simple_route)
        assert result.fidelity > 0
        assert result.cumulative_degradation == pytest.approx(1.0 - result.fidelity)

    def test_post_init_with_explicit_fidelity(self, simple_route):
        result = AttenuationResult(route=simple_route, fidelity=0.5)
        assert result.fidelity == 0.5
        assert result.cumulative_degradation == pytest.approx(0.5)


class TestRelayChainResult:
    """Tests for RelayChainResult dataclass."""

    def test_post_init_computes_required_per_hop(self, simple_route):
        result = RelayChainResult(route=simple_route, target_sla=0.999)
        assert result.required_per_hop > 0

    def test_post_init_finds_weakest_link(self, mixed_reliability_route):
        result = RelayChainResult(route=mixed_reliability_route)
        assert result.weakest_link == "auth"


class TestCapacityResult:
    """Tests for CapacityResult dataclass."""

    def test_post_init_computes_snr(self):
        result = CapacityResult(bandwidth=500, signal_rate=420, noise_rate=80)
        assert result.snr == pytest.approx(5.25)

    def test_post_init_zero_noise(self):
        result = CapacityResult(bandwidth=500, signal_rate=420, noise_rate=0)
        assert result.snr == float("inf")


class TestDLOResult:
    """Tests for DLOResult dataclass."""

    def test_healthy_status(self):
        result = DLOResult(health_score=0.8)
        assert result.health_status == "HEALTHY"

    def test_warning_status(self):
        result = DLOResult(health_score=0.5)
        assert result.health_status == "WARNING"

    def test_critical_status(self):
        result = DLOResult(health_score=0.1)
        assert result.health_status == "CRITICAL"
