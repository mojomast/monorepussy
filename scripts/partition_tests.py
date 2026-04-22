#!/usr/bin/env python3
"""Partition packages into balanced groups for parallel test execution.

Uses historical timing data when available, falling back to heuristic-based
partitioning for new packages.

Usage:
    python partition_tests.py --packages '["pkg1", "pkg2"]' --groups 5
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


def get_test_duration_history() -> Dict[str, float]:
    """Load historical test durations from pytest cache.

    In production, this could read from:
    - pytest cache directory
    - CI artifacts from previous runs
    - A timing database
    """
    durations = {}

    # Try to load from pytest cache
    cache_dir = Path(".pytest_cache/v/cache/durations")
    if cache_dir.exists():
        try:
            content = cache_dir.read_text()
            # Parse durations file format
            # Format: {"test_path::test_name": duration, ...}
            data = json.loads(content)
            # Aggregate by package
            for test_id, duration in data.items():
                # Extract package name from test path
                if "packages/" in test_id:
                    pkg = test_id.split("packages/")[1].split("/")[0]
                    durations[pkg] = durations.get(pkg, 0) + duration
        except (json.JSONDecodeError, IndexError):
            pass

    return durations


def estimate_package_duration(package: str, durations: Dict[str, float]) -> float:
    """Estimate test duration for a package.

    Uses historical data if available, otherwise falls back to heuristics:
    - Number of test files
    - Lines of test code
    - Number of dependencies
    """
    # Check historical data
    if package in durations:
        return durations[package]

    # Heuristic estimation
    test_dir = Path(f"packages/{package}/tests")
    if not test_dir.exists():
        return 10.0  # Default: 10 seconds

    # Count test files
    test_files = list(test_dir.rglob("test_*.py"))
    num_tests = len(test_files)

    # Estimate: ~5 seconds per test file (very rough)
    estimated = num_tests * 5.0

    # Cap at reasonable maximum
    return min(estimated, 120.0)


def partition_by_lpt(
    packages: List[str], durations: Dict[str, float], num_groups: int
) -> List[Dict[str, Any]]:
    """Partition packages using Longest Processing Time (LPT) algorithm.

    LPT algorithm:
    1. Sort packages by duration (longest first)
    2. Assign each package to the group with the shortest total time

    This provides a good (though not optimal) approximation of the
    optimal partition in O(n log n) time.
    """
    if not packages:
        return []

    # Sort packages by duration descending
    sorted_packages = sorted(
        packages, key=lambda p: estimate_package_duration(p, durations), reverse=True
    )

    # Initialize groups
    groups: List[List[str]] = [[] for _ in range(num_groups)]
    group_times = [0.0] * num_groups

    # LPT assignment
    for package in sorted_packages:
        duration = estimate_package_duration(package, durations)

        # Find group with minimum total time
        min_group_idx = group_times.index(min(group_times))

        groups[min_group_idx].append(package)
        group_times[min_group_idx] += duration

    # Build matrix output
    matrix = []
    for i, group in enumerate(groups):
        if group:
            test_paths = " ".join(f"packages/{pkg}/tests" for pkg in group)
            matrix.append(
                {
                    "group_name": f"group-{i + 1}",
                    "packages": group,
                    "test_paths": test_paths,
                    "estimated_duration": round(group_times[i], 1),
                    "package_count": len(group),
                }
            )

    return matrix


def partition_round_robin(packages: List[str], num_groups: int) -> List[Dict[str, Any]]:
    """Simple round-robin partitioning.

    Better than LPT when no timing data is available and packages
    are expected to have similar durations.
    """
    if not packages:
        return []

    groups: List[List[str]] = [[] for _ in range(num_groups)]

    for i, package in enumerate(packages):
        groups[i % num_groups].append(package)

    matrix = []
    for i, group in enumerate(groups):
        if group:
            test_paths = " ".join(f"packages/{pkg}/tests" for pkg in group)
            matrix.append(
                {
                    "group_name": f"group-{i + 1}",
                    "packages": group,
                    "test_paths": test_paths,
                    "package_count": len(group),
                }
            )

    return matrix


def main():
    parser = argparse.ArgumentParser(
        description="Partition packages into balanced test groups"
    )
    parser.add_argument("--packages", required=True, help="JSON array of package names")
    parser.add_argument(
        "--groups", type=int, default=20, help="Number of groups to create"
    )
    parser.add_argument(
        "--algorithm",
        choices=["lpt", "round-robin"],
        default="lpt",
        help="Partitioning algorithm",
    )
    parser.add_argument("--output-json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    # Parse packages
    try:
        packages = json.loads(args.packages)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in --packages: {args.packages}")
        return 1

    if not packages:
        print("Warning: No packages to partition")
        if args.output_json:
            print(json.dumps([]))
        return 0

    # Load timing data
    durations = get_test_duration_history()

    # Partition
    if args.algorithm == "lpt" and durations:
        print(f"Using LPT algorithm with {len(durations)} historical timings")
        matrix = partition_by_lpt(packages, durations, args.groups)
    else:
        if args.algorithm == "lpt" and not durations:
            print("No historical timing data, falling back to round-robin")
        matrix = partition_round_robin(packages, args.groups)

    # Output
    if args.output_json:
        print(json.dumps(matrix))
    else:
        print(f"Partitioned {len(packages)} packages into {len(matrix)} groups:")
        for group in matrix:
            duration = group.get("estimated_duration", "N/A")
            print(
                f"  {group['group_name']}: "
                f"{group['package_count']} packages "
                f"(est. {duration}s)"
            )
            for pkg in group["packages"]:
                print(f"    - {pkg}")

    return 0


if __name__ == "__main__":
    exit(main())
