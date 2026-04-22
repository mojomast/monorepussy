"""Legacy entry point with deprecation warning for coroner."""

import warnings
import sys

from ussy_coroner.cli import main


def legacy_main():
    warnings.warn(
        f"The '{old_module}' command is deprecated. Use 'ussy-coroner' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(legacy_main())
