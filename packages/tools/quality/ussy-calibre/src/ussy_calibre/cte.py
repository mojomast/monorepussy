"""CTE Profiler — Coefficient of Thermal Expansion Measurement."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from ussy_calibre.models import CTEProfile, TestResult


def compute_cte_by_dimension(
    results: List[TestResult],
    dimension_steps: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, float]]:
    """Compute CTE per test per dimension.

    CTE(t, dim) = |∂p(t)/∂(dim)| — rate of pass-rate change per unit
    change in environment dimension.

    Returns: {test_name: {dimension: cte_value}}
    """
    if dimension_steps is None:
        dimension_steps = {
            "python_version": 0.1,
            "parallelism": 1.0,
            "load_level": 0.25,
        }

    # Group by test
    by_test: Dict[str, List[TestResult]] = {}
    for r in results:
        if r.test_name not in by_test:
            by_test[r.test_name] = []
        by_test[r.test_name].append(r)

    profiles: Dict[str, Dict[str, float]] = {}

    for test_name, test_results in by_test.items():
        profiles[test_name] = {}

        for dim_name, step_size in dimension_steps.items():
            # Group by dimension value
            by_val: Dict[float, List[bool]] = {}
            for r in test_results:
                raw_val = getattr(r.condition, dim_name)
                try:
                    val = float(raw_val)
                except (ValueError, TypeError):
                    # For string dimensions like python_version, parse
                    if isinstance(raw_val, str) and "." in raw_val:
                        try:
                            val = float(raw_val)
                        except ValueError:
                            continue
                    else:
                        continue

                if val not in by_val:
                    by_val[val] = []
                by_val[val].append(r.passed)

            if len(by_val) < 2:
                profiles[test_name][dim_name] = 0.0
                continue

            # Compute pass rates at each value
            val_rates = []
            sorted_vals = sorted(by_val.keys())
            for v in sorted_vals:
                outcomes = by_val[v]
                rate = sum(outcomes) / len(outcomes) if outcomes else 0.0
                val_rates.append((v, rate))

            # Compute |Δp/Δdim| for each adjacent pair
            deltas = []
            for i in range(1, len(val_rates)):
                dp = abs(val_rates[i][1] - val_rates[i - 1][1])
                dv = abs(val_rates[i][0] - val_rates[i - 1][0])
                if dv > 0:
                    deltas.append(dp / dv)

            if deltas:
                # Average the gradients
                profiles[test_name][dim_name] = sum(deltas) / len(deltas)
            else:
                profiles[test_name][dim_name] = 0.0

    return profiles


def compute_composite_cte(
    cte_by_dim: Dict[str, float],
    max_cte_by_dim: Optional[Dict[str, float]] = None,
) -> float:
    """Compute composite CTE from dimensional CTEs.

    CTE(t) = √(Σ_dim CTE_norm(t, dim)²)
    Where CTE_norm = CTE(t, dim) / CTE_max(dim)
    """
    if not cte_by_dim:
        return 0.0

    if max_cte_by_dim is None:
        max_cte_by_dim = {
            "python_version": 5.0,
            "parallelism": 1.0,
            "load_level": 2.0,
            "os": 1.0,
        }

    normalized_squares = []
    for dim, cte in cte_by_dim.items():
        max_cte = max_cte_by_dim.get(dim, max(cte, 0.001))
        norm = cte / max_cte if max_cte > 0 else 0.0
        normalized_squares.append(norm * norm)

    return math.sqrt(sum(normalized_squares))


def profile_cte(
    results: List[TestResult],
    max_cte_by_dim: Optional[Dict[str, float]] = None,
) -> Dict[str, CTEProfile]:
    """Run CTE profiling on test results.

    Measures each test's sensitivity to each environmental variable.
    Tests with high composite CTE are 'soda-lime' (fragile);
    low CTE are 'borosilicate' (resilient).
    """
    cte_by_dim = compute_cte_by_dimension(results)

    profiles: Dict[str, CTEProfile] = {}

    for test_name, dims in cte_by_dim.items():
        composite = compute_composite_cte(dims, max_cte_by_dim)
        profiles[test_name] = CTEProfile(
            test_name=test_name,
            cte_by_dimension=dims,
            composite_cte=composite,
        )

    return profiles


def format_cte_profiles(profiles: Dict[str, CTEProfile]) -> str:
    """Format CTE profiles as readable output."""
    lines = []
    lines.append("=" * 60)
    lines.append("CTE PROFILER — Coefficient of Thermal Expansion")
    lines.append("=" * 60)
    lines.append("")

    if not profiles:
        lines.append("No test results to analyze.")
        return "\n".join(lines)

    sorted_profiles = sorted(
        profiles.values(), key=lambda p: p.composite_cte, reverse=True
    )

    for profile in sorted_profiles:
        lines.append(f"  {profile.test_name}")
        lines.append(f"    Composite CTE: {profile.composite_cte:.4f} ({profile.glass_analogy})")

        if profile.cte_by_dimension:
            sorted_dims = sorted(
                profile.cte_by_dimension.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for dim, cte in sorted_dims:
                bar = "█" * min(int(cte * 20), 50)
                lines.append(f"      {dim:20s} {cte:.4f} {bar}")

        lines.append("")

    # Summary
    fragile = sum(1 for p in profiles.values() if p.composite_cte >= 0.3)
    total = len(profiles)
    lines.append(f"Summary: {fragile}/{total} tests have high CTE (fragile)")

    return "\n".join(lines)
