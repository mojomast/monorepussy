"""Sentinel — Immunological Self/Non-Self Code Governance.

Uses the Negative Selection Algorithm from artificial immune systems
to build codebase-specific governance that emerges from the code itself.
"""

__version__ = "1.0.0"

from .checker import (
    AnomalyReport,
    check_directory,
    check_file,
    check_patterns,
    format_report,
)
from .db import SentinelDB
from .detectors import DetectorPopulation, apply_feedback, generate_detectors
from .profile import SelfProfile, build_profile, profile_file_summary

__all__ = [
    "__version__",
    "AnomalyReport",
    "check_directory",
    "check_file",
    "check_patterns",
    "format_report",
    "SentinelDB",
    "DetectorPopulation",
    "apply_feedback",
    "generate_detectors",
    "SelfProfile",
    "build_profile",
    "profile_file_summary",
]
