"""Legacy entry point with deprecation warning for seral.

This module provides backward compatibility for the old `seral` command.
"""

from __future__ import annotations

import warnings
import sys
from ussy_seral.cli import main


def deprecated_main() -> int:
    """Run the CLI with a deprecation warning."""
    warnings.warn(
        f"The '{old_name}' command is deprecated. Use 'ussy-seral' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(deprecated_main())
