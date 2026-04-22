"""CLI interface for Operon."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from operon.enhancer import EnhancerScanner
from operon.epigenetics import EpigeneticStateTracker
from operon.mapper import OperonMapper
from operon.models import (
    Codebase,
    FactorType,
    MarkType,
    RepressorType,
    serialize_to_json,
)
from operon.promoter import PromoterDetector
from operon.repressor import RepressorManager
from operon.storage import StorageManager
from operon.transcription import TranscriptionFactorRegistry


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="operon",
        description="Operon — Gene Regulation for Documentation Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  operon map ./src                          # Discover operons in codebase
  operon promote public_api_change          # Analyze trigger strength
  operon repress old_module.py --type inducible  # Set suppression
  operon enhance auth.py                    # Find distant connections
  operon express operon_0 --audience expert # Generate conditional docs
  operon epigenetics                        # View state marks
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    parser.add_argument(
        "--db",
        type=str,
        default="operon.db",
        help="Path to SQLite database (default: operon.db)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # map command
    map_parser = subparsers.add_parser(
        "map",
        help="Discover operons in codebase",
    )
    map_parser.add_argument(
        "path",
        type=str,
        help="Path to codebase (file or directory)",
    )
    map_parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Coupling threshold for operon detection (default: 0.7)",
    )

    # promote command
    promote_parser = subparsers.add_parser(
        "promote",
        help="Analyze documentation trigger strength",
    )
    promote_parser.add_argument(
        "change",
        type=str,
        help="Change type to analyze",
    )
    promote_parser.add_argument(
        "--codebase",
        type=str,
        help="Path to codebase for context",
    )

    # repress command
    repress_parser = subparsers.add_parser(
        "repress",
        help="Set documentation suppression",
    )
    repress_parser.add_argument(
        "feature",
        type=str,
        help="Feature path to repress",
    )
    repress_parser.add_argument(
        "--type",
        type=str,
        choices=["constitutive", "inducible", "corepressor_dependent"],
        default="inducible",
        help="Type of repressor (default: inducible)",
    )
    repress_parser.add_argument(
        "--lift",
        action="store_true",
        help="Lift repression instead of applying it",
    )

    # enhance command
    enhance_parser = subparsers.add_parser(
        "enhance",
        help="Find distant connections (enhancers) for a module",
    )
    enhance_parser.add_argument(
        "path",
        type=str,
        help="Path to codebase or module",
    )
    enhance_parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top enhancers to show (default: 10)",
    )

    # express command
    express_parser = subparsers.add_parser(
        "express",
        help="Generate conditional documentation for an operon",
    )
    express_parser.add_argument(
        "operon",
        type=str,
        help="Operon ID to express",
    )
    express_parser.add_argument(
        "--audience",
        type=str,
        default="expert",
        choices=["beginner", "expert", "all"],
        help="Target audience (default: expert)",
    )
    express_parser.add_argument(
        "--context",
        type=str,
        default="web",
        help="Context for generation (default: web)",
    )
    express_parser.add_argument(
        "--codebase",
        type=str,
        help="Path to codebase for context",
    )

    # epigenetics command
    epigenetics_parser = subparsers.add_parser(
        "epigenetics",
        help="View epigenetic state marks",
    )
    epigenetics_parser.add_argument(
        "--operon",
        type=str,
        help="Filter by operon ID",
    )
    epigenetics_parser.add_argument(
        "--codebase",
        type=str,
        help="Path to codebase for context",
    )

    return parser


def cmd_map(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the map command."""
    path = Path(args.path)
    if not path.exists():
        return {"error": f"Path not found: {args.path}"}

    codebase = Codebase(root_path=str(path.absolute()))
    mapper = OperonMapper(coupling_threshold=args.threshold)
    operons = mapper.map_operons(codebase)

    # Save to storage
    storage.save_codebase(codebase)
    for operon in operons:
        storage.save_operon(operon)

    return {
        "command": "map",
        "path": str(path.absolute()),
        "threshold": args.threshold,
        "operons_found": len(operons),
        "operons": [o.to_dict() for o in operons],
        "genes_found": len(codebase.genes),
    }


def cmd_promote(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the promote command."""
    detector = PromoterDetector()

    codebase = None
    if getattr(args, "codebase", None):
        path = Path(args.codebase)
        if path.exists():
            codebase = Codebase(root_path=str(path.absolute()))
            mapper = OperonMapper()
            mapper.map_operons(codebase)

    if codebase is None:
        codebase = Codebase(root_path=".", genes=[], operons=[])

    triggers = detector.analyze_promoters(codebase, history=[])

    result = {
        "command": "promote",
        "change": args.change,
        "strength": 0.0,
        "triggers": {},
    }

    if args.change in detector.TRIGGER_DEFINITIONS:
        result["strength"] = detector.TRIGGER_DEFINITIONS[args.change]["strength"]
        result["trigger_info"] = detector.TRIGGER_DEFINITIONS[args.change]

    # Check if it's an operon-specific trigger
    for trigger_id, trigger in triggers.items():
        result["triggers"][trigger_id] = trigger.to_dict()

    return result


def cmd_repress(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the repress command."""
    manager = RepressorManager()

    repressor_type = RepressorType(args.type)

    if args.lift:
        # Try to find and lift repression
        result = {
            "command": "repress",
            "action": "lift",
            "feature": args.feature,
            "success": False,
        }
        return result
    else:
        # Create a repressor for the feature
        from operon.models import Gene

        gene = Gene(name=Path(args.feature).stem, path=args.feature)
        repressor = manager.add_custom_repressor(
            feature_path=args.feature,
            repressor_type=repressor_type,
        )
        storage.save_repressor(repressor)

        return {
            "command": "repress",
            "action": "apply",
            "feature": args.feature,
            "repressor_type": repressor_type.value,
            "repressor_id": repressor.repressor_id,
        }


def cmd_enhance(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the enhance command."""
    path = Path(args.path)
    if not path.exists():
        return {"error": f"Path not found: {args.path}"}

    codebase = Codebase(root_path=str(path.absolute()))
    mapper = OperonMapper()
    mapper.map_operons(codebase)

    scanner = EnhancerScanner()
    enhancers = scanner.find_enhancers(codebase)

    # Save to storage
    for enhancer in enhancers:
        storage.save_enhancer(enhancer)

    top_enhancers = scanner.get_top_enhancers(enhancers, n=args.top)

    return {
        "command": "enhance",
        "path": str(path.absolute()),
        "enhancers_found": len(enhancers),
        "top_enhancers": [e.to_dict() for e in top_enhancers],
    }


def cmd_express(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the express command."""
    # Load operons from storage or analyze codebase
    operons = storage.load_operons()

    if not operons and getattr(args, "codebase", None):
        path = Path(args.codebase)
        if path.exists():
            codebase = Codebase(root_path=str(path.absolute()))
            mapper = OperonMapper()
            operons = mapper.map_operons(codebase)
            for o in operons:
                storage.save_operon(o)

    target_operon = None
    for o in operons:
        if o.operon_id == args.operon:
            target_operon = o
            break

    if not target_operon:
        return {"error": f"Operon not found: {args.operon}", "available_operons": [o.operon_id for o in operons]}

    registry = TranscriptionFactorRegistry()
    audiences = [args.audience] if args.audience != "all" else ["beginner", "expert"]
    factors = registry.define_factors(audiences=audiences, contexts=[args.context])

    result = registry.generate_conditional_docs(target_operon, factors, args.context)

    return {
        "command": "express",
        "operon": args.operon,
        "audience": args.audience,
        "context": args.context,
        "result": result,
    }


def cmd_epigenetics(args: argparse.Namespace, storage: StorageManager) -> dict[str, Any]:
    """Execute the epigenetics command."""
    tracker = EpigeneticStateTracker()

    # Load or create codebase context
    operons = storage.load_operons()
    codebase = Codebase(root_path=".", operons=operons, genes=[])

    if getattr(args, "codebase", None):
        path = Path(args.codebase)
        if path.exists():
            codebase = Codebase(root_path=str(path.absolute()))
            mapper = OperonMapper()
            mapper.map_operons(codebase)
            operons = codebase.operons

    # Load history from storage
    marks = storage.load_epigenetic_marks()

    # Track state
    result = tracker.track_epigenetic_state(doc_history=[], codebase=codebase)

    # Save new marks
    for mark in tracker.marks:
        storage.save_epigenetic_mark(mark)

    # Filter by operon if specified
    if getattr(args, "operon", None):
        result["current_marks"] = [m for m in result["current_marks"] if m.get("operon_id") == args.operon]

    return {
        "command": "epigenetics",
        "marks_count": len(result["current_marks"]),
        "result": result,
    }


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Initialize storage
    storage = StorageManager(args.db)

    try:
        if args.command == "map":
            result = cmd_map(args, storage)
        elif args.command == "promote":
            result = cmd_promote(args, storage)
        elif args.command == "repress":
            result = cmd_repress(args, storage)
        elif args.command == "enhance":
            result = cmd_enhance(args, storage)
        elif args.command == "express":
            result = cmd_express(args, storage)
        elif args.command == "epigenetics":
            result = cmd_epigenetics(args, storage)
        else:
            parser.print_help()
            return 0

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Human-readable output
            print(f"Command: {result.get('command', args.command)}")
            print("-" * 40)
            for key, value in result.items():
                if key == "command":
                    continue
                if key in ["operons", "top_enhancers", "current_marks", "triggers", "result"]:
                    print(f"{key}:")
                    if isinstance(value, list):
                        for item in value[:5]:  # Limit to first 5
                            print(f"  - {item}")
                        if len(value) > 5:
                            print(f"  ... and {len(value) - 5} more")
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            print(f"  {k}: {v}")
                    else:
                        print(f"  {value}")
                else:
                    print(f"{key}: {value}")

        return 0 if "error" not in result else 1

    finally:
        storage.close()


if __name__ == "__main__":
    sys.exit(main())
