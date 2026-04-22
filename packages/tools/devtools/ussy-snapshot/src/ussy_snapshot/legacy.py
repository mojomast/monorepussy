"""Legacy deprecation wrapper for old 'snapshot' entry point."""

import sys
import warnings


def main():
    """Run ussy-snapshot CLI with a deprecation warning."""
    warnings.warn(
        "The 'snapshot' command is deprecated. Use 'ussy-snapshot' instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    from ussy_snapshot.cli import main as _main

    sys.exit(_main())
