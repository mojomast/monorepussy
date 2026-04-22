"""Legacy entry point with deprecation warning."""

from __future__ import annotations

import warnings
from typing import Sequence

from .cli import main as _main


def main(argv: Sequence[str] | None = None) -> int:
    """Deprecated legacy entry point for 'churnmap'."""
    warnings.warn(
        "The 'churnmap' command is deprecated. Use 'ussy-churn' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _main(argv)
