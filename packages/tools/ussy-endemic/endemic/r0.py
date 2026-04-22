"""R0 estimation — calculate basic reproduction number from transmission trees."""

from __future__ import annotations

import math
from typing import Optional

from endemic.models import Pattern, PatternStatus, TransmissionTree


def estimate_r0_from_tree(tree: TransmissionTree) -> float:
    """Estimate R0 from the branching factor of a transmission tree.

    R0 = average number of secondary infections per source module.
    Uses maximum likelihood estimation from the transmission tree.
    """
    if not tree.events:
        return 0.0

    # Count how many times each source module appears
    source_counts: dict[str, int] = {}
    for event in tree.events:
        source_counts[event.source_module] = source_counts.get(event.source_module, 0) + 1

    if not source_counts:
        return 0.0

    # Also include the index case if it was a source
    if tree.index_case:
        # The index case might not appear as source in events
        # if no events traced back to it explicitly
        pass

    # Calculate average branching factor
    total_secondary = sum(source_counts.values())
    num_sources = len(source_counts)

    # Include index case as a source (it produced some infections)
    # Check if index_case is already in source_counts
    if tree.index_case and tree.index_case not in source_counts:
        # Count events where source is index_case
        index_infections = sum(
            1 for e in tree.events if e.source_module == tree.index_case
        )
        if index_infections > 0:
            total_secondary += index_infections  # already counted above
        else:
            # Index case had no tracked secondary infections from events
            pass

    r0 = total_secondary / num_sources if num_sources > 0 else 0.0
    return round(r0, 2)


def estimate_r0_from_counts(new_infections: int, existing_infections: int,
                            period_length: int = 1) -> float:
    """Estimate R0 from infection counts over a period.

    R0 = new_infections / existing_infections per period.
    """
    if existing_infections == 0:
        return 0.0
    return round(new_infections / existing_infections, 2)


def estimate_r0_mle(secondary_counts: list[int]) -> float:
    """Estimate R0 using maximum likelihood from a list of secondary infection counts.

    Assumes negative binomial distribution.
    Simple version: just use the mean.
    """
    if not secondary_counts:
        return 0.0
    return round(sum(secondary_counts) / len(secondary_counts), 2)


def determine_status(r0: float, prevalence_ratio: float) -> PatternStatus:
    """Determine the epidemiological status of a pattern.

    - SPREADING: R0 > 1 and not yet saturated
    - ENDEMIC: R0 ≈ 1 (between 0.9 and 1.1) or pattern is at high prevalence
    - DYING: R0 < 0.9
    - ELIMINATED: R0 ≈ 0 and prevalence ≈ 0
    """
    if r0 < 0.05 and prevalence_ratio < 0.01:
        return PatternStatus.ELIMINATED
    if r0 < 0.9:
        return PatternStatus.DYING
    if r0 <= 1.1:
        return PatternStatus.ENDEMIC
    if prevalence_ratio > 0.8:
        # Even with R0 > 1, if most modules are infected, it's endemic
        return PatternStatus.ENDEMIC
    return PatternStatus.SPREADING


def compute_r0_for_patterns(patterns: list[Pattern],
                            trees: Optional[dict[str, TransmissionTree]] = None,
                            infection_history: Optional[dict[str, dict]] = None) -> list[Pattern]:
    """Compute R0 and status for a list of patterns.

    If transmission trees are available, use branching factor method.
    If infection_history is provided, use the ratio method.
    Otherwise, estimate from prevalence.
    """
    result = []

    for pattern in patterns:
        r0 = 0.0

        if trees and pattern.name in trees:
            r0 = estimate_r0_from_tree(trees[pattern.name])
        elif infection_history and pattern.name in infection_history:
            hist = infection_history[pattern.name]
            new = hist.get("new_infections", 0)
            existing = hist.get("existing_infections", 0)
            r0 = estimate_r0_from_counts(new, existing)
        else:
            # Estimate from prevalence using logistic model
            # If prevalence is high, R0 was likely high
            # Simple heuristic: R0 ≈ -ln(1 - prevalence_ratio) for early stages
            if pattern.prevalence_ratio < 0.99:
                try:
                    r0 = -math.log(1 - pattern.prevalence_ratio) * 1.5
                except (ValueError, ZeroDivisionError):
                    r0 = 0.0
            else:
                r0 = 5.0  # Very high prevalence implies high R0
            r0 = round(r0, 2)

        status = determine_status(r0, pattern.prevalence_ratio)

        updated = Pattern(
            name=pattern.name,
            pattern_type=pattern.pattern_type,
            description=pattern.description,
            regex_pattern=pattern.regex_pattern,
            r0=r0,
            status=status,
            prevalence_count=pattern.prevalence_count,
            total_modules=pattern.total_modules,
        )
        result.append(updated)

    return result
