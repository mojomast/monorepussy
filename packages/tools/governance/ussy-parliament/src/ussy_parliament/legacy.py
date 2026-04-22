"""Legacy entry point with deprecation warning."""

from __future__ import annotations

import warnings

from ussy_parliament.cli import main as _main


def main():
    warnings.warn(
        "The 'parliament' command is deprecated. Use 'ussy-parliament' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _main()


if __name__ == "__main__":
    main()
