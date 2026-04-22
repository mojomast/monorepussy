"""Legacy entry point with deprecation warning for mushin."""
import warnings
import sys
from ussy_mushin.cli import main

def deprecated_main():
    warnings.warn(
        "The 'mushin' command is deprecated. Use 'ussy-mushin' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return main()

if __name__ == "__main__":
    sys.exit(deprecated_main())
