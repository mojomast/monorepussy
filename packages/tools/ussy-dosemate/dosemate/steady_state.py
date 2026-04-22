"""Steady-state and accumulation model — equilibrium change pressure."""

import math
from dataclasses import dataclass

from dosemate.metabolism import MetabolismParams
from dosemate.excretion import ExcretionParams


@dataclass
class SteadyStateParams:
    """Steady-state parameters for the codebase."""
    Css: float  # Steady-state change pressure (changes per module)
    accumulation_factor_R: float  # Debt buildup between releases
    time_to_steady_state_weeks: float  # Time to reach new equilibrium
    sprint_duration_weeks: float  # Release cycle duration
    prs_per_sprint: float  # Average PRs per sprint

    def assessment(self) -> str:
        """Assess the sustainability of the current cadence."""
        if self.accumulation_factor_R < 1.2:
            return "change pressure is sustainable — clearance keeps pace with changes"
        elif self.accumulation_factor_R < 1.5:
            return "moderate accumulation — tech debt growing slowly, consider increasing clearance"
        elif self.accumulation_factor_R < 2.0:
            return "significant accumulation — tech debt growing faster than clearance"
        else:
            return "CRITICAL accumulation — change pressure far exceeds clearance capacity"


@dataclass
class DosePlan:
    """Loading dose vs. maintenance dose analysis."""
    loading_dose: float  # Large initial commit for bootstrap
    maintenance_dose: float  # Ongoing incremental changes
    LD_over_MD: float  # Bootstrap burden ratio
    target_pressure: float  # Target change pressure (Css)
    interpretation: str


def compute_steady_state(
    bioavailability_F: float,
    prs_per_sprint: float,
    clearance_CL: float,
    excretion: ExcretionParams,
    sprint_duration_weeks: float = 2.0,
) -> SteadyStateParams:
    """Compute steady-state parameters.

    Css = (F * Dose) / (CL * tau)
    R = 1 / (1 - e^(-ke * tau))
    t_ss ≈ 4.5 * t_half

    Args:
        bioavailability_F: Total bioavailability (0-1)
        prs_per_sprint: Average PRs per sprint
        clearance_CL: Clearance rate
        excretion: Excretion parameters
        sprint_duration_weeks: Sprint/release cycle in weeks

    Returns:
        SteadyStateParams with computed values
    """
    tau = sprint_duration_weeks
    Dose = prs_per_sprint

    # Steady-state concentration
    if clearance_CL * tau > 0:
        Css = (bioavailability_F * Dose) / (clearance_CL * tau)
    else:
        Css = float('inf')

    # Accumulation factor
    exp_term = math.exp(-excretion.ke * tau)
    if exp_term < 1.0:  # always true for positive ke
        R = 1.0 / (1.0 - exp_term)
    else:
        R = 1.0

    # Time to steady state
    if excretion.t_half > 0 and excretion.t_half != float('inf'):
        t_ss = 4.5 * excretion.t_half
    else:
        t_ss = float('inf')

    return SteadyStateParams(
        Css=Css,
        accumulation_factor_R=R,
        time_to_steady_state_weeks=t_ss,
        sprint_duration_weeks=tau,
        prs_per_sprint=prs_per_sprint,
    )


def compute_dose_plan(
    target_pressure: float,
    Vd: float,
    clearance_CL: float,
    bioavailability_F: float,
    sprint_duration_weeks: float = 2.0,
) -> DosePlan:
    """Compute loading dose and maintenance dose.

    LD = (Css * Vd) / F
    MD = (Css * CL * tau) / F
    LD/MD = Vd / (CL * tau) = t_half / (0.693 * tau)

    Args:
        target_pressure: Target steady-state change pressure (Css)
        Vd: Volume of distribution
        clearance_CL: Clearance rate
        bioavailability_F: Total bioavailability
        sprint_duration_weeks: Sprint duration

    Returns:
        DosePlan with computed values
    """
    tau = sprint_duration_weeks
    F = max(bioavailability_F, 0.01)  # avoid division by zero

    # Loading dose
    LD = (target_pressure * Vd) / F

    # Maintenance dose
    MD = (target_pressure * clearance_CL * tau) / F

    # Ratio
    LD_over_MD = LD / MD if MD > 0 else float('inf')

    # Interpretation
    if LD_over_MD > 5:
        interpretation = "Large bootstrap effort needed (LD >> MD) — typical for greenfield/migration projects"
    elif LD_over_MD > 2:
        interpretation = "Significant initial push required (LD > MD) — plan for a focused sprint"
    elif LD_over_MD > 0.8:
        interpretation = "Balanced effort (LD ≈ MD) — typical for mature, well-maintained systems"
    else:
        interpretation = "Low bootstrap burden (LD < MD) — ongoing maintenance dominates"

    return DosePlan(
        loading_dose=LD,
        maintenance_dose=MD,
        LD_over_MD=LD_over_MD,
        target_pressure=target_pressure,
        interpretation=interpretation,
    )
