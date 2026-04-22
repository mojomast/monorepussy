"""Legacy entry point with deprecation warning for 'kintsugi' command."""

from __future__ import annotations

import warnings
import sys

from .cli import main as _cli_main


def main(argv=None):
    warnings.warn(
        "The 'kintsugi' command is deprecated. Use 'ussy-kintsugi' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _cli_main(argv)


if __name__ == "__main__":
    main()
