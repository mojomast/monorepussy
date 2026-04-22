"""Bühlmann Credibility — Internal/External Threat Intel Blending."""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class CredibilityResult:
    """Result of Bühlmann credibility computation."""
    org_id: str
    n_obs: int
    epv: float          # Expected Process Variance (within-org)
    vhm: float          # Variance of Hypothetical Means (between-org)
    K: float            # K = EPV / VHM (credibility complement)
    Z: float            # Credibility factor Z = n / (n + K)
    internal_mean: float
    population_mean: float
    blended_mean: float  # Z * internal_mean + (1-Z) * population_mean


def compute_epv(group_data: list[list[float]]) -> float:
    """Compute Expected Process Variance (within-group variance).

    EPV = average of within-group variances.
    """
    if not group_data:
        return 0.0

    variances = []
    for group in group_data:
        if len(group) < 2:
            continue
        mean = sum(group) / len(group)
        var = sum((x - mean) ** 2 for x in group) / (len(group) - 1)
        variances.append(var)

    return sum(variances) / len(variances) if variances else 0.0


def compute_vhm(group_means: list[float], epv: float, group_sizes: list[int]) -> float:
    """Compute Variance of Hypothetical Means (between-group variance).

    VHM = max(0, total_variance_of_means - average_EPV/n_i)
    """
    if len(group_means) < 2:
        return 0.0

    overall_mean = sum(group_means) / len(group_means)
    total_var = sum((m - overall_mean) ** 2 for m in group_means) / (len(group_means) - 1)

    # Subtract the expected contribution from process variance
    avg_epv_contribution = sum(epv / n for n in group_sizes if n > 0) / len(group_sizes)

    vhm = total_var - avg_epv_contribution
    return max(0.0, vhm)


def compute_credibility(
    org_id: str,
    n_obs: int,
    internal_data: list[float],
    all_groups_data: list[list[float]],
    population_mean: Optional[float] = None,
) -> CredibilityResult:
    """Compute Bühlmann credibility-weighted exploit probability.

    Args:
        org_id: Organization identifier.
        n_obs: Number of internal observations for this org.
        internal_data: This org's internal exploit rate observations.
        all_groups_data: All organizations' data for EPV/VHM estimation.
        population_mean: Override for population mean (defaults to grand mean).

    Returns:
        CredibilityResult with blended probability.
    """
    epv = compute_epv(all_groups_data)

    group_means = [sum(g) / len(g) for g in all_groups_data if g]
    group_sizes = [len(g) for g in all_groups_data if g]
    vhm = compute_vhm(group_means, epv, group_sizes)

    # K = EPV / VHM (with protection against division by zero)
    K = epv / vhm if vhm > 0 else float('inf')

    # Z = n / (n + K)
    Z = n_obs / (n_obs + K) if K != float('inf') else 0.0
    Z = max(0.0, min(1.0, Z))

    internal_mean = sum(internal_data) / len(internal_data) if internal_data else 0.0

    if population_mean is None:
        # Grand mean across all groups
        all_values = [v for g in all_groups_data for v in g]
        pop_mean = sum(all_values) / len(all_values) if all_values else 0.0
    else:
        pop_mean = population_mean

    # Credibility-weighted estimate
    blended = Z * internal_mean + (1 - Z) * pop_mean

    return CredibilityResult(
        org_id=org_id,
        n_obs=n_obs,
        epv=epv,
        vhm=vhm,
        K=K,
        Z=Z,
        internal_mean=internal_mean,
        population_mean=pop_mean,
        blended_mean=blended,
    )


def credibility_from_params(
    org_id: str,
    n_obs: int,
    epv: float,
    vhm: float,
    internal_mean: float,
    population_mean: float,
) -> CredibilityResult:
    """Compute credibility directly from EPV/VHM parameters.

    Useful when EPV/VHM have been pre-computed or estimated externally.
    """
    K = epv / vhm if vhm > 0 else float('inf')
    Z = n_obs / (n_obs + K) if K != float('inf') else 0.0
    Z = max(0.0, min(1.0, Z))
    blended = Z * internal_mean + (1 - Z) * population_mean

    return CredibilityResult(
        org_id=org_id,
        n_obs=n_obs,
        epv=epv,
        vhm=vhm,
        K=K,
        Z=Z,
        internal_mean=internal_mean,
        population_mean=population_mean,
        blended_mean=blended,
    )


def format_credibility(result: CredibilityResult) -> str:
    """Format a credibility result as a readable string."""
    lines = [
        f"Credibility Analysis: {result.org_id}",
        f"  Observations (n):     {result.n_obs}",
        f"  EPV (within-org):     {result.epv:.6f}",
        f"  VHM (between-org):    {result.vhm:.6f}",
        f"  K = EPV/VHM:          {result.K:.4f}",
        f"  Credibility Z:        {result.Z:.4f}",
        f"  Internal mean:        {result.internal_mean:.6f}",
        f"  Population mean:      {result.population_mean:.6f}",
        f"  Blended estimate:     {result.blended_mean:.6f}",
        "",
        f"  Weight: {result.Z:.1%} internal + {1 - result.Z:.1%} external",
    ]
    return "\n".join(lines)
