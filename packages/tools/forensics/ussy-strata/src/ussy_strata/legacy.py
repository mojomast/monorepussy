"""Legacy entry points with deprecation warnings."""

from __future__ import annotations

import warnings
import sys

from ussy_strata.cli import main as _main
from ussy_strata.missing import missing_cli as _missing_cli


def stratagit() -> None:
    """Legacy entry point for stratagit — redirects to ussy-strata survey."""
    warnings.warn(
        "'stratagit' is deprecated. Use 'ussy-strata' instead. "
        "This alias will be removed in ussyverse 2026.12.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    sys.exit(_main(["survey"] + sys.argv[1:]))


def unconformity() -> None:
    """Legacy entry point for disconformitussy — redirects to ussy-strata missing."""
    warnings.warn(
        "'unconformity' is deprecated. Use 'ussy-strata missing' instead. "
        "This alias will be removed in ussyverse 2026.12.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    sys.exit(_missing_cli(sys.argv[1:]))


def disconformitussy() -> None:
    """Legacy entry point for disconformitussy CLI name."""
    warnings.warn(
        "'disconformitussy' is deprecated. Use 'ussy-strata missing' instead. "
        "This alias will be removed in ussyverse 2026.12.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    sys.exit(_missing_cli(sys.argv[1:]))
