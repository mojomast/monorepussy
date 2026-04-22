"""Legacy alias for gridiron command with deprecation warning."""

import warnings
import sys
from ussy_gridiron.cli import main


def gridiron_alias():
    """Deprecated entry point for 'gridiron' command."""
    warnings.warn(
        "The 'gridiron' command is deprecated. Use 'ussy-gridiron' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    main()


if __name__ == "__main__":
    gridiron_alias()
