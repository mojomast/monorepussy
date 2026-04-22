"""Triage — Error Logs as Crime Scenes.

Analyzes build failures, stack traces, and error logs using a forensic
methodology to produce detective-style diagnostic reports.
"""

__version__ = "1.0.0"

from .cli import main
from .extractor import ErrorExtractor, IsolatedError
from .patterns import PatternMatcher
from .enricher import ContextEnricher
from .renderer import DiagnosisRenderer
from .models import EnrichedError, Diagnosis, ErrorPattern, GitContext, HistoryMatch, VictimType, Confidence

__all__ = [
    "__version__",
    "main",
    "ErrorExtractor",
    "IsolatedError",
    "PatternMatcher",
    "ContextEnricher",
    "DiagnosisRenderer",
    "EnrichedError",
    "Diagnosis",
    "ErrorPattern",
    "GitContext",
    "HistoryMatch",
    "VictimType",
    "Confidence",
]
