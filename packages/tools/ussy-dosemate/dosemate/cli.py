"""CLI interface for Dosemate — Pharmacokinetic ADME Modeling for Code Changes."""

import argparse
import json
import sys
from typing import Optional

from dosemate import __version__
from dosemate.pk_fitter import PKModelFitter, report_to_dict
from dosemate.absorption import compute_absorption, AbsorptionParams
from dosemate.distribution import compute_distribution, DistributionParams
from dosemate.excretion import compute_excretion, ExcretionParams
from dosemate.metabolism import compute_metabolism, MetabolismParams
from dosemate.steady_state import (
    compute_steady_state, compute_dose_plan, SteadyStateParams, DosePlan,
)
from dosemate.ddi import (
    compute_ddi, analyze_all_interactions, compute_breaking_change_displacement,
)
from dosemate.ci_collector import CICollector
from dosemate.git_parser import GitHistoryParser, PullRequestInfo
from dosemate.dependency_graph import DependencyGraphAnalyzer
from dosemate.two_compartment import compute_two_compartment


def parse_duration(duration_str: str) -> str:
    """Convert a human duration like '7d', '2w', '90d' to a git --since compatible string.

    Returns the string suitable for git --since argument.
    """
    # Git handles '7 days ago', '2 weeks ago' etc.
    mapping = {
        'd': 'day',
        'w': 'week',
        'm': 'month',
        'y': 'year',
    }

    for suffix, word in mapping.items():
        if duration_str.endswith(suffix):
            try:
                num = int(duration_str[:-1])
                return f"{num} {word}{'s' if num != 1 else ''} ago"
            except ValueError:
                pass

    # If it's already a date or git-compatible string, return as-is
    return duration_str


def format_section(title: str, content: str) -> str:
    """Format a section with a title underline."""
    line = "=" * len(title)
    return f"\n{title}\n{line}\n{content}\n"


def cmd_analyze(args):
    """Run full ADME analysis on a repository."""
    repo = args.repo or "."
    since = parse_duration(args.since) if args.since else None

    fitter = PKModelFitter(repo_path=repo)
    report = fitter.analyze(since=since)
    data = report_to_dict(report)

    if args.json:
        print(json.dumps(data, indent=2))
        return

    # Human-readable output
    output = []
    output.append(format_section(
        "Dosemate ADME Analysis",
        f"Repository: {repo}\nSince: {args.since or 'all time'}",
    ))

    for pr_id, pk_data in data.get("change_pk", {}).items():
        output.append(format_section(
            f"Change: {pr_id}",
            f"  Dose (lines changed): {pk_data['dose_lines']}\n"
            f"\n  Absorption:\n"
            f"    ka (absorption rate): {pk_data['absorption']['ka_day_neg1']:.4f} day⁻¹\n"
            f"    Lag time: {pk_data['absorption']['lag_time_hours']:.1f} hours\n"
            f"    Fraction absorbed: {pk_data['absorption']['fraction_absorbed']:.2%}\n"
            f"\n  Distribution:\n"
            f"    Vd (volume of distribution): {pk_data['distribution']['Vd_modules']:.1f} modules\n"
            f"    Kp (tissue partition): {pk_data['distribution']['Kp']:.2f}\n"
            f"    fu (unbound fraction): {pk_data['distribution']['fu_public_api_fraction']:.2%}\n"
            f"\n  Metabolism:\n"
            f"    First-pass effect: {pk_data['metabolism']['first_pass_effect']:.2%}\n"
            f"    Bioavailability (F): {pk_data['metabolism']['bioavailability_F']:.2%}\n"
            f"    CI saturation: {pk_data['metabolism']['ci_saturation_fraction']:.1%}\n"
            f"\n  Excretion:\n"
            f"    CL (clearance): {pk_data['excretion']['CL_per_week']:.4f}/week\n"
            f"    ke (elimination rate): {pk_data['excretion']['ke_per_week']:.6f}/week\n"
            f"    t½ (half-life): {pk_data['excretion']['t_half_weeks']:.1f} weeks",
        ))

    if data.get("interactions"):
        output.append(format_section("Drug-Drug Interactions", ""))
        for interaction in data["interactions"]:
            output.append(
                f"  {interaction['pair']}:\n"
                f"    Shared modules: {interaction['shared_modules']}\n"
                f"    AUC ratio: {interaction['AUC_ratio']:.2f}\n"
                f"    Severity: {interaction['severity']}\n"
                f"    → {interaction['recommendation']}\n"
            )

    ss = data.get("steady_state")
    if ss:
        output.append(format_section(
            "Steady State",
            f"  Css (change pressure): {ss['Css_changes_per_module']:.2f} changes/module\n"
            f"  Accumulation factor (R): {ss['accumulation_factor_R']:.2f}\n"
            f"  Time to steady state: {ss['time_to_steady_state_weeks']:.1f} weeks\n"
            f"  Assessment: {ss['assessment']}",
        ))

    dp = data.get("dose_plan")
    if dp:
        output.append(format_section(
            "Dose Plan",
            f"  Loading dose: {dp['loading_dose']:.1f}\n"
            f"  Maintenance dose: {dp['maintenance_dose']:.1f}\n"
            f"  LD/MD ratio: {dp['LD_over_MD']:.2f}\n"
            f"  → {dp['interpretation']}",
        ))

    print("\n".join(output))


def cmd_profile(args):
    """Compute detailed pharmacokinetic profile for recent changes."""
    repo = args.repo or "."
    since = parse_duration(args.since) if args.since else "30 days ago"

    parser = GitHistoryParser(repo)
    prs = parser.synthesize_prs(since=since)

    if not prs:
        print("No merge commits found in the specified time range.")
        return

    dep_analyzer = DependencyGraphAnalyzer(repo)
    dep_analyzer.analyze()
    file_to_module = parser.get_file_module_map()

    print(f"\nPharmacokinetic Profile — {len(prs)} changes since {args.since or '30d'}\n")
    print(f"{'ID':<18} {'Lines':>6} {'ka':>8} {'Vd':>8} {'F':>6} {'t½(w)':>8} {'CL':>8}")
    print("-" * 68)

    ci_collector = CICollector(parser)
    ci_metrics = ci_collector.collect(since=since)

    for pr in prs:
        absorption = compute_absorption([pr])
        distribution = compute_distribution(pr.files_changed, dep_analyzer, file_to_module)
        metabolism = compute_metabolism(ci_metrics, absorption.fraction_absorbed)
        deprecated_removed, total_deprecated = parser.get_deprecated_lines(since)
        excretion = compute_excretion(distribution, deprecated_removed, total_deprecated)

        t_half_str = f"{excretion.t_half:.1f}" if excretion.t_half != float('inf') else "inf"

        print(
            f"{pr.id:<18} {pr.insertions + pr.deletions:>6} "
            f"{absorption.ka:>8.3f} {distribution.Vd:>8.1f} "
            f"{metabolism.bioavailability_F:>6.2%} {t_half_str:>8} "
            f"{excretion.CL:>8.4f}"
        )

    print()


def cmd_interact(args):
    """Detect drug-drug interactions between open/concurrent PRs."""
    repo = args.repo or "."
    since = parse_duration(args.since) if args.since else "7 days ago"

    parser = GitHistoryParser(repo)
    prs = parser.synthesize_prs(since=since)

    if len(prs) < 2:
        if getattr(args, 'json', False):
            print(json.dumps([], indent=2))
        else:
            print("Need at least 2 PRs/merge commits to detect interactions.")
        return

    dep_analyzer = DependencyGraphAnalyzer(repo)
    dep_analyzer.analyze()
    file_to_module = parser.get_file_module_map()

    ci_collector = CICollector(parser)
    ci_metrics = ci_collector.collect(since=since)
    metabolism = compute_metabolism(ci_metrics)

    interactions = analyze_all_interactions(
        prs, dep_analyzer, file_to_module, metabolism,
    )

    if args.json:
        result = []
        for i in interactions:
            result.append({
                "pair": f"{i.pr_a}_x_{i.pr_b}",
                "shared_modules": i.shared_modules,
                "Km_apparent_ratio": round(i.Km_apparent_ratio, 4),
                "AUC_ratio": round(i.AUC_ratio, 4),
                "severity": i.severity,
                "recommendation": i.recommendation,
            })
        print(json.dumps(result, indent=2))
        return

    print(f"\nDrug-Drug Interaction Analysis — {len(prs)} concurrent changes\n")

    severity_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    for interaction in interactions:
        severity_counts[interaction.severity] += 1
        icon = {"low": "✓", "moderate": "⚠", "high": "✗", "critical": "⛔"}.get(
            interaction.severity, "?"
        )
        print(
            f"  {icon} {interaction.pr_a} × {interaction.pr_b}\n"
            f"    Shared modules: {interaction.shared_modules} | "
            f"AUC ratio: {interaction.AUC_ratio:.2f} | "
            f"Severity: {interaction.severity}\n"
            f"    → {interaction.recommendation}\n"
        )

    print(f"Summary: {severity_counts['low']} low, {severity_counts['moderate']} moderate, "
          f"{severity_counts['high']} high, {severity_counts['critical']} critical")


def cmd_saturate(args):
    """Analyze CI/CD saturation using Michaelis-Menten kinetics."""
    repo = args.repo or "."
    since = parse_duration(args.since) if args.since else "30 days ago"

    parser = GitHistoryParser(repo)
    ci_collector = CICollector(parser)
    ci_metrics = ci_collector.collect(since=since)
    metabolism = compute_metabolism(ci_metrics)

    if args.json:
        result = {
            "Vmax_prs_per_day": round(metabolism.Vmax, 2),
            "Km_lines": round(metabolism.Km, 2),
            "ci_saturation_fraction": round(metabolism.ci_saturation_fraction, 4),
            "current_operating_point": f"{metabolism.ci_saturation_fraction * 100:.0f}% of Vmax",
            "diagnosis": metabolism.saturation_diagnosis(),
            "pr_arrival_rate": round(ci_metrics.pr_arrival_rate, 4),
            "avg_pr_size": round(ci_metrics.avg_pr_size_lines, 1),
        }
        print(json.dumps(result, indent=2))
        return

    pct = metabolism.ci_saturation_fraction * 100

    print("\nCI/CD Saturation Analysis (Michaelis-Menten)\n")
    print(f"  Vmax (max CI capacity):     {metabolism.Vmax:.1f} PRs/day")
    print(f"  Km (half-saturation size):   {metabolism.Km:.0f} lines")
    print(f"  Current operating point:     {pct:.0f}% of Vmax")
    print(f"  PR arrival rate:             {ci_metrics.pr_arrival_rate:.2f} PRs/day")
    print(f"  Average PR size:             {ci_metrics.avg_pr_size_lines:.0f} lines")
    print(f"\n  Diagnosis: {metabolism.saturation_diagnosis()}")

    # Michaelis-Menten curve data points
    print(f"\n  Throughput Curve (lines → throughput):")
    print(f"  {'Lines':>8} {'Rate (PRs/day)':>15} {'%Vmax':>8}")
    print(f"  {'-'*35}")
    for lines in [100, 200, 400, 800, 1600, 3200]:
        rate = metabolism.michaelis_menten_rate(lines)
        print(f"  {lines:>8} {rate:>15.2f} {rate/metabolism.Vmax*100:>7.1f}%")
    print()


def cmd_steady_state(args):
    """Compute steady-state change pressure and accumulation."""
    repo = args.repo or "."
    since = parse_duration(args.since) if args.since else "90 days ago"
    sprint = args.sprint or "2w"

    # Parse sprint duration
    sprint_weeks = 2.0
    if sprint.endswith('w'):
        try:
            sprint_weeks = float(sprint[:-1])
        except ValueError:
            pass
    elif sprint.endswith('d'):
        try:
            sprint_weeks = float(sprint[:-1]) / 7.0
        except ValueError:
            pass

    fitter = PKModelFitter(repo_path=repo)
    report = fitter.analyze(since=since)
    data = report_to_dict(report)

    if args.json:
        print(json.dumps(data.get("steady_state", {}), indent=2))
        return

    ss = data.get("steady_state", {})
    dp = data.get("dose_plan", {})

    print("\nSteady-State & Accumulation Analysis\n")
    print(f"  Sprint duration:             {sprint_weeks:.1f} weeks")
    if ss:
        print(f"  Css (change pressure):       {ss.get('Css_changes_per_module', 'N/A')} changes/module")
        print(f"  Accumulation factor (R):     {ss.get('accumulation_factor_R', 'N/A')}")
        print(f"  Time to steady state:        {ss.get('time_to_steady_state_weeks', 'N/A')} weeks")
        print(f"  Assessment:                  {ss.get('assessment', 'N/A')}")

    if dp:
        print(f"\n  Dose Plan:")
        print(f"    Loading dose:              {dp.get('loading_dose', 'N/A'):.1f}")
        print(f"    Maintenance dose:          {dp.get('maintenance_dose', 'N/A'):.1f}")
        print(f"    LD/MD ratio:               {dp.get('LD_over_MD', 'N/A')}")
        print(f"    → {dp.get('interpretation', 'N/A')}")

    print()


def build_parser():
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="dosemate",
        description="Dosemate — Pharmacokinetic ADME Modeling for Code Change Propagation",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze ADME parameters for recent changes")
    p_analyze.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    p_analyze.add_argument("--since", default="30d", help="Lookback window (e.g., 7d, 2w, 90d)")
    p_analyze.add_argument("--json", action="store_true", help="Output as JSON")

    # profile
    p_profile = subparsers.add_parser("profile", help="Compute PK profile for recent changes")
    p_profile.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    p_profile.add_argument("--since", default="30d", help="Lookback window (e.g., 7d, 2w, 90d)")

    # interact
    p_interact = subparsers.add_parser("interact", help="Detect drug-drug interactions between PRs")
    p_interact.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    p_interact.add_argument("--since", default="7d", help="Lookback window")
    p_interact.add_argument("--json", action="store_true", help="Output as JSON")

    # saturate
    p_saturate = subparsers.add_parser("saturate", help="Analyze CI/CD saturation (Michaelis-Menten)")
    p_saturate.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    p_saturate.add_argument("--since", default="30d", help="Lookback window")
    p_saturate.add_argument("--json", action="store_true", help="Output as JSON")

    # steady-state
    p_ss = subparsers.add_parser("steady-state", help="Compute steady-state change pressure")
    p_ss.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    p_ss.add_argument("--since", default="90d", help="Lookback window")
    p_ss.add_argument("--sprint", default="2w", help="Sprint/release duration (e.g., 1w, 2w, 4w)")
    p_ss.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def main():
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "analyze": cmd_analyze,
        "profile": cmd_profile,
        "interact": cmd_interact,
        "saturate": cmd_saturate,
        "steady-state": cmd_steady_state,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
