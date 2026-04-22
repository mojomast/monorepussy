"""Allow running fatigue as a module: python -m fatigue"""
import sys
from .cli import main

sys.exit(main())
