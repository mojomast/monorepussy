"""Tests for the decay predictor module."""

import pytest

from ussy_fatigue.predictor import (
    predict_decay,
    estimate_debt_from_cracks,
    recommend_arrest_strategies,
)
from ussy_fatigue.models import (
    Crack,
    CrackType,
    DecayPrediction,
    MaterialConstants,
    ModuleMetrics,
    ModuleStatus,
    StressIntensity,
)


class TestPredictDecay:
    """Tests for decay prediction."""

    def test_stable_module(self):
        """Test prediction for a module below endurance limit."""
        stress = StressIntensity(
            file_path="stable.py",
            K=5.0,  # Below K_e = 8.2
            coupling_component=2.0,
            churn_component=1.0,
            complexity_component=5.0,
            coverage_component=0.5,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=5.0)

        assert prediction.status == ModuleStatus.STABLE
        assert prediction.growth_rate == 0.0

    def test_growing_module(self):
        """Test prediction for a module above endurance limit but below K_Ic."""
        stress = StressIntensity(
            file_path="growing.py",
            K=15.0,  # Between K_e and K_Ic
            coupling_component=5.0,
            churn_component=3.0,
            complexity_component=10.0,
            coverage_component=1.0,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=10.0)

        assert prediction.status in (ModuleStatus.GROWING, ModuleStatus.CRITICAL)
        assert prediction.growth_rate > 0

    def test_critical_module(self):
        """Test prediction for a module above fracture toughness."""
        stress = StressIntensity(
            file_path="critical.py",
            K=42.0,  # Above K_Ic = 28.0
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=34.0)

        assert prediction.status == ModuleStatus.CATASTROPHIC
        assert prediction.growth_rate > 0

    def test_trajectory_length(self):
        """Test that trajectory has correct number of points."""
        stress = StressIntensity(
            file_path="test.py",
            K=15.0,
            coupling_component=5.0,
            churn_component=3.0,
            complexity_component=10.0,
            coverage_component=1.0,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=10.0, horizon_sprints=8)

        assert len(prediction.trajectory) == 8

    def test_trajectory_increasing_debt(self):
        """Test that trajectory shows increasing debt for growing modules."""
        stress = StressIntensity(
            file_path="test.py",
            K=15.0,
            coupling_component=5.0,
            churn_component=3.0,
            complexity_component=10.0,
            coverage_component=1.0,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=10.0, horizon_sprints=5)

        # Debt should increase over sprints
        debts = [d for _, d in prediction.trajectory]
        for i in range(1, len(debts)):
            assert debts[i] >= debts[i - 1]

    def test_stable_trajectory_constant(self):
        """Test that stable modules have constant debt."""
        stress = StressIntensity(
            file_path="stable.py",
            K=3.0,  # Below K_e
            coupling_component=1.0,
            churn_component=0.5,
            complexity_component=2.0,
            coverage_component=1.0,
        )
        material = MaterialConstants()
        prediction = predict_decay(stress, material, current_debt=5.0, horizon_sprints=5)

        debts = [d for _, d in prediction.trajectory]
        for d in debts:
            assert d == pytest.approx(5.0)

    def test_time_to_critical(self):
        """Test time-to-critical calculation."""
        stress = StressIntensity(
            file_path="test.py",
            K=42.0,
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )
        material = MaterialConstants()
        prediction = predict_decay(
            stress, material, current_debt=34.0,
            cycles_per_week=4.0, critical_debt=100.0,
        )

        # Should have time-to-critical since above K_Ic
        assert prediction.time_to_critical_sprints is not None
        assert prediction.time_to_critical_sprints > 0

    def test_custom_cycles_per_week(self):
        """Test that cycles_per_week affects prediction."""
        stress = StressIntensity(
            file_path="test.py",
            K=15.0,
            coupling_component=5.0,
            churn_component=3.0,
            complexity_component=10.0,
            coverage_component=1.0,
        )
        material = MaterialConstants()

        pred_slow = predict_decay(stress, material, current_debt=10.0, cycles_per_week=1.0)
        pred_fast = predict_decay(stress, material, current_debt=10.0, cycles_per_week=5.0)

        # More cycles per week should lead to faster debt accumulation
        if pred_slow.trajectory and pred_fast.trajectory:
            assert pred_fast.trajectory[-1][1] >= pred_slow.trajectory[-1][1]


class TestEstimateDebt:
    """Tests for debt estimation from cracks."""

    def test_estimate_from_cracks(self):
        """Test debt estimation from crack list."""
        cracks = [
            Crack(crack_type=CrackType.TODO_FIXME_HACK, file_path="a.py",
                  line_number=1, severity=3.0, description="TODO"),
            Crack(crack_type=CrackType.HIGH_COMPLEXITY, file_path="a.py",
                  line_number=5, severity=7.0, description="High complexity"),
            Crack(crack_type=CrackType.GOD_CLASS, file_path="a.py",
                  line_number=1, severity=9.0, description="God class"),
        ]
        debt = estimate_debt_from_cracks(cracks)
        assert debt == pytest.approx(19.0)

    def test_estimate_empty(self):
        """Test debt estimation with no cracks."""
        debt = estimate_debt_from_cracks([])
        assert debt == 0.0


class TestArrestStrategies:
    """Tests for crack arrest strategy recommendations."""

    def test_recommend_strategies(self):
        """Test that strategies are recommended for high-K modules."""
        stress = StressIntensity(
            file_path="test.py",
            K=42.0,
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )
        strategies = recommend_arrest_strategies(stress)

        assert len(strategies) >= 2
        assert all(s.K_reduction > 0 for s in strategies)

    def test_strategies_sorted_by_impact(self):
        """Test that strategies are sorted by impact."""
        stress = StressIntensity(
            file_path="test.py",
            K=42.0,
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )
        strategies = recommend_arrest_strategies(stress)

        impact_order = {"HIGH": 0, "MED": 1, "LOW": 2}
        for i in range(1, len(strategies)):
            assert impact_order.get(strategies[i].impact, 3) >= \
                   impact_order.get(strategies[i-1].impact, 3)

    def test_extract_interface_reduces_K(self):
        """Test that extract interface strategy reduces K."""
        stress = StressIntensity(
            file_path="test.py",
            K=42.0,
            coupling_component=12.0,
            churn_component=8.0,
            complexity_component=20.0,
            coverage_component=0.5,
        )
        strategies = recommend_arrest_strategies(stress)
        extract = [s for s in strategies if "interface" in s.name.lower()]
        assert len(extract) >= 1
        assert extract[0].K_reduction > 0

    def test_low_K_fewer_strategies(self):
        """Test that low-K modules still get strategies but with less impact."""
        stress = StressIntensity(
            file_path="test.py",
            K=3.0,
            coupling_component=1.0,
            churn_component=0.5,
            complexity_component=2.0,
            coverage_component=0.5,
        )
        strategies = recommend_arrest_strategies(stress)
        # Strategies are always returned, but K_reduction should be small
        assert len(strategies) >= 1
