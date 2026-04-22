"""Test configuration for actuary test suite."""

import sys
import os

# Ensure src directory is on the path for imports
src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
