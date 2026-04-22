#!/usr/bin/env python3
"""Run tests for a specific group in the nightly full suite.

Usage:
    python run_test_group.py --group 1 --total 25
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_all_packages() -> list[str]:
    """Get all packages in the monorepo."""
    packages_dir = Path("packages")
    return sorted(
        [
            d.name
            for d in packages_dir.iterdir()
            if d.is_dir() and (d / "pyproject.toml").exists()
        ]
    )


def get_packages_for_group(
    all_packages: list[str], group: int, total: int
) -> list[str]:
    """Get packages assigned to a specific group."""
    # Simple round-robin assignment
    return [pkg for i, pkg in enumerate(all_packages) if i % total == (group - 1)]


def run_tests(packages: list[str]) -> int:
    """Run tests for the given packages."""
    if not packages:
        print("No packages assigned to this group")
        return 0

    test_paths = " ".join(f"packages/{pkg}/tests" for pkg in packages)

    cmd = [
        "uv",
        "run",
        "pytest",
        "-xvs",
        "--tb=short",
        "-n",
        "auto",
        "--dist=loadgroup",
        "--cov=packages",
        "--cov-report=xml",
    ] + test_paths.split()

    print(f"Running tests for: {', '.join(packages)}")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--group", type=int, required=True, help="Group number (1-based)"
    )
    parser.add_argument(
        "--total", type=int, required=True, help="Total number of groups"
    )
    args = parser.parse_args()

    all_packages = get_all_packages()
    group_packages = get_packages_for_group(all_packages, args.group, args.total)

    print(f"Group {args.group}/{args.total}: {len(group_packages)} packages")

    return run_tests(group_packages)


if __name__ == "__main__":
    sys.exit(main())
