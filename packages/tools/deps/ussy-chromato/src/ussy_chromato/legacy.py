"""Legacy entry point with deprecation warning for 'chromato' command."""

from __future__ import annotations

import warnings
import sys

from ussy_chromato.cli import main as _main


def main(argv: list[str] | None = None) -> int:
    warnings.warn(
        "The 'chromato' command is deprecated. Use 'ussy-chromato' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _main(argv)


if __name__ == "__main__":
    sys.exit(main())
