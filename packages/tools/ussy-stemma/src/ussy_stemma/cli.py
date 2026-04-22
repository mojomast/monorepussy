"""CLI interface for Stemma."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .collation import collate, collate_path, load_witnesses
from .classify import classify_all
from .contaminate import detect_contamination, detect_contamination_from_collation
from .display import (
    format_archetype,
    format_classifications,
    format_collation,
    format_contamination,
    format_stemma,
)
from .export import ussy_stemma_to_dot
from .reconstruct import reconstruct_archetype
from .stemma_builder import build_stemma


def _resolve_path(path_str: str) -> Path:
    """Resolve a path string to a Path object."""
    return Path(path_str).resolve()


def cmd_collate(args: argparse.Namespace) -> int:
    """Align variants and display collation table."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    result = collate_path(path)
    print(format_collation(result))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Reconstruct stemma tree from shared errors."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    collation = collate_path(path)
    classified = classify_all(collation)
    tree = build_stemma(classified)

    # Detect contamination
    reports = detect_contamination(classified, tree)
    if not reports:
        reports = detect_contamination_from_collation(classified)

    print(format_stemma(tree))
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    """Classify variants as errors vs. intent."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    collation = collate_path(path)
    classified = classify_all(collation)
    print(format_classifications(classified))
    return 0


def cmd_reconstruct(args: argparse.Namespace) -> int:
    """Output the archetype reconstruction."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    witness = getattr(args, "witness", None)
    collation = collate_path(path)
    classified = classify_all(collation)
    archetype = reconstruct_archetype(classified, prefer_witness=witness)

    func_name = str(path)
    print(format_archetype(archetype, func_name))
    return 0


def cmd_contaminate(args: argparse.Namespace) -> int:
    """Detect contaminated witnesses."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    collation = collate_path(path)
    classified = classify_all(collation)
    tree = build_stemma(classified)

    reports = detect_contamination(classified, tree)
    if not reports:
        reports = detect_contamination_from_collation(classified)

    print(format_contamination(reports))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export stemma as Graphviz DOT or other format."""
    path = _resolve_path(getattr(args, "path", "."))
    if not path.exists():
        print(f"Error: path '{path}' does not exist", file=sys.stderr)
        return 1

    fmt = getattr(args, "format", "dot")
    collation = collate_path(path)
    classified = classify_all(collation)
    tree = build_stemma(classified)

    # Detect contamination
    detect_contamination(classified, tree)
    detect_contamination_from_collation(classified)

    if fmt == "dot":
        print(stemma_to_dot(tree, title=f"Stemma: {path}"))
    else:
        print(f"Error: unsupported format '{fmt}'", file=sys.stderr)
        return 1

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="stemma",
        description="Stemma — Philological Code Variant Reconstruction from Textual Evidence Alone",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"stemma {__version__}",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands",
    )

    # collate
    p_collate = subparsers.add_parser(
        "collate",
        help="Align variants and display collation table",
    )
    p_collate.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )

    # build
    p_build = subparsers.add_parser(
        "build",
        help="Reconstruct stemma tree from shared errors",
    )
    p_build.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )

    # classify
    p_classify = subparsers.add_parser(
        "classify",
        help="Classify variants as errors vs. intent",
    )
    p_classify.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )

    # reconstruct
    p_reconstruct = subparsers.add_parser(
        "reconstruct",
        help="Output the archetype reconstruction",
    )
    p_reconstruct.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )
    p_reconstruct.add_argument(
        "--witness",
        "-w",
        help="Prefer a specific witness's readings",
    )

    # contaminate
    p_contaminate = subparsers.add_parser(
        "contaminate",
        help="Detect contaminated witnesses",
    )
    p_contaminate.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )

    # export
    p_export = subparsers.add_parser(
        "export",
        help="Export stemma as Graphviz DOT",
    )
    p_export.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to file or directory containing witness files",
    )
    p_export.add_argument(
        "--format",
        choices=["dot"],
        default="dot",
        help="Output format (default: dot)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    command = getattr(args, "command", None)
    if command is None:
        parser.print_help()
        return 0

    cmd_map = {
        "collate": cmd_collate,
        "build": cmd_build,
        "classify": cmd_classify,
        "reconstruct": cmd_reconstruct,
        "contaminate": cmd_contaminate,
        "export": cmd_export,
    }

    handler = cmd_map.get(command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
