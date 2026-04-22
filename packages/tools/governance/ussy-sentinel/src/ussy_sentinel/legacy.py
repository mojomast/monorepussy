"""Legacy alias for sentinel command with deprecation warning."""

import warnings
import sys
from .cli import main


def sentinel_alias():
    """Legacy entry point that warns about deprecation."""
    warnings.warn(
        "The 'sentinel' command is deprecated. Use 'ussy-sentinel' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(sentinel_alias())
