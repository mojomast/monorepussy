"""What-if analysis — simulates refactoring interventions.

Compares decay trajectory with and without an intervention,
computing ROI and recommended timing.
"""

from __future__ import annotations

from typing import Optional

from .models import (
    DecayPrediction,
    MaterialConstants,
    ModuleStatus,
    StressIntensity,
    WhatIfScenario,
)
from .predictor import predict_decay


# Intervention definitions: name -> factor adjustments
# Factors represent what fraction of the original component remains
INTERVENTIONS = {
    "extract_interface": {
        "coupling_factor": 0.25,   # Reduce coupling to 25% of original
        "description": "Extract interface from module",
    },
    "add_tests": {
        "coverage_ratio": 0.85,    # Target 85% coverage (adjusts coverage component)
        "description": "Add integration tests",
    },
    "break_god_class": {
        "complexity_factor": 0.40,  # Reduce complexity to 40% of original
        "description": "Break god class into smaller modules",
    },
    "reduce_churn": {
        "churn_factor": 0.50,      # Reduce churn to 50%
        "description": "Stabilize module (reduce change frequency)",
    },
    "full_refactor": {
        "coupling_factor": 0.20,
        "complexity_factor": 0.30,
        "coverage_ratio": 0.85,
        "description": "Full refactor (reduce coupling, complexity, add tests)",
    },
}


def simulate_intervention(
    stress: StressIntensity,
    material: MaterialConstants,
    current_debt: float,
    intervention: str,
    intervention_sprint: int = 1,
    horizon_sprints: int = 10,
    cycles_per_week: float = 2.0,
    weeks_per_sprint: float = 2.0,
    critical_debt: float = 100.0,
) -> WhatIfScenario:
    """Simulate a what-if intervention scenario.

    Args:
        stress: Current stress intensity.
        material: Material constants.
        current_debt: Current debt magnitude.
        intervention: Name of the intervention strategy.
        intervention_sprint: Sprint in which the intervention occurs.
        horizon_sprints: Total projection horizon.
        cycles_per_week: Load cycles per week.
        weeks_per_sprint: Weeks per sprint.
        critical_debt: Debt threshold for critical failure.

    Returns:
        WhatIfScenario comparing with/without intervention.
    """
    if intervention not in INTERVENTIONS:
        raise ValueError(
            f"Unknown intervention: {intervention}. "
            f"Available: {', '.join(INTERVENTIONS.keys())}"
        )

    intervention_config = INTERVENTIONS[intervention]

    # Predict without intervention
    without_prediction = predict_decay(
        stress=stress,
        material=material,
        current_debt=current_debt,
        cycles_per_week=cycles_per_week,
        weeks_per_sprint=weeks_per_sprint,
        critical_debt=critical_debt,
        horizon_sprints=horizon_sprints,
    )

    # Compute modified stress after intervention
    modified_stress = _apply_intervention(stress, intervention_config)

    # Predict with intervention
    with_prediction = predict_decay(
        stress=modified_stress,
        material=material,
        current_debt=current_debt,
        cycles_per_week=cycles_per_week,
        weeks_per_sprint=weeks_per_sprint,
        critical_debt=critical_debt,
        horizon_sprints=horizon_sprints,
    )

    # Get debt at horizon
    without_debt = without_prediction.trajectory[-1][1] if without_prediction.trajectory else current_debt
    with_debt = with_prediction.trajectory[-1][1] if with_prediction.trajectory else current_debt

    debt_prevented = without_debt - with_debt

    roi_desc = (
        f"{intervention_sprint}-sprint investment prevents "
        f"{debt_prevented:.1f} unit debt accumulation"
    )

    return WhatIfScenario(
        file_path=stress.file_path,
        intervention=intervention,
        intervention_sprint=intervention_sprint,
        without_debt_at_horizon=round(without_debt, 1),
        with_debt_at_horizon=round(with_debt, 1),
        debt_prevented=round(debt_prevented, 1),
        without_K_at_horizon=round(stress.K, 1),
        with_K_at_horizon=round(modified_stress.K, 1),
        without_status=without_prediction.status,
        with_status=with_prediction.status,
        roi_description=roi_desc,
    )


def _apply_intervention(
    stress: StressIntensity,
    config: dict,
) -> StressIntensity:
    """Apply intervention factors to stress intensity.

    Uses proportional K reduction: K is proportional to each numerator
    component and inversely proportional to coverage.

    Args:
        stress: Original stress intensity.
        config: Intervention configuration with factor adjustments.

    Returns:
        Modified StressIntensity after intervention.
    """
    K = stress.K

    # Apply proportional reductions for numerator components
    if "coupling_factor" in config:
        K *= config["coupling_factor"]
    if "churn_factor" in config:
        K *= config["churn_factor"]
    if "complexity_factor" in config:
        K *= config["complexity_factor"]

    # For coverage: K is inversely proportional to coverage
    # coverage_ratio = target coverage; increasing coverage reduces K
    if "coverage_ratio" in config:
        target_coverage = config["coverage_ratio"] + 0.1  # Add 0.1 buffer
        current_coverage = stress.coverage_component
        if target_coverage > current_coverage and current_coverage > 0:
            K *= current_coverage / target_coverage

    K = round(K, 2)

    # Compute modified components
    coupling = stress.coupling_component * config.get("coupling_factor", 1.0)
    churn = stress.churn_component * config.get("churn_factor", 1.0)
    complexity = stress.complexity_component * config.get("complexity_factor", 1.0)
    coverage = stress.coverage_component
    if "coverage_ratio" in config:
        coverage = config["coverage_ratio"] + 0.1

    return StressIntensity(
        file_path=stress.file_path,
        K=K,
        delta_K=round(K - stress.K, 2),
        coupling_component=round(coupling, 2),
        churn_component=round(churn, 2),
        complexity_component=round(complexity, 2),
        coverage_component=round(coverage, 2),
    )


def list_interventions() -> dict[str, str]:
    """Return available interventions with descriptions."""
    return {name: cfg["description"] for name, cfg in INTERVENTIONS.items()}
