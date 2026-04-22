"""Excretion model — change clearance and half-life."""

import math
from dataclasses import dataclass

from dosemate.distribution import DistributionParams


@dataclass
class ExcretionParams:
    """Excretion parameters for changes."""
    CL: float  # Clearance rate (lines per week)
    ke: float  # Elimination rate constant (per week)
    t_half: float  # Half-life in weeks

    def concentration_at_time(self, C0: float, t_weeks: float) -> float:
        """Compute change concentration at time t.

        C(t) = C0 * e^(-ke * t)
        """
        return C0 * math.exp(-self.ke * t_weeks)

    def time_to_threshold(self, C0: float, threshold: float) -> float:
        """Compute time for concentration to drop below threshold.

        t = -ln(threshold/C0) / ke
        Returns infinity if ke is 0 or threshold >= C0.
        """
        if self.ke <= 0 or threshold >= C0:
            return float('inf')
        return -math.log(threshold / C0) / self.ke

    def influence_remaining(self, t_weeks: float) -> float:
        """Fraction of original influence remaining at time t.

        Returns value in [0, 1].
        """
        return math.exp(-self.ke * t_weeks)


def compute_excretion(
    distribution: DistributionParams,
    deprecated_lines_removed: int = 0,
    total_deprecated_lines: int = 1,
    observed_deprecation_rate: float = 0.0,
) -> ExcretionParams:
    """Compute excretion parameters.

    Args:
        distribution: Distribution parameters (provides Vd)
        deprecated_lines_removed: Deprecated lines removed per week
        total_deprecated_lines: Total deprecated lines in codebase
        observed_deprecation_rate: If provided, overrides computed CL

    Returns:
        ExcretionParams with computed values
    """
    # Clearance rate: how fast deprecated code is removed
    if observed_deprecation_rate > 0:
        CL = observed_deprecation_rate
    elif total_deprecated_lines > 0:
        CL = deprecated_lines_removed / total_deprecated_lines
    else:
        CL = 0.1  # default: 10% per week

    # Scale CL to be reasonable (0.01 to 10 lines/week equivalent)
    # The CL here represents a fractional clearance rate
    CL = max(CL, 0.001)

    # ke = CL / Vd (elimination rate constant)
    if distribution.Vd > 0:
        ke = CL / distribution.Vd
    else:
        ke = 0.001

    # Half-life: t½ = 0.693 * Vd / CL = 0.693 / ke
    if CL > 0:
        t_half = 0.693 * distribution.Vd / CL
    else:
        t_half = float('inf')

    return ExcretionParams(CL=CL, ke=ke, t_half=t_half)
