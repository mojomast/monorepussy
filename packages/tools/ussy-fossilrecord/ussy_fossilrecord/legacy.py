"""Legacy entry point with deprecation warning for fossil."""
import warnings
import sys
from ussy_fossilrecord.cli import main

def deprecated_main():
    warnings.warn(
        "The 'fossil' command is deprecated. Use 'ussy-fossilrecord' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
