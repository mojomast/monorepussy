"""Legacy deprecation wrapper for petrichor command."""

import warnings
import sys


def main():
    """Run the CLI with a deprecation warning."""
    warnings.warn(
        "The 'petrichor' command is deprecated. Use 'ussy-petrichor' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from ussy_petrichor.cli import main as _main

    sys.exit(_main() or 0)
