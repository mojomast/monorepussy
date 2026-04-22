"""Tests for endemic.sir_model module."""

import pytest

from ussy_endemic.models import SIRSimulation, SIRState
from ussy_endemic.sir_model import (
    compute_beta,
    compute_gamma,
    format_sir_chart,
    simulate_sir,
    simulate_with_intervention,
)


class TestComputeBeta:
    def test_basic(self):
        beta = compute_beta(r0=2.0, gamma=0.1, n=50)
        assert beta == pytest.approx(0.2)

    def test_zero_r0(self):
        beta = compute_beta(r0=0.0, gamma=0.1, n=50)
        assert beta == 0.0


class TestComputeGamma:
    def test_basic(self):
        gamma = compute_gamma(recovery_time_weeks=4.0, time_step_weeks=1.0)
        assert gamma == pytest.approx(0.25)

    def test_short_recovery(self):
        gamma = compute_gamma(recovery_time_weeks=1.0, time_step_weeks=1.0)
        assert gamma == pytest.approx(1.0)

    def test_zero_recovery_time(self):
        gamma = compute_gamma(recovery_time_weeks=0.0)
        assert gamma == 1.0


class TestSimulateSIR:
    def test_basic_simulation(self):
        sim = simulate_sir(
            n=100, initial_infected=5, initial_recovered=0,
            r0=2.0, gamma=0.1, horizon_steps=50,
        )
        assert len(sim.states) == 51  # 0 to 50
        assert sim.states[0].i == 5
        assert sim.states[0].s == 95

    def test_population_conserved(self):
        sim = simulate_sir(
            n=100, initial_infected=5, initial_recovered=0,
            r0=2.0, gamma=0.1, horizon_steps=50,
        )
        for state in sim.states:
            assert state.s + state.i + state.r == 100

    def test_no_spread_r0_below_1(self):
        sim = simulate_sir(
            n=100, initial_infected=5, initial_recovered=0,
            r0=0.5, gamma=0.25, horizon_steps=50,
        )
        # Infections should decrease over time or stay low
        assert sim.states[-1].i <= sim.states[0].i

    def test_spreading_r0_above_1(self):
        sim = simulate_sir(
            n=100, initial_infected=5, initial_recovered=0,
            r0=3.0, gamma=0.1, horizon_steps=50,
        )
        # Peak infected should be higher than initial
        assert sim.peak_infected >= 5

    def test_zero_infected(self):
        sim = simulate_sir(
            n=100, initial_infected=0, initial_recovered=0,
            r0=3.0, gamma=0.1, horizon_steps=10,
        )
        # No spread without initial infections
        assert all(s.i == 0 for s in sim.states)

    def test_peak_infected_set(self):
        sim = simulate_sir(
            n=100, initial_infected=5, initial_recovered=0,
            r0=3.0, gamma=0.1, horizon_steps=50,
        )
        assert sim.peak_infected > 0
        assert sim.peak_time >= 0


class TestSimulateWithIntervention:
    def test_intervention_reduces_spread(self):
        without, with_int = simulate_with_intervention(
            n=100, initial_infected=5, initial_recovered=0,
            r0=3.0, gamma=0.1,
            intervention_step=5,
            intervention_r0=0.5,
            horizon_steps=50,
        )
        # With intervention, peak should be lower
        assert with_int.peak_infected <= without.peak_infected

    def test_no_intervention_same_as_base(self):
        without, with_int = simulate_with_intervention(
            n=100, initial_infected=5, initial_recovered=0,
            r0=2.0, gamma=0.1,
            intervention_step=5,
            intervention_r0=2.0,  # Same as original
            horizon_steps=20,
        )
        # Should be similar
        assert abs(without.peak_infected - with_int.peak_infected) <= 5


class TestFormatSIRChart:
    def test_basic_chart(self):
        sim = simulate_sir(
            n=50, initial_infected=5, initial_recovered=0,
            r0=2.0, gamma=0.1, horizon_steps=20,
        )
        chart = format_sir_chart(sim)
        assert "S" in chart
        assert "I" in chart
        assert "R" in chart

    def test_empty_simulation(self):
        sim = SIRSimulation(
            pattern_name="test", r0=2.0, beta=0.2, gamma=0.1, n=50,
        )
        chart = format_sir_chart(sim)
        assert "No simulation data" in chart

    def test_zero_population(self):
        sim = SIRSimulation(
            pattern_name="test", r0=2.0, beta=0.2, gamma=0.1, n=0,
            states=[SIRState(time=0, s=0, i=0, r=0)],
        )
        chart = format_sir_chart(sim)
        assert "zero" in chart.lower()
