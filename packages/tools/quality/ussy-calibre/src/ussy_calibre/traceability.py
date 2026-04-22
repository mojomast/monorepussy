"""Traceability Auditor — Calibration Traceability Chain.

A traceability chain is an unbroken sequence of calibrations linking a
measurement to a reference standard, with documented uncertainty at each level.

Chain levels (from top to bottom):
  1. stakeholder_need  → SI Unit / NMI standard
  2. specification     → Primary standard
  3. acceptance_criteria → Secondary standard
  4. test_plan         → Working standard
  5. assertion         → Instrument reading

Chain uncertainty: u_chain = sqrt(u²_level1 + u²_level2 + ... + u²_levelN)

Orphan detection: tests with no chain (no requirement linkage)
Stale chain alerts: requirements past their review interval
Chain integrity score: based on completeness and cumulative uncertainty
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set

from ussy_calibre.models import TraceabilityLink, TraceabilityResult


# Ordered chain levels from highest to lowest
CHAIN_LEVELS = [
    "stakeholder_need",
    "specification",
    "acceptance_criteria",
    "test_plan",
    "assertion",
]


def compute_chain_uncertainty(links: List[TraceabilityLink]) -> float:
    """Compute cumulative chain uncertainty.

    u_chain = sqrt(sum(u_i^2))
    """
    if not links:
        return float("inf")  # No chain = infinite uncertainty
    return math.sqrt(sum(link.uncertainty**2 for link in links))


def detect_orphan(links: List[TraceabilityLink]) -> bool:
    """Detect if a test is an orphan (has no traceability chain)."""
    return len(links) == 0


def detect_stale_links(
    links: List[TraceabilityLink],
    now: Optional[datetime] = None,
) -> List[str]:
    """Detect stale traceability links past their review interval.

    Returns list of stale reference IDs.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stale: List[str] = []
    for link in links:
        if link.last_verified is not None:
            age = (now - link.last_verified).days
            if age > link.review_interval_days:
                stale.append(link.reference)
        else:
            # Never verified = always stale
            stale.append(link.reference)

    return stale


def check_chain_completeness(links: List[TraceabilityLink]) -> float:
    """Check how complete a traceability chain is.

    Returns a score from 0.0 to 1.0 based on how many required levels
    are present in the chain.
    """
    if not links:
        return 0.0

    present_levels: Set[str] = set()
    for link in links:
        present_levels.add(link.level)

    present_count = sum(1 for level in CHAIN_LEVELS if level in present_levels)
    return present_count / len(CHAIN_LEVELS)


def compute_integrity_score(
    completeness: float,
    chain_uncertainty: float,
    has_stale: bool,
) -> float:
    """Compute overall chain integrity score.

    Factors:
    - Completeness (0-1): how many levels are present
    - Uncertainty penalty: higher uncertainty = lower score
    - Stale penalty: stale links reduce score

    Score is 0.0 to 1.0.
    """
    score = completeness

    # Uncertainty penalty: reduce by factor based on chain uncertainty
    # A chain with u > 0.5 is considered very uncertain
    uncertainty_penalty = min(chain_uncertainty / 0.5, 1.0) * 0.3
    score -= uncertainty_penalty

    # Stale penalty
    if has_stale:
        score -= 0.2

    return max(0.0, min(1.0, score))


def audit_traceability(
    test_name: str,
    links: List[TraceabilityLink],
    now: Optional[datetime] = None,
) -> TraceabilityResult:
    """Perform a complete traceability audit for a test.

    Args:
        test_name: Name of the test being audited.
        links: Traceability chain links for this test.
        now: Current time (defaults to UTC now).
    """
    is_orphan = detect_orphan(links)
    stale = detect_stale_links(links, now)
    has_stale = len(stale) > 0
    chain_uncertainty = compute_chain_uncertainty(links)
    completeness = check_chain_completeness(links)
    integrity_score = compute_integrity_score(
        completeness, chain_uncertainty if chain_uncertainty != float("inf") else 1.0, has_stale
    )

    # Diagnosis
    if is_orphan:
        diagnosis = "ORPHAN TEST: No traceability chain — assertion has no requirement linkage"
    elif has_stale:
        diagnosis = (
            f"STALE CHAIN: {len(stale)} link(s) past review interval. "
            f"Chain uncertainty u_chain={chain_uncertainty:.4f}. "
            f"Re-verify stale requirements."
        )
    elif completeness < 0.6:
        diagnosis = (
            f"INCOMPLETE CHAIN: Only {completeness:.0%} of levels present. "
            f"Gap in traceability — some links are missing."
        )
    elif chain_uncertainty > 0.3:
        diagnosis = (
            f"HIGH CHAIN UNCERTAINTY: u_chain={chain_uncertainty:.4f}. "
            f"Cumulative ambiguity is too high — tighten specifications."
        )
    else:
        diagnosis = (
            f"Chain integrity: {integrity_score:.2f}. "
            f"u_chain={chain_uncertainty:.4f}. Traceability is adequate."
        )

    return TraceabilityResult(
        test_name=test_name,
        chain=links,
        chain_uncertainty=chain_uncertainty,
        is_orphan=is_orphan,
        has_stale_links=has_stale,
        integrity_score=integrity_score,
        stale_links=stale,
        diagnosis=diagnosis,
    )


def format_traceability(result: TraceabilityResult) -> str:
    """Format a traceability audit result as a readable report."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Traceability Audit: {result.test_name}")
    lines.append(f"{'='*60}")
    lines.append("")

    if result.is_orphan:
        lines.append("  ⚠ ORPHAN TEST — No traceability chain")
        lines.append("")
    else:
        lines.append("  Chain:")
        for link in result.chain:
            verified = (
                link.last_verified.strftime("%Y-%m-%d") if link.last_verified else "NEVER"
            )
            lines.append(
                f"    {link.level:<22} → {link.reference:<20} "
                f"u={link.uncertainty:.4f}  verified={verified}"
            )
        lines.append("")
        lines.append(f"  Chain uncertainty: u_chain = {result.chain_uncertainty:.4f}")
        lines.append(f"  Completeness: {check_chain_completeness(result.chain):.0%}")
        lines.append(f"  Integrity score: {result.integrity_score:.2f}")

        if result.stale_links:
            lines.append(f"  Stale links: {', '.join(result.stale_links)}")

    lines.append("")
    lines.append(f"  Diagnosis: {result.diagnosis}")
    lines.append("")

    return "\n".join(lines)
