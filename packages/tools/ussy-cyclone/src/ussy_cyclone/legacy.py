"""Legacy entry point with deprecation warning for cyclone."""
import warnings
import sys
from ussy_cyclone.cli import main

def deprecated_main():
    warnings.warn(
        "The 'cyclone' command is deprecated. Use 'ussy-cyclone' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
