"""
Operon — Gene Regulation for Documentation Generation

A Python package that applies gene regulation biology as a functional model
for documentation generation and management.
"""

__version__ = "1.0.0"
__author__ = "Operon Team"

from operon.models import (
    Gene,
    Operon,
    Promoter,
    Repressor,
    Enhancer,
    TranscriptionFactor,
    EpigeneticMark,
)

from operon.mapper import OperonMapper
from operon.promoter import PromoterDetector
from operon.repressor import RepressorManager
from operon.enhancer import EnhancerScanner
from operon.transcription import TranscriptionFactorRegistry
from operon.epigenetics import EpigeneticStateTracker
from operon.storage import StorageManager

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
