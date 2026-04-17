"""Allow running triage as a module: python -m triage"""
import sys
from .cli import main

sys.exit(main())
