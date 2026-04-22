"""Drug-drug interaction model — concurrent PR interference and amplification."""

import math
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from dosemate.dependency_graph import DependencyGraphAnalyzer
from dosemate.metabolism import MetabolismParams
from dosemate.git_parser import PullRequestInfo


@dataclass
class DDIResult:
    """Result of a drug-drug interaction analysis between two PRs."""
    pr_a: str
    pr_b: str
    shared_modules: int
    Km_apparent_ratio: float  # Km_apparent / Km (how much slower CI appears)
    AUC_ratio: float  # 1 + [I]/Ki — amplification factor
    severity: str  # "low", "moderate", "high", "critical"
    recommendation: str


def compute_ddi(
    pr_a: PullRequestInfo,
    pr_b: PullRequestInfo,
    dep_analyzer: DependencyGraphAnalyzer,
    file_to_module: Dict[str, str],
    metabolism: MetabolismParams,
    module_resilience_Ki: float = 5.0,
    induction_coeff: float = 0.1,
    tooling_improvement: float = 0.0,
) -> DDIResult:
    """Compute drug-drug interaction between two concurrent PRs.

    Args:
        pr_a: First PR
        pr_b: Second PR
        dep_analyzer: Dependency graph analyzer
        file_to_module: File to module mapping
        metabolism: Current metabolism parameters
        module_resilience_Ki: Module resilience to concurrent changes (higher = more resilient)
        induction_coeff: Coefficient for enzyme induction from tooling
        tooling_improvement: Factor of tooling improvement (0 = none)

    Returns:
        DDIResult with interaction analysis
    """
    # Find shared modules
    modules_a = set(file_to_module.get(f, "root") for f in pr_a.files_changed)
    modules_b = set(file_to_module.get(f, "root") for f in pr_b.files_changed)
    shared = modules_a & modules_b

    # Inhibitor concentration: concurrent change volume in shared modules
    I_concentration = len(shared) * (
        (pr_a.insertions + pr_a.deletions + pr_b.insertions + pr_b.deletions) / 2
    )

    # Apparent Km with competitive inhibition
    # Km_app = Km * (1 + [I] / Ki)
    Km_ratio = 1 + I_concentration / module_resilience_Ki
    Km_apparent = metabolism.Km * Km_ratio

    # AUC ratio: amplification factor
    AUC_ratio = Km_ratio

    # Apply enzyme induction from tooling improvements
    if tooling_improvement > 0:
        Vmax_induced = metabolism.Vmax * (1 + induction_coeff * tooling_improvement)
        # Tooling improvements reduce the effective AUC ratio
        AUC_ratio *= metabolism.Vmax / Vmax_induced

    # Severity classification
    if AUC_ratio < 1.2:
        severity = "low"
    elif AUC_ratio < 2.0:
        severity = "moderate"
    elif AUC_ratio < 3.0:
        severity = "high"
    else:
        severity = "critical"

    # Recommendation
    if severity == "low":
        recommendation = "changes can be merged concurrently with minimal risk"
    elif severity == "moderate":
        recommendation = "merge sequentially, not concurrently — moderate interference expected"
    elif severity == "high":
        recommendation = "HIGH RISK: merge one at a time with rebase — significant interference likely"
    else:
        recommendation = "CRITICAL: do not merge concurrently — refactor shared modules first"

    return DDIResult(
        pr_a=pr_a.id,
        pr_b=pr_b.id,
        shared_modules=len(shared),
        Km_apparent_ratio=Km_ratio,
        AUC_ratio=AUC_ratio,
        severity=severity,
        recommendation=recommendation,
    )


def compute_breaking_change_displacement(
    fu: float,
    breaking_change_magnitude: float,
    Kd: float = 10.0,
) -> float:
    """Compute protein binding displacement from a breaking API change.

    fu_new = fu * (1 + [breaking_change_magnitude] / Kd)

    Args:
        fu: Current unbound fraction
        breaking_change_magnitude: Size of the breaking change (lines)
        Kd: Dissociation constant (higher = more resilient)

    Returns:
        New unbound fraction (clamped to [0, 1])
    """
    fu_new = fu * (1 + breaking_change_magnitude / Kd)
    return min(fu_new, 1.0)


def analyze_all_interactions(
    prs: List[PullRequestInfo],
    dep_analyzer: DependencyGraphAnalyzer,
    file_to_module: Dict[str, str],
    metabolism: MetabolismParams,
    module_resilience_Ki: float = 5.0,
) -> List[DDIResult]:
    """Analyze all pairwise DDI between open PRs.

    Args:
        prs: List of open PRs
        dep_analyzer: Dependency graph analyzer
        file_to_module: File to module mapping
        metabolism: Metabolism parameters
        module_resilience_Ki: Module resilience coefficient

    Returns:
        List of DDIResult for each pair of PRs
    """
    results = []
    for i in range(len(prs)):
        for j in range(i + 1, len(prs)):
            result = compute_ddi(
                prs[i], prs[j], dep_analyzer, file_to_module,
                metabolism, module_resilience_Ki,
            )
            results.append(result)
    return results
