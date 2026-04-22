"""Legacy entry point with deprecation warning for operon."""
import warnings
import sys
from ussy_operon.cli import main

def deprecated_main():
    warnings.warn(
        "The 'operon' command is deprecated. Use 'ussy-operon' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
