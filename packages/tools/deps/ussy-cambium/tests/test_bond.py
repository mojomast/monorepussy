"""Tests for Cambium bond module."""

from __future__ import annotations

import pytest

from cambium.bond import (
    bond_trajectory,
    compute_bond_strength,
    detect_decay,
    format_bond_report,
)
from cambium.models import BondStrength, BondTrend


class TestComputeBondStrength:
    """Tests for compute_bond_strength."""

    def test_basic_creation(self):
        bond = compute_bond_strength()
        assert bond.b_max == 1.0
        assert bond.k_b == 0.3
        assert bond.t50 == 5.0

    def test_custom_params(self):
        bond = compute_bond_strength(b_max=0.9, k_b=0.25, t50=4.0)
        assert bond.b_max == 0.9
        assert bond.k_b == 0.25
        assert bond.t50 == 4.0


class TestBondTrajectory:
    """Tests for bond_trajectory."""

    def test_basic_trajectory(self):
        bond = compute_bond_strength(b_max=1.0, k_b=0.3, t50=5.0)
        traj = bond_trajectory(bond, months=12, step=3)
        assert len(traj) == 5  # 0, 3, 6, 9, 12

    def test_strength_increases_to_max(self):
        bond = compute_bond_strength(b_max=1.0, k_b=0.3, t50=5.0)
        traj = bond_trajectory(bond, months=50, step=10)
        # Strength should approach b_max
        last = traj[-1]
        assert last["strength"] > 0.9

    def test_trend_classification(self):
        bond = compute_bond_strength(b_max=1.0, k_b=0.3, t50=5.0)
        traj = bond_trajectory(bond, months=12)
        # Early points should be strengthening
        early = [p for p in traj if p["month"] < 8]
        assert any(p["trend"] == "strengthening" for p in early)


class TestDetectDecay:
    """Tests for detect_decay."""

    def test_no_decay_in_normal_bond(self):
        bond = compute_bond_strength(b_max=1.0, k_b=0.3, t50=5.0)
        # Sigmoid bonds don't decay; they approach B_max
        decay = detect_decay(bond, months=24)
        # With standard sigmoid, there shouldn't be decaying periods
        # (dB/dt > 0 until it flattens)
        # Only a truly decaying bond would have dB/dt < 0
        # A normal sigmoid with k_b > 0 has positive dB/dt always
        assert len(decay) == 0


class TestFormatBondReport:
    """Tests for format_bond_report."""

    def test_basic_report(self):
        bond = compute_bond_strength(b_max=1.0, k_b=0.3, t50=5.0)
        report = format_bond_report(bond)
        assert "Integration Bond Strength Trajectory" in report
        assert "B_max" in report
        assert "dB/dt" in report
