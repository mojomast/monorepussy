"""Decay predictor — forecasts when modules will fail.

Uses Paris' Law to project crack growth over time and predict
time-to-failure for each module.
"""

from __future__ import annotations

import math
from typing import Optional

from .models import (
    Crack,
    CrackArrestStrategy,
    CrackType,
    DecayPrediction,
    MaterialConstants,
    ModuleStatus,
    StressIntensity,
)

# Maximum K value to prevent numerical overflow
MAX_K = 200.0
# Maximum growth rate per cycle to prevent overflow
MAX_GROWTH_RATE = 50.0


def predict_decay(
    stress: StressIntensity,
    material: MaterialConstants,
    current_debt: float,
    cycles_per_week: float = 2.0,
    weeks_per_sprint: float = 2.0,
    critical_debt: float = 100.0,
    horizon_sprints: int = 10,
) -> DecayPrediction:
    """Predict decay trajectory for a module.

    Args:
        stress: Current stress intensity for the module.
        material: Material constants (C, m, K_Ic, K_e).
        current_debt: Current debt magnitude.
        cycles_per_week: Number of load cycles per week.
        weeks_per_sprint: Number of weeks per sprint.
        critical_debt: Debt threshold for critical failure.
        horizon_sprints: How many sprints to project.

    Returns:
        DecayPrediction with trajectory and time-to-failure.
    """
    K = min(stress.K, MAX_K)
    delta_K = abs(stress.delta_K) if stress.delta_K > 0 else K

    # Compute growth rate
    if K <= material.K_e:
        # Below endurance limit: no fatigue growth
        growth_rate = 0.0
        status = ModuleStatus.STABLE
    elif K >= material.K_Ic:
        # Above fracture toughness: catastrophic growth
        growth_rate = min(material.C * (delta_K ** material.m) * 2.0, MAX_GROWTH_RATE)
        status = ModuleStatus.CATASTROPHIC
    else:
        # Normal Paris' Law growth
        growth_rate = min(material.C * (delta_K ** material.m), MAX_GROWTH_RATE)
        # Check if accelerating
        if growth_rate > 1.0:
            status = ModuleStatus.CRITICAL
        else:
            status = ModuleStatus.GROWING

    # Project trajectory
    trajectory: list[tuple[int, float]] = []
    debt = current_debt

    for sprint in range(1, horizon_sprints + 1):
        cycles_in_sprint = cycles_per_week * weeks_per_sprint

        if K >= material.K_Ic:
            # Above fracture toughness: growth accelerates
            for _ in range(int(cycles_in_sprint)):
                debt += growth_rate
                # K increases as debt grows (positive feedback)
                K = min(K + growth_rate * 0.01, MAX_K)
                growth_rate = min(material.C * (K ** material.m) * 2.0, MAX_GROWTH_RATE)
                # Cap debt to prevent overflow
                if debt >= critical_debt * 5:
                    debt = critical_debt * 5
                    break
        elif K > material.K_e:
            # Normal growth
            for _ in range(int(cycles_in_sprint)):
                debt += growth_rate
                K = min(K + growth_rate * 0.005, MAX_K)
                growth_rate = min(material.C * (K ** material.m), MAX_GROWTH_RATE)
        else:
            # No growth below endurance limit
            pass

        trajectory.append((sprint, round(debt, 2)))

    # Compute time to critical debt
    time_to_critical_cycles = None
    time_to_critical_weeks = None
    time_to_critical_sprints = None

    if growth_rate > 0:
        for sprint, projected_debt in trajectory:
            if projected_debt >= critical_debt:
                time_to_critical_sprints = float(sprint)
                time_to_critical_weeks = sprint * weeks_per_sprint
                time_to_critical_cycles = time_to_critical_weeks * cycles_per_week
                break

    return DecayPrediction(
        file_path=stress.file_path,
        current_debt=round(current_debt, 2),
        current_K=round(stress.K, 2),
        growth_rate=round(growth_rate, 4),
        cycles_per_week=cycles_per_week,
        status=status,
        time_to_critical_cycles=round(time_to_critical_cycles, 1) if time_to_critical_cycles else None,
        time_to_critical_weeks=round(time_to_critical_weeks, 1) if time_to_critical_weeks else None,
        time_to_critical_sprints=round(time_to_critical_sprints, 1) if time_to_critical_sprints else None,
        trajectory=trajectory,
    )


def estimate_debt_from_cracks(cracks: list[Crack]) -> float:
    """Estimate debt magnitude from detected cracks.

    Each crack contributes severity as debt units.
    """
    return sum(crack.severity for crack in cracks)


def recommend_arrest_strategies(
    stress: StressIntensity,
    metrics=None,
) -> list[CrackArrestStrategy]:
    """Recommend crack arrest strategies to reduce stress intensity.

    Strategies reduce K proportionally based on the component they target.

    Args:
        stress: Current stress intensity.
        metrics: Optional module metrics for context.

    Returns:
        List of recommended CrackArrestStrategy objects.
    """
    strategies: list[CrackArrestStrategy] = []
    K = stress.K

    # Strategy 1: Extract interface (reduces coupling by ~60%)
    # K is proportional to coupling, so reducing coupling reduces K proportionally
    coupling_factor = 0.4  # 60% reduction in coupling
    K_after = _proportional_K_reduction(stress, coupling_factor=coupling_factor)
    reduction = K - K_after
    strategies.append(CrackArrestStrategy(
        name="Extract interface",
        description=f"Reduces coupling: K {K:.1f}→{K_after:.1f}",
        K_reduction=round(reduction, 1),
        impact="HIGH" if reduction > 10 else "MED" if reduction > 3 else "LOW",
    ))

    # Strategy 2: Add integration tests (increases coverage, reduces stress)
    # K is inversely proportional to coverage; moving from current to 80% coverage
    current_coverage = stress.coverage_component
    target_coverage = 0.9  # 80% coverage + 0.1 buffer
    K_after = K * current_coverage / target_coverage if target_coverage > 0 else K
    reduction = K - K_after
    strategies.append(CrackArrestStrategy(
        name="Add integration tests",
        description=f"Reduces stress: K {K:.1f}→{K_after:.1f}",
        K_reduction=round(max(reduction, 0), 1),
        impact="HIGH" if reduction > 8 else "MED" if reduction > 2 else "LOW",
    ))

    # Strategy 3: Break god class into smaller modules (reduces complexity by ~50%)
    complexity_factor = 0.5  # 50% reduction in complexity
    K_after = _proportional_K_reduction(stress, complexity_factor=complexity_factor)
    reduction = K - K_after
    strategies.append(CrackArrestStrategy(
        name="Break god class into modules",
        description=f"Reduces complexity: K {K:.1f}→{K_after:.1f}",
        K_reduction=round(reduction, 1),
        impact="HIGH" if reduction > 10 else "MED" if reduction > 3 else "LOW",
    ))

    # Sort by impact
    impact_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    strategies.sort(key=lambda s: impact_order.get(s.impact, 3))

    return strategies


def _proportional_K_reduction(
    stress: StressIntensity,
    coupling_factor: float = 1.0,
    churn_factor: float = 1.0,
    complexity_factor: float = 1.0,
) -> float:
    """Compute K after proportional reduction of components.

    Since K = coupling * churn * complexity / coverage, reducing any
    numerator component by a factor f reduces K by the same factor.

    Args:
        stress: Current stress intensity.
        coupling_factor: New coupling as fraction of current (0-1).
        churn_factor: New churn as fraction of current (0-1).
        complexity_factor: New complexity as fraction of current (0-1).

    Returns:
        New K value after proportional reduction.
    """
    K = stress.K
    # Each factor reduces K proportionally
    K_after = K * coupling_factor * churn_factor * complexity_factor
    return round(K_after, 2)


def _recompute_K(
    stress: StressIntensity,
    coupling_factor: Optional[float] = None,
    churn_factor: Optional[float] = None,
    complexity_factor: Optional[float] = None,
    coverage_factor: Optional[float] = None,
) -> float:
    """Recompute K with modified factors.

    Uses proportional reduction: K_after = K * (coupling_ratio * churn_ratio * complexity_ratio / coverage_ratio)
    """
    K = stress.K

    if coupling_factor is not None:
        K = K * coupling_factor / max(stress.coupling_component, 0.1)
    if churn_factor is not None:
        K = K * churn_factor / max(stress.churn_component, 0.1)
    if complexity_factor is not None:
        K = K * complexity_factor / max(stress.complexity_component, 0.1)
    if coverage_factor is not None:
        K = K * stress.coverage_component / max(coverage_factor, 0.1)

    return round(K, 2)
