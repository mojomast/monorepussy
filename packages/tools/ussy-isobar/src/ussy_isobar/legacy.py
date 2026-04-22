"""Legacy entry point with deprecation warning for isobar."""

import warnings
import sys

from ussy_isobar.cli import main


def legacy_main():
    warnings.warn(
        f"The '{old_module}' command is deprecated. Use 'ussy-isobar' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(legacy_main())
