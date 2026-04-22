"""Legacy entry point for backward compatibility."""

from __future__ import annotations

import sys
import warnings


def main(argv=None):
    """Deprecated alias for ussy-stratax CLI."""
    warnings.warn(
        "The 'strata' command is deprecated. Use 'ussy-stratax' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from ussy_stratax.cli import main

    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
