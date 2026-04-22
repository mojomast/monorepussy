"""Legacy entry point with deprecation warning for curator."""
import warnings
import sys
from ussy_curator.cli import main

def deprecated_main():
    warnings.warn(
        "The 'curator' command is deprecated. Use 'ussy-curator' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
