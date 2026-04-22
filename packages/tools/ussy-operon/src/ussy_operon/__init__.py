"""
Operon — Gene Regulation for Documentation Generation

A Python package that applies gene regulation biology as a functional model
for documentation generation and management.
"""

__version__ = "1.0.0"
__author__ = "Operon Team"

from ussy_operon.models import (
    Gene,
    Operon,
    Promoter,
    Repressor,
    Enhancer,
    TranscriptionFactor,
    EpigeneticMark,
)

from ussy_operon.mapper import OperonMapper
from ussy_operon.promoter import PromoterDetector
from ussy_operon.repressor import RepressorManager
from ussy_operon.enhancer import EnhancerScanner
from ussy_operon.transcription import TranscriptionFactorRegistry
from ussy_operon.epigenetics import EpigeneticStateTracker
from ussy_operon.storage import StorageManager

__all__ = [
    "Gene",
    "Operon",
    "Promoter",
    "Repressor",
    "Enhancer",
    "TranscriptionFactor",
    "EpigeneticMark",
    "OperonMapper",
    "PromoterDetector",
    "RepressorManager",
    "EnhancerScanner",
    "TranscriptionFactorRegistry",
    "EpigeneticStateTracker",
    "StorageManager",
]
