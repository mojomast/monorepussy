"""Good pathogen promotion — model and accelerate the spread of best practices."""

from __future__ import annotations

import math
from typing import Optional

from endemic.models import (
    Module,
    Pattern,
    PatternType,
    PromoteResult,
)
from endemic.sir_model import compute_beta, simulate_sir


def find_optimal_seed(
    pattern: Pattern,
    modules: list[Module],
    infected_modules: Optional[set[str]] = None,
) -> str:
    """Find the optimal module to seed a good pattern.

    The optimal seed is the susceptible module with the highest
    developer traffic and most dependents — it will spread the
    pattern fastest.
    """
    if infected_modules is None:
        infected_modules = set()
        for m in modules:
            if pattern.name in m.patterns:
                infected_modules.add(m.path)

    susceptible = [
        m for m in modules
        if m.path not in infected_modules and pattern.name not in m.patterns
    ]

    if not susceptible:
        # All modules infected, find the one with highest traffic
        if modules:
            return max(modules, key=lambda m: m.developer_traffic + m.dependents).path
        return ""

    # Score each susceptible module by traffic * dependents
    best = max(
        susceptible,
        key=lambda m: (m.developer_traffic + 1) * (m.dependents + 1),
    )
    return best.path


def predict_r0_increase(
    pattern: Pattern,
    seed_module: str,
    modules: list[Module],
) -> float:
    """Predict how much R0 would increase by seeding a module.

    The increase is proportional to the seed module's traffic and
    the current fraction of susceptible modules.
    """
    infected_count = sum(1 for m in modules if pattern.name in m.patterns)
    n = len(modules)
    if n == 0:
        return 0.0

    susceptible_fraction = (n - infected_count - 1) / n

    # Find the seed module's traffic multiplier
    seed_mod = None
    for m in modules:
        if m.path == seed_module:
            seed_mod = m
            break

    traffic = seed_mod.developer_traffic if seed_mod else 1
    dependents = seed_mod.dependents if seed_mod else 0

    # R0 increase is proportional to reach of seed module
    # Use a meaningful boost factor even for small codebases
    reach_factor = (1 + traffic * 0.1 + dependents * 0.05)
    boost = reach_factor * max(susceptible_fraction, 1.0 / n) * (1 + pattern.r0 * 0.1)
    return round(max(0.0, boost), 2)


def compute_cross_protection(
    good_pattern: Pattern,
    bad_patterns: list[Pattern],
    modules: list[Module],
) -> dict[str, float]:
    """Compute how much a good pattern protects against bad patterns.

    Cross-protection = fraction of modules with the good pattern
    that DON'T have the bad pattern, vs. overall bad pattern prevalence.

    Returns dict mapping bad_pattern_name -> protection_fraction (0-1).
    """
    protection = {}

    good_modules = {m.path for m in modules if good_pattern.name in m.patterns}

    for bad_pattern in bad_patterns:
        if bad_pattern.pattern_type != PatternType.BAD:
            continue

        bad_modules = {m.path for m in modules if bad_pattern.name in m.patterns}
        total_with_bad = len(bad_modules)

        if total_with_bad == 0 or len(good_modules) == 0:
            continue

        # Modules with good pattern that also have bad pattern
        overlap = good_modules & bad_modules
        bad_rate_in_good = len(overlap) / len(good_modules)

        # Overall bad rate
        overall_bad_rate = len(bad_modules) / len(modules) if modules else 0

        if overall_bad_rate > 0:
            # Protection = 1 - (bad_rate_in_good / overall_bad_rate)
            prot = 1.0 - (bad_rate_in_good / overall_bad_rate)
            protection[bad_pattern.name] = round(max(0.0, min(1.0, prot)), 2)

    return protection


def promote_pattern(
    pattern: Pattern,
    modules: list[Module],
    bad_patterns: Optional[list[Pattern]] = None,
    seed_path: Optional[str] = None,
    gamma: float = 0.1,
    horizon_weeks: int = 26,
) -> PromoteResult:
    """Analyze promotion strategy for a good pattern.

    Args:
        pattern: The good pattern to promote.
        modules: All modules in the codebase.
        bad_patterns: Bad patterns to check cross-protection against.
        seed_path: Explicit seed module (if None, auto-detect).
        gamma: Recovery rate for SIR model.
        horizon_weeks: Simulation horizon.

    Returns:
        PromoteResult with full analysis.
    """
    n = len(modules)
    if n == 0:
        return PromoteResult(pattern_name=pattern.name, current_r0=pattern.r0)

    # Count current prevalence
    infected_count = sum(1 for m in modules if pattern.name in m.patterns)
    total = n

    # Find optimal seed
    if not seed_path:
        seed_path = find_optimal_seed(pattern, modules)

    # Predict R0 increase
    r0_increase = predict_r0_increase(pattern, seed_path, modules)
    predicted_r0 = pattern.r0 + r0_increase

    # Simulate time to 80% prevalence with current R0
    current_sim = simulate_sir(
        n=total,
        initial_infected=max(1, infected_count),
        initial_recovered=0,
        r0=pattern.r0,
        gamma=gamma,
        horizon_steps=horizon_weeks,
    )

    time_to_80_current = _time_to_prevalence(current_sim, 0.8)

    # Simulate with seeding
    seeded_sim = simulate_sir(
        n=total,
        initial_infected=max(1, infected_count + 1),
        initial_recovered=0,
        r0=max(pattern.r0, predicted_r0),
        gamma=gamma,
        horizon_steps=horizon_weeks,
    )

    time_to_80_seeded = _time_to_prevalence(seeded_sim, 0.8)

    # Cross-protection
    cross_protection = {}
    if bad_patterns:
        cross_protection = compute_cross_protection(pattern, bad_patterns, modules)

    return PromoteResult(
        pattern_name=pattern.name,
        current_r0=pattern.r0,
        current_prevalence=infected_count,
        total_modules=total,
        optimal_seed_module=seed_path,
        predicted_r0_increase=r0_increase,
        time_to_80pct_weeks=time_to_80_seeded,
        time_to_80pct_without_seeding_weeks=time_to_80_current,
        cross_protection=cross_protection,
    )


def _time_to_prevalence(sim, target_frac: float) -> float:
    """Find the time step at which prevalence (I + R) reaches target_frac."""
    if not sim.states or sim.n == 0:
        return float("inf")

    for state in sim.states:
        prevalence = (state.i + state.r) / sim.n
        if prevalence >= target_frac:
            return state.time

    return float("inf")
