"""Tests for cavity.modes module."""

from __future__ import annotations

import numpy as np
import pytest

from cavity.modes import (
    RiskLevel,
    ResonanceMode,
    classify_damping,
    compute_natural_frequencies,
    format_modes,
    predict_deadlocks,
)


# ---------------------------------------------------------------------------
# classify_damping
# ---------------------------------------------------------------------------


class TestClassifyDamping:
    def test_undamped(self):
        assert classify_damping(0.0) == RiskLevel.UNDAMPED
        assert classify_damping(0.04) == RiskLevel.UNDAMPED

    def test_underdamped(self):
        assert classify_damping(0.1) == RiskLevel.UNDERDAMPED
        assert classify_damping(0.5) == RiskLevel.UNDERDAMPED
        assert classify_damping(0.89) == RiskLevel.UNDERDAMPED

    def test_critically_damped(self):
        assert classify_damping(0.96) == RiskLevel.CRITICALLY_DAMPED
        assert classify_damping(1.0) == RiskLevel.CRITICALLY_DAMPED
        assert classify_damping(1.04) == RiskLevel.CRITICALLY_DAMPED

    def test_overdamped(self):
        assert classify_damping(1.2) == RiskLevel.OVERDAMPED
        assert classify_damping(5.0) == RiskLevel.OVERDAMPED


# ---------------------------------------------------------------------------
# compute_natural_frequencies
# ---------------------------------------------------------------------------


class TestComputeNaturalFrequencies:
    def test_empty_matrix(self):
        modes = compute_natural_frequencies(np.zeros((0, 0)))
        assert modes == []

    def test_identity_matrix(self):
        A = np.eye(3)
        modes = compute_natural_frequencies(A)
        assert len(modes) == 3

    def test_zero_matrix(self):
        A = np.zeros((3, 3))
        modes = compute_natural_frequencies(A)
        assert len(modes) == 3
        # All eigenvalues are 0, so frequency and damping should be 0
        for m in modes:
            assert m.frequency == 0.0
            assert m.damping_ratio == 0.0

    def test_symmetric_matrix(self):
        """Symmetric matrix has real eigenvalues."""
        A = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
        modes = compute_natural_frequencies(A)
        assert len(modes) == 3

    def test_node_names_assigned(self):
        A = np.eye(2)
        modes = compute_natural_frequencies(A, node_names=["worker_a", "lock_x"])
        for m in modes:
            assert len(m.involved_nodes) > 0

    def test_dt_affects_frequency(self):
        A = np.array([[0, 1], [1, 0]], dtype=float)
        modes_dt1 = compute_natural_frequencies(A, dt=1.0)
        modes_dt2 = compute_natural_frequencies(A, dt=2.0)
        # Frequency with dt=2 should be half of dt=1
        f1 = sum(m.frequency for m in modes_dt1)
        f2 = sum(m.frequency for m in modes_dt2)
        assert abs(f2 - f1 / 2.0) < 0.01 or f1 < 1e-10

    def test_modes_sorted_by_risk(self):
        """Undamped modes should come first."""
        A = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=float)
        modes = compute_natural_frequencies(A)
        risk_order = {
            RiskLevel.UNDAMPED: 0,
            RiskLevel.UNDERDAMPED: 1,
            RiskLevel.CRITICALLY_DAMPED: 2,
            RiskLevel.OVERDAMPED: 3,
        }
        for i in range(len(modes) - 1):
            assert risk_order[modes[i].risk_level] <= risk_order[modes[i + 1].risk_level]


# ---------------------------------------------------------------------------
# ResonanceMode
# ---------------------------------------------------------------------------


class TestResonanceMode:
    def test_q_factor_undamped(self):
        m = ResonanceMode(
            index=0, frequency=1.0, damping_ratio=0.0,
            risk_level=RiskLevel.UNDAMPED,
            eigenvalue=1.0 + 0j, eigenvector=np.array([1.0]),
        )
        assert m.q_factor == float("inf")

    def test_q_factor_damped(self):
        m = ResonanceMode(
            index=0, frequency=1.0, damping_ratio=0.5,
            risk_level=RiskLevel.UNDERDAMPED,
            eigenvalue=1.0 + 0j, eigenvector=np.array([1.0]),
        )
        assert abs(m.q_factor - 1.0) < 1e-10

    def test_summary_string(self):
        m = ResonanceMode(
            index=1, frequency=0.3, damping_ratio=0.02,
            risk_level=RiskLevel.UNDAMPED,
            eigenvalue=1.0 + 0j, eigenvector=np.array([1.0]),
        )
        s = m.summary()
        assert "Mode 1" in s
        assert "UNDAMPED" in s


# ---------------------------------------------------------------------------
# predict_deadlocks
# ---------------------------------------------------------------------------


class TestPredictDeadlocks:
    def test_no_deadlocks_in_zero_matrix(self):
        A = np.zeros((3, 3))
        modes = predict_deadlocks(A)
        # Zero eigenvalues → undamped, but also 0 frequency
        # They should be returned as potential risks
        assert isinstance(modes, list)

    def test_with_topology(self, simple_topology):
        adj = simple_topology.adjacency_matrix
        modes = predict_deadlocks(adj, simple_topology.node_names)
        assert isinstance(modes, list)

    def test_with_max_risk(self):
        A = np.eye(3)
        modes = predict_deadlocks(A, max_risk=RiskLevel.OVERDAMPED)
        assert len(modes) == 3  # All modes included

    def test_with_undamped_max_risk(self):
        A = np.eye(3)
        modes = predict_deadlocks(A, max_risk=RiskLevel.UNDAMPED)
        # Only undamped modes
        for m in modes:
            assert m.risk_level == RiskLevel.UNDAMPED


# ---------------------------------------------------------------------------
# format_modes
# ---------------------------------------------------------------------------


class TestFormatModes:
    def test_empty(self):
        s = format_modes([])
        assert "No resonance modes" in s

    def test_with_modes(self):
        modes = [
            ResonanceMode(
                index=0, frequency=0.3, damping_ratio=0.02,
                risk_level=RiskLevel.UNDAMPED,
                eigenvalue=1 + 0j, eigenvector=np.array([1.0]),
                involved_nodes=["worker_a", "lock_x"],
            ),
        ]
        s = format_modes(modes)
        assert "Mode 0" in s
        assert "worker_a" in s
