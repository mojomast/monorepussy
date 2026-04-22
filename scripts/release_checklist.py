#!/usr/bin/env python3
"""Release checklist validator.

Validates that a package is ready for release by checking:
1. CHANGELOG.md is updated
2. Tests pass
3. Version is bumped in pyproject.toml
4. No uncommitted changes (if running locally)

Usage:
    python release_checklist.py actuaryussy 1.2.3
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_changelog(package: str) -> tuple[bool, str]:
    """Ensure CHANGELOG.md exists and is updated."""
    changelog = Path(f"packages/{package}/CHANGELOG.md")

    if not changelog.exists():
        return False, f"CHANGELOG.md not found for {package}"

    # Check if changelog has content beyond header
    content = changelog.read_text().strip()
    lines = [l for l in content.split("\n") if l.strip()]

    if len(lines) <= 1:
        return False, f"CHANGELOG.md appears empty for {package}"

    return True, f"CHANGELOG.md present ({len(lines)} lines)"


def check_tests_pass(package: str) -> tuple[bool, str]:
    """Run tests for the package."""
    test_dir = Path(f"packages/{package}/tests")
    if not test_dir.exists():
        return True, "No tests directory (skipping)"

    result = subprocess.run(
        [
            "uv",
            "run",
            "--package",
            package,
            "pytest",
            "-x",
            f"packages/{package}/tests",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, "All tests pass"
    else:
        # Extract failure summary
        lines = result.stdout.split("\n") + result.stderr.split("\n")
        failures = [l for l in lines if "FAILED" in l or "ERROR" in l][:3]
        return False, f"Tests failed: {'; '.join(failures)}"


def check_version_bump(package: str, version: str) -> tuple[bool, str]:
    """Verify version is updated in pyproject.toml."""
    pyproject = Path(f"packages/{package}/pyproject.toml")

    if not pyproject.exists():
        return False, f"pyproject.toml not found for {package}"

    content = pyproject.read_text()

    # Check for version string
    version_line = f'version = "{version}"'
    if version_line in content:
        return True, f"Version bumped to {version}"

    # Try to find current version
    import re

    match = re.search(r'version = "([^"]+)"', content)
    if match:
        current = match.group(1)
        return False, f"Version is {current}, expected {version}"

    return False, "Version not found in pyproject.toml"


def check_git_clean() -> tuple[bool, str]:
    """Check if working directory is clean."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        return False, "Uncommitted changes detected"

    return True, "Working directory clean"


def check_documentation(package: str) -> tuple[bool, str]:
    """Check if README.md exists."""
    readme = Path(f"packages/{package}/README.md")

    if not readme.exists():
        return False, "README.md not found"

    return True, "README.md present"


def main():
    parser = argparse.ArgumentParser(
        description="Validate package is ready for release"
    )
    parser.add_argument("package", help="Package name")
    parser.add_argument("version", help="Target version")
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip test execution (faster)"
    )
    parser.add_argument(
        "--skip-git-check", action="store_true", help="Skip git clean check"
    )
    args = parser.parse_args()

    print(f"Running release checklist for {args.package} v{args.version}")
    print("=" * 60)

    checks = [
        ("Version bumped", lambda: check_version_bump(args.package, args.version)),
        ("CHANGELOG updated", lambda: check_changelog(args.package)),
        ("Documentation present", lambda: check_documentation(args.package)),
    ]

    if not args.skip_tests:
        checks.append(("Tests passing", lambda: check_tests_pass(args.package)))

    if not args.skip_git_check:
        checks.append(("Git clean", check_git_clean))

    all_passed = True
    results = []

    for name, check_fn in checks:
        print(f"\nChecking: {name}...", end=" ")
        try:
            passed, message = check_fn()
        except Exception as e:
            passed, message = False, f"Error: {e}"

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {message}")

        results.append((name, passed, message))
        if not passed:
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, passed, message in results:
        icon = " " if passed else ""
        print(f"{icon} {name}: {message}")

    if all_passed:
        print(f"\n {args.package} v{args.version} is ready for release!")
        return 0
    else:
        print(f"\n {args.package} v{args.version} is NOT ready for release.")
        print("Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
