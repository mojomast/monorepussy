"""Legacy entry points with deprecation warnings."""

from __future__ import annotations

import warnings
import sys

from ussy_calibre.cli_measure import main as measure_main
from ussy_calibre.hearing import main as hearing_main
from ussy_calibre.stabilize import main as stabilize_main
from ussy_calibre.precision import main as precision_main
from ussy_calibre.health import main as health_main


def _warn(old: str, new: str) -> None:
    warnings.warn(
        f"'{old}' is deprecated. Use 'ussy-calibre {new}' instead.",
        DeprecationWarning,
        stacklevel=2,
    )


def calibre_main() -> None:
    """Legacy entry point for calibre."""
    _warn("calibre", "measure")
    measure_main(sys.argv[1:])


def acumen_main() -> None:
    """Legacy entry point for acumen."""
    _warn("acumen", "hearing")
    hearing_main(sys.argv[1:])


def lehr_main() -> None:
    """Legacy entry point for lehr."""
    _warn("lehr", "stabilize")
    stabilize_main(sys.argv[1:])


def marksman_main() -> None:
    """Legacy entry point for marksman."""
    _warn("marksman", "precision")
    precision_main(sys.argv[1:])


def levain_main() -> None:
    """Legacy entry point for levain."""
    _warn("levain", "health")
    health_main(sys.argv[1:])
