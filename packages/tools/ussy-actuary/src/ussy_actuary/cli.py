"""Actuary CLI — Command-line interface for actuarial vulnerability risk quantification."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ussy_actuary.survival import (
    compute_life_table,
    apply_graduation,
    format_life_table,
)
from ussy_actuary.backlog import (
    DevelopmentTriangle,
    chain_ladder_analysis,
    format_triangle,
)
from ussy_actuary.credibility import (
    compute_credibility,
    credibility_from_params,
    format_credibility,
)
from ussy_actuary.ibnr import (
    bornhuetter_ferguson,
    cape_cod,
    ibnr_from_density,
    format_ibnr,
)
from ussy_actuary.aggregate import (
    simulate_aggregate_loss,
    format_copula_result,
)
from ussy_actuary.moral_hazard import (
    compute_moral_hazard,
    analyze_sla,
    format_moral_hazard,
)
from ussy_actuary.db import get_connection, DEFAULT_DB_PATH


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="actuary",
        description="Actuary — Actuarial Vulnerability Risk Quantification",
    )
    parser.add_argument(
        "--db", default=None,
        help="Path to SQLite database (default: ~/.actuary/actuary.db)",
    )
    parser.add_argument(
        "--json", action="store_true", default=False,
        help="Output results as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # survival command
    survival = subparsers.add_parser(
        "survival",
        help="Compute CVE exploit survival table (actuarial life table)",
    )
    survival.add_argument(
        "--cohort", default="default",
        help="Cohort identifier (e.g., Q1-2025)",
    )
    survival.add_argument(
        "--lambda", type=float, default=1.0, dest="lambda_",
        help="Whittaker-Henderson smoothing parameter (default: 1.0)",
    )
    survival.add_argument(
        "--data", nargs="+", default=["nvd"],
        help="Data sources: nvd, kev, greynoise",
    )

    # backlog command
    backlog = subparsers.add_parser(
        "backlog",
        help="Project vulnerability backlog using chain ladder method",
    )
    backlog.add_argument(
        "--repo", default=".",
        help="Repository path or identifier",
    )
    backlog.add_argument(
        "--quarters", type=int, default=8,
        help="Number of quarters to project (default: 8)",
    )
    backlog.add_argument(
        "--confidence", type=float, default=0.95,
        help="Confidence level for intervals (default: 0.95)",
    )

    # credibility command
    cred = subparsers.add_parser(
        "credibility",
        help="Blend internal/external threat intel using Bühlmann credibility",
    )
    cred.add_argument(
        "--org", default="default",
        help="Organization identifier",
    )
    cred.add_argument(
        "--n-obs", type=int, default=0,
        help="Number of internal observations",
    )
    cred.add_argument(
        "--internal", default=None,
        help="Path to internal SOC/WAF log CSV",
    )
    cred.add_argument(
        "--external", nargs="+", default=["epss", "kev"],
        help="External data sources",
    )
    cred.add_argument(
        "--epv", type=float, default=None,
        help="Override EPV (Expected Process Variance)",
    )
    cred.add_argument(
        "--vhm", type=float, default=None,
        help="Override VHM (Variance of Hypothetical Means)",
    )

    # ibnr command
    ibnr = subparsers.add_parser(
        "ibnr",
        help="Estimate latent vulnerabilities via IBNR methods",
    )
    ibnr.add_argument(
        "--repo", default=".",
        help="Repository path or identifier",
    )
    ibnr.add_argument(
        "--density", type=float, default=15.0,
        help="Industry bugs/KLOC density (default: 15.0)",
    )
    ibnr.add_argument(
        "--kloc", type=float, default=10.0,
        help="Codebase size in thousands of lines of code (default: 10.0)",
    )
    ibnr.add_argument(
        "--reported", type=int, default=0,
        help="Number of reported vulnerabilities (default: 0, uses DB)",
    )
    ibnr.add_argument(
        "--method", choices=["bf", "cape-cod"], default="bf",
        help="IBNR method: bf (Bornhuetter-Ferguson) or cape-cod (default: bf)",
    )

    # aggregate command
    agg = subparsers.add_parser(
        "aggregate",
        help="Correlated vulnerability risk aggregation with copula models",
    )
    agg.add_argument(
        "--assets", type=int, default=100,
        help="Number of vulnerable assets (default: 100)",
    )
    agg.add_argument(
        "--prob", type=float, default=0.01,
        help="Base exploit probability per asset (default: 0.01)",
    )
    agg.add_argument(
        "--copula", choices=["independent", "gaussian", "clayton", "gumbel"],
        default="independent",
        help="Copula type (default: independent)",
    )
    agg.add_argument(
        "--alpha", type=float, default=2.0,
        help="Clayton copula alpha parameter (default: 2.0)",
    )
    agg.add_argument(
        "--beta", type=float, default=2.0,
        help="Gumbel copula beta parameter (default: 2.0)",
    )
    agg.add_argument(
        "--correlation", type=float, default=0.3,
        help="Gaussian copula correlation (default: 0.3)",
    )
    agg.add_argument(
        "--var", type=float, default=0.99, dest="var_level",
        help="Value-at-Risk level (default: 0.99)",
    )
    agg.add_argument(
        "--sims", type=int, default=10000,
        help="Number of Monte Carlo simulations (default: 10000)",
    )
    agg.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    # moral-hazard command
    mh = subparsers.add_parser(
        "moral-hazard",
        help="Quantify security incentive misalignment from SLAs/insurance",
    )
    mh.add_argument(
        "--loss", type=float, default=1_000_000,
        help="Potential loss from a breach (default: 1000000)",
    )
    mh.add_argument(
        "--probability", type=float, default=0.05,
        help="Base breach probability without coverage (default: 0.05)",
    )
    mh.add_argument(
        "--effort-cost", type=float, default=0.3,
        help="Cost per unit of security effort (default: 0.3)",
    )
    mh.add_argument(
        "--coverage", type=float, default=0.8,
        help="Fraction of loss covered by SLA/insurance (default: 0.8)",
    )
    mh.add_argument(
        "--elasticity", type=float, default=0.5,
        help="Effort elasticity of breach probability (default: 0.5)",
    )
    mh.add_argument(
        "--sla-penalty", type=float, default=None,
        help="SLA violation penalty (for SLA analysis)",
    )

    return parser


def cmd_survival(args: argparse.Namespace) -> str:
    """Handle the survival command."""
    # Demo: create a sample cohort life table
    # In production, this would load from NVD/KEV/Greynoise
    ages = [0, 30, 60, 90, 180, 365]
    l_values = [847, 812, 741, 634, 421, 198]
    d_values = [12, 28, 45, 38, 15, 4]

    table = compute_life_table(ages, l_values, d_values, cohort_id=args.cohort)

    if args.lambda_ > 0:
        table = apply_graduation(table, lambda_=args.lambda_)

    if getattr(args, "json", False):
        rows = []
        for r in table.rows:
            rows.append({
                "age_days": r.age_days,
                "l_v": r.l_v,
                "d_v": r.d_v,
                "q_v": r.q_v,
                "mu_v": round(r.mu_v, 6),
                "e_v": round(r.e_v, 1),
                "q_v_graduated": round(r.q_v_graduated, 6),
            })
        return json.dumps({"cohort_id": table.cohort_id, "rows": rows}, indent=2)

    return format_life_table(table, use_graduated=args.lambda_ > 0)


def cmd_backlog(args: argparse.Namespace) -> str:
    """Handle the backlog command."""
    # Demo: create a sample development triangle
    triangle = DevelopmentTriangle(repo_id=args.repo)
    data = [
        ("Q1-2024", 0, 12), ("Q1-2024", 1, 28), ("Q1-2024", 2, 41),
        ("Q1-2024", 3, 48), ("Q1-2024", 4, 52),
        ("Q2-2024", 0, 15), ("Q2-2024", 1, 33), ("Q2-2024", 2, 49),
        ("Q2-2024", 3, 57),
        ("Q3-2024", 0, 18), ("Q3-2024", 1, 39), ("Q3-2024", 2, 56),
        ("Q4-2024", 0, 21), ("Q4-2024", 1, 44),
        ("Q1-2025", 0, 24),
    ]
    for cohort, dev_q, count in data:
        triangle.set_value(cohort, dev_q, count)

    result = chain_ladder_analysis(triangle, confidence_level=args.confidence)

    if getattr(args, "json", False):
        return json.dumps({
            "repo_id": args.repo,
            "age_to_age_factors": result.age_to_age_factors,
            "total_reserve": result.total_reserve,
            "confidence_lower": result.confidence_lower,
            "confidence_upper": result.confidence_upper,
            "projected": {
                k: {str(k2): v2 for k2, v2 in v.items()}
                for k, v in result.projected_triangle.items()
            },
        }, indent=2)

    return format_triangle(triangle, result)


def cmd_credibility(args: argparse.Namespace) -> str:
    """Handle the credibility command."""
    if args.epv is not None and args.vhm is not None:
        # Direct parameter mode
        result = credibility_from_params(
            org_id=args.org,
            n_obs=args.n_obs,
            epv=args.epv,
            vhm=args.vhm,
            internal_mean=0.05,  # Would come from internal data
            population_mean=0.03,  # Would come from EPSS
        )
    else:
        # Demo with sample data
        org_data = [[0.04 + 0.01 * i for i in range(max(1, args.n_obs))]]
        all_groups = [
            [0.02, 0.03, 0.025, 0.035],
            [0.05, 0.06, 0.055, 0.065],
            org_data[0] if args.n_obs > 0 else [0.04],
        ]
        result = compute_credibility(
            org_id=args.org,
            n_obs=max(1, args.n_obs),
            internal_data=org_data[0] if args.n_obs > 0 else [0.04],
            all_groups_data=all_groups,
            population_mean=0.03,
        )

    if getattr(args, "json", False):
        return json.dumps({
            "org_id": result.org_id,
            "n_obs": result.n_obs,
            "epv": result.epv,
            "vhm": result.vhm,
            "K": result.K,
            "Z": result.Z,
            "internal_mean": result.internal_mean,
            "population_mean": result.population_mean,
            "blended_mean": result.blended_mean,
        }, indent=2)

    return format_credibility(result)


def cmd_ibnr(args: argparse.Namespace) -> str:
    """Handle the ibnr command."""
    if args.reported > 0 and args.density > 0 and args.kloc > 0:
        # Simple density-based IBNR
        result = ibnr_from_density(
            reported_count=args.reported,
            density_per_kloc=args.density,
            kloc=args.kloc,
            method=args.method,
        )
        results = [result]
    else:
        # Demo with development triangle
        triangle = DevelopmentTriangle(repo_id=args.repo)
        data = [
            ("Q1-2024", 0, 12), ("Q1-2024", 1, 28), ("Q1-2024", 2, 41),
            ("Q1-2024", 3, 48), ("Q1-2024", 4, 52),
            ("Q2-2024", 0, 15), ("Q2-2024", 1, 33), ("Q2-2024", 2, 49),
            ("Q2-2024", 3, 57),
            ("Q3-2024", 0, 18), ("Q3-2024", 1, 39), ("Q3-2024", 2, 56),
            ("Q4-2024", 0, 21), ("Q4-2024", 1, 44),
            ("Q1-2025", 0, 24),
        ]
        for cohort, dev_q, count in data:
            triangle.set_value(cohort, dev_q, count)

        if args.method == "bf":
            priors = {"Q2-2024": 65, "Q3-2024": 72, "Q4-2024": 58, "Q1-2025": 68}
            results = bornhuetter_ferguson(triangle, priors)
        else:
            results = cape_cod(triangle)

    if getattr(args, "json", False):
        return json.dumps([{
            "repo_id": r.repo_id,
            "method": r.method,
            "reported_count": r.reported_count,
            "prior_ultimate": r.prior_ultimate,
            "bf_reserve": r.bf_reserve,
            "bf_ultimate": r.bf_ultimate,
            "cape_cod_prior": r.cape_cod_prior,
        } for r in results], indent=2)

    return format_ibnr(results)


def cmd_aggregate(args: argparse.Namespace) -> str:
    """Handle the aggregate command."""
    copula_params = {}
    if args.copula == "gaussian":
        copula_params["correlation"] = args.correlation
    elif args.copula == "clayton":
        copula_params["alpha"] = args.alpha
    elif args.copula == "gumbel":
        copula_params["beta"] = args.beta
    copula_params["var_level"] = args.var_level

    result = simulate_aggregate_loss(
        n_assets=args.assets,
        exploit_prob=args.prob,
        copula_type=args.copula,
        copula_params=copula_params,
        n_simulations=args.sims,
        seed=args.seed,
    )

    if getattr(args, "json", False):
        return json.dumps({
            "model_id": result.model_id,
            "copula_type": result.copula_type,
            "n_assets": result.n_assets,
            "n_simulations": result.n_simulations,
            "var_level": result.var_level,
            "var_value": round(result.var_value, 2),
            "tvar_value": round(result.tvar_value, 2),
            "mean_loss": round(result.mean_loss, 2),
        }, indent=2)

    return format_copula_result(result)


def cmd_moral_hazard(args: argparse.Namespace) -> str:
    """Handle the moral-hazard command."""
    if args.sla_penalty is not None:
        result = analyze_sla(
            vendor_coverage=args.coverage,
            sla_penalty=args.sla_penalty,
            base_loss=args.loss,
            base_probability=args.probability,
            effort_cost=args.effort_cost,
            effort_elasticity=args.elasticity,
        )
        if getattr(args, "json", False):
            return json.dumps(result, indent=2)
        lines = [
            "SLA Moral Hazard Analysis",
            f"  Vendor coverage:     {result['vendor_coverage']:.2%}",
            f"  SLA penalty:         {result['sla_penalty']:,.0f}",
            f"  Effective coverage:  {result['effective_coverage']:.2%}",
            f"  Effort reduction:    {result['effort_reduction_pct']:.1f}%",
            f"  Welfare loss:        {result['welfare_loss']:,.0f}",
            f"  Optimal coinsurance: {result['optimal_coinsurance']:.2%}",
            f"  Breach prob change:  {result['breach_probability_change']:+.4f}",
            f"  Recommendation:      {result['recommendation']}",
        ]
        return "\n".join(lines)

    result = compute_moral_hazard(
        base_loss=args.loss,
        base_probability=args.probability,
        effort_cost=args.effort_cost,
        coverage_fraction=args.coverage,
        effort_elasticity=args.elasticity,
    )

    if getattr(args, "json", False):
        return json.dumps({
            "base_loss": result.base_loss,
            "base_probability": result.base_probability,
            "coverage_fraction": result.coverage_fraction,
            "optimal_effort_uncovered": result.optimal_effort_uncovered,
            "optimal_effort_covered": result.optimal_effort_covered,
            "effort_reduction_pct": result.effort_reduction_pct,
            "welfare_loss": result.welfare_loss,
            "optimal_coinsurance": result.optimal_coinsurance,
            "covered_breach_probability": result.covered_breach_probability,
        }, indent=2)

    return format_moral_hazard(result)


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    # Ensure json flag is available
    if not hasattr(args, "json"):
        args.json = False

    commands = {
        "survival": cmd_survival,
        "backlog": cmd_backlog,
        "credibility": cmd_credibility,
        "ibnr": cmd_ibnr,
        "aggregate": cmd_aggregate,
        "moral-hazard": cmd_moral_hazard,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return

    try:
        output = handler(args)
        print(output)
    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
