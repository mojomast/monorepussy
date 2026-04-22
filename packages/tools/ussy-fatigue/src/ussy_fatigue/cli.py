"""CLI interface for Fatigue — Fracture Mechanics for Code Decay Prediction.

Commands:
    scan       — Detect cracks and compute stress intensity
    predict    — Predict decay trajectory for a module
    what-if    — Simulate refactoring interventions
    calibrate  — Calibrate material constants from git history
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import __version__, DEFAULT_C, DEFAULT_M, DEFAULT_K_IC, DEFAULT_K_E
from .models import (
    Crack,
    CrackType,
    MaterialConstants,
    ModuleMetrics,
    ModuleStatus,
    StressIntensity,
)
from .scanner import CrackScanner, build_import_graph, detect_circular_dependencies
from .stress import (
    compute_churn_rate,
    compute_coupling,
    compute_stress_intensity,
    estimate_test_coverage,
)
from .paris import (
    calibrate_from_history,
    calibrate_material_constants,
    calibrate_per_module,
    estimate_endurance_limit,
    estimate_fracture_toughness,
    paris_law,
)
from .predictor import (
    estimate_debt_from_cracks,
    predict_decay,
    recommend_arrest_strategies,
)
from .whatif import simulate_intervention, list_interventions
from .monitor import run_monitor


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fatigue",
        description="Fatigue — Fracture Mechanics for Code Decay Prediction",
    )
    parser.add_argument(
        "--version", action="version", version=f"fatigue {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Detect cracks and compute stress intensity"
    )
    scan_parser.add_argument(
        "path", help="Directory or file to scan"
    )
    scan_parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)"
    )

    # predict command
    predict_parser = subparsers.add_parser(
        "predict", help="Predict decay trajectory for a module"
    )
    predict_parser.add_argument(
        "path", help="Module path to predict decay for"
    )
    predict_parser.add_argument(
        "--horizon", type=int, default=10,
        help="Prediction horizon in sprints (default: 10)"
    )
    predict_parser.add_argument(
        "--cycles-per-week", type=float, default=2.0,
        help="Load cycles per week (default: 2.0)"
    )
    predict_parser.add_argument(
        "--C", type=float, default=DEFAULT_C,
        help=f"Paris' Law C coefficient (default: {DEFAULT_C})"
    )
    predict_parser.add_argument(
        "--m", type=float, default=DEFAULT_M,
        help=f"Paris' Law m exponent (default: {DEFAULT_M})"
    )
    predict_parser.add_argument(
        "--K-Ic", type=float, default=DEFAULT_K_IC,
        help=f"Fracture toughness (default: {DEFAULT_K_IC})"
    )
    predict_parser.add_argument(
        "--K-e", type=float, default=DEFAULT_K_E,
        help=f"Endurance limit (default: {DEFAULT_K_E})"
    )

    # what-if command
    whatif_parser = subparsers.add_parser(
        "what-if", help="Simulate refactoring interventions"
    )
    whatif_parser.add_argument(
        "path", help="Module path to analyze"
    )
    whatif_parser.add_argument(
        "--refactor", required=True,
        choices=list(list_interventions().keys()),
        help="Intervention type"
    )
    whatif_parser.add_argument(
        "--in", dest="in_sprints", type=int, default=1,
        help="Sprint number for intervention (default: 1)"
    )
    whatif_parser.add_argument(
        "--horizon", type=int, default=10,
        help="Projection horizon in sprints (default: 10)"
    )
    whatif_parser.add_argument(
        "--C", type=float, default=DEFAULT_C,
        help=f"Paris' Law C coefficient (default: {DEFAULT_C})"
    )
    whatif_parser.add_argument(
        "--m", type=float, default=DEFAULT_M,
        help=f"Paris' Law m exponent (default: {DEFAULT_M})"
    )
    whatif_parser.add_argument(
        "--K-Ic", type=float, default=DEFAULT_K_IC,
        help=f"Fracture toughness (default: {DEFAULT_K_IC})"
    )
    whatif_parser.add_argument(
        "--K-e", type=float, default=DEFAULT_K_E,
        help=f"Endurance limit (default: {DEFAULT_K_E})"
    )

    # calibrate command
    calibrate_parser = subparsers.add_parser(
        "calibrate", help="Calibrate material constants from git history"
    )
    calibrate_parser.add_argument(
        "path", help="Project directory to calibrate"
    )
    calibrate_parser.add_argument(
        "--history", type=str, default="6months",
        help="History period to analyze (default: 6months)"
    )
    calibrate_parser.add_argument(
        "--K-Ic", type=float, default=DEFAULT_K_IC,
        help=f"Fracture toughness (default: {DEFAULT_K_IC})"
    )
    calibrate_parser.add_argument(
        "--K-e", type=float, default=DEFAULT_K_E,
        help=f"Endurance limit (default: {DEFAULT_K_E})"
    )
    calibrate_parser.add_argument(
        "--data", type=str, default=None,
        help="JSON file with historical delta_K and growth_rate data"
    )

    return parser


def cmd_scan(args: argparse.Namespace) -> int:
    """Execute the scan command."""
    scanner = CrackScanner()
    path = args.path

    # Scan for cracks
    if os.path.isfile(path):
        cracks = scanner.scan_file(path)
        # Also compute metrics
        metrics_map = {path: scanner.compute_module_metrics(path)}
    elif os.path.isdir(path):
        cracks = scanner.scan_directory(path)
        # Compute metrics for all Python files
        metrics_map = {}
        for py_file in Path(path).rglob("*.py"):
            fpath = str(py_file)
            metrics_map[fpath] = scanner.compute_module_metrics(fpath)
    else:
        print(f"Error: {path} is not a valid file or directory", file=sys.stderr)
        return 1

    # Detect circular dependencies
    if os.path.isdir(path):
        import_graph = build_import_graph(path)
        cycles = detect_circular_dependencies(import_graph)
    else:
        import_graph = {}
        cycles = []

    # Add circular dependency cracks
    for cycle in cycles:
        for module in cycle:
            cracks.append(Crack(
                crack_type=CrackType.CIRCULAR_DEPENDENCY,
                file_path=module.replace(".", os.sep) + ".py",
                line_number=0,
                severity=8.5,
                description=f"Circular dependency: {' → '.join(cycle)} → {cycle[0]}",
            ))

    # Compute coupling and stress intensity for each module
    stress_map: dict[str, StressIntensity] = {}
    for fpath, metrics in metrics_map.items():
        # Compute coupling
        metrics.coupling = compute_coupling(fpath, path if os.path.isdir(path) else os.path.dirname(path), import_graph)
        # Compute churn
        metrics.churn_rate = compute_churn_rate(fpath)
        # Estimate coverage
        metrics.test_coverage = estimate_test_coverage(fpath)

        stress = compute_stress_intensity(metrics)
        stress_map[fpath] = stress

    # Organize cracks by type
    crack_counts: dict[CrackType, list[Crack]] = {}
    for crack in cracks:
        crack_counts.setdefault(crack.crack_type, []).append(crack)

    # Identify critical cracks (K > K_Ic)
    material = MaterialConstants()
    critical_cracks = []
    for crack in cracks:
        if crack.file_path in stress_map:
            s = stress_map[crack.file_path]
            if s.K >= material.K_Ic:
                critical_cracks.append((crack, s))

    if args.format == "json":
        output = {
            "total_cracks": len(cracks),
            "modules_scanned": len(metrics_map),
            "crack_types": {
                ct.value: len(cs) for ct, cs in crack_counts.items()
            },
            "cracks": [
                {
                    "type": c.crack_type.value,
                    "file": c.file_path,
                    "line": c.line_number,
                    "severity": c.severity,
                    "description": c.description,
                }
                for c in cracks
            ],
            "stress_intensities": {
                fp: {"K": s.K, "delta_K": s.delta_K}
                for fp, s in stress_map.items()
            },
            "critical": [
                {
                    "file": c.file_path,
                    "type": c.crack_type.value,
                    "K": s.K,
                    "description": c.description,
                }
                for c, s in critical_cracks
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Text output
        print(f"\n{'='*70}")
        print(f"  FATIGUE — Crack Detection Report")
        print(f"{'='*70}")
        print()
        print(f"  🔍 {len(cracks)} cracks detected across {len(metrics_map)} modules")
        print()
        print(f"  {'CRACK TYPE':<24} {'COUNT':>6} {'AVG SEVERITY':>14}")
        print(f"  {'─'*24} {'─'*6} {'─'*14}")

        for crack_type in CrackType:
            if crack_type in crack_counts:
                cs = crack_counts[crack_type]
                avg_sev = sum(c.severity for c in cs) / len(cs)
                print(f"  {crack_type.value:<24} {len(cs):>6} {avg_sev:>10.1f}/10")

        if critical_cracks:
            print()
            print(f"  ⚠️  CRITICAL CRACKS (K > K_Ic = {material.K_Ic}):")
            print()
            for crack, stress in critical_cracks:
                print(f"  {crack.file_path}")
                print(f"    Crack: {crack.description}")
                print(f"    Stress intensity: K = {stress.K:.1f} (K_Ic = {material.K_Ic})")
                growth = paris_law(stress.K, material.C, material.m)
                print(f"    Growth rate: da/dN = {growth:.1f} debt units/cycle")
                print()

        print(f"{'='*70}")

    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    """Execute the predict command."""
    path = args.path

    if not os.path.exists(path):
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 1

    # Create material constants
    material = MaterialConstants(
        C=args.C, m=args.m, K_Ic=args.K_Ic, K_e=args.K_e
    )

    # Compute metrics
    scanner = CrackScanner()
    if os.path.isfile(path):
        metrics = scanner.compute_module_metrics(path)
        cracks = scanner.scan_file(path)
    else:
        # For a directory, find the most stressed module
        metrics = scanner.compute_module_metrics(path)
        cracks = scanner.scan_directory(path)

    # Compute stress
    metrics.churn_rate = compute_churn_rate(path)
    metrics.coupling = metrics.fan_in + metrics.fan_out
    metrics.test_coverage = estimate_test_coverage(path)
    stress = compute_stress_intensity(metrics)

    # Estimate debt
    debt = estimate_debt_from_cracks(cracks)
    if debt == 0:
        debt = metrics.cyclomatic_complexity * 0.5  # Fallback debt estimate

    # Predict
    prediction = predict_decay(
        stress=stress,
        material=material,
        current_debt=debt,
        cycles_per_week=args.cycles_per_week,
        horizon_sprints=args.horizon,
    )

    # Output
    print(f"\n{'='*70}")
    print(f"  FATIGUE — Decay Prediction for {path}")
    print(f"{'='*70}")
    print()
    print(f"  Current state:")
    print(f"    Debt magnitude (a): {prediction.current_debt:.1f} units")
    k_status = ""
    if prediction.current_K >= material.K_Ic:
        k_status = f" (ABOVE K_Ic = {material.K_Ic} ⚠️)"
    elif prediction.current_K >= material.K_e:
        k_status = f" (ABOVE K_e = {material.K_e})"
    print(f"    Stress intensity (K): {prediction.current_K:.1f}{k_status}")
    print(f"    Growth rate (da/dN): {prediction.growth_rate:.2f} units/cycle")
    print(f"    Status: {prediction.status.value}")
    print()

    if prediction.trajectory:
        print(f"  Projected decay trajectory:")
        print()
        print(f"  {'Sprint':<10} {'Debt':<12} {'Status'}")
        print(f"  {'─'*10} {'─'*12} {'─'*12}")
        for sprint, debt_val in prediction.trajectory:
            marker = ""
            if debt_val >= 100:
                marker = "CRITICAL"
            elif debt_val >= 60:
                marker = "WARNING"
            print(f"  {sprint:<10} {debt_val:<12.1f} {marker}")

    print()
    if prediction.time_to_critical_sprints is not None:
        print(f"  ⏱  Time to critical debt: Sprint {int(prediction.time_to_critical_sprints)} "
              f"(~{prediction.time_to_critical_weeks:.0f} weeks)")
        print()

    # Recommend arrest strategies
    strategies = recommend_arrest_strategies(stress, metrics)
    if strategies:
        print(f"  Recommended crack arrest strategies:")
        for i, s in enumerate(strategies, 1):
            print(f"    {i}. {s.name} ({s.description}) [Impact: {s.impact}]")

    print(f"\n{'='*70}")
    return 0


def cmd_whatif(args: argparse.Namespace) -> int:
    """Execute the what-if command."""
    path = args.path

    if not os.path.exists(path):
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 1

    material = MaterialConstants(
        C=args.C, m=args.m, K_Ic=args.K_Ic, K_e=args.K_e
    )

    # Compute metrics
    scanner = CrackScanner()
    metrics = scanner.compute_module_metrics(path)
    cracks = scanner.scan_file(path) if os.path.isfile(path) else scanner.scan_directory(path)
    metrics.churn_rate = compute_churn_rate(path)
    metrics.coupling = metrics.fan_in + metrics.fan_out
    metrics.test_coverage = estimate_test_coverage(path)
    stress = compute_stress_intensity(metrics)

    debt = estimate_debt_from_cracks(cracks)
    if debt == 0:
        debt = metrics.cyclomatic_complexity * 0.5

    # Simulate
    scenario = simulate_intervention(
        stress=stress,
        material=material,
        current_debt=debt,
        intervention=args.refactor,
        intervention_sprint=args.in_sprints,
        horizon_sprints=args.horizon,
    )

    # Output
    interventions = list_interventions()
    intervention_desc = interventions.get(args.refactor, args.refactor)

    print(f"\n{'='*70}")
    print(f"  FATIGUE — What-If Analysis")
    print(f"{'='*70}")
    print()
    print(f"  Scenario: {intervention_desc} in Sprint {args.in_sprints}")
    print()
    print(f"  WITHOUT intervention:")
    print(f"    Horizon: Debt = {scenario.without_debt_at_horizon:.1f}, "
          f"K = {scenario.without_K_at_horizon:.1f}, "
          f"Status: {scenario.without_status.value}")
    print()
    print(f"  WITH intervention (Sprint {args.in_sprints}):")
    print(f"    Horizon: Debt = {scenario.with_debt_at_horizon:.1f}, "
          f"K = {scenario.with_K_at_horizon:.1f}, "
          f"Status: {scenario.with_status.value}")
    print()
    print(f"  ROI: {scenario.roi_description}")
    print(f"       Debt prevented: {scenario.debt_prevented:.1f} units")
    print(f"\n{'='*70}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Execute the calibrate command."""
    path = args.path

    if not os.path.isdir(path):
        print(f"Error: {path} is not a directory", file=sys.stderr)
        return 1

    K_Ic = args.K_Ic
    K_e = args.K_e

    # Load data from JSON file or generate synthetic data from git history
    if args.data:
        try:
            with open(args.data, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading data file: {e}", file=sys.stderr)
            return 1

        if isinstance(data, list):
            material = calibrate_from_history(data, K_Ic, K_e)
        elif isinstance(data, dict):
            # Per-module data
            per_module = calibrate_per_module(data, K_Ic, K_e)
            material = per_module.get("__global__", MaterialConstants(K_Ic=K_Ic, K_e=K_e))
            if "__global__" not in per_module:
                # Use first module as global default
                material = next(iter(per_module.values()), MaterialConstants(K_Ic=K_Ic, K_e=K_e))

            # Show per-module results
            print(f"\n{'='*70}")
            print(f"  FATIGUE — Material Property Calibration")
            print(f"{'='*70}")
            print()
            print(f"  Per-module constants:")
            for module, mc in per_module.items():
                brittleness = "Ductile" if mc.m < 2.0 else "Moderate" if mc.m < 3.0 else "Brittle"
                print(f"    {module:<30} C={mc.C:<8.4f} m={mc.m:<5.1f} R²={mc.r_squared:.2f} ← {brittleness}")
            print()
            print(f"  Endurance limit: K_e = {K_e}")
            print(f"  Fracture toughness: K_Ic = {K_Ic}")
            print(f"\n{'='*70}")
            return 0
        else:
            print("Error: Data file must contain a list or dict", file=sys.stderr)
            return 1
    else:
        # Generate synthetic calibration data from git history
        scanner = CrackScanner()
        history_data = _generate_synthetic_history(path, scanner)

        if len(history_data) < 2:
            print("Insufficient data for calibration. Using default constants.")
            material = MaterialConstants(K_Ic=K_Ic, K_e=K_e)
        else:
            material = calibrate_from_history(history_data, K_Ic, K_e)

            # Also estimate K_e and K_Ic from data
            dk_values = [d['delta_K'] for d in history_data]
            gr_values = [d['growth_rate'] for d in history_data]
            if dk_values and gr_values:
                estimated_K_e = estimate_endurance_limit(dk_values, gr_values)
                estimated_K_Ic = estimate_fracture_toughness(dk_values, gr_values)
                material.K_e = estimated_K_e
                material.K_Ic = estimated_K_Ic

    # Output
    brittleness = "Ductile" if material.m < 2.0 else "Moderate" if material.m < 3.0 else "Brittle"

    print(f"\n{'='*70}")
    print(f"  FATIGUE — Material Property Calibration")
    print(f"{'='*70}")
    print()
    print(f"  Training data: {len(history_data) if 'history_data' in dir() else 0} data points")
    print()
    print(f"  Global material constants:")
    print(f"    C = {material.C:.4f}  (debt growth coefficient)")
    print(f"    m = {material.m:.1f}    (stress exponent — {brittleness})")
    print()
    print(f"  Endurance limit: K_e = {material.K_e:.1f} (below this, no fatigue failure)")
    print(f"  Fracture toughness: K_Ic = {material.K_Ic:.1f} (above this, catastrophic growth)")
    print()
    print(f"  Model fit: R² = {material.r_squared:.2f}", end="")
    if material.r_squared > 0.8:
        print(" (good predictive power)")
    elif material.r_squared > 0.5:
        print(" (moderate predictive power)")
    else:
        print(" (limited predictive power — more data recommended)")
    print(f"\n{'='*70}")
    return 0


def _generate_synthetic_history(directory: str, scanner: CrackScanner) -> list[dict]:
    """Generate synthetic calibration data by scanning the project.

    Creates data points by estimating stress and growth from current
    module metrics when git history is insufficient.
    """
    history_data: list[dict] = []

    for py_file in Path(directory).rglob("*.py"):
        fpath = str(py_file)
        metrics = scanner.compute_module_metrics(fpath)
        metrics.churn_rate = compute_churn_rate(fpath)
        metrics.coupling = metrics.fan_in + metrics.fan_out
        metrics.test_coverage = estimate_test_coverage(fpath)

        stress = compute_stress_intensity(metrics)

        # Estimate growth rate from current metrics
        if stress.K > 0:
            # Use a simple heuristic: growth rate proportional to K
            growth = 0.01 * (stress.K ** 1.5)
            history_data.append({
                'delta_K': stress.K,
                'growth_rate': growth,
            })

    return history_data


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "scan": cmd_scan,
        "predict": cmd_predict,
        "what-if": cmd_whatif,
        "calibrate": cmd_calibrate,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
