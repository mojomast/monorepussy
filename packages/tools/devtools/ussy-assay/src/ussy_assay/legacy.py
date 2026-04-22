"""Legacy entry point for backward compatibility."""

import sys
import warnings


def main():
    """Run the CLI with a deprecation warning."""
    warnings.warn(
        "The 'assay' command is deprecated. Use 'ussy-assay' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from ussy_assay.cli import main as _main

    sys.exit(_main())
