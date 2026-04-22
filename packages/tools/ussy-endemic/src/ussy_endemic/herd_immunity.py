"""Herd immunity — calculate vaccination thresholds for code patterns."""

from __future__ import annotations

import math
from typing import Optional

from ussy_endemic.models import (
    HerdImmunityResult,
    Module,
    Pattern,
    VaccinationStrategy,
)


def herd_immunity_threshold(r0: float) -> float:
    """Calculate herd immunity threshold.

    HIT = 1 - 1/R0

    If R0 <= 1, threshold is 0 (no vaccination needed — disease dies out).
    """
    if r0 <= 1.0:
        return 0.0
    return 1.0 - (1.0 / r0)


def calculate_herd_immunity(pattern: Pattern,
                            immune_modules: int = 0,
                            total_modules: Optional[int] = None) -> HerdImmunityResult:
    """Calculate herd immunity analysis for a pattern.

    Args:
        pattern: The pattern to analyze.
        immune_modules: Number of modules currently immune (recovered).
        total_modules: Total number of modules (overrides pattern.total_modules).

    Returns:
        HerdImmunityResult with full analysis.
    """
    total = total_modules or pattern.total_modules
    if total == 0:
        total = 1  # Avoid division by zero

    threshold = herd_immunity_threshold(pattern.r0)
    modules_needed = math.ceil(threshold * total)
    modules_to_vaccinate = max(0, modules_needed - immune_modules)

    return HerdImmunityResult(
        pattern_name=pattern.name,
        r0=pattern.r0,
        threshold=threshold,
        current_immune_count=immune_modules,
        total_modules=total,
        modules_to_vaccinate=modules_to_vaccinate,
    )


def generate_vaccination_strategies(
    result: HerdImmunityResult,
    modules: list[Module],
    superspreader_modules: Optional[list[tuple[str, int]]] = None,
    developer_infections: Optional[dict[str, int]] = None,
) -> list[VaccinationStrategy]:
    """Generate ranked vaccination strategies.

    Strategies prioritize superspreaders, cross-domain modules,
    and high-traffic developers.

    Args:
        result: Herd immunity result.
        modules: List of all modules.
        superspreader_modules: List of (module_path, infection_count).
        developer_infections: Dict of developer -> infection count.

    Returns:
        List of VaccinationStrategy ranked by efficiency.
    """
    strategies = []
    rank = 1

    # Strategy 1: Refactor superspreader modules
    if superspreader_modules:
        for mod_path, inf_count in superspreader_modules[:3]:
            # Superspreader is equivalent to many random vaccinations
            equivalent = max(1, inf_count // 2)
            effort = 1.0 + inf_count * 0.3  # Rough estimate
            strategies.append(VaccinationStrategy(
                target=f"Refactor {mod_path} (superspreader)",
                action=f"Refactor module to remove pattern and adopt protective pattern",
                prevented_infections=inf_count,
                effort_hours=effort,
                equivalent_random_vaccinations=equivalent,
                rank=rank,
            ))
            rank += 1

    # Strategy 2: Cross-domain vaccination (block zoonotic jumps)
    domains = set()
    for m in modules:
        if m.domain and m.compartment.value == "I":
            domains.add(m.domain)

    if len(domains) >= 2:
        domain_list = sorted(domains)
        strategies.append(VaccinationStrategy(
            target=f"Add protective patterns to {domain_list[0]} boundary modules",
            action="Add domain-specific patterns to block cross-domain spread",
            prevented_infections=max(1, len(modules) // 5),
            effort_hours=4.0,
            equivalent_random_vaccinations=max(1, len(modules) // 8),
            rank=rank,
        ))
        rank += 1

    # Strategy 3: Developer coaching for high-infection developers
    if developer_infections:
        sorted_devs = sorted(developer_infections.items(), key=lambda x: -x[1])
        for email, count in sorted_devs[:2]:
            if count >= 3:
                strategies.append(VaccinationStrategy(
                    target=f"Developer coaching for {email}",
                    action="Training on replacement patterns to reduce developer-level transmission",
                    prevented_infections=count,
                    effort_hours=1.0,
                    equivalent_random_vaccinations=max(1, count),
                    rank=rank,
                ))
                rank += 1

    return strategies


def calculate_combined_effort(strategies: list[VaccinationStrategy],
                              total_infected: int,
                              hours_per_refactor: float = 2.0) -> dict:
    """Calculate combined strategy efficiency vs. full refactor.

    Returns dict with:
        combined_hours: Total hours for all strategies
        full_refactor_hours: Hours to refactor all infected modules
        savings: Hours saved
        strategies_needed: Number of strategies needed for herd immunity
    """
    if not strategies:
        return {
            "combined_hours": 0.0,
            "full_refactor_hours": total_infected * hours_per_refactor,
            "savings": 0.0,
            "strategies_needed": 0,
        }

    combined_hours = sum(s.effort_hours for s in strategies)
    full_refactor_hours = total_infected * hours_per_refactor

    return {
        "combined_hours": combined_hours,
        "full_refactor_hours": full_refactor_hours,
        "savings": full_refactor_hours - combined_hours,
        "strategies_needed": len(strategies),
    }
