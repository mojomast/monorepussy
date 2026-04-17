"""Runner: orchestrates probe execution and result collection."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from syntrop.ir import DiffResult, ProbeResult, ScanResult
from syntrop.probes import PROBE_REGISTRY
from syntrop.analyzer import BehavioralAssumption, scan_file, scan_source


def run_probe(
    source: str,
    probe_name: str,
    func_name: str = "main",
    *args: Any,
    **kwargs: Any,
) -> ProbeResult:
    """Run a single semantic probe on source code.

    Args:
        source: Python source code.
        probe_name: Name of the probe to run.
        func_name: Name of the function to test.
        *args: Arguments to pass to the function.
        **kwargs: Keyword arguments.

    Returns:
        ProbeResult with divergence information.
    """
    if probe_name not in PROBE_REGISTRY:
        raise ValueError(
            f"Unknown probe: {probe_name}. "
            f"Available probes: {', '.join(PROBE_REGISTRY.keys())}"
        )
    probe_class = PROBE_REGISTRY[probe_name]
    probe = probe_class()
    return probe.run(source, func_name, *args, **kwargs)


def run_all_probes(
    source: str,
    func_name: str = "main",
    probe_names: list[str] | None = None,
    *args: Any,
    **kwargs: Any,
) -> list[ProbeResult]:
    """Run multiple semantic probes on source code.

    Args:
        source: Python source code.
        func_name: Name of the function to test.
        probe_names: List of probe names. If None, runs all.
        *args: Arguments to pass to the function.
        **kwargs: Keyword arguments.

    Returns:
        List of ProbeResults.
    """
    if probe_names is None:
        probe_names = list(PROBE_REGISTRY.keys())

    results: list[ProbeResult] = []
    for name in probe_names:
        result = run_probe(source, name, func_name, *args, **kwargs)
        results.append(result)
    return results


def probe_file(
    path: str,
    probe_names: list[str] | None = None,
    func_name: str = "main",
) -> list[ProbeResult]:
    """Run probes on a Python file.

    Args:
        path: Path to the Python file.
        probe_names: List of probe names. If None, runs all.
        func_name: Name of the function to test.

    Returns:
        List of ProbeResults.
    """
    with open(path, "r") as f:
        source = f.read()
    return run_all_probes(source, func_name, probe_names)


def scan_directory(
    directory: str,
    probe_names: list[str] | None = None,
) -> list[ScanResult]:
    """Scan a directory for behavioral assumptions.

    Args:
        directory: Path to the directory to scan.
        probe_names: List of probe names. If None, runs all.

    Returns:
        List of ScanResults, one per Python file found.
    """
    dir_path = Path(directory)
    results: list[ScanResult] = []

    py_files = sorted(dir_path.glob("**/*.py"))
    for py_file in py_files:
        try:
            source = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue

        assumptions = scan_source(source)
        probe_results: list[ProbeResult] = []

        # Run relevant probes based on detected assumptions
        relevant_probes = set()
        for assumption in assumptions:
            relevant_probes.update(assumption.related_probes)

        if probe_names:
            relevant_probes = relevant_probes.intersection(probe_names)

        relevant_probes = relevant_probes.intersection(PROBE_REGISTRY.keys())

        if relevant_probes:
            for probe_name in sorted(relevant_probes):
                try:
                    result = run_probe(source, probe_name)
                    probe_results.append(result)
                except Exception:
                    pass

        # Build summary
        n_warnings = sum(1 for a in assumptions if a.severity == "warning")
        n_errors = sum(1 for a in assumptions if a.severity == "error")
        n_diverged = sum(1 for r in probe_results if r.diverged)

        summary_parts = []
        if n_warnings:
            summary_parts.append(f"{n_warnings} warning(s)")
        if n_errors:
            summary_parts.append(f"{n_errors} error(s)")
        if n_diverged:
            summary_parts.append(f"{n_diverged} divergence(s)")
        summary = ", ".join(summary_parts) if summary_parts else "No issues found"

        results.append(
            ScanResult(
                path=str(py_file),
                assumptions=[_assumption_to_dict(a) for a in assumptions],
                probe_results=probe_results,
                summary=summary,
            )
        )

    return results


def diff_probes(
    source: str,
    probe_names: list[str] | None = None,
    func_name: str = "main",
) -> DiffResult:
    """Compare behavior across multiple probe modes.

    Args:
        source: Python source code.
        probe_names: List of probe names to compare. If None, runs all.
        func_name: Name of the function to test.

    Returns:
        DiffResult comparing behavior across probes.
    """
    if probe_names is None:
        probe_names = list(PROBE_REGISTRY.keys())

    results = run_all_probes(source, func_name, probe_names)

    divergences: list[dict[str, Any]] = []
    consistent = True

    for result in results:
        if result.diverged:
            consistent = False
            divergences.append(
                {
                    "probe": result.probe_name,
                    "type": result.divergence_type,
                    "explanation": result.explanation,
                    "severity": result.severity,
                    "original_output": repr(result.original_output),
                    "probed_output": repr(result.probed_output),
                }
            )

    n_divergent = len(divergences)
    summary = (
        f"Tested {len(probe_names)} probe modes, "
        f"found {n_divergent} divergence(s)"
    )

    return DiffResult(
        file_path="<source>",
        modes_compared=probe_names,
        divergences=divergences,
        consistent=consistent,
        summary=summary,
    )


def _assumption_to_dict(a: BehavioralAssumption) -> dict[str, Any]:
    """Convert a BehavioralAssumption to a dictionary."""
    return {
        "kind": a.kind,
        "description": a.description,
        "line": a.line,
        "col": a.col,
        "code_snippet": a.code_snippet,
        "severity": a.severity,
        "related_probes": a.related_probes,
    }
