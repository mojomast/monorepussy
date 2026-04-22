"""Legacy entry-point wrappers with deprecation warnings.

Provides backward-compatible CLI commands:
  - stenograph  (stenographussy legacy)
  - stenography (stenography legacy)

Each prints a deprecation warning and delegates to ussy-steno.
"""

from __future__ import annotations

import sys
import warnings

from ussy_steno.cli import main as _main


def _warn(old: str, new: str) -> None:
    warnings.warn(
        f"'{old}' is deprecated. Use '{new}' instead.",
        DeprecationWarning,
        stacklevel=2,
    )


def stenograph_main(argv: list[str] | None = None) -> int:
    """Legacy entry point for 'stenograph' command."""
    _warn("stenograph", "ussy-steno")
    return _main(argv)


def stenography_main(argv: list[str] | None = None) -> int:
    """Legacy entry point for 'stenography' command."""
    _warn("stenography", "ussy-steno")
    return _main(argv)


if __name__ == "__main__":
    sys.exit(stenography_main())
