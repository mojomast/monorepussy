"""Two-compartment model — deep dependency propagation."""

import math
from dataclasses import dataclass
from typing import List, Tuple

from dosemate.distribution import DistributionParams


@dataclass
class TwoCompartmentParams:
    """Parameters for the two-compartment model."""
    alpha: float  # Fast phase rate constant (direct dependents)
    beta: float  # Slow phase rate constant (transitive dependents)
    A: float  # Coefficient for alpha phase
    B: float  # Coefficient for beta phase
    alpha_half_life_hours: float  # Half-life of alpha phase
    beta_half_life_days: float  # Half-life of beta phase

    def concentration(self, t_hours: float) -> float:
        """Compute change concentration at time t.

        C(t) = A * e^(-alpha * t) + B * e^(-beta * t_hours)
        where t is in hours.
        """
        # Convert beta to per-hour for consistent units
        beta_per_hour = self.beta / 24.0  # beta is per day
        return self.A * math.exp(-self.alpha * t_hours) + self.B * math.exp(-beta_per_hour * t_hours)

    def phase_dominant_at(self, t_hours: float) -> str:
        """Determine which phase dominates at time t."""
        alpha_contribution = self.A * math.exp(-self.alpha * t_hours)
        beta_per_hour = self.beta / 24.0
        beta_contribution = self.B * math.exp(-beta_per_hour * t_hours)
        if alpha_contribution > beta_contribution:
            return "alpha (direct propagation)"
        else:
            return "beta (transitive propagation)"


def compute_two_compartment(
    distribution: DistributionParams,
    avg_direct_adoption_hours: float = 4.0,
    avg_transitive_adoption_days: float = 14.0,
) -> TwoCompartmentParams:
    """Compute two-compartment model parameters.

    Args:
        distribution: Distribution parameters
        avg_direct_adoption_hours: Average time for direct dependents to adopt (hours)
        avg_transitive_adoption_days: Average time for transitive dependents to adopt (days)

    Returns:
        TwoCompartmentParams with computed values
    """
    # Alpha: rate constant for direct dependency propagation
    # Typical: a few hours
    alpha = math.log(2) / max(avg_direct_adoption_hours, 0.1)

    # Beta: rate constant for transitive dependency propagation
    # Typical: days to weeks
    beta = math.log(2) / max(avg_transitive_adoption_days, 0.1)

    # Coefficients: split based on central vs peripheral compartment sizes
    total = distribution.central_compartment_size + distribution.peripheral_compartment_size
    if total > 0:
        A_frac = distribution.central_compartment_size / total
    else:
        A_frac = 0.7
    B_frac = 1.0 - A_frac

    # Scale A and B so total "dose" = 1.0 (normalized)
    A = A_frac
    B = B_frac

    # Half-lives
    alpha_half_life_hours = 0.693 / alpha if alpha > 0 else float('inf')
    beta_half_life_days = 0.693 / beta if beta > 0 else float('inf')

    return TwoCompartmentParams(
        alpha=alpha,
        beta=beta,
        A=A,
        B=B,
        alpha_half_life_hours=alpha_half_life_hours,
        beta_half_life_days=beta_half_life_days,
    )


def compute_propagation_curve(
    params: TwoCompartmentParams,
    time_points_hours: List[float],
) -> List[Tuple[float, float]]:
    """Compute the full propagation curve at given time points.

    Returns list of (time_hours, concentration) tuples.
    """
    return [(t, params.concentration(t)) for t in time_points_hours]
