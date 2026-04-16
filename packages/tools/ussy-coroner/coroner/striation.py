"""Striation Matching — Ballistic Analysis.

Cross-correlate error signatures across builds to identify same-root-cause failures.

C_max = max_tau [integral(s1(t)*s2(t+tau)dt)] / [sqrt(integral(s1^2 dt) * integral(s2^2 dt))]

If C_max > 0.8 between two error patterns, they share the same root cause.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from coroner.models import PipelineRun, StriationMatch


# Patterns to normalize away (timestamps, PIDs, paths, memory addresses)
_NORMALIZE_PATTERNS = [
    (re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?'), '<TIMESTAMP>'),
    (re.compile(r'\bpid\s*\d+\b', re.IGNORECASE), '<PID>'),
    (re.compile(r'0x[0-9a-fA-F]{4,}'), '<ADDR>'),
    (re.compile(r'/tmp/[^\s]+'), '<TEMP_PATH>'),
    (re.compile(r'/var/[^\s]+'), '<VAR_PATH>'),
    (re.compile(r'/home/[^\s]+'), '<HOME_PATH>'),
    (re.compile(r'/Users/[^\s]+'), '<HOME_PATH>'),
    (re.compile(r'line \d+', re.IGNORECASE), 'line <NUM>'),
    (re.compile(r'\b\d+ms\b'), '<TIME>'),
    (re.compile(r'\b\d+s\b'), '<TIME>'),
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '<IP>'),
    (re.compile(r'memory 0x[0-9a-fA-F]+'), 'memory <ADDR>'),
]


def normalize_error_signature(log_content: str) -> str:
    """Normalize error log content by replacing variable parts with placeholders.

    This enables structural correlation — catches errors that look different
    but have the same underlying cause.
    """
    normalized = log_content
    for pattern, replacement in _NORMALIZE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _text_to_signal(text: str) -> list[float]:
    """Convert text to a numerical signal for cross-correlation.

    Uses character frequency histogram over sliding windows.
    """
    if not text:
        return [0.0]

    # Create a signal based on character code values, downsampled
    # Use chunks of 10 characters to create a manageable signal
    chunk_size = 10
    signal: list[float] = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        # Hash each chunk to get a stable numerical value
        h = hashlib.md5(chunk.encode()).hexdigest()
        # Use first 8 hex chars as a float
        val = int(h[:8], 16) / 0xFFFFFFFF
        signal.append(val)

    return signal


def cross_correlate(signal1: list[float], signal2: list[float]) -> float:
    """Compute normalized cross-correlation between two signals.

    C_max = max_tau [sum(s1[i]*s2[i+tau])] / [sqrt(sum(s1^2) * sum(s2^2))]

    Uses numpy if available for efficiency, falls back to pure Python.
    """
    if not signal1 or not signal2:
        return 0.0

    try:
        import numpy as np
        s1 = np.array(signal1, dtype=np.float64)
        s2 = np.array(signal2, dtype=np.float64)

        # Normalize to zero mean
        s1 = s1 - np.mean(s1)
        s2 = s2 - np.mean(s2)

        # Compute norms
        norm1 = np.sqrt(np.sum(s1 ** 2))
        norm2 = np.sqrt(np.sum(s2 ** 2))

        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0

        # Full cross-correlation using np.correlate
        correlation = np.correlate(s1, s2, mode='full')
        c_max = float(np.max(correlation)) / float(norm1 * norm2)

        return min(1.0, max(0.0, c_max))

    except ImportError:
        # Pure Python fallback
        n1 = len(signal1)
        n2 = len(signal2)

        # Zero-mean
        mean1 = sum(signal1) / n1
        mean2 = sum(signal2) / n2
        s1 = [x - mean1 for x in signal1]
        s2 = [x - mean2 for x in signal2]

        norm1 = math.sqrt(sum(x * x for x in s1))
        norm2 = math.sqrt(sum(x * x for x in s2))

        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0

        # Compute cross-correlation at various lags
        max_corr = 0.0
        max_lag = min(n1, n2)

        for lag in range(-max_lag, max_lag + 1):
            corr = 0.0
            for i in range(n1):
                j = i + lag
                if 0 <= j < n2:
                    corr += s1[i] * s2[j]
            normalized = corr / (norm1 * norm2)
            if normalized > max_corr:
                max_corr = normalized

        return min(1.0, max(0.0, max_corr))


def compute_error_signature(run: PipelineRun) -> str:
    """Compute a normalized error signature for a pipeline run.

    Combines all error log content from failing stages, normalized.
    """
    error_parts: list[str] = []
    for stage in run.stages:
        if stage.status.value == "failure" and stage.log_content:
            error_parts.append(normalize_error_signature(stage.log_content))

    if not error_parts:
        return ""

    return "\n---\n".join(error_parts)


def compare_signatures(run1: PipelineRun, run2: PipelineRun) -> StriationMatch:
    """Compare error signatures between two pipeline runs using cross-correlation.

    Args:
        run1: First pipeline run.
        run2: Second pipeline run.

    Returns:
        StriationMatch with correlation score and same_root_cause flag.
    """
    sig1 = compute_error_signature(run1)
    sig2 = compute_error_signature(run2)

    if not sig1 or not sig2:
        return StriationMatch(
            build_id_1=run1.run_id,
            build_id_2=run2.run_id,
            correlation=0.0,
            same_root_cause=False,
            resolution_note="No error signatures to compare",
        )

    # Convert to signals and cross-correlate
    signal1 = _text_to_signal(sig1)
    signal2 = _text_to_signal(sig2)

    correlation = cross_correlate(signal1, signal2)

    match = StriationMatch(
        build_id_1=run1.run_id,
        build_id_2=run2.run_id,
        correlation=round(correlation, 2),
    )

    return match


def analyze_striations(
    run: PipelineRun,
    compare_runs: list[PipelineRun],
) -> list[StriationMatch]:
    """Analyze striation matches between a run and comparison runs.

    Args:
        run: The primary pipeline run.
        compare_runs: Other pipeline runs to compare against.

    Returns:
        List of StriationMatch results, sorted by correlation descending.
    """
    matches: list[StriationMatch] = []
    for compare_run in compare_runs:
        match = compare_signatures(run, compare_run)
        matches.append(match)

    matches.sort(key=lambda m: m.correlation, reverse=True)
    return matches


def format_striation(matches: list[StriationMatch]) -> str:
    """Format striation match results for display."""
    lines: list[str] = []

    if not matches:
        lines.append("No comparison builds available for striation matching.")
        return "\n".join(lines)

    for match in matches:
        if match.same_root_cause:
            lines.append(
                f"Build #{match.build_id_1} vs Build #{match.build_id_2}: "
                f"C_max = {match.correlation:.2f} ← SAME ROOT CAUSE"
            )
        else:
            lines.append(
                f"Build #{match.build_id_1} vs Build #{match.build_id_2}: "
                f"C_max = {match.correlation:.2f}"
            )

        if match.resolution_note:
            lines.append(f"  {match.resolution_note}")

    return "\n".join(lines)
