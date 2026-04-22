"""Tests for the steady-state module."""

import math

import pytest

from ussy_dosemate.steady_state import (
    SteadyStateParams, DosePlan,
    compute_steady_state, compute_dose_plan,
)
from ussy_dosemate.excretion import ExcretionParams


class TestComputeSteadyState:
    """Tests for compute_steady_state function."""

    def test_accumulation_factor_ge_1(self):
        """Accumulation factor R should always be >= 1."""
        excretion = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        result = compute_steady_state(0.5, 10.0, 0.5, excretion, 2.0)
        assert result.accumulation_factor_R >= 1.0

    def test_fast_clearance_low_accumulation(self):
        """Fast clearance (high ke) should result in R close to 1."""
        excretion = ExcretionParams(CL=10.0, ke=10.0, t_half=0.069)
        result = compute_steady_state(0.5, 10.0, 10.0, excretion, 2.0)
        assert result.accumulation_factor_R < 1.1

    def test_slow_clearance_high_accumulation(self):
        """Slow clearance (low ke) should result in high R."""
        excretion = ExcretionParams(CL=0.001, ke=0.001, t_half=693.0)
        result = compute_steady_state(0.5, 10.0, 0.001, excretion, 2.0)
        assert result.accumulation_factor_R > 1.5

    def test_css_positive(self):
        """Css should be positive for positive inputs."""
        excretion = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        result = compute_steady_state(0.5, 10.0, 0.5, excretion, 2.0)
        assert result.Css > 0

    def test_time_to_steady_state(self):
        """Time to steady state should be approximately 4.5 * t_half."""
        excretion = ExcretionParams(CL=0.5, ke=0.1, t_half=6.93)
        result = compute_steady_state(0.5, 10.0, 0.5, excretion, 2.0)
        assert abs(result.time_to_steady_state_weeks - 4.5 * 6.93) < 0.1

    def test_assessment_sustainable(self):
        """Low accumulation should yield sustainable assessment."""
        excretion = ExcretionParams(CL=10.0, ke=10.0, t_half=0.069)
        result = compute_steady_state(0.5, 10.0, 10.0, excretion, 2.0)
        assert "sustainable" in result.assessment().lower()

    def test_assessment_critical(self):
        """Very high accumulation should yield critical assessment."""
        excretion = ExcretionParams(CL=0.001, ke=0.0001, t_half=6930.0)
        result = compute_steady_state(0.5, 100.0, 0.001, excretion, 1.0)
        assert "CRITICAL" in result.assessment() or "critical" in result.assessment().lower()


class TestComputeDosePlan:
    """Tests for compute_dose_plan function."""

    def test_loading_dose_positive(self):
        """Loading dose should be positive."""
        plan = compute_dose_plan(0.5, 10.0, 0.5, 0.5, 2.0)
        assert plan.loading_dose > 0

    def test_maintenance_dose_positive(self):
        """Maintenance dose should be positive."""
        plan = compute_dose_plan(0.5, 10.0, 0.5, 0.5, 2.0)
        assert plan.maintenance_dose > 0

    def test_ld_over_md_ratio(self):
        """LD/MD = Vd / (CL * tau)."""
        Vd = 20.0
        CL = 0.5
        F = 0.5
        tau = 2.0
        plan = compute_dose_plan(0.5, Vd, CL, F, tau)
        expected_ratio = Vd / (CL * tau)
        assert abs(plan.LD_over_MD - expected_ratio) < 0.01

    def test_high_vd_high_bootstrap(self):
        """High Vd should result in LD >> MD (high bootstrap burden)."""
        plan_high_vd = compute_dose_plan(0.5, 100.0, 0.5, 0.5, 2.0)
        plan_low_vd = compute_dose_plan(0.5, 5.0, 0.5, 0.5, 2.0)
        assert plan_high_vd.LD_over_MD > plan_low_vd.LD_over_MD

    def test_greenfield_interpretation(self):
        """High LD/MD ratio should indicate greenfield/migration."""
        plan = compute_dose_plan(0.5, 100.0, 0.5, 0.5, 2.0)
        # LD/MD = 100 / (0.5 * 2) = 100
        assert plan.LD_over_MD > 5
        assert "bootstrap" in plan.interpretation.lower() or "greenfield" in plan.interpretation.lower() or "migration" in plan.interpretation.lower()

    def test_balanced_interpretation(self):
        """LD ≈ MD should indicate balanced/mature system."""
        # Vd / (CL * tau) ≈ 1
        plan = compute_dose_plan(0.5, 1.0, 0.5, 0.5, 2.0)
        assert 0.8 <= plan.LD_over_MD <= 2.0
        assert "balanced" in plan.interpretation.lower() or "mature" in plan.interpretation.lower()
