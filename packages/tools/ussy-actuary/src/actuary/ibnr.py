"""IBNR — Latent Vulnerability Estimation via Bornhuetter-Ferguson and Cape Cod."""

import math
from dataclasses import dataclass
from typing import Optional

from actuary.backlog import (
    DevelopmentTriangle,
    compute_age_to_age_factors,
    project_triangle,
)


@dataclass
class IBNRResult:
    """Result of IBNR estimation."""
    repo_id: str
    method: str  # "bf" or "cape_cod"
    reported_count: int
    prior_ultimate: float
    bf_reserve: float
    bf_ultimate: float
    cape_cod_prior: Optional[float] = None


def bornhuetter_ferguson(
    triangle: DevelopmentTriangle,
    priors: dict[str, float],
) -> list[IBNRResult]:
    """Bornhuetter-Ferguson IBNR estimation.

    BF_reserve_i = mu_i * (1 - 1/Product(f_k for k from j* to n-1))
    BF_ultimate_i = C_{i,j*} + BF_reserve_i

    Args:
        triangle: The development triangle.
        priors: Prior expected ultimate for each cohort: {cohort_quarter: expected_ultimate}.

    Returns:
        List of IBNRResult, one per cohort.
    """
    factors = compute_age_to_age_factors(triangle)
    results = []
    max_dev = triangle.max_dev

    for cohort in triangle.cohorts:
        # Find the latest known development quarter
        last_known_j = max(
            j for j in range(max_dev + 1)
            if triangle.get_value(cohort, j) is not None
        )
        current = float(triangle.get_value(cohort, last_known_j) or 0)

        # Compute cumulative product of future factors
        # f_j for j from last_known_j to max_dev-1
        cum_factor = 1.0
        for j in range(last_known_j, min(len(factors), max_dev)):
            cum_factor *= factors[j]

        prior_ultimate = priors.get(cohort, current * cum_factor)

        # BF reserve = prior_ultimate * (1 - 1/cum_factor)
        if cum_factor > 0:
            bf_reserve = prior_ultimate * (1.0 - 1.0 / cum_factor)
        else:
            bf_reserve = 0.0

        bf_ultimate = current + bf_reserve

        results.append(IBNRResult(
            repo_id=triangle.repo_id,
            method="bf",
            reported_count=int(current),
            prior_ultimate=prior_ultimate,
            bf_reserve=bf_reserve,
            bf_ultimate=bf_ultimate,
        ))

    return results


def cape_cod(
    triangle: DevelopmentTriangle,
    reported_counts: Optional[dict[str, int]] = None,
) -> list[IBNRResult]:
    """Cape Cod IBNR estimation (data-driven prior).

    mu_hat_i = (sum_j C_{i,j} * f_j) / (sum_j 1/f_j)
    Then applies BF formula with this estimated prior.

    Args:
        triangle: The development triangle.
        reported_counts: Override reported counts per cohort.

    Returns:
        List of IBNRResult, one per cohort.
    """
    factors = compute_age_to_age_factors(triangle)
    results = []
    max_dev = triangle.max_dev

    for cohort in triangle.cohorts:
        last_known_j = max(
            j for j in range(max_dev + 1)
            if triangle.get_value(cohort, j) is not None
        )

        # Compute Cape Cod prior
        numerator = 0.0
        denominator = 0.0
        for j in range(last_known_j + 1):
            c_ij = triangle.get_value(cohort, j)
            if c_ij is not None:
                f_j = 1.0
                for k in range(j, min(len(factors), max_dev)):
                    f_j *= factors[k]
                numerator += c_ij * f_j
                denominator += 1.0 / f_j if f_j > 0 else 0.0

        cape_cod_prior = numerator / denominator if denominator > 0 else 0.0

        current = float(triangle.get_value(cohort, last_known_j) or 0)

        # BF with Cape Cod prior
        cum_factor = 1.0
        for j in range(last_known_j, min(len(factors), max_dev)):
            cum_factor *= factors[j]

        if cum_factor > 0:
            bf_reserve = cape_cod_prior * (1.0 - 1.0 / cum_factor)
        else:
            bf_reserve = 0.0

        bf_ultimate = current + bf_reserve

        results.append(IBNRResult(
            repo_id=triangle.repo_id,
            method="cape_cod",
            reported_count=int(current),
            prior_ultimate=cape_cod_prior,
            bf_reserve=bf_reserve,
            bf_ultimate=bf_ultimate,
            cape_cod_prior=cape_cod_prior,
        ))

    return results


def ibnr_from_density(
    reported_count: int,
    density_per_kloc: float,
    kloc: float,
    method: str = "bf",
) -> IBNRResult:
    """Estimate IBNR from bugs/KLOC density.

    This is a simplified version that estimates latent vulnerabilities
    from industry density data without a full development triangle.

    Args:
        reported_count: Number of known/reported vulnerabilities.
        density_per_kloc: Industry bugs/KLOC density for similar codebases.
        kloc: Size of the codebase in thousands of lines of code.
        method: "bf" for Bornhuetter-Ferguson.

    Returns:
        IBNRResult with estimated latent count.
    """
    prior_ultimate = density_per_kloc * kloc

    # BF reserve = prior_ultimate * (1 - reported/prior_ultimate)
    if prior_ultimate > 0:
        development_pct = reported_count / prior_ultimate
        bf_reserve = prior_ultimate * (1.0 - development_pct)
    else:
        bf_reserve = 0.0

    bf_ultimate = reported_count + bf_reserve

    return IBNRResult(
        repo_id="density-based",
        method=method,
        reported_count=reported_count,
        prior_ultimate=prior_ultimate,
        bf_reserve=bf_reserve,
        bf_ultimate=bf_ultimate,
    )


def format_ibnr(results: list[IBNRResult]) -> str:
    """Format IBNR results as a readable string."""
    lines = []
    method = results[0].method if results else "unknown"
    lines.append(f"IBNR Estimation ({method.upper()})")
    lines.append(f"{'Repo':>15} {'Reported':>10} {'Prior μ':>10} "
                 f"{'Reserve':>10} {'Ultimate':>10}")
    lines.append("-" * 60)

    for r in results:
        lines.append(
            f"{r.repo_id:>15} {r.reported_count:>10} {r.prior_ultimate:>10.1f} "
            f"{r.bf_reserve:>10.1f} {r.bf_ultimate:>10.1f}"
        )

    total_reserve = sum(r.bf_reserve for r in results)
    total_ultimate = sum(r.bf_ultimate for r in results)
    total_reported = sum(r.reported_count for r in results)
    lines.append("-" * 60)
    lines.append(
        f"{'TOTAL':>15} {total_reported:>10} {'':>10} "
        f"{total_reserve:>10.1f} {total_ultimate:>10.1f}"
    )
    lines.append(f"\nEstimated latent vulnerabilities: {total_reserve:.1f}")

    return "\n".join(lines)
