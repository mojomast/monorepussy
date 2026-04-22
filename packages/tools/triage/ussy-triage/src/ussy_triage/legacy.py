"""Legacy compatibility wrapper for the old `triage` command.

This module provides a deprecation-warning shim so that existing scripts
and muscle memory using the `triage` entry point continue to work while
alerting users to migrate to `ussy-triage`.
"""

import sys
import warnings
from .cli import main


def triage_alias() -> int:
    """Legacy entry point that warns and delegates to the new CLI."""
    warnings.warn(
        "The `triage` command is deprecated. Use `ussy-triage` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(triage_alias())
