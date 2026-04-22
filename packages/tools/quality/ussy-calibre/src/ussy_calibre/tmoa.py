"""
TMOA — Test Minute of Angle (Scale-Invariant Quality Metric).

Normalizes test quality by codebase complexity, enabling
cross-project comparison. Analogous to MOA in precision shooting.
"""

from __future__ import annotations

import math
from typing import Sequence

from ussy_calibre.models import TMOAClass, TMOAResult


def compute_tmoa(sigma_t: float, n_dependencies: int) -> float:
    """
    Compute the Test Minute of Angle.

    TMOA = arctan(σ_T / √N_dependencies), expressed in degrees.
    """
    if n_dependencies < 1:
        n_dependencies = 1
    return math.degrees(math.atan(sigma_t / math.sqrt(n_dependencies)))


def classify_tmoa(tmoa_deg: float) -> TMOAClass:
    """
    Classify the TMOA score.

    < 0.5°  → Elite
    0.5-1.5° → Competition
    1.5-3.0° → Serviceable
    > 3.0°  → Sub-MOA (poor)
    """
    if tmoa_deg < 0.5:
        return TMOAClass.ELITE
    elif tmoa_deg < 1.5:
        return TMOAClass.COMPETITION
    elif tmoa_deg < 3.0:
        return TMOAClass.SERVICEABLE
    else:
        return TMOAClass.SUB_MOA


def analyze_tmoa(
    sigma_t: float,
    n_dependencies: int,
    project: str = "",
) -> TMOAResult:
    """
    Full TMOA analysis for a project.
    """
    return TMOAResult(
        project=project,
        sigma_t=sigma_t,
        n_dependencies=n_dependencies,
    )


def compare_tmoa(results: Sequence[TMOAResult]) -> list[dict]:
    """
    Compare TMOA results across projects.

    Returns a sorted list of comparison dicts.
    """
    comparisons = []
    for r in results:
        comparisons.append({
            "project": r.project,
            "tmoa_deg": round(r.tmoa_deg, 4),
            "sigma_t": round(r.sigma_t, 4),
            "n_dependencies": r.n_dependencies,
            "classification": r.classification.value,
        })
    comparisons.sort(key=lambda x: x["tmoa_deg"])
    return comparisons
