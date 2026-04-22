"""Legacy entry point with deprecation warning for mint.

This module provides backward compatibility for the old `mint` command.
"""

from __future__ import annotations

import warnings
import sys
from ussy_mint.cli import main


def deprecated_main() -> int:
    """Run the CLI with a deprecation warning."""
    warnings.warn(
        f"The '{old_name}' command is deprecated. Use 'ussy-mint' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(deprecated_main())
