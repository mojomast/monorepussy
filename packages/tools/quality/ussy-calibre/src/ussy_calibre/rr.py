"""R&R Study — Gauge Repeatability & Reproducibility.

Implements two-way random-effects ANOVA for variance decomposition:
Y_ijk = mu + P_i + O_j + (PO)_ij + epsilon_ijk

Where:
  P_i = Part effect (code version / build)
  O_j = Operator effect (execution environment)
  (PO)_ij = Interaction
  epsilon_ijk = Repeatability (test code inherent noise)

Variance decomposition:
  sigma^2_Total = sigma^2_Part + sigma^2_Operator + sigma^2_Interaction + sigma^2_Equipment

Key metrics:
  %GRR = (sigma_GRR / sigma_Total) * 100
  ndc = floor(1.41 * (sigma_Part / sigma_Gauge))

AIAG acceptance criteria:
  %GRR < 10%  → acceptable
  10% <= %GRR <= 30% → conditional
  %GRR > 30%  → unacceptable
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from calibre.models import (
    RRCategory,
    RRObservation,
    RRSummary,
    TestRun,
)


def anova_two_way_random(
    observations: List[RRObservation],
) -> Dict[str, float]:
    """Perform two-way random-effects ANOVA.

    Returns variance component estimates.
    """
    if not observations:
        return {
            "var_part": 0.0,
            "var_operator": 0.0,
            "var_interaction": 0.0,
            "var_error": 0.0,
        }

    # Organize data: build x environment -> list of replicates
    data: Dict[Tuple[str, str], List[float]] = {}
    builds: set = set()
    envs: set = set()

    for obs in observations:
        key = (obs.build_id, obs.environment)
        data.setdefault(key, []).append(obs.value)
        builds.add(obs.build_id)
        envs.add(obs.environment)

    p = len(builds)  # number of parts (builds)
    o = len(envs)    # number of operators (environments)

    if p < 2 or o < 2:
        return {
            "var_part": 0.0,
            "var_operator": 0.0,
            "var_interaction": 0.0,
            "var_error": 0.0,
        }

    # Compute number of replicates per cell (use minimum)
    r = min(len(v) for v in data.values())
    if r < 1:
        r = 1

    # Build data matrix for ANOVA
    n = p * o * r

    # Grand mean
    all_values = [obs.value for obs in observations]
    grand_mean = sum(all_values) / len(all_values)

    # SS Part
    build_means: Dict[str, float] = {}
    for obs in observations:
        build_means.setdefault(obs.build_id, []).append(obs.value)
    ss_part = 0.0
    for build_id, vals in build_means.items():
        bm = sum(vals) / len(vals)
        ss_part += len(vals) * (bm - grand_mean) ** 2

    # SS Operator
    env_means: Dict[str, float] = {}
    for obs in observations:
        env_means.setdefault(obs.environment, []).append(obs.value)
    ss_operator = 0.0
    for env, vals in env_means.items():
        em = sum(vals) / len(vals)
        ss_operator += len(vals) * (em - grand_mean) ** 2

    # SS Interaction
    ss_total = sum((v - grand_mean) ** 2 for v in all_values)
    ss_within = 0.0
    for vals in data.values():
        cell_mean = sum(vals) / len(vals)
        ss_within += sum((v - cell_mean) ** 2 for v in vals)

    ss_interaction = ss_total - ss_part - ss_operator - ss_within

    # Clamp negative SS to zero
    ss_interaction = max(0.0, ss_interaction)

    # Mean squares
    ms_part = ss_part / max(p - 1, 1)
    ms_operator = ss_operator / max(o - 1, 1)
    ms_interaction = ss_interaction / max((p - 1) * (o - 1), 1)
    ms_error = ss_within / max(p * o * (r - 1), 1) if r > 1 else ms_interaction

    # Variance components (expected mean squares for random model)
    var_error = max(ms_error, 0.0)
    var_interaction = max((ms_interaction - ms_error) / r, 0.0)
    var_operator = max((ms_operator - ms_interaction) / (p * r), 0.0)
    var_part = max((ms_part - ms_interaction) / (o * r), 0.0)

    return {
        "var_part": var_part,
        "var_operator": var_operator,
        "var_interaction": var_interaction,
        "var_error": var_error,
    }


def compute_rr_summary(
    suite: str,
    observations: List[RRObservation],
) -> RRSummary:
    """Compute a full Gauge R&R summary."""
    if not observations:
        return RRSummary(suite=suite, category=RRCategory.UNACCEPTABLE, diagnosis="No data")

    components = anova_two_way_random(observations)

    sigma_part = components["var_part"] ** 0.5
    sigma_operator = components["var_operator"] ** 0.5
    sigma_interaction = components["var_interaction"] ** 0.5
    sigma_equipment = components["var_error"] ** 0.5

    sigma_grr = (components["var_operator"] + components["var_interaction"] + components["var_error"]) ** 0.5
    sigma_total = (components["var_part"] + components["var_operator"] + components["var_interaction"] + components["var_error"]) ** 0.5

    if sigma_total > 0:
        grr_percent = (sigma_grr / sigma_total) * 100.0
        part_pct = (components["var_part"] / (sigma_total ** 2)) * 100.0
        operator_pct = (components["var_operator"] / (sigma_total ** 2)) * 100.0
        interaction_pct = (components["var_interaction"] / (sigma_total ** 2)) * 100.0
        equipment_pct = (components["var_error"] / (sigma_total ** 2)) * 100.0
    else:
        grr_percent = 100.0
        part_pct = 0.0
        operator_pct = 0.0
        interaction_pct = 0.0
        equipment_pct = 0.0

    # ndc = floor(1.41 * sigma_part / sigma_grr)
    if sigma_grr > 0:
        ndc = max(1, int(math.floor(1.41 * sigma_part / sigma_grr)))
    else:
        ndc = 1

    # AIAG classification
    if grr_percent < 10:
        category = RRCategory.ACCEPTABLE
    elif grr_percent <= 30:
        category = RRCategory.CONDITIONAL
    else:
        category = RRCategory.UNACCEPTABLE

    # Diagnosis
    if operator_pct > equipment_pct and operator_pct > part_pct:
        diagnosis = "Reproducibility dominates → fix environments"
    elif equipment_pct > operator_pct and equipment_pct > part_pct:
        diagnosis = "Repeatability dominates → fix test code"
    elif ndc <= 1:
        diagnosis = "ndc = 1 → suite cannot meaningfully distinguish good from bad code"
    else:
        diagnosis = "Part variation dominates → suite is measuring real code changes"

    return RRSummary(
        suite=suite,
        sigma_part=sigma_part,
        sigma_operator=sigma_operator,
        sigma_interaction=sigma_interaction,
        sigma_equipment=sigma_equipment,
        sigma_total=sigma_total,
        grr_percent=grr_percent,
        ndc=ndc,
        category=category,
        part_variance_pct=part_pct,
        operator_variance_pct=operator_pct,
        interaction_variance_pct=interaction_pct,
        equipment_variance_pct=equipment_pct,
        diagnosis=diagnosis,
    )


def runs_to_rr_observations(runs: List[TestRun]) -> List[RRObservation]:
    """Convert TestRun data to RRObservations for R&R analysis."""
    # Group by (build, env, test) and assign replicate numbers
    groups: Dict[Tuple[str, str, str], List[TestRun]] = {}
    for run in runs:
        key = (run.build_id, run.environment, run.test_name)
        groups.setdefault(key, []).append(run)

    observations: List[RRObservation] = []
    for (build_id, env, test_name), test_runs in groups.items():
        for i, run in enumerate(test_runs):
            observations.append(
                RRObservation(
                    build_id=build_id,
                    environment=env,
                    test_name=test_name,
                    replicate=i + 1,
                    value=run.numeric_result,
                )
            )

    return observations


def format_rr_summary(summary: RRSummary) -> str:
    """Format an R&R summary as a readable report."""
    lines: List[str] = []
    lines.append(f"{'='*60}")
    lines.append(f"Gauge R&R Study: {summary.suite}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append("Variance Decomposition:")
    lines.append(f"  Part (build variation):     {summary.part_variance_pct:>6.1f}%  sigma={summary.sigma_part:.4f}")
    lines.append(f"  Operator (environment):     {summary.operator_variance_pct:>6.1f}%  sigma={summary.sigma_operator:.4f}")
    lines.append(f"  Interaction:                {summary.interaction_variance_pct:>6.1f}%  sigma={summary.sigma_interaction:.4f}")
    lines.append(f"  Equipment (test code):      {summary.equipment_variance_pct:>6.1f}%  sigma={summary.sigma_equipment:.4f}")
    lines.append("")
    lines.append(f"  %GRR = {summary.grr_percent:.1f}%")
    lines.append(f"  ndc   = {summary.ndc}")
    lines.append(f"  Category: {summary.category.value}")
    lines.append("")
    lines.append(f"  Diagnosis: {summary.diagnosis}")
    lines.append("")

    return "\n".join(lines)
