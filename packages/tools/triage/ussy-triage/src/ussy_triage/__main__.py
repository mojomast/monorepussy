"""Allow running ussy-triage as a module: python -m ussy_triage"""
import sys
from .cli import main

sys.exit(main())
