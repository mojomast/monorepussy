"""CLI interface for Crystallo."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from ussy_crystallo import __version__
from ussy_crystallo.classify import classify_module, detect_unit_cells
from ussy_crystallo.defects import detect_defects, detect_translational_groups
from ussy_crystallo.models import SymmetryType
from ussy_crystallo.parser import parse_directory, parse_file
from ussy_crystallo.report import (
    format_classification,
    format_defects,
    format_fingerprint_summary,
    format_symmetry_relations,
    format_unit_cells,
)
from ussy_crystallo.similarity import compute_pairwise_similarities


def _collect_python_files(path: str) -> list[Path]:
    """If path is a directory, walk it for Python files; otherwise return the file."""
    p = Path(path)
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(p.rglob("*.py"))
    print(f"Warning: {path} is not a file or directory", file=sys.stderr)
    return []


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    """Extract structural units and classify symmetry."""
    paths = getattr(args, "paths", [])
    threshold = getattr(args, "threshold", 0.4)
    if not paths:
        print("Error: provide at least one path", file=sys.stderr)
        return 1

    all_fps = []
    for p in paths:
        all_fps.extend(parse_directory(p))

    print(format_fingerprint_summary(all_fps))

    relations = compute_pairwise_similarities(all_fps, threshold=threshold)
    print(format_symmetry_relations(relations))
    return 0


def cmd_symmetry(args: argparse.Namespace) -> int:
    """List all detected symmetry operations."""
    paths = getattr(args, "paths", [])
    threshold = getattr(args, "threshold", 0.4)
    if not paths:
        print("Error: provide at least one path", file=sys.stderr)
        return 1

    all_fps = []
    for p in paths:
        all_fps.extend(parse_directory(p))

    relations = compute_pairwise_similarities(all_fps, threshold=threshold)

    # Filter by type if requested
    filter_type = getattr(args, "type", None)
    if filter_type:
        try:
            sym_type = SymmetryType[filter_type.upper()]
            relations = [r for r in relations if r.symmetry_type == sym_type]
        except KeyError:
            print(f"Unknown symmetry type: {filter_type}", file=sys.stderr)
            return 1

    print(format_symmetry_relations(relations))
    return 0


def cmd_defects(args: argparse.Namespace) -> int:
    """Report broken symmetry and accidental duplication."""
    paths = getattr(args, "paths", [])
    threshold = getattr(args, "threshold", 0.4)
    defect_threshold = getattr(args, "defect_threshold", 0.5)
    if not paths:
        print("Error: provide at least one path", file=sys.stderr)
        return 1

    all_fps = []
    for p in paths:
        all_fps.extend(parse_directory(p))

    relations = compute_pairwise_similarities(all_fps, threshold=threshold)
    defects = detect_defects(all_fps, relations, similarity_threshold=defect_threshold)

    # Also check for translational groups
    trans_groups = detect_translational_groups(all_fps, relations)
    defects.extend(trans_groups)

    print(format_defects(defects))
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    """Assign structural group to each module."""
    paths = getattr(args, "paths", [])
    threshold = getattr(args, "threshold", 0.4)
    if not paths:
        print("Error: provide at least one path", file=sys.stderr)
        return 1

    for p in paths:
        fps = parse_directory(p)
        relations = compute_pairwise_similarities(fps, threshold=threshold)
        classification = classify_module(p, fps, relations)
        print(format_classification(classification))

    return 0


def cmd_unit_cell(args: argparse.Namespace) -> int:
    """Show the repeating structural unit."""
    paths = getattr(args, "paths", [])
    threshold = getattr(args, "threshold", 0.4)
    if not paths:
        print("Error: provide at least one path", file=sys.stderr)
        return 1

    all_fps = []
    for p in paths:
        all_fps.extend(parse_directory(p))

    relations = compute_pairwise_similarities(all_fps, threshold=threshold)
    unit_cells = detect_unit_cells(all_fps, relations)
    print(format_unit_cells(unit_cells))
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="crystallo",
        description="Crystallographic symmetry detection in code structure",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    p_scan = sub.add_parser("scan", help="Extract structural units and classify symmetry")
    p_scan.add_argument("paths", nargs="*", help="Files or directories to scan")
    p_scan.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold (default: 0.4)")

    # symmetry
    p_sym = sub.add_parser("symmetry", help="List all detected symmetry operations")
    p_sym.add_argument("paths", nargs="*", help="Files or directories to analyze")
    p_sym.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold (default: 0.4)")
    p_sym.add_argument("--type", type=str, default=None, help="Filter by symmetry type (rotational, reflection, translational, glide, broken)")

    # defects
    p_def = sub.add_parser("defects", help="Report broken symmetry and accidental duplication")
    p_def.add_argument("paths", nargs="*", help="Files or directories to analyze")
    p_def.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold (default: 0.4)")
    p_def.add_argument("--defect-threshold", type=float, default=0.5, dest="defect_threshold", help="Defect confidence threshold (default: 0.5)")

    # classify
    p_cls = sub.add_parser("classify", help="Assign structural group to each module")
    p_cls.add_argument("paths", nargs="*", help="Directories to classify")
    p_cls.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold (default: 0.4)")

    # unit-cell
    p_uc = sub.add_parser("unit-cell", help="Show the repeating structural unit")
    p_uc.add_argument("paths", nargs="*", help="Files or directories to analyze")
    p_uc.add_argument("--threshold", type=float, default=0.4, help="Similarity threshold (default: 0.4)")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    dispatch = {
        "scan": cmd_scan,
        "symmetry": cmd_symmetry,
        "defects": cmd_defects,
        "classify": cmd_classify,
        "unit-cell": cmd_unit_cell,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
