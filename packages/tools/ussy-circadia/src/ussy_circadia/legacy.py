"""Legacy entry point with deprecation warning for circadia."""

import warnings
import sys

from ussy_circadia.cli import main


def legacy_main():
    warnings.warn(
        f"The '{old_module}' command is deprecated. Use 'ussy-circadia' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(legacy_main())
