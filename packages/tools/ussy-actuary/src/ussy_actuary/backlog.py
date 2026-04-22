"""Chain Ladder — Vulnerability Backlog Projection with Mack's variance."""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DevelopmentTriangle:
    """Vulnerability development triangle for chain ladder projection."""
    repo_id: str
    cohorts: list[str] = field(default_factory=list)
    data: dict[str, dict[int, int]] = field(default_factory=dict)
    # data[cohort_quarter][dev_quarter] = vuln_count

    def set_value(self, cohort: str, dev_quarter: int, count: int) -> None:
        if cohort not in self.data:
            self.data[cohort] = {}
            self.cohorts.append(cohort)
        self.data[cohort][dev_quarter] = count

    def get_value(self, cohort: str, dev_quarter: int) -> Optional[int]:
        return self.data.get(cohort, {}).get(dev_quarter)

    @property
    def max_dev(self) -> int:
        """Maximum development quarter across all cohorts."""
        max_d = 0
        for cohort_data in self.data.values():
            max_d = max(max_d, max(cohort_data.keys(), default=0))
        return max_d


@dataclass
class ChainLadderResult:
    """Result of chain ladder projection."""
    age_to_age_factors: list[float]
    projected_triangle: dict[str, dict[int, float]]
    total_reserve: float
    mack_variance: list[float]
    confidence_lower: float
    confidence_upper: float


def compute_age_to_age_factors(triangle: DevelopmentTriangle) -> list[float]:
    """Compute chain ladder age-to-age factors f_j.

    f_j = sum(C_{i,j+1}) / sum(C_{i,j}) for all cohorts i where both values exist.
    """
    max_dev = triangle.max_dev
    factors = []

    for j in range(max_dev):
        numerator = 0.0
        denominator = 0.0
        for cohort in triangle.cohorts:
            c_j = triangle.get_value(cohort, j)
            c_j1 = triangle.get_value(cohort, j + 1)
            if c_j is not None and c_j1 is not None and c_j > 0:
                numerator += c_j1
                denominator += c_j
        if denominator > 0:
            factors.append(numerator / denominator)
        else:
            factors.append(1.0)

    return factors


def compute_mack_variance(triangle: DevelopmentTriangle,
                          factors: list[float]) -> list[float]:
    """Compute Mack's variance estimates for each development period.

    sigma^2_j = 1/(n-j-1) * sum C_{i,j} * (C_{i,j+1}/C_{i,j} - f_j)^2
    """
    max_dev = triangle.max_dev
    variances = []

    for j in range(len(factors)):
        numerator = 0.0
        count = 0
        for cohort in triangle.cohorts:
            c_j = triangle.get_value(cohort, j)
            c_j1 = triangle.get_value(cohort, j + 1)
            if c_j is not None and c_j1 is not None and c_j > 0:
                individual_factor = c_j1 / c_j
                numerator += c_j * (individual_factor - factors[j]) ** 2
                count += 1

        if count > 1:
            variances.append(numerator / (count - 1))
        else:
            variances.append(0.0)

    return variances


def project_triangle(triangle: DevelopmentTriangle,
                     factors: list[float]) -> dict[str, dict[int, float]]:
    """Project future values in the development triangle using chain ladder.

    Returns the full projected triangle (known + projected values).
    """
    projected = {}
    max_dev = triangle.max_dev

    for cohort in triangle.cohorts:
        projected[cohort] = {}
        # Copy known values
        for j in range(max_dev + 1):
            val = triangle.get_value(cohort, j)
            if val is not None:
                projected[cohort][j] = float(val)

        # Project forward from last known value
        last_known_j = max(
            j for j in range(max_dev + 1)
            if triangle.get_value(cohort, j) is not None
        )
        last_val = float(triangle.get_value(cohort, last_known_j))

        for j in range(last_known_j + 1, max_dev + 1):
            if j - 1 < len(factors):
                last_val = last_val * factors[j - 1]
            else:
                last_val = last_val * factors[-1] if factors else last_val
            projected[cohort][j] = last_val

    return projected


def compute_reserve(projected: dict[str, dict[int, float]],
                    triangle: DevelopmentTriangle) -> float:
    """Compute the total backlog reserve.

    R_hat = sum_i (C_hat_{i,n} - C_{i,j*})
    where j* is the latest known development quarter for cohort i.
    """
    total_reserve = 0.0
    max_dev = max(
        max(d.keys(), default=0) for d in projected.values()
    ) if projected else 0

    for cohort in triangle.cohorts:
        ultimate = projected.get(cohort, {}).get(max_dev, 0.0)
        last_known_j = max(
            j for j in range(max_dev + 1)
            if triangle.get_value(cohort, j) is not None
        )
        current = float(triangle.get_value(cohort, last_known_j) or 0)
        total_reserve += ultimate - current

    return total_reserve


def chain_ladder_analysis(
    triangle: DevelopmentTriangle,
    confidence_level: float = 0.95,
) -> ChainLadderResult:
    """Run full chain ladder analysis with Mack's variance.

    Args:
        triangle: The development triangle with known values.
        confidence_level: Confidence level for intervals (default 0.95).

    Returns:
        ChainLadderResult with projections and confidence intervals.
    """
    factors = compute_age_to_age_factors(triangle)
    projected = project_triangle(triangle, factors)
    reserve = compute_reserve(projected, triangle)
    mack_var = compute_mack_variance(triangle, factors)

    # Compute confidence interval using Mack's formula
    # Standard error of reserve estimate
    total_se_sq = 0.0
    max_dev = triangle.max_dev
    for cohort in triangle.cohorts:
        last_known_j = max(
            j for j in range(max_dev + 1)
            if triangle.get_value(cohort, j) is not None
        )
        c_current = float(triangle.get_value(cohort, last_known_j) or 0)

        # Accumulate variance across projected periods
        for j in range(last_known_j, min(len(factors), max_dev)):
            if j < len(mack_var) and factors[j] != 0:
                se_j = mack_var[j] / (factors[j] ** 2 * c_current) if c_current > 0 else 0
                total_se_sq += se_j * c_current

    se = math.sqrt(total_se_sq) if total_se_sq > 0 else 0.0

    # Normal approximation for confidence interval
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence_level, 1.96)
    lower = max(0.0, reserve - z * se)
    upper = reserve + z * se

    return ChainLadderResult(
        age_to_age_factors=factors,
        projected_triangle=projected,
        total_reserve=reserve,
        mack_variance=mack_var,
        confidence_lower=lower,
        confidence_upper=upper,
    )


def format_triangle(triangle: DevelopmentTriangle,
                    result: Optional[ChainLadderResult] = None) -> str:
    """Format development triangle as a readable string."""
    lines = []
    max_dev = triangle.max_dev
    lines.append(f"Vulnerability Development Triangle: {triangle.repo_id}")
    header = f"{'Cohort':>10}"
    for j in range(max_dev + 1):
        header += f" {j:>8}"
    lines.append(header)
    lines.append("-" * (12 + (max_dev + 1) * 9))

    for cohort in triangle.cohorts:
        line = f"{cohort:>10}"
        for j in range(max_dev + 1):
            val = triangle.get_value(cohort, j)
            if val is not None:
                line += f" {val:>8}"
            else:
                # Show projected value if available
                if result and cohort in result.projected_triangle:
                    proj_val = result.projected_triangle[cohort].get(j)
                    if proj_val is not None:
                        line += f" {proj_val:>7.1f}*"
                    else:
                        line += f" {'?':>8}"
                else:
                    line += f" {'?':>8}"
        lines.append(line)

    if result:
        lines.append("")
        lines.append("Age-to-age factors:")
        for j, f in enumerate(result.age_to_age_factors):
            lines.append(f"  f_{j} = {f:.4f}")
        lines.append(f"\nTotal reserve: {result.total_reserve:.1f}")
        lines.append(
            f"95% CI: [{result.confidence_lower:.1f}, {result.confidence_upper:.1f}]"
        )

    return "\n".join(lines)
