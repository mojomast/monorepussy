"""Legacy entry point with deprecation warning for aquifer.

This module provides backward compatibility for the old `aquifer` command.
"""

from __future__ import annotations

import warnings
import sys
from ussy_aquifer.cli import main


def deprecated_main() -> int:
    """Run the CLI with a deprecation warning."""
    warnings.warn(
        f"The '{old_name}' command is deprecated. Use 'ussy-aquifer' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(deprecated_main())
