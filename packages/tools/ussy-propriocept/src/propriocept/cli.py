"""Command-line interface for Propriocept."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from propriocept.schema import build_schema, load_schema, scan_limb
from propriocept.sense import render_ascii, sense
from propriocept.kinesthesia import compute_vectors, parse_history
from propriocept.muscle_memory import (
    extract_commands,
    find_motor_programs,
    format_alias,
)
from propriocept.drift import detect_drift, render_report


def _schema_cmd(args: argparse.Namespace) -> int:
    root: Path = args.root.expanduser().resolve()
    output: Path = args.output.expanduser().resolve()
    schema = build_schema(root, output)
    print(f"Schema built with {len(schema['limbs'])} limbs → {output}")
    return 0


def _sense_cmd(args: argparse.Namespace) -> int:
    schema_path: Path = args.schema.expanduser().resolve()
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 1
    schema = load_schema(schema_path)
    schema = sense(schema)
    if args.format == "json":
        print(json.dumps(schema, indent=2))
    else:
        print(render_ascii(schema))
    return 0


def _kinesthesia_cmd(args: argparse.Namespace) -> int:
    history: Path = args.history.expanduser().resolve()
    moves = parse_history(history)
    vectors = compute_vectors(moves)
    if args.format == "json":
        print(json.dumps(vectors, indent=2))
    else:
        print("Kinesthetic Vectors")
        print("=" * 30)
        for k, v in vectors.items():
            print(f"  {k}: {v}")
        if vectors.get("flow_guard"):
            print("\n⚠️  Flow guard: high context-switch velocity detected.")
    return 0


def _muscle_memory_cmd(args: argparse.Namespace) -> int:
    history: Path = args.history.expanduser().resolve()
    raw = history.read_text() if history.exists() else ""
    commands = extract_commands(raw)
    programs = find_motor_programs(commands, min_freq=args.min_freq, max_len=args.max_len)
    if not programs:
        print("No motor programs found. Keep coding — habits will form.")
        return 0
    lines = []
    for seq, count in sorted(programs.items(), key=lambda x: x[1], reverse=True):
        lines.append(format_alias(seq, count))
    output = "\n\n".join(lines)
    if args.output:
        out_path: Path = args.output.expanduser().resolve()
        out_path.write_text(output + "\n")
        print(f"Motor programs written to {out_path}")
    else:
        print(output)
    return 0


def _drift_cmd(args: argparse.Namespace) -> int:
    schema_path: Path = args.schema.expanduser().resolve()
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 1
    schema = load_schema(schema_path)
    drifts = detect_drift(schema)
    if args.report:
        print(render_report(drifts, threshold=args.threshold))
    else:
        filtered = [d for d in drifts if d["score"] >= args.threshold]
        print(json.dumps(filtered, indent=2))
    return 0


def _limb_cmd(args: argparse.Namespace) -> int:
    path: Path = args.path.expanduser().resolve()
    if not path.exists():
        print(f"Limb not found: {path}", file=sys.stderr)
        return 1
    limb = scan_limb(path)
    print(json.dumps(limb, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Propriocept — proprioception for your dev environment"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # schema
    p_schema = sub.add_parser("schema", help="Build the body schema")
    p_schema.add_argument(
        "--root", type=Path, default=Path.home() / "projects"
    )
    p_schema.add_argument(
        "--output", type=Path, default=Path("body_schema.json")
    )
    p_schema.set_defaults(func=_schema_cmd)

    # sense
    p_sense = sub.add_parser("sense", help="Passive sense of workspace state")
    p_sense.add_argument(
        "--format", choices=["ascii", "json"], default="ascii"
    )
    p_sense.add_argument(
        "--schema", type=Path, default=Path("body_schema.json")
    )
    p_sense.set_defaults(func=_sense_cmd)

    # kinesthesia
    p_kin = sub.add_parser("kinesthesia", help="Context velocity tracking")
    p_kin.add_argument(
        "--history", type=Path, default=Path.home() / ".bash_history"
    )
    p_kin.add_argument(
        "--format", choices=["ascii", "json"], default="ascii"
    )
    p_kin.set_defaults(func=_kinesthesia_cmd)

    # muscle-memory
    p_mm = sub.add_parser("muscle-memory", help="Extract motor programs")
    p_mm.add_argument(
        "--min-freq", type=int, default=5
    )
    p_mm.add_argument(
        "--max-len", type=int, default=5
    )
    p_mm.add_argument(
        "--output", type=Path
    )
    p_mm.add_argument(
        "--history", type=Path, default=Path.home() / ".bash_history"
    )
    p_mm.set_defaults(func=_muscle_memory_cmd)

    # drift
    p_drift = sub.add_parser("drift", help="Detect model-reality mismatches")
    p_drift.add_argument(
        "--threshold", type=float, default=0.3
    )
    p_drift.add_argument(
        "--report", action="store_true"
    )
    p_drift.add_argument(
        "--schema", type=Path, default=Path("body_schema.json")
    )
    p_drift.set_defaults(func=_drift_cmd)

    # limb
    p_limb = sub.add_parser("limb", help="Inspect a single limb")
    p_limb_sub = p_limb.add_subparsers(dest="limb_cmd", required=True)
    p_limb_status = p_limb_sub.add_parser("status", help="Show limb status")
    p_limb_status.add_argument(
        "path", type=Path, help="Path to the limb directory"
    )
    p_limb_status.set_defaults(func=_limb_cmd)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
