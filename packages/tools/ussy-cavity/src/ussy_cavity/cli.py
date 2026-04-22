"""CLI interface for Cavity — acoustic resonance pipeline deadlock detection.

Subcommands:
  modes      Predict deadlocks from pipeline topology
  impedance  Analyze backpressure via impedance mismatch
  monitor    Temporal analysis (standing waves + livelocks)
  report     Full resonance analysis report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from ussy_cavity import __version__
from ussy_cavity.topology import PipelineTopology


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_topology(path: str) -> PipelineTopology:
    """Load a topology from a file path (YAML or JSON)."""
    p = Path(path)
    if p.is_dir():
        # Look for pipeline.yaml or pipeline.json in directory
        for candidate in ["pipeline.yaml", "pipeline.yml", "pipeline.json"]:
            candidate_path = p / candidate
            if candidate_path.exists():
                return PipelineTopology.from_file(candidate_path)
        raise FileNotFoundError(
            f"No pipeline.yaml or pipeline.json found in directory: {path}"
        )
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return PipelineTopology.from_file(p)


def _load_timeseries(path: str) -> dict:
    """Load time series data from a JSON file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return json.loads(text)


# ---------------------------------------------------------------------------
# Subcommand: modes
# ---------------------------------------------------------------------------


def cmd_modes(args: argparse.Namespace) -> int:
    """Predict deadlocks from pipeline topology eigenvalue decomposition."""
    from ussy_cavity.modes import compute_natural_frequencies, format_modes, predict_deadlocks

    topology = _load_topology(args.pipeline)
    adj = topology.adjacency_matrix
    node_names = topology.node_names
    dt = args.dt if hasattr(args, "dt") and args.dt else 1.0

    if args.all_modes:
        modes = compute_natural_frequencies(adj, node_names, dt)
    else:
        modes = predict_deadlocks(adj, node_names, dt)

    if args.json:
        data = [
            {
                "index": m.index,
                "frequency": m.frequency,
                "damping_ratio": m.damping_ratio,
                "risk_level": m.risk_level.value,
                "q_factor": m.q_factor if m.q_factor < 1e6 else "inf",
                "involved_nodes": m.involved_nodes,
            }
            for m in modes
        ]
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_modes(modes))

    return 0


# ---------------------------------------------------------------------------
# Subcommand: impedance
# ---------------------------------------------------------------------------


def cmd_impedance(args: argparse.Namespace) -> int:
    """Analyze backpressure via impedance mismatch."""
    from ussy_cavity.impedance import (
        analyze_impedance_mismatches,
        format_impedance_profile,
        format_recommendations,
        recommend_damping,
    )

    topology = _load_topology(args.pipeline)
    profile = analyze_impedance_mismatches(topology)

    if args.json:
        print(json.dumps({
            "boundaries": [
                {
                    "upstream": b.upstream,
                    "downstream": b.downstream,
                    "z_upstream": b.z_upstream,
                    "z_downstream": b.z_downstream,
                    "reflection_coefficient": b.reflection_coefficient,
                    "transmission_coefficient": b.transmission_coefficient,
                    "is_mismatch": b.is_mismatch,
                }
                for b in profile.boundaries
            ],
            "mismatches": len(profile.mismatches),
            "resonant_cavity_risks": [
                {"upstream": r[0], "downstream": r[1], "description": r[2]}
                for r in profile.resonant_cavity_risks
            ],
        }, indent=2))
    else:
        print(format_impedance_profile(profile))
        if profile.mismatches:
            print()
            recommendations = recommend_damping(topology, target_zeta=args.target_zeta)
            print(format_recommendations(recommendations))

    return 0


# ---------------------------------------------------------------------------
# Subcommand: monitor
# ---------------------------------------------------------------------------


def cmd_monitor(args: argparse.Namespace) -> int:
    """Temporal analysis: standing wave and livelock detection."""
    from ussy_cavity.beat_frequency import format_beat_frequencies
    from ussy_cavity.standing_wave import format_standing_waves

    # Load time series data
    data = _load_timeseries(args.timeseries)
    wait_series = data.get("wait_durations", data.get("wait_time_series", []))
    throughput_series = data.get("throughput", [])
    fs = data.get("fs", args.fs)
    resource_names = data.get("resource_names", None)

    signal = np.array(wait_series, dtype=float)
    throughput = np.array(throughput_series, dtype=float) if throughput_series else None

    if len(signal) == 0:
        print("Error: No wait duration data found in timeseries file.", file=sys.stderr)
        return 1

    # Standing wave detection
    waves = detect_standing_waves_with_names(signal, fs, args.window, resource_names)

    # Beat frequency detection
    from ussy_cavity.beat_frequency import detect_livelock
    beats = detect_livelock(signal, throughput, fs)

    if args.json:
        result = {
            "standing_waves": [
                {
                    "frequency": w.frequency,
                    "amplitude": w.amplitude,
                    "persistence": w.persistence,
                    "q_factor": w.q_factor if w.q_factor < 1e6 else "inf",
                }
                for w in waves
            ],
            "beat_frequencies": [
                {
                    "beat_frequency": b.beat_frequency,
                    "beat_period": b.beat_period,
                    "f1": b.f1,
                    "f2": b.f2,
                    "amplitude": b.amplitude,
                    "is_livelock": b.is_livelock,
                }
                for b in beats
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print(format_standing_waves(waves))
        print()
        print(format_beat_frequencies(beats))

    return 0


def detect_standing_waves_with_names(signal, fs, window, resource_names):
    """Wrapper to call detect_standing_waves with CLI parameters."""
    from ussy_cavity.standing_wave import detect_standing_waves
    nperseg = min(window, len(signal)) if window else min(256, len(signal))
    return detect_standing_waves(
        signal, fs=fs, nperseg=nperseg,
        resource_names=resource_names,
    )


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    """Generate a full resonance analysis report."""
    from ussy_cavity.report import generate_report

    topology = _load_topology(args.pipeline)

    wait_time_series = None
    throughput_series = None
    fs = args.fs

    if args.timeseries:
        data = _load_timeseries(args.timeseries)
        wait_time_series = data.get("wait_durations", data.get("wait_time_series", []))
        throughput_series = data.get("throughput", [])
        if "fs" in data:
            fs = data["fs"]

    pipeline_name = args.pipeline
    report = generate_report(
        topology,
        wait_time_series=wait_time_series,
        throughput_series=throughput_series,
        fs=fs,
        target_zeta=args.target_zeta,
        pipeline_name=pipeline_name,
    )

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the cavity CLI."""
    parser = argparse.ArgumentParser(
        prog="cavity",
        description="Acoustic resonance analysis for concurrent pipeline deadlock & livelock detection",
    )
    parser.add_argument("--version", action="version", version=f"cavity {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- modes ---
    modes_parser = subparsers.add_parser(
        "modes",
        help="Predict deadlocks from pipeline topology",
    )
    modes_parser.add_argument(
        "pipeline",
        help="Path to pipeline topology file (YAML/JSON) or directory containing pipeline.yaml",
    )
    modes_parser.add_argument(
        "--all-modes", action="store_true",
        help="Show all modes (including well-damped)",
    )
    modes_parser.add_argument(
        "--dt", type=float, default=1.0,
        help="Time step for frequency calculation (default: 1.0s)",
    )
    modes_parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format",
    )

    # --- impedance ---
    impedance_parser = subparsers.add_parser(
        "impedance",
        help="Analyze backpressure via impedance mismatch",
    )
    impedance_parser.add_argument(
        "pipeline",
        help="Path to pipeline topology file (YAML/JSON) or directory",
    )
    impedance_parser.add_argument(
        "--target-zeta", type=float, default=1.0,
        help="Target damping ratio for recommendations (default: 1.0)",
    )
    impedance_parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format",
    )

    # --- monitor ---
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Temporal analysis: standing wave and livelock detection",
    )
    monitor_parser.add_argument(
        "timeseries",
        help="Path to time series data file (JSON)",
    )
    monitor_parser.add_argument(
        "--fs", type=float, default=1.0,
        help="Sampling frequency in Hz (default: 1.0)",
    )
    monitor_parser.add_argument(
        "--window", type=int, default=256,
        help="STFT window size (default: 256)",
    )
    monitor_parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format",
    )

    # --- report ---
    report_parser = subparsers.add_parser(
        "report",
        help="Generate full resonance analysis report",
    )
    report_parser.add_argument(
        "pipeline",
        help="Path to pipeline topology file (YAML/JSON) or directory",
    )
    report_parser.add_argument(
        "--timeseries",
        help="Path to time series data file (JSON) for temporal analysis",
    )
    report_parser.add_argument(
        "--fs", type=float, default=1.0,
        help="Sampling frequency in Hz (default: 1.0)",
    )
    report_parser.add_argument(
        "--target-zeta", type=float, default=1.0,
        help="Target damping ratio for recommendations (default: 1.0)",
    )
    report_parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the cavity CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "modes": cmd_modes,
        "impedance": cmd_impedance,
        "monitor": cmd_monitor,
        "report": cmd_report,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
