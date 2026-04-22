"""CLI interface for the gamut package.

Provides subcommands:
  profile   — Profile a data system or pipeline stage
  analyze   — Analyze a pipeline for clipping risks
  visualize — Render CIE-style gamut diagrams
  sample    — Sample actual data for clipping detection
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ussy_gamut import __version__
from ussy_gamut.models import PipelineDAG, StageProfile
from ussy_gamut.profiler import (
    profile_from_json,
    profile_stage,
    resolve_type,
    dag_from_json,
    dag_from_dir,
)
from ussy_gamut.dag_parser import parse_pipeline
from ussy_gamut.analyzer import analyze_boundary, analyze_pipeline
from ussy_gamut.visualizer import (
    render_gamut_diagram,
    render_pipeline_overview,
    render_field_detail,
    render_boundary_comparison,
)
from ussy_gamut.sampler import (
    sample_boundary,
    load_csv_data,
    load_json_data,
    format_sample_report,
)


def cmd_profile(args: argparse.Namespace) -> int:
    """Profile a data system or pipeline stage."""
    if args.system and args.type_name:
        # Resolve a single type
        gamut = resolve_type(args.system, args.type_name)
        print(f"System     : {gamut.system}")
        print(f"Type       : {gamut.type_name}")
        print(f"Field type : {gamut.field_type.value}")
        print(f"Min value  : {gamut.min_value}")
        print(f"Max value  : {gamut.max_value}")
        print(f"Precision  : {gamut.precision}")
        print(f"Scale      : {gamut.scale}")
        print(f"Charset    : {gamut.charset}")
        print(f"Max length : {gamut.max_length}")
        print(f"TZ aware   : {gamut.timezone_aware}")
        print(f"TZ precision: {gamut.tz_precision}")
        print(f"Nullable   : {gamut.nullable}")
        return 0

    if args.input:
        p = Path(args.input)
        if p.is_dir():
            dag = dag_from_dir(p)
        else:
            dag = dag_from_json(p)

        print(f"Pipeline: {dag.name}")
        print(f"Stages: {len(dag.stages)}")
        print(f"Edges: {len(dag.edges)}")
        print("")
        for name, stage in dag.stages.items():
            print(f"  Stage: {name} (system={stage.system})")
            for field in stage.fields:
                print(f"    {field.name}: {field.gamut.type_name} "
                      f"[{field.gamut.field_type.value}]")
            print("")
        return 0

    print("Error: provide --system and --type-name, or --input", file=sys.stderr)
    return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze a pipeline for clipping risks."""
    p = Path(args.input)
    try:
        dag = parse_pipeline(p)
    except Exception as e:
        print(f"Error parsing pipeline: {e}", file=sys.stderr)
        return 1

    reports = analyze_pipeline(dag)

    if not reports:
        print("No boundaries found in pipeline.")
        return 0

    # Render overview
    overview = render_pipeline_overview(reports, dag)
    print(overview)

    # Optionally render detailed diagrams
    if args.detailed:
        for report in reports:
            diagram = render_gamut_diagram(report)
            print(diagram)
            src = dag.get_stage(report.source_stage)
            dst = dag.get_stage(report.dest_stage)
            if src and dst:
                comp = render_boundary_comparison(src, dst, report)
                print(comp)

    # Output JSON if requested
    if args.output:
        output_data = {
            "pipeline": dag.name,
            "boundaries": [],
        }
        for report in reports:
            boundary_data = {
                "source": report.source_stage,
                "dest": report.dest_stage,
                "fields": [],
            }
            for cr in report.results:
                field_data = {
                    "name": cr.field_name,
                    "source_type": cr.source_gamut.type_name,
                    "dest_type": cr.dest_gamut.type_name,
                    "source_system": cr.source_gamut.system,
                    "dest_system": cr.dest_gamut.system,
                    "delta_e": cr.delta_e,
                    "risk": cr.risk.value,
                    "rendering_intent": cr.rendering_intent.value,
                    "is_clipping": cr.is_clipping,
                    "clipped_examples": cr.clipped_examples,
                    "notes": cr.notes,
                }
                boundary_data["fields"].append(field_data)
            output_data["boundaries"].append(boundary_data)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results written to {args.output}")

    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Render CIE-style gamut diagrams."""
    p = Path(args.input)
    try:
        dag = parse_pipeline(p)
    except Exception as e:
        print(f"Error parsing pipeline: {e}", file=sys.stderr)
        return 1

    reports = analyze_pipeline(dag)

    if not reports:
        print("No boundaries found in pipeline.")
        return 0

    for report in reports:
        diagram = render_gamut_diagram(report, width=args.width, height=args.height)
        print(diagram)

        if args.detail_field:
            for cr in report.results:
                if cr.field_name == args.detail_field:
                    detail = render_field_detail(cr)
                    print(detail)

    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Sample actual data for clipping detection."""
    p = Path(args.input)
    try:
        dag = parse_pipeline(p)
    except Exception as e:
        print(f"Error parsing pipeline: {e}", file=sys.stderr)
        return 1

    pairs = dag.boundary_pairs()
    if not pairs:
        print("No boundaries found in pipeline.")
        return 0

    # Load sample data
    data_path = Path(args.data)
    source_data: list[dict] = []
    dest_data: list[dict] | None = None

    if data_path.suffix.lower() == ".csv":
        source_data = load_csv_data(data_path)
    elif data_path.suffix.lower() == ".json":
        source_data = load_json_data(data_path)
    else:
        print(f"Unsupported data format: {data_path.suffix}", file=sys.stderr)
        return 1

    # Load dest data if provided
    if args.dest_data:
        dest_path = Path(args.dest_data)
        if dest_path.suffix.lower() == ".csv":
            dest_data = load_csv_data(dest_path)
        elif dest_path.suffix.lower() == ".json":
            dest_data = load_json_data(dest_path)

    # Sample the first boundary (or specified one)
    if args.boundary:
        parts = args.boundary.split(":")
        if len(parts) == 2:
            src_name, dst_name = parts
            src = dag.get_stage(src_name)
            dst = dag.get_stage(dst_name)
            if not src or not dst:
                print(f"Boundary {args.boundary} not found in pipeline.", file=sys.stderr)
                return 1
        else:
            print("Boundary format: source_stage:dest_stage", file=sys.stderr)
            return 1
    else:
        src, dst = pairs[0]

    report = sample_boundary(src, dst, source_data, dest_data)
    output = format_sample_report(report)
    print(output)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="gamut",
        description="Color science gamut mapping for data pipeline fidelity analysis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # profile subcommand
    profile_p = subparsers.add_parser("profile", help="Profile a data system or pipeline stage")
    profile_p.add_argument("--system", "-s", help="Data system name (e.g. postgresql, json)")
    profile_p.add_argument("--type-name", "-t", help="Type name to resolve (e.g. INTEGER, number)")
    profile_p.add_argument("--input", "-i", help="Path to pipeline JSON or directory")

    # analyze subcommand
    analyze_p = subparsers.add_parser("analyze", help="Analyze a pipeline for clipping risks")
    analyze_p.add_argument("input", help="Path to pipeline definition (JSON, YAML, or directory)")
    analyze_p.add_argument("--detailed", "-d", action="store_true", help="Show detailed diagrams")
    analyze_p.add_argument("--output", "-o", help="Output JSON file for results")

    # visualize subcommand
    viz_p = subparsers.add_parser("visualize", help="Render CIE-style gamut diagrams")
    viz_p.add_argument("input", help="Path to pipeline definition")
    viz_p.add_argument("--width", "-W", type=int, default=60, help="Diagram width in characters")
    viz_p.add_argument("--height", "-H", type=int, default=20, help="Diagram height in characters")
    viz_p.add_argument("--detail-field", help="Show field detail for a specific field name")

    # sample subcommand
    sample_p = subparsers.add_parser("sample", help="Sample actual data for clipping detection")
    sample_p.add_argument("input", help="Path to pipeline definition")
    sample_p.add_argument("--data", "-d", required=True, help="Path to sample data (CSV or JSON)")
    sample_p.add_argument("--dest-data", help="Path to destination sample data for comparison")
    sample_p.add_argument("--boundary", "-b", help="Boundary to sample (format: source:dest)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    dispatch = {
        "profile": cmd_profile,
        "analyze": cmd_analyze,
        "visualize": cmd_visualize,
        "sample": cmd_sample,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
