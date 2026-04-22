"""Legacy entry point with deprecation warning for stemma."""

import warnings
import sys

from ussy_stemma.cli import main


def legacy_main():
    warnings.warn(
        f"The '{old_module}' command is deprecated. Use 'ussy-stemma' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()


if __name__ == "__main__":
    sys.exit(legacy_main())
