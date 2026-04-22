"""Structural health monitor — continuous tracking via git hooks and CI.

Recalculates stress intensity for affected modules after each commit,
checks for cracks that have crossed K_Ic, and emits alerts.
"""

from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Optional

from .models import (
    Crack,
    DecayPrediction,
    MaterialConstants,
    ModuleMetrics,
    ModuleStatus,
    StressIntensity,
)
from .paris import paris_law
from .scanner import CrackScanner
from .stress import compute_churn_rate, compute_coupling, compute_stress_intensity, estimate_test_coverage


def get_changed_files(commit: str = "HEAD") -> list[str]:
    """Get files changed in a specific commit.

    Args:
        commit: Git commit hash or reference.

    Returns:
        List of changed file paths.
    """
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().splitlines() if f.endswith(".py")]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return []


def get_previous_K(module: str, history_file: Optional[str] = None) -> Optional[float]:
    """Get previously recorded stress intensity for a module.

    Args:
        module: Module file path.
        history_file: Path to history file (default: .fatigue_history in repo root).

    Returns:
        Previous K value, or None if not found.
    """
    if history_file is None:
        try:
            repo_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if repo_root.returncode == 0:
                history_file = os.path.join(repo_root.stdout.strip(), ".fatigue_history")
            else:
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    if not os.path.exists(history_file):
        return None

    try:
        with open(history_file, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2 and parts[0] == module:
                    return float(parts[1])
    except (OSError, ValueError):
        pass

    return None


def save_K(module: str, K: float, history_file: Optional[str] = None) -> None:
    """Save stress intensity for a module to history file.

    Args:
        module: Module file path.
        K: Current stress intensity value.
        history_file: Path to history file.
    """
    if history_file is None:
        try:
            repo_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10,
            )
            if repo_root.returncode == 0:
                history_file = os.path.join(repo_root.stdout.strip(), ".fatigue_history")
            else:
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return

    # Read existing entries
    entries: dict[str, float] = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        entries[parts[0]] = float(parts[1])
        except (OSError, ValueError):
            pass

    # Update entry
    entries[module] = K

    # Write back
    try:
        with open(history_file, "w") as f:
            for mod, k in sorted(entries.items()):
                f.write(f"{mod},{k}\n")
    except OSError:
        pass


def format_alert(
    file_path: str,
    K: float,
    prev_K: Optional[float],
    material: MaterialConstants,
    growth_rate: float,
) -> str:
    """Format a fatigue alert message for a module.

    Args:
        file_path: Path to the affected module.
        K: Current stress intensity.
        prev_K: Previous stress intensity.
        material: Material constants.
        growth_rate: Current crack growth rate.

    Returns:
        Formatted alert string.
    """
    lines = [f"[FATIGUE] Commit touched {file_path}"]

    delta = ""
    if prev_K is not None:
        diff = K - prev_K
        if diff > 0:
            delta = f" (▲ +{diff:.1f} from last cycle)"
        elif diff < 0:
            delta = f" (▼ {diff:.1f} from last cycle)"
        else:
            delta = " (─ unchanged)"

    lines.append(f"  Stress intensity: K = {K:.1f}{delta}")

    if K >= material.K_Ic:
        lines.append(f"  ⚠️ ABOVE FRACTURE TOUGHNESS (K_Ic = {material.K_Ic})")
    elif K >= material.K_e:
        lines.append(f"  ⚡ Above endurance limit (K_e = {material.K_e})")

    lines.append(f"  Growth rate: da/dN = {growth_rate:.2f}", )

    if growth_rate > 1.0:
        lines.append("  ⚠️ ACCELERATING — Recommend intervention before next sprint")
    elif growth_rate > 0:
        lines.append("  Growing steadily")

    return "\n".join(lines)


def run_monitor(
    directory: str = ".",
    material: Optional[MaterialConstants] = None,
    commit: str = "HEAD",
) -> list[str]:
    """Run structural health monitoring check.

    After each commit:
    1. Identifies changed Python files
    2. Recalculates stress intensity for affected modules
    3. Checks if any crack has crossed K_Ic
    4. Emits alerts for accelerating growth rates

    Args:
        directory: Root directory to scan.
        material: Material constants (uses defaults if not provided).
        commit: Git commit to check.

    Returns:
        List of alert strings.
    """
    if material is None:
        material = MaterialConstants()

    scanner = CrackScanner()
    alerts: list[str] = []

    # Get changed files
    changed = get_changed_files(commit)
    if not changed:
        return alerts

    # Analyze each changed file
    for file_path in changed:
        full_path = os.path.join(directory, file_path) if not os.path.isabs(file_path) else file_path

        if not os.path.exists(full_path):
            continue

        # Compute metrics
        metrics = scanner.compute_module_metrics(full_path)
        metrics.churn_rate = compute_churn_rate(full_path)

        # Get previous K
        prev_K = get_previous_K(full_path)

        # Compute stress intensity
        stress = compute_stress_intensity(metrics, prev_K)

        # Compute growth rate
        growth_rate = paris_law(abs(stress.delta_K) if stress.delta_K > 0 else stress.K,
                                material.C, material.m)

        # Generate alert if above endurance limit
        if stress.K >= material.K_e:
            alert = format_alert(full_path, stress.K, prev_K, material, growth_rate)
            alerts.append(alert)

        # Save current K
        save_K(full_path, stress.K)

    return alerts
