"""Tests for Cambium models."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from cambium.models import (
    AlignmentScore,
    BondStrength,
    BondTrend,
    CallusDynamics,
    CompatibilityScore,
    CompatibilityZone,
    DependencyNode,
    DependencyPair,
    DriftDebt,
    DwarfFactor,
    GCISnapshot,
    InterfaceInfo,
)


class TestCompatibilityScore:
    """Tests for CompatibilityScore model."""

    def test_composite_default_weights(self):
        score = CompatibilityScore(
            type_similarity=1.0,
            precondition_satisfaction=1.0,
            version_overlap=1.0,
        )
        assert score.composite == pytest.approx(1.0)

    def test_composite_zero_all(self):
        score = CompatibilityScore()
        assert score.composite == pytest.approx(0.0)

    def test_composite_partial(self):
        score = CompatibilityScore(
            type_similarity=0.8,
            precondition_satisfaction=0.6,
            version_overlap=0.9,
        )
        expected = 0.4 * 0.8 + 0.3 * 0.6 + 0.3 * 0.9
        assert score.composite == pytest.approx(expected)

    def test_composite_only_types(self):
        score = CompatibilityScore(type_similarity=0.5)
        assert score.composite == pytest.approx(0.4 * 0.5)


class TestAlignmentScore:
    """Tests for AlignmentScore model."""

    def test_composite_aligned(self):
        score = AlignmentScore(name_match=1.0, signature_match=1.0, semantic_match=1.0)
        assert score.composite == pytest.approx(1.0)

    def test_composite_zero(self):
        score = AlignmentScore()
        assert score.composite == pytest.approx(0.0)

    def test_status_aligned(self):
        score = AlignmentScore(name_match=0.95, signature_match=0.9, semantic_match=0.95)
        assert score.status == "ALIGNED"

    def test_status_partial(self):
        score = AlignmentScore(name_match=0.7, signature_match=0.6, semantic_match=0.7)
        assert score.status == "PARTIAL"

    def test_status_misaligned(self):
        score = AlignmentScore(name_match=0.2, signature_match=0.3, semantic_match=0.1)
        assert score.status == "MISALIGNED"

    def test_weights_sum_to_one(self):
        score = AlignmentScore()
        assert score.w_name + score.w_signature + score.w_semantic == pytest.approx(1.0)


class TestCallusDynamics:
    """Tests for CallusDynamics model."""

    def test_callus_at_zero(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5)
        assert cd.callus_at(0) == pytest.approx(2.0)

    def test_callus_at_infinity(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5)
        # At large t, should approach k_adapter
        result = cd.callus_at(1000)
        assert result == pytest.approx(10.0, rel=0.01)

    def test_callus_monotonic(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5)
        prev = cd.callus_at(0)
        for t in [1, 2, 4, 8, 16, 32]:
            current = cd.callus_at(t)
            assert current >= prev
            prev = current

    def test_bridging_time_finite(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5)
        bt = cd.bridging_time
        assert bt > 0
        assert bt < float("inf")

    def test_bridging_time_zero_k(self):
        cd = CallusDynamics(k_adapter=0.0, n0=1.0, r_gen=0.5)
        assert cd.bridging_time == float("inf")

    def test_adapter_quality_property(self):
        cd = CallusDynamics(test_pass_rate=0.75)
        assert cd.adapter_quality == pytest.approx(0.75)


class TestDriftDebt:
    """Tests for DriftDebt model."""

    def test_delta_0_computation(self):
        dd = DriftDebt(delta_behavior=0.02, delta_contract=0.01, delta_environment=0.005)
        assert dd.delta_0 == pytest.approx(0.035)

    def test_drift_at_zero(self):
        dd = DriftDebt(delta_behavior=0.02, delta_contract=0.01, delta_environment=0.005)
        assert dd.drift_at(0) == pytest.approx(0.0)

    def test_drift_at_large_t(self):
        dd = DriftDebt(delta_behavior=0.02, delta_contract=0.01, delta_environment=0.005, lambda_s=6.0)
        # At large t, D(t) → Δ₀ · λ_s
        expected = dd.delta_0 * dd.lambda_s
        result = dd.drift_at(1000)
        assert result == pytest.approx(expected, rel=0.01)

    def test_safe_zone(self):
        dd = DriftDebt(delta_behavior=0.001, delta_contract=0.001, delta_environment=0.001,
                       lambda_s=6.0, d_critical=1.0)
        assert dd.zone == CompatibilityZone.SAFE

    def test_doomed_zone(self):
        dd = DriftDebt(delta_behavior=0.1, delta_contract=0.1, delta_environment=0.1,
                       lambda_s=6.0, d_critical=1.0)
        assert dd.zone == CompatibilityZone.DOOMED

    def test_breakage_time_doomed(self):
        dd = DriftDebt(delta_behavior=0.05, delta_contract=0.03, delta_environment=0.02,
                       lambda_s=6.0, d_critical=1.0)
        # Δ₀·λ_s = 0.1 * 6 = 0.6, which is < D_critical=1.0, so safe
        # Need higher drift for doomed
        dd2 = DriftDebt(delta_behavior=0.1, delta_contract=0.1, delta_environment=0.1,
                        lambda_s=6.0, d_critical=1.0)
        # Δ₀·λ_s = 0.3 * 6 = 1.8 > 1.0, so doomed
        bt = dd2.breakage_time
        assert 0 < bt < float("inf")

    def test_breakage_time_safe_is_inf(self):
        dd = DriftDebt(delta_behavior=0.001, delta_contract=0.001, delta_environment=0.001,
                       lambda_s=6.0, d_critical=1.0)
        assert dd.breakage_time == float("inf")

    def test_drift_budget_consumed(self):
        dd = DriftDebt(delta_behavior=0.1, delta_contract=0.1, delta_environment=0.1,
                       lambda_s=6.0, d_critical=1.0)
        budget = dd.drift_budget_consumed(0)
        assert budget == pytest.approx(0.0)


class TestBondStrength:
    """Tests for BondStrength model."""

    def test_strength_at_t50(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        # At t=t50, strength = B_max / 2
        assert bond.strength_at(5.0) == pytest.approx(0.5)

    def test_strength_at_zero(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        s = bond.strength_at(0)
        assert 0 < s < 0.5

    def test_strength_at_large_t(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        s = bond.strength_at(1000)
        assert s == pytest.approx(1.0, rel=0.01)

    def test_strength_rate_positive_before_t50(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        rate = bond.strength_rate(2.0)
        assert rate > 0

    def test_trend_strengthening(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        assert bond.trend_at(2.0) == BondTrend.STRENGTHENING

    def test_trend_stable(self):
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=5.0)
        # At t >> t50, rate approaches 0
        assert bond.trend_at(1000) == BondTrend.STABLE

    def test_zero_b_max(self):
        bond = BondStrength(b_max=0.0)
        assert bond.strength_at(5.0) == 0.0


class TestDwarfFactor:
    """Tests for DwarfFactor model."""

    def test_no_dwarfing(self):
        df = DwarfFactor(capability_with=0.95, capability_without=1.0)
        assert df.dwarf_ratio == pytest.approx(0.95)
        assert not df.is_dwarfing

    def test_dwarfing(self):
        df = DwarfFactor(capability_with=0.42, capability_without=1.0)
        assert df.dwarf_ratio == pytest.approx(0.42)
        assert df.is_dwarfing

    def test_capability_reduction_pct(self):
        df = DwarfFactor(capability_with=0.42, capability_without=1.0)
        assert df.capability_reduction_pct == pytest.approx(58.0)

    def test_zero_without(self):
        df = DwarfFactor(capability_with=0.5, capability_without=0.0)
        assert df.dwarf_ratio == 0.0


class TestDependencyNode:
    """Tests for DependencyNode model."""

    def test_chain_capability_single(self):
        node = DependencyNode(name="root", capability=1.0)
        assert node.chain_capability == pytest.approx(1.0)

    def test_chain_capability_linear(self):
        # 1 / (1/0.9 + 1/0.8) = 1 / (1.111 + 1.25) = 1/2.361 = 0.424
        root = DependencyNode(name="root", capability=0.9, children=[
            DependencyNode(name="child", capability=0.8),
        ])
        cap = root.chain_capability
        expected = 1.0 / (1.0 / 0.9 + 1.0 / 0.8)
        assert cap == pytest.approx(expected, rel=0.01)

    def test_chain_capability_zero_propagates(self):
        root = DependencyNode(name="root", capability=0.9, children=[
            DependencyNode(name="child", capability=0.0),
        ])
        assert root.chain_capability == 0.0


class TestGCISnapshot:
    """Tests for GCISnapshot model."""

    def test_gci_perfect(self):
        snap = GCISnapshot(
            compatibility=1.0, alignment=1.0, adapter_quality=1.0,
            drift_fraction=0.0, bond_fraction=1.0, system_vigor=1.0,
        )
        assert snap.gci == pytest.approx(1.0)

    def test_gci_zero_component_kills(self):
        snap = GCISnapshot(
            compatibility=1.0, alignment=0.0, adapter_quality=1.0,
            drift_fraction=0.0, bond_fraction=1.0, system_vigor=1.0,
        )
        assert snap.gci == pytest.approx(0.0)

    def test_gci_drift_penalty(self):
        snap = GCISnapshot(
            compatibility=1.0, alignment=1.0, adapter_quality=1.0,
            drift_fraction=0.5, bond_fraction=1.0, system_vigor=1.0,
        )
        assert snap.gci == pytest.approx(0.5)

    def test_gci_partial(self):
        snap = GCISnapshot(
            compatibility=0.8, alignment=0.9, adapter_quality=0.7,
            drift_fraction=0.1, bond_fraction=0.85, system_vigor=0.9,
        )
        # 0.8 * 0.9 * 0.7 * 0.9 * 0.85 * 0.9
        expected = 0.8 * 0.9 * 0.7 * 0.9 * 0.85 * 0.9
        assert snap.gci == pytest.approx(expected, rel=0.01)

    def test_gci_to_dict(self):
        snap = GCISnapshot(
            compatibility=0.8, alignment=0.9, adapter_quality=0.7,
            drift_fraction=0.1, bond_fraction=0.85, system_vigor=0.9,
        )
        d = snap.to_dict()
        assert "gci" in d
        assert "compatibility" in d
        assert isinstance(d["gci"], float)

    def test_gci_timestamp_auto(self):
        snap = GCISnapshot()
        assert snap.timestamp  # should be non-empty

    def test_gci_drift_fraction_exceeds_one(self):
        """Drift fraction > 1.0 means past critical, GCI should be 0."""
        snap = GCISnapshot(
            compatibility=1.0, alignment=1.0, adapter_quality=1.0,
            drift_fraction=1.5, bond_fraction=1.0, system_vigor=1.0,
        )
        assert snap.gci == pytest.approx(0.0)


class TestDependencyPair:
    """Tests for DependencyPair model."""

    def test_auto_timestamp(self):
        dp = DependencyPair(consumer="a", provider="b")
        assert dp.timestamp  # should be auto-generated

    def test_explicit_timestamp(self):
        dp = DependencyPair(consumer="a", provider="b", timestamp="2024-01-01")
        assert dp.timestamp == "2024-01-01"
