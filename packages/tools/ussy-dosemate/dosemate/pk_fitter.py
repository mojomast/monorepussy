"""PK Model Fitter — orchestrates all ADME computations."""

import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dosemate.absorption import AbsorptionParams, compute_absorption
from dosemate.ci_collector import CICollector, CIMetrics
from dosemate.ddi import DDIResult, analyze_all_interactions, compute_breaking_change_displacement
from dosemate.dependency_graph import DependencyGraphAnalyzer
from dosemate.distribution import DistributionParams, compute_distribution
from dosemate.excretion import ExcretionParams, compute_excretion
from dosemate.git_parser import GitHistoryParser, PullRequestInfo
from dosemate.metabolism import MetabolismParams, compute_metabolism
from dosemate.steady_state import (
    SteadyStateParams, DosePlan,
    compute_steady_state, compute_dose_plan,
)
from dosemate.two_compartment import TwoCompartmentParams, compute_two_compartment


@dataclass
class ChangePK:
    """Complete pharmacokinetic profile for a code change."""
    id: str
    dose_lines: int
    absorption: AbsorptionParams
    distribution: DistributionParams
    metabolism: MetabolismParams
    excretion: ExcretionParams
    two_compartment: Optional[TwoCompartmentParams] = None


@dataclass
class PKReport:
    """Full pharmacokinetic report for a repository."""
    change_pk: Dict[str, ChangePK] = field(default_factory=dict)
    interactions: List[DDIResult] = field(default_factory=list)
    steady_state: Optional[SteadyStateParams] = None
    dose_plan: Optional[DosePlan] = None
    ci_metrics: Optional[CIMetrics] = None


class PKModelFitter:
    """Fit pharmacokinetic models to code change data."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.git_parser = GitHistoryParser(repo_path)
        self.dep_analyzer = DependencyGraphAnalyzer(repo_path)
        self.ci_collector = CICollector(self.git_parser)
        self._analyzed = False

    def analyze(self, since: Optional[str] = None) -> PKReport:
        """Run full PK analysis on the repository.

        Args:
            since: Git date spec for lookback window

        Returns:
            PKReport with complete pharmacokinetic analysis
        """
        # Step 1: Analyze dependency graph
        self.dep_analyzer.analyze()
        file_to_module = self.git_parser.get_file_module_map()
        self._analyzed = True

        # Step 2: Collect CI metrics
        ci_metrics = self.ci_collector.collect(since=since)

        # Step 3: Get commits and synthesize PRs
        prs = self.git_parser.synthesize_prs(since=since)
        commits = self.git_parser.parse_commits(since=since)

        # Step 4: Compute ADME for each PR
        change_pk = {}
        for pr in prs:
            # Absorption
            absorption = compute_absorption([pr])

            # Distribution
            distribution = compute_distribution(
                pr.files_changed, self.dep_analyzer, file_to_module,
            )

            # Metabolism
            metabolism = compute_metabolism(ci_metrics, absorption.fraction_absorbed)

            # Excretion
            deprecated_removed, total_deprecated = self.git_parser.get_deprecated_lines(since)
            excretion = compute_excretion(distribution, deprecated_removed, total_deprecated)

            # Two-compartment model
            two_comp = compute_two_compartment(distribution)

            change_pk[pr.id] = ChangePK(
                id=pr.id,
                dose_lines=pr.insertions + pr.deletions,
                absorption=absorption,
                distribution=distribution,
                metabolism=metabolism,
                excretion=excretion,
                two_compartment=two_comp,
            )

        # Step 5: Drug-drug interactions
        interactions = analyze_all_interactions(
            prs, self.dep_analyzer, file_to_module,
            compute_metabolism(ci_metrics),
        )

        # Step 6: Steady state
        if change_pk:
            avg_F = sum(pk.metabolism.bioavailability_F for pk in change_pk.values()) / len(change_pk)
            avg_CL = sum(pk.excretion.CL for pk in change_pk.values()) / len(change_pk)
            avg_ke = sum(pk.excretion.ke for pk in change_pk.values()) / len(change_pk)
            avg_t_half = sum(pk.excretion.t_half for pk in change_pk.values()) / len(change_pk)
        else:
            avg_F = 0.5
            avg_CL = 0.1
            avg_ke = 0.05
            avg_t_half = 14.0

        steady_state = compute_steady_state(
            bioavailability_F=avg_F,
            prs_per_sprint=len(prs),
            clearance_CL=avg_CL,
            excretion=ExcretionParams(CL=avg_CL, ke=avg_ke, t_half=avg_t_half),
            sprint_duration_weeks=2.0,
        )

        # Step 7: Dose plan
        if change_pk:
            avg_Vd = sum(pk.distribution.Vd for pk in change_pk.values()) / len(change_pk)
        else:
            avg_Vd = 10.0
        dose_plan = compute_dose_plan(
            target_pressure=0.5,
            Vd=avg_Vd,
            clearance_CL=avg_CL,
            bioavailability_F=avg_F,
            sprint_duration_weeks=2.0,
        )

        return PKReport(
            change_pk=change_pk,
            interactions=interactions,
            steady_state=steady_state,
            dose_plan=dose_plan,
            ci_metrics=ci_metrics,
        )

    def analyze_change(self, pr: PullRequestInfo, file_to_module: Dict[str, str]) -> ChangePK:
        """Analyze a single change/PR.

        Args:
            pr: Pull request to analyze
            file_to_module: File to module mapping

        Returns:
            ChangePK for the specific change
        """
        if not self._analyzed:
            self.dep_analyzer.analyze()
            self._analyzed = True

        ci_metrics = self.ci_collector.collect()

        absorption = compute_absorption([pr])
        distribution = compute_distribution(pr.files_changed, self.dep_analyzer, file_to_module)
        metabolism = compute_metabolism(ci_metrics, absorption.fraction_absorbed)
        deprecated_removed, total_deprecated = self.git_parser.get_deprecated_lines()
        excretion = compute_excretion(distribution, deprecated_removed, total_deprecated)
        two_comp = compute_two_compartment(distribution)

        return ChangePK(
            id=pr.id,
            dose_lines=pr.insertions + pr.deletions,
            absorption=absorption,
            distribution=distribution,
            metabolism=metabolism,
            excretion=excretion,
            two_compartment=two_comp,
        )


def report_to_dict(report: PKReport) -> dict:
    """Convert a PKReport to a JSON-serializable dictionary."""
    result = {
        "change_pk": {},
        "interactions": [],
        "steady_state": None,
        "dose_plan": None,
    }

    for pr_id, pk in report.change_pk.items():
        result["change_pk"][pr_id] = {
            "dose_lines": pk.dose_lines,
            "absorption": {
                "ka_day_neg1": round(pk.absorption.ka, 4),
                "lag_time_hours": round(pk.absorption.lag_time_hours, 2),
                "fraction_absorbed": round(pk.absorption.fraction_absorbed, 4),
                "median_time_to_merge_days": round(pk.absorption.median_time_to_merge_days, 2),
            },
            "distribution": {
                "Vd_modules": round(pk.distribution.Vd, 2),
                "Kp": round(pk.distribution.Kp, 4),
                "fu_public_api_fraction": round(pk.distribution.fu, 4),
                "total_dependent_modules": pk.distribution.total_dependent_modules,
                "central_compartment_size": pk.distribution.central_compartment_size,
                "peripheral_compartment_size": pk.distribution.peripheral_compartment_size,
            },
            "metabolism": {
                "first_pass_effect": round(pk.metabolism.first_pass_effect, 4),
                "bioavailability_F": round(pk.metabolism.bioavailability_F, 4),
                "ci_saturation_fraction": round(pk.metabolism.ci_saturation_fraction, 4),
                "Vmax_prs_per_day": round(pk.metabolism.Vmax, 2),
                "Km_lines": round(pk.metabolism.Km, 2),
            },
            "excretion": {
                "CL_per_week": round(pk.excretion.CL, 4),
                "ke_per_week": round(pk.excretion.ke, 6),
                "t_half_weeks": round(pk.excretion.t_half, 2) if pk.excretion.t_half != float('inf') else "inf",
            },
        }

        if pk.two_compartment:
            result["change_pk"][pr_id]["two_compartment"] = {
                "alpha_per_hour": round(pk.two_compartment.alpha, 6),
                "beta_per_day": round(pk.two_compartment.beta, 6),
                "alpha_half_life_hours": round(pk.two_compartment.alpha_half_life_hours, 2),
                "beta_half_life_days": round(pk.two_compartment.beta_half_life_days, 2),
            }

    for interaction in report.interactions:
        result["interactions"].append({
            "pair": f"{interaction.pr_a}_x_{interaction.pr_b}",
            "shared_modules": interaction.shared_modules,
            "Km_apparent_ratio": round(interaction.Km_apparent_ratio, 4),
            "AUC_ratio": round(interaction.AUC_ratio, 4),
            "severity": interaction.severity,
            "recommendation": interaction.recommendation,
        })

    if report.steady_state:
        result["steady_state"] = {
            "Css_changes_per_module": round(report.steady_state.Css, 4),
            "accumulation_factor_R": round(report.steady_state.accumulation_factor_R, 4),
            "time_to_steady_state_weeks": round(report.steady_state.time_to_steady_state_weeks, 2)
                if report.steady_state.time_to_steady_state_weeks != float('inf') else "inf",
            "assessment": report.steady_state.assessment(),
        }

    if report.dose_plan:
        result["dose_plan"] = {
            "loading_dose": round(report.dose_plan.loading_dose, 2),
            "maintenance_dose": round(report.dose_plan.maintenance_dose, 2),
            "LD_over_MD": round(report.dose_plan.LD_over_MD, 4),
            "target_pressure": report.dose_plan.target_pressure,
            "interpretation": report.dose_plan.interpretation,
        }

    if report.ci_metrics:
        result["ci_metrics"] = {
            "pr_arrival_rate": round(report.ci_metrics.pr_arrival_rate, 4),
            "Vmax_prs_per_day": round(report.ci_metrics.max_ci_capacity, 2),
            "Km_lines": round(report.ci_metrics.half_saturation_size, 2),
        }

    return result
