"""Legacy entry point with deprecation warning for syntrop."""
import warnings
import sys
from ussy_syntrop.cli import main

def deprecated_main():
    warnings.warn(
        "The 'syntrop' command is deprecated. Use 'ussy-syntrop' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
