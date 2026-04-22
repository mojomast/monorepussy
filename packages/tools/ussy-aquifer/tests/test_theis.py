"""Tests for the Theis equation module."""

import math

import pytest

from ussy_aquifer.topology import ServiceLayer, FlowConnection, Topology
from ussy_aquifer.theis import (
    well_function,
    compute_drawdown,
    compute_time_to_saturation,
    predict_system,
)


class TestWellFunction:
    """Test the Theis well function W(u)."""

    def test_small_u(self):
        """For very small u, W(u) ≈ -0.5772 - ln(u)."""
        u = 1e-8
        W = well_function(u)
        expected = -0.5772156649 - math.log(u)
        assert W == pytest.approx(expected, rel=1e-4)

    def test_large_u(self):
        """For large u, W(u) should be small."""
        u = 10.0
        W = well_function(u)
        assert W < 0.01

    def test_u_equals_one(self):
        """W(1) should be approximately 0.2194."""
        W = well_function(1.0)
        # Known value: W(1) ≈ 0.2194
        assert abs(W - 0.2194) < 0.01

    def test_u_zero_returns_inf(self):
        """W(0) should be infinity."""
        W = well_function(0.0)
        assert W == float("inf")

    def test_u_negative_returns_inf(self):
        """Negative u should return infinity."""
        W = well_function(-1.0)
        assert W == float("inf")

    def test_monotonic_decreasing(self):
        """W(u) should be monotonically decreasing."""
        u_values = [0.001, 0.01, 0.1, 1.0, 5.0]
        W_values = [well_function(u) for u in u_values]
        for i in range(len(W_values) - 1):
            assert W_values[i] > W_values[i + 1]

    def test_very_small_u(self):
        """Test with extremely small u."""
        u = 1e-15
        W = well_function(u)
        assert W > 30  # Should be very large


class TestDrawdown:
    """Test drawdown computation using the Theis equation."""

    def test_basic_drawdown(self):
        """Basic drawdown should be positive when Q > 0."""
        s = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        assert s > 0

    def test_zero_Q_no_drawdown(self):
        """No pumping = no drawdown."""
        s = compute_drawdown(Q=0.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        assert s == 0.0

    def test_zero_time_no_drawdown(self):
        """No time elapsed = no drawdown."""
        s = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=0.0)
        assert s == 0.0

    def test_zero_T_no_drawdown(self):
        """Zero transmissivity = no drawdown."""
        s = compute_drawdown(Q=100.0, T=0.0, S=0.01, r=1.0, t=3600.0)
        assert s == 0.0

    def test_zero_S_no_drawdown(self):
        """Zero storage = no drawdown."""
        s = compute_drawdown(Q=100.0, T=500.0, S=0.0, r=1.0, t=3600.0)
        assert s == 0.0

    def test_increases_with_Q(self):
        """Drawdown should increase with pumping rate."""
        s1 = compute_drawdown(Q=50.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        s2 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        assert s2 > s1

    def test_decreases_with_T(self):
        """Drawdown should decrease with higher transmissivity."""
        s1 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        s2 = compute_drawdown(Q=100.0, T=1000.0, S=0.01, r=1.0, t=3600.0)
        assert s2 < s1

    def test_increases_with_time(self):
        """Drawdown should increase over time."""
        s1 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        s2 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=7200.0)
        assert s2 > s1

    def test_decreases_with_distance(self):
        """Drawdown should decrease with distance from the well."""
        s1 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=1.0, t=3600.0)
        s2 = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=5.0, t=3600.0)
        assert s2 < s1

    def test_zero_r_uses_small_value(self):
        """At r=0, we use a small value to avoid division by zero."""
        s = compute_drawdown(Q=100.0, T=500.0, S=0.01, r=0.0, t=3600.0)
        assert s > 0  # Should not crash


class TestTimeToSaturation:
    """Test time-to-saturation computation."""

    def test_finds_saturation_time(self):
        """Should find a finite time for high enough load."""
        t = compute_time_to_saturation(
            Q=500.0, T=100.0, S=0.01, r=0.001, saturation_drawdown=1.0
        )
        assert t is not None
        assert t > 0

    def test_zero_Q_returns_none(self):
        """No load = no saturation."""
        t = compute_time_to_saturation(
            Q=0.0, T=100.0, S=0.01, r=0.001, saturation_drawdown=1.0
        )
        assert t is None

    def test_high_T_may_never_saturate(self):
        """Very high transmissivity may never saturate."""
        t = compute_time_to_saturation(
            Q=1.0, T=1e6, S=0.01, r=0.001, saturation_drawdown=1.0
        )
        # May or may not saturate depending on parameters
        # Just verify it doesn't crash
        assert t is None or t > 0


class TestPredictSystem:
    """Test system-wide prediction."""

    def _make_topo(self):
        topo = Topology(name="predict_test")
        topo.add_service(ServiceLayer("src", 100.0, queue_depth=50,
                                       processing_latency=0.1, is_recharge=True,
                                       grid_x=0, grid_y=0))
        topo.add_service(ServiceLayer("mid", 50.0, queue_depth=100,
                                       processing_latency=0.2, grid_x=1, grid_y=0))
        topo.add_service(ServiceLayer("snk", 80.0, queue_depth=10,
                                       processing_latency=0.05, is_discharge=True,
                                       grid_x=2, grid_y=0))
        topo.add_connection(FlowConnection("src", "mid"))
        topo.add_connection(FlowConnection("mid", "snk"))
        return topo

    def test_prediction_returns_results(self):
        topo = self._make_topo()
        pred = predict_system(topo, duration_hours=1.0)
        assert len(pred.service_predictions) == 3

    def test_prediction_has_service_names(self):
        topo = self._make_topo()
        pred = predict_system(topo, duration_hours=1.0)
        names = {p.service_name for p in pred.service_predictions}
        assert names == {"src", "mid", "snk"}

    def test_prediction_with_load_multiplier(self):
        topo = self._make_topo()
        pred1 = predict_system(topo, duration_hours=1.0, load_multiplier=1.0)
        pred2 = predict_system(topo, duration_hours=1.0, load_multiplier=2.0)
        # Higher load should generally cause more drawdown
        total_dd1 = sum(p.drawdown for p in pred1.service_predictions)
        total_dd2 = sum(p.drawdown for p in pred2.service_predictions)
        assert total_dd2 >= total_dd1

    def test_prediction_summary(self):
        topo = self._make_topo()
        pred = predict_system(topo, duration_hours=1.0)
        summary = pred.summary()
        assert "System Prediction" in summary
        assert "1.0h" in summary

    def test_prediction_duration(self):
        topo = self._make_topo()
        pred = predict_system(topo, duration_hours=2.5)
        assert pred.duration_hours == 2.5
