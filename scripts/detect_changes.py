#!/usr/bin/env python3
"""Detect which packages changed in a PR and generate test matrix.

Usage:
    python detect_changes.py --base HEAD~1 --head HEAD --output-json
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Set


def run_git_command(args: List[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_changed_files(base: str, head: str) -> List[str]:
    """Get list of files changed between base and head commits."""
    output = run_git_command(["diff", "--name-only", f"{base}...{head}"])
    if not output:
        return []
    return output.split("\n")


def get_all_packages() -> List[str]:
    """Get all packages in the monorepo."""
    packages_dir = Path("packages")
    if not packages_dir.exists():
        return []
    return sorted(
        [
            d.name
            for d in packages_dir.iterdir()
            if d.is_dir() and (d / "pyproject.toml").exists()
        ]
    )


def get_package_dependencies(package: str) -> Set[str]:
    """Get workspace dependencies for a package."""
    pyproject_path = Path(f"packages/{package}/pyproject.toml")
    if not pyproject_path.exists():
        return set()

    deps = set()
    content = pyproject_path.read_text()

    # Simple parsing: look for workspace = true in dependencies
    # This is a simplified version - in production, use toml library
    import re

    # Match patterns like: package = { workspace = true }
    workspace_deps = re.findall(
        r"^([a-zA-Z0-9_-]+)\s*=\s*\{\s*workspace\s*=\s*true\s*\}", content, re.MULTILINE
    )
    deps.update(workspace_deps)

    return deps


def build_dependency_graph(packages: List[str]) -> Dict[str, Set[str]]:
    """Build a dependency graph of all packages."""
    graph = {}
    for pkg in packages:
        graph[pkg] = get_package_dependencies(pkg)
    return graph


def get_dependents(package: str, graph: Dict[str, Set[str]]) -> Set[str]:
    """Get all packages that depend on the given package."""
    dependents = set()
    for pkg, deps in graph.items():
        if package in deps:
            dependents.add(pkg)
            # Recursively get dependents
            dependents.update(get_dependents(pkg, graph))
    return dependents


def detect_changed_packages(
    changed_files: List[str], all_packages: List[str]
) -> List[str]:
    """Determine which packages need testing based on changed files.

    Rules:
    1. Root config changes -> test all packages
    2. Shared libs changes -> test all packages
    3. Tools changes -> test all packages
    4. Package file changes -> test that package + dependents
    5. No packages detected but Python files changed -> test all
    """
    changed_packages = set()

    # Check for global changes
    global_files = {
        "pyproject.toml",
        "uv.lock",
        "pytest.ini",
        ".github/workflows/ci.yml",
        "scripts/detect_changes.py",
        "scripts/partition_tests.py",
    }

    for file in changed_files:
        # Root config changes affect all packages
        if file in global_files or file.startswith("tools/"):
            print(
                f"Global file changed: {file} -> testing all packages", file=sys.stderr
            )
            return all_packages

        # Shared libs affect all packages
        if file.startswith("libs/"):
            print(
                f"Shared lib changed: {file} -> testing all packages", file=sys.stderr
            )
            return all_packages

        # Determine which package a file belongs to
        if file.startswith("packages/"):
            parts = file.split("/")
            if len(parts) >= 2:
                pkg_name = parts[1]
                if pkg_name in all_packages:
                    changed_packages.add(pkg_name)

    # If no packages detected but Python files changed, test all
    if not changed_packages:
        python_files_changed = any(f.endswith(".py") for f in changed_files)
        if python_files_changed:
            print(
                "Python files changed outside packages -> testing all", file=sys.stderr
            )
            return all_packages

    # Add dependents for changed packages
    graph = build_dependency_graph(all_packages)
    additional_packages = set()
    for pkg in changed_packages:
        dependents = get_dependents(pkg, graph)
        if dependents:
            print(
                f"Package {pkg} changed, adding dependents: {dependents}",
                file=sys.stderr,
            )
            additional_packages.update(dependents)

    changed_packages.update(additional_packages)

    return sorted(changed_packages)


def partition_packages(packages: List[str], max_jobs: int = 20) -> List[Dict[str, Any]]:
    """Partition packages into groups for parallel execution.

    Uses a simple round-robin distribution. In production, enhance with:
    - Historical test duration data
    - Longest Processing Time (LPT) algorithm
    - Package size/complexity heuristics
    """
    if not packages:
        return []

    num_packages = len(packages)

    # Determine number of groups
    # Aim for ~2-3 packages per group for optimal parallelization
    packages_per_group = 3
    num_groups = max(
        1, min(max_jobs, (num_packages + packages_per_group - 1) // packages_per_group)
    )

    # Distribute packages round-robin for better balance
    groups = [[] for _ in range(num_groups)]
    for i, pkg in enumerate(packages):
        groups[i % num_groups].append(pkg)

    # Build matrix
    matrix = []
    for i, group in enumerate(groups):
        if group:  # Skip empty groups
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
        description="Detect changed packages and generate test matrix"
    )
    parser.add_argument("--base", required=True, help="Base commit/branch")
    parser.add_argument("--head", required=True, help="Head commit/branch")
    parser.add_argument("--output-json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--max-jobs", type=int, default=20, help="Maximum number of parallel jobs"
    )
    args = parser.parse_args()

    # Get changed files
    changed_files = get_changed_files(args.base, args.head)
    print(f"Changed files ({len(changed_files)}):", file=sys.stderr)
    for f in changed_files[:10]:  # Show first 10
        print(f"  {f}", file=sys.stderr)
    if len(changed_files) > 10:
        print(f"  ... and {len(changed_files) - 10} more", file=sys.stderr)

    # Get all packages
    all_packages = get_all_packages()
    print(f"\nTotal packages: {len(all_packages)}", file=sys.stderr)

    # Detect changed packages
    changed_packages = detect_changed_packages(changed_files, all_packages)
    print(f"Packages to test: {changed_packages}", file=sys.stderr)

    # Partition into groups
    matrix = partition_packages(changed_packages, args.max_jobs)
    print(f"Matrix groups: {len(matrix)}", file=sys.stderr)
    for group in matrix:
        print(f"  {group['group_name']}: {group['packages']}", file=sys.stderr)

    # Output results
    if args.output_json:
        output = {
            "packages": changed_packages,
            "matrix": matrix,
            "any-python": str(bool(changed_packages)).lower(),
            "package-count": len(changed_packages),
        }
        print(json.dumps(output))

    # Set GitHub Actions outputs if running in CI
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"packages={json.dumps(changed_packages)}\n")
            f.write(f"matrix={json.dumps(matrix)}\n")
            f.write(f"any-python={str(bool(changed_packages)).lower()}\n")
            f.write(f"package-count={len(changed_packages)}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
