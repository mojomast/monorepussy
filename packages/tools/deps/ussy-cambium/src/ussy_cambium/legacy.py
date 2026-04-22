"""Legacy CLI entry point with deprecation warning."""

from __future__ import annotations

import sys
import warnings


def main() -> int:
    warnings.warn(
        "The 'cambium' command is deprecated. Use 'ussy-cambium' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Import here to avoid circular imports
    from ussy_cambium.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
