"""Tests for Cambium GCI module."""

from __future__ import annotations

import pytest

from cambium.gci import (
    compute_gci,
    compute_gci_simple,
    format_gci_report,
    gci_trajectory,
)
from cambium.models import (
    AlignmentScore,
    BondStrength,
    CallusDynamics,
    CompatibilityScore,
    DriftDebt,
    GCISnapshot,
)


class TestComputeGCI:
    """Tests for compute_gci."""

    def test_perfect_gci(self):
        compat = CompatibilityScore(
            type_similarity=1.0, precondition_satisfaction=1.0, version_overlap=1.0
        )
        align = AlignmentScore(name_match=1.0, signature_match=1.0, semantic_match=1.0)
        callus = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=1.0)
        drift = DriftDebt(lambda_s=6.0, d_critical=1.0)
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=-100)  # already at max

        snap = compute_gci(compat, align, callus, drift, bond, system_vigor=1.0, time_months=0)
        assert snap.gci == pytest.approx(1.0, rel=0.01)

    def test_zero_alignment_kills_gci(self):
        compat = CompatibilityScore(
            type_similarity=1.0, precondition_satisfaction=1.0, version_overlap=1.0
        )
        align = AlignmentScore(name_match=0.0, signature_match=0.0, semantic_match=0.0)
        callus = CallusDynamics(test_pass_rate=1.0)
        drift = DriftDebt()
        bond = BondStrength()

        snap = compute_gci(compat, align, callus, drift, bond, system_vigor=1.0)
        assert snap.gci == pytest.approx(0.0)

    def test_zero_adapter_quality_kills_gci(self):
        compat = CompatibilityScore(
            type_similarity=1.0, precondition_satisfaction=1.0, version_overlap=1.0
        )
        align = AlignmentScore(name_match=1.0, signature_match=1.0, semantic_match=1.0)
        callus = CallusDynamics(test_pass_rate=0.0)
        drift = DriftDebt()
        bond = BondStrength()

        snap = compute_gci(compat, align, callus, drift, bond, system_vigor=1.0)
        assert snap.gci == pytest.approx(0.0)

    def test_drift_consumes_budget(self):
        compat = CompatibilityScore(
            type_similarity=1.0, precondition_satisfaction=1.0, version_overlap=1.0
        )
        align = AlignmentScore(name_match=1.0, signature_match=1.0, semantic_match=1.0)
        callus = CallusDynamics(test_pass_rate=1.0)
        drift = DriftDebt(
            delta_behavior=0.1, delta_contract=0.1, delta_environment=0.1,
            lambda_s=6.0, d_critical=1.0,
        )
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=-100)

        snap_t0 = compute_gci(compat, align, callus, drift, bond, system_vigor=1.0, time_months=0)
        snap_t12 = compute_gci(compat, align, callus, drift, bond, system_vigor=1.0, time_months=12)

        # GCI should decrease over time as drift accumulates
        assert snap_t12.gci < snap_t0.gci


class TestComputeGCISimple:
    """Tests for compute_gci_simple."""

    def test_all_perfect(self):
        snap = compute_gci_simple()
        assert snap.gci == pytest.approx(1.0)

    def test_one_zero(self):
        snap = compute_gci_simple(alignment=0.0)
        assert snap.gci == pytest.approx(0.0)

    def test_partial(self):
        snap = compute_gci_simple(
            compatibility=0.8,
            alignment=0.9,
            adapter_quality=0.7,
            drift_fraction=0.1,
            bond_fraction=0.85,
            system_vigor=0.9,
        )
        expected = 0.8 * 0.9 * 0.7 * 0.9 * 0.85 * 0.9
        assert snap.gci == pytest.approx(expected, rel=0.01)


class TestGCITrajectory:
    """Tests for gci_trajectory."""

    def test_basic_trajectory(self):
        compat = CompatibilityScore(
            type_similarity=0.8, precondition_satisfaction=0.7, version_overlap=0.9
        )
        align = AlignmentScore(name_match=0.8, signature_match=0.6, semantic_match=0.7)
        callus = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=0.7)
        drift = DriftDebt(
            delta_behavior=0.02, delta_contract=0.01, delta_environment=0.005,
            lambda_s=6.0, d_critical=1.0,
        )
        bond = BondStrength(b_max=0.9, k_b=0.25, t50=4.0)

        traj = gci_trajectory(
            compat, align, callus, drift, bond,
            system_vigor=0.9, months=12, step=3,
        )
        assert len(traj) == 5
        for snap in traj:
            assert 0.0 <= snap.gci <= 1.0

    def test_gci_decreasing_with_drift(self):
        compat = CompatibilityScore(
            type_similarity=1.0, precondition_satisfaction=1.0, version_overlap=1.0
        )
        align = AlignmentScore(name_match=1.0, signature_match=1.0, semantic_match=1.0)
        callus = CallusDynamics(test_pass_rate=1.0)
        drift = DriftDebt(
            delta_behavior=0.1, delta_contract=0.1, delta_environment=0.1,
            lambda_s=6.0, d_critical=1.0,
        )
        bond = BondStrength(b_max=1.0, k_b=0.3, t50=-100)

        traj = gci_trajectory(
            compat, align, callus, drift, bond,
            system_vigor=1.0, months=24, step=6,
        )
        # GCI should decrease over time
        for i in range(1, len(traj)):
            assert traj[i].gci <= traj[i - 1].gci


class TestFormatGCIReport:
    """Tests for format_gci_report."""

    def test_healthy_gci(self):
        snap = GCISnapshot(
            compatibility=0.98, alignment=0.97, adapter_quality=0.95,
            drift_fraction=0.02, bond_fraction=0.97, system_vigor=0.98,
        )
        report = format_gci_report(snap)
        assert "HEALTHY" in report

    def test_critical_gci(self):
        snap = GCISnapshot(
            compatibility=0.1, alignment=0.1, adapter_quality=0.1,
            drift_fraction=0.9, bond_fraction=0.1, system_vigor=0.1,
        )
        report = format_gci_report(snap)
        assert "CRITICAL" in report

    def test_partial_gci(self):
        snap = GCISnapshot(
            compatibility=0.6, alignment=0.7, adapter_quality=0.8,
            drift_fraction=0.2, bond_fraction=0.75, system_vigor=0.8,
        )
        report = format_gci_report(snap)
        assert "GCI" in report

    def test_component_breakdown(self):
        snap = GCISnapshot(
            compatibility=0.9, alignment=0.85, adapter_quality=0.8,
            drift_fraction=0.05, bond_fraction=0.9, system_vigor=0.95,
        )
        report = format_gci_report(snap)
        assert "Compatibility" in report
        assert "Alignment" in report
        assert "Adapter Quality" in report
