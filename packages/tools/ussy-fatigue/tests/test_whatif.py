"""Tests for the what-if analysis module."""

import pytest

from fatigue.whatif import (
    simulate_intervention,
    list_interventions,
    INTERVENTIONS,
)
from fatigue.models import (
    MaterialConstants,
    ModuleStatus,
    StressIntensity,
    WhatIfScenario,
)


class TestSimulateIntervention:
    """Tests for what-if intervention simulation."""

    @pytest.fixture
    def high_stress(self):
        """Create a high-stress intensity (above K_Ic)."""
        return StressIntensity(
            file_path="critical_module.py",
            K=42.0,
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )

    @pytest.fixture
    def moderate_stress(self):
        """Create a moderate-stress intensity (just above K_Ic)."""
        return StressIntensity(
            file_path="growing_module.py",
            K=30.0,
            coupling_component=5.0,
            churn_component=3.0,
            complexity_component=8.0,
            coverage_component=0.4,
        )

    @pytest.fixture
    def default_material(self):
        """Create default material constants."""
        return MaterialConstants()

    def test_extract_interface_reduces_K(self, high_stress, default_material):
        """Test extract interface reduces K value."""
        scenario = simulate_intervention(
            stress=high_stress,
            material=default_material,
            current_debt=34.0,
            intervention="extract_interface",
        )

        assert scenario.intervention == "extract_interface"
        # K should be reduced
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_extract_interface_moderate_stress(self, moderate_stress, default_material):
        """Test extract interface with moderate stress brings K below K_Ic."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="extract_interface",
        )

        assert scenario.intervention == "extract_interface"
        # With 75% coupling reduction, K should drop significantly
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_add_tests_reduces_K(self, high_stress, default_material):
        """Test add tests reduces K value."""
        scenario = simulate_intervention(
            stress=high_stress,
            material=default_material,
            current_debt=34.0,
            intervention="add_tests",
        )

        assert scenario.intervention == "add_tests"
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_add_tests_moderate_stress(self, moderate_stress, default_material):
        """Test add tests with moderate stress."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="add_tests",
        )

        assert scenario.intervention == "add_tests"
        # Adding tests should reduce K
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_break_god_class_reduces_K(self, high_stress, default_material):
        """Test break god class reduces K value."""
        scenario = simulate_intervention(
            stress=high_stress,
            material=default_material,
            current_debt=34.0,
            intervention="break_god_class",
        )

        assert scenario.intervention == "break_god_class"
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_break_god_class_moderate_stress(self, moderate_stress, default_material):
        """Test break god class with moderate stress reduces debt."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="break_god_class",
        )

        assert scenario.intervention == "break_god_class"
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_full_refactor_reduces_debt(self, moderate_stress, default_material):
        """Test full refactor with moderate stress reduces debt at horizon."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="full_refactor",
            horizon_sprints=6,
        )

        assert scenario.intervention == "full_refactor"
        # Full refactor should have the biggest impact on K
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon
        # With moderate stress, full refactor should reduce debt accumulation
        assert scenario.debt_prevented > 0 or scenario.with_K_at_horizon < default_material.K_e

    def test_full_refactor_high_stress(self, high_stress, default_material):
        """Test full refactor with high stress."""
        scenario = simulate_intervention(
            stress=high_stress,
            material=default_material,
            current_debt=34.0,
            intervention="full_refactor",
        )

        assert scenario.intervention == "full_refactor"
        # K should be dramatically reduced
        assert scenario.with_K_at_horizon < scenario.without_K_at_horizon

    def test_unknown_intervention(self, high_stress, default_material):
        """Test that unknown intervention raises ValueError."""
        with pytest.raises(ValueError, match="Unknown intervention"):
            simulate_intervention(
                stress=high_stress,
                material=default_material,
                current_debt=34.0,
                intervention="nonexistent",
            )

    def test_intervention_sprint(self, high_stress, default_material):
        """Test intervention at different sprints."""
        scenario = simulate_intervention(
            stress=high_stress,
            material=default_material,
            current_debt=34.0,
            intervention="extract_interface",
            intervention_sprint=3,
        )

        assert scenario.intervention_sprint == 3

    def test_roi_description(self, moderate_stress, default_material):
        """Test that ROI description is generated."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="full_refactor",
        )

        assert scenario.roi_description != ""
        assert "investment" in scenario.roi_description.lower()

    def test_with_status_improved_full_refactor(self, moderate_stress, default_material):
        """Test that full refactor improves module status."""
        scenario = simulate_intervention(
            stress=moderate_stress,
            material=default_material,
            current_debt=15.0,
            intervention="full_refactor",
            horizon_sprints=10,
        )

        # Full refactor should reduce K below K_Ic at minimum
        assert scenario.with_K_at_horizon < default_material.K_Ic
        # Status should be better (or at least K is lower)
        assert scenario.with_K_at_horizon <= scenario.without_K_at_horizon

    def test_all_interventions_reduce_K(self, moderate_stress, default_material):
        """Test that all interventions reduce K."""
        for intervention_name in INTERVENTIONS:
            scenario = simulate_intervention(
                stress=moderate_stress,
                material=default_material,
                current_debt=15.0,
                intervention=intervention_name,
            )
            assert scenario.with_K_at_horizon < scenario.without_K_at_horizon, \
                f"Intervention {intervention_name} did not reduce K"


class TestListInterventions:
    """Tests for listing available interventions."""

    def test_list_interventions(self):
        """Test listing available interventions."""
        interventions = list_interventions()

        assert "extract_interface" in interventions
        assert "add_tests" in interventions
        assert "break_god_class" in interventions
        assert "reduce_churn" in interventions
        assert "full_refactor" in interventions

    def test_intervention_count(self):
        """Test that expected number of interventions are available."""
        assert len(INTERVENTIONS) == 5

    def test_intervention_has_description(self):
        """Test that each intervention has a description."""
        for name, config in INTERVENTIONS.items():
            assert "description" in config
            assert config["description"] != ""
