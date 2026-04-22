"""Utility helpers for acumen."""

from __future__ import annotations

import ast
import math
import os
from typing import Sequence


# ---------------------------------------------------------------------------
# Cyclomatic complexity from AST
# ---------------------------------------------------------------------------

_DECISION_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.Assert,
)

_BOOLEAN_OPS = (ast.And, ast.Or)


def cyclomatic_complexity(source: str) -> int:
    """Compute McCabe cyclomatic complexity for a source string.

    CC = decision_points + 1
    Decision points: if, for, while, except, with, assert, and, or, elif (nested If in orelse).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 1

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, _DECISION_NODES):
            count += 1
        elif isinstance(node, _BOOLEAN_OPS):
            count += 1
    return max(count + 1, 1)


def functions_from_source(source: str, filepath: str) -> list[dict]:
    """Extract function-level info from Python source.

    Returns list of dicts with keys: name, lineno, complexity.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_source = ast.get_source_segment(source, node)
            if func_source is None:
                func_source = ""
            cc = cyclomatic_complexity(func_source) if func_source else 1
            results.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "complexity": cc,
                }
            )
    return results


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def classify_test_function(name: str) -> str:
    """Classify a test function as 'unit' or 'integration' by naming convention."""
    name_lower = name.lower()
    integration_keywords = [
        "integration",
        "e2e",
        "end_to_end",
        "system",
        "acceptance",
        "functional",
        "smoke",
    ]
    for kw in integration_keywords:
        if kw in name_lower:
            return "integration"
    return "unit"


def is_test_file(filepath: str) -> bool:
    """Return True if the filepath looks like a test file."""
    basename = os.path.basename(filepath)
    return basename.startswith("test_") or basename.endswith("_test.py")


# ---------------------------------------------------------------------------
# Math helpers (no numpy/scipy dependency)
# ---------------------------------------------------------------------------

def mean(values: Sequence[float]) -> float:
    """Arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def stdev(values: Sequence[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def dft_magnitudes(signal: Sequence[float]) -> list[float]:
    """Compute Discrete Fourier Transform magnitude spectrum (manual, no numpy).

    Returns magnitudes for frequencies 0..N//2.
    """
    N = len(signal)
    if N == 0:
        return []
    num_bins = N // 2 + 1
    magnitudes = []
    for k in range(num_bins):
        real = 0.0
        imag = 0.0
        for n in range(N):
            angle = 2 * math.pi * k * n / N
            real += signal[n] * math.cos(angle)
            imag -= signal[n] * math.sin(angle)
        magnitudes.append(math.sqrt(real * real + imag * imag) / N)
    return magnitudes


def psd(signal: Sequence[float]) -> list[float]:
    """Power spectral density estimate (squared magnitude spectrum, in dB)."""
    mags = dft_magnitudes(signal)
    psd_vals = []
    for m in mags:
        power = m * m
        if power > 0:
            psd_vals.append(10 * math.log10(power))
        else:
            psd_vals.append(-120.0)  # floor
    return psd_vals


def linear_regression(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Simple linear regression returning (slope, intercept)."""
    n = len(x)
    if n < 2:
        return (0.0, mean(y) if y else 0.0)
    mx = mean(x)
    my = mean(y)
    ss_xx = sum((xi - mx) ** 2 for xi in x)
    ss_xy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    if ss_xx == 0:
        return (0.0, my)
    slope = ss_xy / ss_xx
    intercept = my - slope * mx
    return (slope, intercept)


# ---------------------------------------------------------------------------
# String / formatting helpers
# ---------------------------------------------------------------------------

def format_threshold(t: float) -> str:
    """Format a detection threshold for display."""
    return f"{t:.1f} dB"


def severity_label(t: float) -> str:
    """Map a detection threshold to a clinical severity label."""
    if t <= 10:
        return "normal"
    elif t <= 20:
        return "mild loss"
    elif t <= 30:
        return "moderate loss"
    elif t <= 40:
        return "moderately-severe loss"
    elif t <= 50:
        return "severe loss"
    else:
        return "profound loss"
