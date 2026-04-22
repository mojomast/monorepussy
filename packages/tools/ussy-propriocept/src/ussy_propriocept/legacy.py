"""Legacy entry point with deprecation warning for propriocept."""
import warnings
import sys
from ussy_propriocept.cli import main

def deprecated_main():
    warnings.warn(
        "The 'propriocept' command is deprecated. Use 'ussy-propriocept' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
