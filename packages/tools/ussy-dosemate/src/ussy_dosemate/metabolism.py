"""Metabolism model — first-pass effect and Michaelis-Menten CI saturation."""

import math
from dataclasses import dataclass

from ussy_dosemate.ci_collector import CIMetrics


@dataclass
class MetabolismParams:
    """Metabolism parameters for changes."""
    first_pass_effect: float  # Fraction of change transformed before merge (0-1)
    bioavailability_F: float  # Total bioavailability (0-1)
    ci_saturation_fraction: float  # Current CI load as fraction of Vmax
    Vmax: float  # Maximum CI processing capacity (PRs/day)
    Km: float  # Change size at half-saturation (lines)
    processing_rate: float  # Current CI processing rate (PRs/day)

    def michaelis_menten_rate(self, substrate_concentration: float) -> float:
        """Compute Michaelis-Menten processing rate.

        v = (Vmax * [S]) / (Km + [S])
        """
        if self.Km + substrate_concentration == 0:
            return 0.0
        return (self.Vmax * substrate_concentration) / (self.Km + substrate_concentration)

    def saturation_diagnosis(self) -> str:
        """Diagnose CI saturation level."""
        pct = self.ci_saturation_fraction * 100
        if pct < 50:
            return "CI is running comfortably — ample capacity"
        elif pct < 75:
            return "CI is moderately loaded — monitor for growth"
        elif pct < 90:
            return "CI is heavily loaded — consider adding capacity or reducing PR size"
        else:
            return "CI is near saturation — URGENT: add runners or reduce change volume"


def compute_metabolism(
    ci_metrics: CIMetrics,
    fraction_absorbed: float = 0.78,
) -> MetabolismParams:
    """Compute metabolism parameters from CI metrics.

    Args:
        ci_metrics: Collected CI/CD metrics
        fraction_absorbed: Fraction of change surviving review (from absorption model)

    Returns:
        MetabolismParams with computed values
    """
    # First-pass effect: fraction of changes transformed by CI before merge
    # F_hepatic = Q_h / (Q_h + CL_int)
    Q_h = ci_metrics.pr_arrival_rate
    CL_int = ci_metrics.ci_thoroughness
    if Q_h + CL_int > 0:
        F_hepatic = Q_h / (Q_h + CL_int)
    else:
        F_hepatic = 1.0
    first_pass_effect = 1.0 - F_hepatic  # fraction metabolized

    # Total bioavailability: F = f_absorption * f_lint * f_review
    f_absorption = fraction_absorbed
    f_lint = ci_metrics.lint_pass_rate
    f_review = ci_metrics.review_survival_rate
    bioavailability_F = f_absorption * f_lint * f_review
    # Clamp to [0, 1]
    bioavailability_F = max(0.0, min(1.0, bioavailability_F))

    # Michaelis-Menten parameters
    Vmax = ci_metrics.max_ci_capacity
    Km = ci_metrics.half_saturation_size

    # Current processing rate
    substrate = ci_metrics.pr_arrival_rate * ci_metrics.avg_pr_size_lines
    processing_rate = (Vmax * substrate) / (Km + substrate) if (Km + substrate) > 0 else 0.0

    # CI saturation fraction
    if Vmax > 0:
        ci_saturation_fraction = min(processing_rate / Vmax, 1.0)
    else:
        ci_saturation_fraction = 0.0

    return MetabolismParams(
        first_pass_effect=first_pass_effect,
        bioavailability_F=bioavailability_F,
        ci_saturation_fraction=ci_saturation_fraction,
        Vmax=Vmax,
        Km=Km,
        processing_rate=processing_rate,
    )
