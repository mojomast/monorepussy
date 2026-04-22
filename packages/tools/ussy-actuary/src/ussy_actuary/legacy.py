"""Legacy entry point with deprecation warning for actuary."""

import warnings
import sys

from ussy_actuary.cli import main


def legacy_main():
    warnings.warn(
        f"The '{old_module}' command is deprecated. Use 'ussy-actuary' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(legacy_main())
