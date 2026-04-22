"""Strata: Geological Semver for Codebase Archeology.

Treat your dependency tree as a geological formation. Measure seismic activity
(behavioral change rate), identify bedrock (stable API surfaces), flag fault lines
(boundaries between stable and unstable regions), and detect erosion (slow deprecation).
"""

__version__ = "0.1.0"

# Core data models
from strata.models import (
    ProbeResult,
    Probe,
    StratigraphicColumn,
    BedrockReport,
    SeismicReport,
    FaultLine,
    ErosionReport,
    VersionProbeResult,
    DiffResult,
    ScanResult,
)

__all__ = [
    "ProbeResult",
    "Probe",
    "StratigraphicColumn",
    "BedrockReport",
    "SeismicReport",
    "FaultLine",
    "ErosionReport",
    "VersionProbeResult",
    "DiffResult",
    "ScanResult",
]
