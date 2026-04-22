"""Legacy entry point with deprecation warning for portmore."""
import warnings
import sys
from ussy_portmore.cli import main

def deprecated_main():
    warnings.warn(
        "The 'portmore' command is deprecated. Use 'ussy-portmore' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
