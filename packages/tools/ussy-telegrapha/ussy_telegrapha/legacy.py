"""Legacy entry point with deprecation warning for telegrapha."""
import warnings
import sys
from ussy_telegrapha.cli import main

def deprecated_main():
    warnings.warn(
        "The 'telegrapha' command is deprecated. Use 'ussy-telegrapha' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
