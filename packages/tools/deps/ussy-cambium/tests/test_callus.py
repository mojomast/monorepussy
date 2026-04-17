"""Tests for Cambium callus module."""

from __future__ import annotations

import math

import pytest

from cambium.callus import (
    callus_trajectory,
    compute_adapter_quality,
    compute_callus_dynamics,
    estimate_adapter_mismatches,
    format_callus_report,
)
from cambium.models import CallusDynamics


class TestComputeCallusDynamics:
    """Tests for compute_callus_dynamics."""

    def test_basic_creation(self):
        cd = compute_callus_dynamics(total_mismatches=10)
        assert cd.k_adapter == 10.0
        assert cd.n0 == 2.0
        assert cd.r_gen == 0.5

    def test_custom_params(self):
        cd = compute_callus_dynamics(
            total_mismatches=5,
            initially_resolved=3,
            generation_rate=0.8,
            test_pass_rate=0.9,
        )
        assert cd.k_adapter == 5.0
        assert cd.n0 == 3.0
        assert cd.r_gen == 0.8
        assert cd.test_pass_rate == 0.9


class TestEstimateAdapterMismatches:
    """Tests for estimate_adapter_mismatches."""

    def test_no_mismatches(self):
        assert estimate_adapter_mismatches({"a", "b"}, {"a", "b"}) == 0

    def test_all_mismatches(self):
        assert estimate_adapter_mismatches({"x"}, {"y"}) == 1

    def test_partial_mismatches(self):
        result = estimate_adapter_mismatches({"a", "b", "c"}, {"b", "c", "d"})
        assert result == 1  # only "a" is consumer-only


class TestComputeAdapterQuality:
    """Tests for compute_adapter_quality."""

    def test_perfect_quality(self):
        q = compute_adapter_quality([10, 10, 10], [10, 10, 10])
        assert q == pytest.approx(1.0)

    def test_zero_quality(self):
        q = compute_adapter_quality([0, 0], [10, 10])
        assert q == pytest.approx(0.0)

    def test_partial_quality(self):
        q = compute_adapter_quality([7, 8, 9], [10, 10, 10])
        expected = (0.7 + 0.8 + 0.9) / 3
        assert q == pytest.approx(expected)

    def test_empty_data(self):
        q = compute_adapter_quality([], [])
        assert q == pytest.approx(1.0)  # no data = assume perfect

    def test_zero_total(self):
        q = compute_adapter_quality([0], [0])
        assert q == pytest.approx(0.0)


class TestCallusTrajectory:
    """Tests for callus_trajectory."""

    def test_basic_trajectory(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=0.7)
        traj = callus_trajectory(cd, [0, 1, 2, 4, 8])
        assert len(traj) == 5
        assert traj[0]["time"] == 0
        assert traj[0]["adapters_resolved"] == pytest.approx(2.0)
        # Should be monotonically increasing
        for i in range(1, len(traj)):
            assert traj[i]["adapters_resolved"] >= traj[i - 1]["adapters_resolved"]


class TestFormatCallusReport:
    """Tests for format_callus_report."""

    def test_basic_report(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=0.8)
        report = format_callus_report(cd)
        assert "Adapter Generation Dynamics" in report
        assert "Bridging time" in report
        assert "Adapter quality" in report

    def test_low_quality_warning(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=0.3)
        report = format_callus_report(cd)
        assert "undifferentiated callus" in report

    def test_good_quality(self):
        cd = CallusDynamics(k_adapter=10.0, n0=2.0, r_gen=0.5, test_pass_rate=0.9)
        report = format_callus_report(cd)
        assert "Good adapter quality" in report
