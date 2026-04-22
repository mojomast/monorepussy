"""Unified CLI dispatcher for ussy-calibre."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from ussy_calibre import __version__
from ussy_calibre.cli_measure import main as measure_main
from ussy_calibre.hearing import main as hearing_main
from ussy_calibre.stabilize import main as stabilize_main
from ussy_calibre.precision import main as precision_main
from ussy_calibre.health_cli import main as health_main


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for ussy-calibre."""
    parser = argparse.ArgumentParser(
        prog="ussy-calibre",
        description="Ussy-calibre — Test Suite Quality Analysis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # measure (calibreussy)
    measure_parser = subparsers.add_parser("measure", help="Metrological measurement science")
    measure_parser.set_defaults(func=lambda args: measure_main(sys.argv[2:]))

    # hearing (acumenussy)
    hearing_parser = subparsers.add_parser("hearing", help="Audiological diagnostics")
    hearing_parser.set_defaults(func=lambda args: hearing_main(sys.argv[2:]))

    # stabilize (lehrussy)
    stabilize_parser = subparsers.add_parser("stabilize", help="Glass annealing stabilization")
    stabilize_parser.set_defaults(func=lambda args: stabilize_main(sys.argv[2:]))

    # precision (marksmanussy)
    precision_parser = subparsers.add_parser("precision", help="Archery precision grouping")
    precision_parser.set_defaults(func=lambda args: precision_main(sys.argv[2:]))

    # health (levainussy)
    health_parser = subparsers.add_parser("health", help="Fermentation health analysis")
    health_parser.set_defaults(func=lambda args: health_main(sys.argv[2:]))

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
