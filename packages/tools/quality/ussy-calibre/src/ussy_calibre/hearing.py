"""CLI interface for acumen audiological diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from ussy_calibre import __version__
from ussy_calibre.models import (
    COMPLEXITY_BANDS,
    FullDiagnostic,
)
from ussy_calibre.utils import severity_label


def _resolve_path(path: str) -> str:
    """Resolve a path, handling both files and directories."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        print(f"Error: path does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    return path


def _print_testigram(result, args):
    """Pretty-print a Testigram result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║          TESTIGRAM — Pure-Tone Audiometry            ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print(f"  Shape: {result.shape}")
    print(f"  PTA (unit):        {result.pta_unit:.1f} dB  —  {severity_label(result.pta_unit)}")
    print(f"  PTA (integration): {result.pta_integration:.1f} dB  —  {severity_label(result.pta_integration)}")
    print()

    # Print audiogram table
    print(f"  {'Band':<10} {'Unit ○':<12} {'Integration ●':<16} {'Severity'}")
    print(f"  {'─'*10} {'─'*12} {'─'*16} {'─'*20}")

    for label, _, _ in COMPLEXITY_BANDS:
        unit_t = next(
            (p.detection_threshold for p in result.points
             if p.complexity_band == label and p.test_type == "unit"),
            0.0,
        )
        int_t = next(
            (p.detection_threshold for p in result.points
             if p.complexity_band == label and p.test_type == "integration"),
            0.0,
        )
        sev = severity_label(max(unit_t, int_t))
        print(f"  {label:<10} {unit_t:<12.1f} {int_t:<16.1f} {sev}")

    print()


def _print_srt(result, args):
    """Pretty-print an SRT result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     SPEECH RECEPTION TEST — Integration SRT          ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print(f"  SRT Value:          {result.srt_value:.2f}")
    print(f"  Roll-over:          {'DETECTED ⚠' if result.has_rollover else 'Not detected'}")
    if result.rollover_point is not None:
        print(f"  Roll-over point:    {result.rollover_point:.2f}")
    print(f"  SRT-PTA agreement:  {result.agreement_delta:.1f} dB  ({'consistent ✓' if result.is_consistent else 'MISMATCH ⚠'})")
    print()

    if result.candidates:
        print(f"  {'Fidelity':<12} {'Pass Rate'}")
        print(f"  {'─'*12} {'─'*12}")
        for c in result.candidates:
            marker = " ◄ SRT" if c.environment_fidelity == result.srt_value else ""
            print(f"  {c.environment_fidelity:<12.2f} {c.pass_rate:.3f}{marker}")

    print()


def _print_companogram(result, args):
    """Pretty-print a Companogram result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     COMPANOGRAM — Environment Compliance             ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    type_descriptions = {
        "As": "Over-rigid (brittle on config drift)",
        "Ad": "Over-compliant (weak assertions)",
        "B": "Broken (always fails)",
        "C": "Config drift (passes in CI, not prod)",
    }

    print(f"  Peak Type:          {result.peak_type}  —  {type_descriptions.get(result.peak_type, 'Unknown')}")
    print(f"  Tolerance Width:    {result.tolerance_width:.3f}")
    print(f"  Rigidity Score:     {result.rigidity_score:.3f}")
    print(f"  Peak Location:      {result.peak_location:.2f}")
    print(f"  Peak Pass Rate:     {result.peak_pass_rate:.3f}")
    print()

    if result.points:
        print(f"  {'Config':<10} {'Pass Rate'}")
        print(f"  {'─'*10} {'─'*12}")
        for p in result.points:
            bar = "█" * int(p.pass_rate * 40)
            print(f"  {p.config_value:<10.2f} {p.pass_rate:.3f}  {bar}")

    print()


def _print_flakegram(result, args):
    """Pretty-print a Flakegram result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     FLAKEGRAM — Otoacoustic Emissions / Self-Noise   ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print(f"  Overall α:          {result.overall_alpha:.3f}")
    print(f"  Overall Health:     {result.overall_health}")
    print()

    for mod in result.modules:
        soae_marker = " ⚠ SOAE PRESENT" if mod.soae_present else ""
        print(f"  Module: {mod.module_name}")
        print(f"    SOAE Index:      {mod.soae_index:.2f} dB{soae_marker}")
        print(f"    Detection SNR:   {mod.snr_value:.2f}")
        print(f"    Growth α:        {mod.growth_alpha:.3f}  ({mod.health_status})")
        print()

    print()


def _print_conduction(result, args):
    """Pretty-print a Conduction study result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     CONDUCTION STUDY — Test Chain ABR                ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    if result.stages:
        print(f"  {'Stage':<25} {'Latency (ms)':<15} {'Assertions':<12} {'Fsp'}")
        print(f"  {'─'*25} {'─'*15} {'─'*12} {'─'*8}")
        for stage in result.stages:
            fsp = result.fsp_values.get(stage.name, 0.0)
            fsp_status = "✓" if fsp >= 2.5 else "⚠ noise"
            print(f"  {stage.name:<25} {stage.latency_ms:<15.1f} {stage.assertion_count:<12} {fsp:.2f} {fsp_status}")

    print()
    if result.interstage_latencies:
        print("  Interstage Conduction Times:")
        for i, ict in enumerate(result.interstage_latencies):
            stage_from = result.stages[i].name if i < len(result.stages) else "?"
            stage_to = result.stages[i + 1].name if i + 1 < len(result.stages) else "?"
            print(f"    {stage_from} → {stage_to}: {ict:.1f} ms")

    print()
    print(f"  V/I Ratio:          {result.vi_ratio:.3f}", end="")
    if result.vi_ratio < 0.5:
        print("  ⚠ Signal loss (< 0.5)")
    elif result.vi_ratio > 2.0:
        print("  ⚠ Amplification (> 2.0)")
    else:
        print("  ✓ Normal")

    if result.bottleneck_stage:
        print(f"  Bottleneck:         {result.bottleneck_stage}")

    print()


def _print_isolation(result, args):
    """Pretty-print an Isolation result."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     ISOLATION AUDIOMETRY — Masking Effectiveness     ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    for mr in result.module_results:
        print(f"  Pair: {mr.module_a} ↔ {mr.module_b}")
        print(f"    Crosstalk:        {mr.crosstalk:.4f}")
        print(f"    Attenuation:      {mr.attenuation:.2f} dB")
        print(f"    Plateau Range:    {mr.plateau_range[0]}% – {mr.plateau_range[1]}%")
        flags = []
        if mr.is_overmocked:
            flags.append("OVERMASKED ⚠")
        if mr.is_undermasked:
            flags.append("UNDERMASKED ⚠")
        if mr.is_dilemma:
            flags.append("ISOLATION DILEMMA ⚠")
        if flags:
            print(f"    Flags:            {', '.join(flags)}")
        print()

    if result.dilemmas:
        print(f"  Isolation Dilemmas: {', '.join(result.dilemmas)}")
    if result.overmocked_modules:
        print(f"  Overmasked Modules: {', '.join(result.overmocked_modules)}")
    if result.undermasked_modules:
        print(f"  Undermasked Modules: {', '.join(result.undermasked_modules)}")

    print()


def _print_full_diagnostic(diag, args):
    """Print a complete audiological workup."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   ACUMEN — Complete Audiological Workup              ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"\n  Project: {diag.project_root}")
    print(f"  Date:    {diag.timestamp}\n")

    if diag.testigram:
        _print_testigram(diag.testigram, args)
    if diag.srt:
        _print_srt(diag.srt, args)
    if diag.companogram:
        _print_companogram(diag.companogram, args)
    if diag.flakegram:
        _print_flakegram(diag.flakegram, args)
    if diag.conduction:
        _print_conduction(diag.conduction, args)
    if diag.isolation:
        _print_isolation(diag.isolation, args)


def _output_result(result, args):
    """Output result as JSON if --json flag is set."""
    if getattr(args, "json", False):
        from ussy_calibre.storage import result_to_dict
        print(json.dumps(result_to_dict(result), indent=2, default=str))
        return True
    if getattr(args, "output", None):
        from ussy_calibre.storage import save_result_json
        path = save_result_json(result, args.output)
        print(f"  Result saved to: {path}", file=sys.stderr)
    return False


def cmd_testigram(args):
    """Generate audiogram of test sensitivity."""
    from ussy_calibre.testigram import run_testigram
    path = _resolve_path(args.project)
    result = run_testigram(path)
    if not _output_result(result, args):
        _print_testigram(result, args)


def cmd_srt(args):
    """Measure integration SRT + roll-over."""
    from ussy_calibre.srt import run_srt
    path = _resolve_path(args.project)
    result = run_srt(path)
    if not _output_result(result, args):
        _print_srt(result, args)


def cmd_companogram(args):
    """Config perturbation compliance profile."""
    from ussy_calibre.companogram import run_companogram
    path = _resolve_path(args.project)
    result = run_companogram(path)
    if not _output_result(result, args):
        _print_companogram(result, args)


def cmd_flakegram(args):
    """Self-noise spectral analysis + SNR."""
    from ussy_calibre.flakegram import run_flakegram
    path = _resolve_path(args.project)
    result = run_flakegram(path)
    if not _output_result(result, args):
        _print_flakegram(result, args)


def cmd_conduction(args):
    """Test chain latency study."""
    from ussy_calibre.conduction import run_conduction
    path = _resolve_path(args.project)
    result = run_conduction(path)
    if not _output_result(result, args):
        _print_conduction(result, args)


def cmd_isolation(args):
    """Isolation effectiveness + plateau sweep."""
    from ussy_calibre.isolation import run_isolation
    path = _resolve_path(args.project)
    result = run_isolation(path)
    if not _output_result(result, args):
        _print_isolation(result, args)


def cmd_full_diagnostic(args):
    """Complete audiological workup."""
    from ussy_calibre.testigram import run_testigram
    from ussy_calibre.srt import run_srt
    from ussy_calibre.companogram import run_companogram
    from ussy_calibre.flakegram import run_flakegram
    from ussy_calibre.conduction import run_conduction
    from ussy_calibre.isolation import run_isolation

    path = _resolve_path(args.project)

    print("Running complete audiological workup...", file=sys.stderr)
    testigram = run_testigram(path)
    srt = run_srt(path, pta_value=testigram.pta_unit)
    companogram = run_companogram(path)
    flakegram = run_flakegram(path)
    conduction = run_conduction(path)
    isolation = run_isolation(path)

    diag = FullDiagnostic(
        project_root=path,
        testigram=testigram,
        srt=srt,
        companogram=companogram,
        flakegram=flakegram,
        conduction=conduction,
        isolation=isolation,
    )

    if not _output_result(diag, args):
        _print_full_diagnostic(diag, args)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="acumen",
        description="Acumen — Audiological Diagnostics for Test Suite Hearing Acuity",
    )
    parser.add_argument(
        "--version", action="version", version=f"acumen {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Diagnostic commands")

    # Common arguments
    def add_common_args(sub):
        sub.add_argument(
            "--json", action="store_true", help="Output result as JSON"
        )
        sub.add_argument(
            "-o", "--output", help="Save result to JSON file"
        )

    # testigram
    p_testigram = subparsers.add_parser(
        "testigram",
        help="Generate audiogram of test sensitivity",
    )
    p_testigram.add_argument("project", help="Path to project directory or file")
    add_common_args(p_testigram)
    p_testigram.set_defaults(func=cmd_testigram)

    # srt
    p_srt = subparsers.add_parser(
        "srt",
        help="Measure integration SRT + roll-over",
    )
    p_srt.add_argument("project", help="Path to project directory or file")
    add_common_args(p_srt)
    p_srt.set_defaults(func=cmd_srt)

    # companogram
    p_companogram = subparsers.add_parser(
        "companogram",
        help="Config perturbation compliance profile",
    )
    p_companogram.add_argument("project", help="Path to project directory or file")
    add_common_args(p_companogram)
    p_companogram.set_defaults(func=cmd_companogram)

    # flakegram
    p_flakegram = subparsers.add_parser(
        "flakegram",
        help="Self-noise spectral analysis + SNR",
    )
    p_flakegram.add_argument("project", help="Path to project directory or file")
    add_common_args(p_flakegram)
    p_flakegram.set_defaults(func=cmd_flakegram)

    # conduction
    p_conduction = subparsers.add_parser(
        "conduction",
        help="Test chain latency study",
    )
    p_conduction.add_argument("project", help="Path to project directory or file")
    add_common_args(p_conduction)
    p_conduction.set_defaults(func=cmd_conduction)

    # isolation
    p_isolation = subparsers.add_parser(
        "isolation",
        help="Isolation effectiveness + plateau sweep",
    )
    p_isolation.add_argument("project", help="Path to project directory or file")
    add_common_args(p_isolation)
    p_isolation.set_defaults(func=cmd_isolation)

    # full-diagnostic
    p_full = subparsers.add_parser(
        "full-diagnostic",
        help="Complete audiological workup",
    )
    p_full.add_argument("project", help="Path to project directory or file")
    add_common_args(p_full)
    p_full.set_defaults(func=cmd_full_diagnostic)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
