# Ussyverse Monorepo CI/CD Architecture

## Executive Summary

This document designs a complete CI/CD system for consolidating 63 repositories from github.com/mojomast into a Python monorepo (the "ussyverse" ecosystem), reducing to ~50 packages. The design targets a **<5 minute full test suite** using modern tooling (uv, pytest-xdist, GitHub Actions matrix with dynamic partitioning).

---

## 1. CI/CD Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GITHUB ACTIONS WORKFLOWS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   TRIGGER   │───▶│   CHANGE    │───▶│   MATRIX    │───▶│   TEST      │  │
│  │   (PR/Push) │    │ DETECTION   │    │ GENERATION  │    │ PARTITION   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     PARALLEL EXECUTION LAYER                        │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ Runner  │ │ Runner  │ │ Runner  │ │ Runner  │ │ Runner  │       │   │
│  │  │  #1     │ │  #2     │ │  #3     │ │  #4     │ │  #N     │       │   │
│  │  │(pkg 1-5)│ │(pkg 6-10)│ │(pkg11-15)│ │(pkg16-20)│ │(rest)  │       │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │   │
│  │       └───────────┴───────────┴───────────┴───────────┘              │   │
│  │                           │                                          │   │
│  │                           ▼                                          │   │
│  │                    ┌─────────────┐                                   │   │
│  │                    │   RESULT    │                                   │   │
│  │                    │  AGGREGATOR │                                   │   │
│  │                    └──────┬──────┘                                   │   │
│  │                           │                                          │   │
│  └───────────────────────────┼──────────────────────────────────────────┘   │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      POST-TEST PIPELINE                             │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │   │
│  │  │    LINT     │───▶│  TYPECHECK  │───▶│   BUILD     │             │   │
│  │  │   (ruff)    │    │   (mypy)    │    │  (wheels)   │             │   │
│  │  └─────────────┘    └─────────────┘    └──────┬──────┘             │   │
│  │                                               │                     │   │
│  │                                               ▼                     │   │
│  │                                        ┌─────────────┐              │   │
│  │                                        │   PUBLISH   │              │   │
│  │                                        │   (PyPI)    │              │   │
│  │                                        └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CACHING INFRASTRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   UV GLOBAL     │  │   VENV PER      │  │   TEST ARTIFACT │             │
│  │   CACHE         │  │   PACKAGE       │  │   CACHE         │             │
│  │                 │  │                 │  │                 │             │
│  │ • pip packages  │  │ • .venv/ per    │  │ • .pytest_cache │             │
│  │ • wheels        │  │   package       │  │ • coverage data │             │
│  │ • build artifacts│ │ • editable      │  │ • mypy cache    │             │
│  │                 │  │   installs      │  │                 │             │
│  │ Key: uv-lock-   │  │ Key: venv-{pkg}-│  │ Key: test-{pkg}-│             │
│  │   {hash}        │  │   {pyver}-{hash}│  │   {hash}        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Monorepo Structure

```
ussyverse/
├── pyproject.toml              # Workspace root configuration
├── uv.lock                     # Unified lockfile for all packages
├── .github/
│   └── workflows/
│       ├── ci.yml              # Main CI workflow
│       ├── release.yml         # Release automation
│       └── nightly.yml         # Nightly full suite
├── scripts/
│   ├── detect_changes.py       # Change detection script
│   ├── partition_tests.py      # Test partitioning logic
│   └── publish_package.py      # Individual package publishing
├── packages/                   # All 50 packages
│   ├── actuaryussy/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── actuaryussy/
│   │   └── tests/
│   ├── acumenussy/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── acumenussy/
│   │   └── tests/
│   ├── alembicussy/
│   ├── aquiferussy/
│   ├── assayussy/
│   ├── ... (46 more)
│   └── swarmussy/
├── libs/                       # Shared internal libraries (if any)
│   └── ussy-core/
│       ├── pyproject.toml
│       └── src/
└── tools/                      # Development tools
    ├── conftest.py             # Shared pytest fixtures
    └── pytest.ini              # Root pytest configuration
```

### Root pyproject.toml

```toml
[project]
name = "ussyverse"
version = "0.1.0"
description = "The Ussyverse - A constellation of Python packages"
requires-python = ">=3.10"

[tool.uv.workspace]
members = ["packages/*", "libs/*"]

[tool.uv.sources]
# Internal dependencies resolved from workspace
ussy-core = { workspace = true }

[tool.pytest.ini_options]
testpaths = ["packages"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-ra -q --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.ruff]
target-version = "py310"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

## 3. GitHub Actions Workflow Design

### 3.1 Main CI Workflow (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ─────────────────────────────────────────────────────────
  # STAGE 1: Detect Changes
  # ─────────────────────────────────────────────────────────
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.changes.outputs.packages }}
      matrix: ${{ steps.changes.outputs.matrix }}
      any-python: ${{ steps.changes.outputs.any-python }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect changed packages
        id: changes
        run: |
          python scripts/detect_changes.py \
            --base ${{ github.event.pull_request.base.sha || 'HEAD~1' }} \
            --head ${{ github.sha }} \
            --output-json

  # ─────────────────────────────────────────────────────────
  # STAGE 2: Lint & Typecheck (Fast feedback)
  # ─────────────────────────────────────────────────────────
  lint:
    needs: detect-changes
    if: ${{ needs.detect-changes.outputs.any-python == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true

      - name: Run ruff check
        run: uv run ruff check packages/

      - name: Run ruff format check
        run: uv run ruff format --check packages/

  typecheck:
    needs: detect-changes
    if: ${{ needs.detect-changes.outputs.any-python == 'true' }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJson(needs.detect-changes.outputs.packages) }}
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true

      - name: Typecheck ${{ matrix.package }}
        run: |
          cd packages/${{ matrix.package }}
          uv run --package ${{ matrix.package }} mypy src/

  # ─────────────────────────────────────────────────────────
  # STAGE 3: Test Matrix (Parallel Execution)
  # ─────────────────────────────────────────────────────────
  test:
    needs: [detect-changes, lint]
    if: ${{ needs.detect-changes.outputs.packages != '[]' }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true

      - name: Restore uv cache
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/uv
            ~/.local/share/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Sync dependencies
        run: uv sync --frozen

      - name: Run tests for ${{ matrix.group_name }}
        run: |
          uv run pytest \
            -xvs \
            --tb=short \
            -n auto \
            --dist=loadgroup \
            ${{ matrix.test_paths }}
        env:
          PYTHONPATH: ${{ github.workspace }}/packages

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: ${{ matrix.group_name }}

  # ─────────────────────────────────────────────────────────
  # STAGE 4: Integration Tests (Full suite on main)
  # ─────────────────────────────────────────────────────────
  integration-test:
    needs: [detect-changes, test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true

      - name: Run integration tests
        run: |
          uv run pytest \
            -m integration \
            --tb=short \
            -n 4

  # ─────────────────────────────────────────────────────────
  # STAGE 5: Build Verification
  # ─────────────────────────────────────────────────────────
  build:
    needs: [detect-changes, test]
    if: ${{ needs.detect-changes.outputs.packages != '[]' }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJson(needs.detect-changes.outputs.packages) }}
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"
          enable-cache: true

      - name: Build ${{ matrix.package }}
        run: |
          cd packages/${{ matrix.package }}
          uv build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 7
```

### 3.2 Change Detection Script (`scripts/detect_changes.py`)

```python
#!/usr/bin/env python3
"""Detect which packages changed in a PR and generate test matrix."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any


def get_changed_files(base: str, head: str) -> List[str]:
    """Get list of files changed between base and head commits."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().split("\n")


def get_all_packages() -> List[str]:
    """Get all packages in the monorepo."""
    packages_dir = Path("packages")
    return [d.name for d in packages_dir.iterdir() if d.is_dir() and (d / "pyproject.toml").exists()]


def detect_changed_packages(changed_files: List[str]) -> List[str]:
    """Determine which packages need testing based on changed files."""
    packages = get_all_packages()
    changed_packages = set()
    
    for file in changed_files:
        # Root config changes affect all packages
        if file in ["pyproject.toml", "uv.lock", "pytest.ini"]:
            return packages  # Test everything
        
        # Shared libs affect all packages
        if file.startswith("libs/"):
            return packages
        
        # Tools affect all packages
        if file.startswith("tools/"):
            return packages
        
        # Determine which package a file belongs to
        if file.startswith("packages/"):
            pkg_name = file.split("/")[1]
            if pkg_name in packages:
                changed_packages.add(pkg_name)
    
    # If no packages detected but Python files changed, test all
    if not changed_packages and any(f.endswith(".py") for f in changed_files):
        return packages
    
    return sorted(changed_packages)


def partition_packages(packages: List[str], max_jobs: int = 20) -> List[Dict[str, Any]]:
    """Partition packages into groups for parallel execution.
    
    Strategy: Group packages by estimated test duration to balance load.
    """
    if not packages:
        return []
    
    # Simple partitioning: distribute evenly
    # In production, you'd use historical timing data
    num_packages = len(packages)
    num_groups = min(max_jobs, num_packages)
    
    groups = []
    packages_per_group = max(1, num_packages // num_groups)
    
    for i in range(0, num_packages, packages_per_group):
        group = packages[i:i + packages_per_group]
        test_paths = " ".join(f"packages/{pkg}/tests" for pkg in group)
        groups.append({
            "group_name": f"group-{len(groups) + 1}",
            "packages": group,
            "test_paths": test_paths,
        })
    
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output-json", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=20)
    args = parser.parse_args()
    
    changed_files = get_changed_files(args.base, args.head)
    changed_packages = detect_changed_packages(changed_files)
    matrix = partition_packages(changed_packages, args.max_jobs)
    
    if args.output_json:
        output = {
            "packages": changed_packages,
            "matrix": matrix,
            "any-python": str(bool(changed_packages)).lower(),
        }
        print(json.dumps(output))
    else:
        print(f"Changed packages: {changed_packages}")
        print(f"Matrix groups: {len(matrix)}")
        for group in matrix:
            print(f"  {group['group_name']}: {group['packages']}")
    
    # Set GitHub Actions outputs
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"packages={json.dumps(changed_packages)}\n")
            f.write(f"matrix={json.dumps(matrix)}\n")
            f.write(f"any-python={str(bool(changed_packages)).lower()}\n")


if __name__ == "__main__":
    import os
    main()
```

### 3.3 Release Workflow (`.github/workflows/release.yml`)

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
      - "*/v*"  # Package-specific tags: actuaryussy/v1.2.3
  workflow_dispatch:
    inputs:
      package:
        description: "Package to release"
        required: true
        type: choice
        options: # Dynamically populated or maintained list
          - actuaryussy
          - acumenussy
          - swarmussy
      version:
        description: "Version to release (e.g., 1.2.3)"
        required: true
        type: string

jobs:
  determine-package:
    runs-on: ubuntu-latest
    outputs:
      package: ${{ steps.parse.outputs.package }}
      version: ${{ steps.parse.outputs.version }}
    steps:
      - name: Parse tag
        id: parse
        run: |
          if [[ "${{ github.ref }}" == refs/tags/* ]]; then
            TAG=${GITHUB_REF#refs/tags/}
            if [[ "$TAG" == */* ]]; then
              # Format: package/v1.2.3
              PACKAGE=${TAG%/*}
              VERSION=${TAG#*/v}
            else
              # Format: v1.2.3 (root release)
              PACKAGE="all"
              VERSION=${TAG#v}
            fi
          else
            PACKAGE="${{ github.event.inputs.package }}"
            VERSION="${{ github.event.inputs.version }}"
          fi
          echo "package=$PACKAGE" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT

  release:
    needs: determine-package
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # For OIDC PyPI publishing
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "0.5.x"

      - name: Build and publish
        run: |
          if [ "${{ needs.determine-package.outputs.package }}" == "all" ]; then
            # Release all changed packages
            for pkg in packages/*/; do
              cd "$pkg"
              uv build
              uv publish
              cd -
            done
          else
            cd "packages/${{ needs.determine-package.outputs.package }}"
            # Update version
            sed -i "s/^version = .*/version = \"${{ needs.determine-package.outputs.version }}\"/" pyproject.toml
            uv build
            uv publish
          fi
```

---

## 4. Caching Strategy

### 4.1 Three-Tier Caching Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIER 1: UV GLOBAL CACHE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Location: ~/.cache/uv                                          │
│  Content:                                                       │
│    • Downloaded wheels                                          │
│    • Built wheels                                               │
│    • Git repositories                                           │
│  Cache Key: uv-{os}-{uv.lock hash}                              │
│  Size: ~2-5 GB (shared across all packages)                     │
│  TTL: 7 days (GitHub Actions cache)                             │
│                                                                 │
│  Benefits:                                                      │
│    • 10-100x faster than pip                                    │
│    • Deduplicates shared dependencies                           │
│    • Survives between CI runs                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TIER 2: VIRTUAL ENVIRONMENT CACHE              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Location: packages/{pkg}/.venv                                 │
│  Content:                                                       │
│    • Installed package + dependencies                           │
│    • Editable install of workspace deps                         │
│  Cache Key: venv-{pkg}-{python-version}-{deps-hash}             │
│  Size: ~50-200 MB per package                                   │
│  TTL: 1 day                                                     │
│                                                                 │
│  Strategy:                                                      │
│    • Cache .venv directories per package                        │
│    • Use uv sync --frozen for reproducibility                   │
│    • Invalidate when pyproject.toml or uv.lock changes          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TIER 3: TEST ARTIFACT CACHE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Location: .pytest_cache/, .mypy_cache/                         │
│  Content:                                                       │
│    • pytest cache (lastfailed, nodeids)                         │
│    • mypy incremental cache                                     │
│    • Coverage data                                              │
│  Cache Key: test-{pkg}-{test-files-hash}                        │
│  Size: ~10-50 MB per package                                    │
│  TTL: 1 day                                                     │
│                                                                 │
│  Benefits:                                                      │
│    • Incremental mypy (2-5x speedup)                            │
│    --ff (only failed tests)                                     │
│    • Coverage merge across parallel jobs                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Cache Implementation in GitHub Actions

```yaml
# Add to each job that needs dependencies

- name: Cache uv global
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      ~/.local/share/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}-
      uv-${{ runner.os }}-

- name: Cache virtual environments
  uses: actions/cache@v4
  with:
    path: |
      packages/*/.venv
    key: venvs-${{ runner.os }}-${{ hashFiles('uv.lock') }}-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      venvs-${{ runner.os }}-${{ hashFiles('uv.lock') }}-
      venvs-${{ runner.os }}-

- name: Cache test artifacts
  uses: actions/cache@v4
  with:
    path: |
      .pytest_cache
      .mypy_cache
      .coverage
    key: test-artifacts-${{ runner.os }}-${{ github.run_id }}
    restore-keys: |
      test-artifacts-${{ runner.os }}-
```

### 4.3 Cache Invalidation Strategy

| Cache Tier | Invalidation Trigger | Strategy |
|-----------|---------------------|----------|
| UV Global | `uv.lock` changes | Hash-based key |
| Venv per package | `pyproject.toml` changes | Per-package hash |
| Test artifacts | Test file changes | Test file hash |
| Manual | Emergency clear | Workflow dispatch with `clear-cache` input |

---

## 5. Parallel Test Execution Strategy

### 5.1 Multi-Level Parallelism

```
Level 1: Job Parallelism (GitHub Actions matrix)
  └── 20 concurrent runners max
  └── Each runner handles 2-3 packages
  └── Total: 50 packages / 20 runners = ~3 packages per runner

Level 2: Process Parallelism (pytest-xdist)
  └── Each runner uses -n auto (CPU cores)
  └── Typical: 4 vCPU = 4 parallel pytest processes
  └── Total: 20 runners × 4 processes = 80 concurrent test processes

Level 3: Test Isolation
  └── Each package tests in isolated venv
  └── No shared state between packages
  └── Temporary directories for file operations
```

### 5.2 Test Isolation Design

```python
# tools/conftest.py - Shared fixtures for all packages

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="function")
def isolated_tmp_path():
    """Provide an isolated temporary directory per test."""
    path = Path(tempfile.mkdtemp(prefix="ussytest_"))
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def package_venv():
    """Ensure each package's tests run in its own venv context."""
    # This is handled by uv run --package <pkg>
    pass


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables that might leak between tests."""
    original_env = dict(os.environ)
    yield
    # Restore original environment
    for key in list(os.environ.keys()):
        if key not in original_env:
            del os.environ[key]
    os.environ.update(original_env)
```

### 5.3 Test Partitioning Algorithm

```python
# scripts/partition_tests.py

import json
from pathlib import Path
from typing import List, Dict
import subprocess


def get_test_duration_history() -> Dict[str, float]:
    """Load historical test durations from cache."""
    cache_file = Path(".pytest_cache/v/cache/durations")
    if cache_file.exists():
        # Parse durations file
        return {}
    return {}


def partition_by_timing(packages: List[str], num_groups: int) -> List[Dict]:
    """Partition packages using historical timing data for optimal balance.
    
    Uses Longest Processing Time (LPT) algorithm:
    1. Sort packages by estimated duration (longest first)
    2. Assign each package to the group with the shortest total time
    """
    durations = get_test_duration_history()
    
    # Default duration for unknown packages
    default_duration = 30.0  # seconds
    
    # Sort by duration descending
    sorted_packages = sorted(
        packages,
        key=lambda p: durations.get(p, default_duration),
        reverse=True
    )
    
    # Initialize groups
    groups = [[] for _ in range(num_groups)]
    group_times = [0.0] * num_groups
    
    # LPT assignment
    for package in sorted_packages:
        duration = durations.get(package, default_duration)
        # Find group with minimum total time
        min_group = group_times.index(min(group_times))
        groups[min_group].append(package)
        group_times[min_group] += duration
    
    # Build matrix
    matrix = []
    for i, group in enumerate(groups):
        if group:
            matrix.append({
                "group_name": f"group-{i + 1}",
                "packages": group,
                "test_paths": " ".join(f"packages/{pkg}/tests" for pkg in group),
                "estimated_duration": group_times[i],
            })
    
    return matrix
```

---

## 6. Release Automation Design

### 6.1 Versioning Strategy

```
┌─────────────────────────────────────────────────────────────┐
│              SEMANTIC VERSIONING PER PACKAGE                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Format: MAJOR.MINOR.PATCH                                  │
│                                                             │
│  actuaryussy/v1.2.3   → Package-specific tag               │
│  v2024.03.15         → Monorepo-wide snapshot              │
│                                                             │
│  Rules:                                                     │
│    • Each package versions independently                    │
│    • Breaking changes bump MAJOR                            │
│    • Features bump MINOR                                    │
│    • Fixes bump PATCH                                       │
│    • Tags trigger automated release                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Release Workflow

```yaml
# .github/workflows/release.yml (simplified)

name: Release Package

on:
  push:
    tags:
      - "*/v*"  # actuaryussy/v1.2.3

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Parse tag
        id: parse
        run: |
          TAG=${GITHUB_REF#refs/tags/}
          PACKAGE=${TAG%/*}
          VERSION=${TAG#*/v}
          echo "package=$PACKAGE" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - uses: astral-sh/setup-uv@v3
      
      - name: Update version
        run: |
          cd packages/${{ steps.parse.outputs.package }}
          # Update version in pyproject.toml
          sed -i 's/^version = .*/version = "${{ steps.parse.outputs.version }}"/' pyproject.toml
      
      - name: Build and publish
        run: |
          cd packages/${{ steps.parse.outputs.package }}
          uv build
          uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

### 6.3 Release Checklist Automation

```python
# scripts/release_checklist.py

import subprocess
import sys
from pathlib import Path


def check_changelog(package: str) -> bool:
    """Ensure CHANGELOG.md is updated."""
    changelog = Path(f"packages/{package}/CHANGELOG.md")
    return changelog.exists()


def check_tests_pass(package: str) -> bool:
    """Run tests before release."""
    result = subprocess.run(
        ["uv", "run", "--package", package, "pytest", "-x"],
        capture_output=True,
    )
    return result.returncode == 0


def check_version_bump(package: str, version: str) -> bool:
    """Verify version is updated."""
    pyproject = Path(f"packages/{package}/pyproject.toml")
    content = pyproject.read_text()
    return f'version = "{version}"' in content


def main():
    package = sys.argv[1]
    version = sys.argv[2]
    
    checks = [
        ("Changelog updated", check_changelog(package)),
        ("Tests passing", check_tests_pass(package)),
        ("Version bumped", check_version_bump(package, version)),
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        if not passed:
            all_passed = False
    
    sys.exit(0 if all_passed else 1)
```

---

## 7. Change Detection Strategy

### 7.1 Detection Rules

```python
# Pseudocode for change detection

def should_test_package(package: str, changed_files: List[str]) -> bool:
    """Determine if a package needs testing."""
    
    # Always test if root config changes
    if any(f in ["pyproject.toml", "uv.lock", "pytest.ini"] for f in changed_files):
        return True
    
    # Always test if shared libs change
    if any(f.startswith("libs/") for f in changed_files):
        return True
    
    # Test if package's own files change
    if any(f.startswith(f"packages/{package}/") for f in changed_files):
        return True
    
    # Test if dependency package changes
    deps = get_package_dependencies(package)
    for dep in deps:
        if any(f.startswith(f"packages/{dep}/") for f in changed_files):
            return True
    
    return False
```

### 7.2 Dependency Graph

```
# Build dependency graph from pyproject.toml files
# Example:

actuaryussy
├── ussy-core (workspace)
└── numpy (external)

swarmussy
├── ussy-core (workspace)
├── actuaryussy (workspace)
└── requests (external)

# If ussy-core changes: test ALL packages that depend on it
# If actuaryussy changes: test actuaryussy + swarmussy
# If numpy changes: test only actuaryussy
```

---

## 8. Tool Recommendations

### 8.1 Primary Tool Stack

| Tool | Purpose | Justification |
|------|---------|---------------|
| **uv** | Package manager, venv, build | 10-100x faster than pip, workspace support, single tool replaces pip/pip-tools/virtualenv/twine |
| **pytest** | Test framework | Industry standard, rich plugin ecosystem, excellent parallelization support |
| **pytest-xdist** | Parallel test execution | `-n auto` for CPU-based parallelism, `loadgroup` for balanced distribution |
| **ruff** | Linting & formatting | 10-100x faster than flake8/black, unified tool, compatible rules |
| **mypy** | Type checking | Standard for Python type checking, incremental mode for speed |
| **GitHub Actions** | CI/CD platform | Native GitHub integration, matrix jobs, caching, OIDC for PyPI |

### 8.2 Tools Evaluated but Not Selected

| Tool | Reason for Exclusion |
|------|---------------------|
| **tox** | Redundant with uv workspaces and GHA matrices; adds complexity without benefit |
| **nox** | Similar to tox; session-based approach overkill for this use case |
| **Pants** | Heavyweight for 50 Python packages; learning curve too steep; better for polyglot repos |
| **Bazel** | Extreme overkill; designed for Google's scale; complex BUILD files |
| **Earthly** | No longer actively maintained; container-based adds overhead; GHA sufficient |
| **Poetry** | Slower than uv; no native workspace support; lockfile conflicts in monorepo |
| **Hatch** | Good alternative but uv is faster and simpler for this use case |

### 8.3 Why uv over alternatives

```
uv advantages for this monorepo:

1. WORKSPACE SUPPORT
   - Native Cargo-style workspaces
   - Single uv.lock for all 50 packages
   - Editable installs between workspace members

2. SPEED
   - 10-100x faster pip replacement
   - Parallel package installation
   - Global cache deduplicates dependencies

3. SIMPLICITY
   - Single tool: replaces pip + pip-tools + virtualenv + twine
   - No separate requirements.txt files
   - Universal lockfile (cross-platform)

4. CI/CD INTEGRATION
   - Official GitHub Action (astral-sh/setup-uv)
   - Excellent caching support
   - Fast cold starts

5. PUBLISHING
   - Built-in uv publish command
   - Supports PyPI, TestPyPI, private indexes
```

---

## 9. Test Strategy

### 9.1 Test Pyramid

```
                    ┌─────────┐
                    │   E2E   │  < 5% of tests
                    │  Tests  │  Run nightly only
                    │ (~20)   │  5-10 min total
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │Integration│  ~15% of tests
                    │  Tests   │  Run on main merge
                    │ (~200)   │  2-3 min per package
                    └────┬────┘
                         │
              ┌─────────┴──────────┐
              │     UNIT TESTS      │  ~80% of tests
              │    (~1000 total)    │  Run on every PR
              │  < 1 min per package │  Target: 3 min total
              └─────────────────────┘
```

### 9.2 Test Configuration per Package

```toml
# packages/{pkg}/pyproject.toml

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-xdist>=3.5",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.21",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers -n auto"
markers = [
    "unit: Fast unit tests (default)",
    "integration: Integration tests requiring external services",
    "slow: Tests taking > 1 second",
]
```

### 9.3 Running Tests

```bash
# Run all tests (full suite)
uv run pytest packages/ -n auto --dist=loadgroup

# Run tests for specific package
uv run --package actuaryussy pytest packages/actuaryussy/tests

# Run only unit tests (fast)
uv run pytest packages/ -m "not integration and not slow" -n auto

# Run with coverage
uv run pytest packages/ --cov=packages --cov-report=xml -n auto

# Run failed tests only (using cache)
uv run pytest packages/ --lf -n auto
```

---

## 10. Lint/Typecheck Automation

### 10.1 Ruff Configuration

```toml
# Root pyproject.toml

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### 10.2 MyPy Configuration

```toml
# Root pyproject.toml

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_ignores = true
show_error_codes = true

# Per-package overrides can be in packages/{pkg}/pyproject.toml
```

### 10.3 Pre-commit Hook (Optional)

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
        args: ["packages/"]
```

---

## 11. Artifact Building & PyPI Publishing

### 11.1 Build Strategy

```
Per-package builds:
  1. uv build (creates sdist + wheel)
  2. Store in packages/{pkg}/dist/
  3. Upload as GitHub artifact
  4. Publish to PyPI on release

Build optimization:
  - Only build changed packages in PR
  - Build all packages on main (for verification)
  - Use cibuildwheel for multi-platform wheels (if needed)
```

### 11.2 PyPI Publishing with OIDC

```yaml
# No long-lived tokens needed!
# Configure trusted publisher in PyPI:
#   - Repository: mojomast/ussyverse
#   - Workflow: release.yml
#   - Environment: pypi

permissions:
  id-token: write  # Required for OIDC

steps:
  - name: Publish to PyPI
    run: uv publish
    env:
      # No token needed - uses OIDC
```

### 11.3 Package Index Strategy

```
Publishing targets:
  1. PyPI (public packages)
     - Each package published independently
     - Namespace: ussy-{package} (if needed for uniqueness)
  
  2. GitHub Packages (optional)
     - For internal/private packages
     - Integrated with GitHub permissions
  
  3. Private Index (future)
     - If commercial packages added
     - Simple index via S3/GCS
```

---

## 12. Timing Budget Breakdown (< 5 Minutes)

### 12.1 Target Allocation

```
Total Budget: 5 minutes (300 seconds)

┌────────────────────────────────────────────────────────────┐
│ Phase                    │ Target    │ Strategy            │
├────────────────────────────────────────────────────────────┤
│ Checkout code            │ 5s        │ shallow clone       │
│ Setup uv                 │ 3s        │ cached binary       │
│ Restore caches           │ 10s       │ optimized keys      │
│ Install dependencies     │ 15s       │ uv sync (cached)    │
│ Detect changes           │ 5s        │ git diff only       │
├────────────────────────────────────────────────────────────┤
│ Lint (ruff)              │ 10s       │ parallel, cached    │
│ Typecheck (mypy)         │ 30s       │ incremental, cached │
├────────────────────────────────────────────────────────────┤
│ Test execution           │ 180s      │ 20 parallel runners │
│   - Collection           │ 10s       │ parallel discovery  │
│   - Unit tests           │ 120s      │ pytest-xdist        │
│   - Integration tests    │ 50s       │ selective run       │
├────────────────────────────────────────────────────────────┤
│ Build packages           │ 30s       │ only changed pkgs   │
│ Upload artifacts         │ 10s       │ async upload        │
├────────────────────────────────────────────────────────────┤
│ Report aggregation       │ 5s        │ parallel merge      │
├────────────────────────────────────────────────────────────┤
│ TOTAL                    │ ~300s     │                     │
│ (with 20 parallel jobs)  │           │                     │
└────────────────────────────────────────────────────────────┘
```

### 12.2 Achieving Sub-5-Minute Full Suite

```
Key strategies:

1. AGGRESSIVE PARALLELIZATION
   - 20 GitHub Actions runners
   - 4 pytest-xdist workers per runner
   - 80 concurrent test processes total

2. INTELLIGENT CHANGE DETECTION
   - Only test changed packages + dependents
   - Average PR touches 2-3 packages
   - Full suite runs on schedule (nightly)

3. LAYERED CACHING
   - uv global cache: ~99% hit rate
   - venv cache: ~95% hit rate
   - mypy incremental: ~90% speedup

4. FAST TOOLS
   - uv: 10-100x faster than pip
   - ruff: 10-100x faster than flake8
   - pytest-xdist: near-linear speedup

5. TEST OPTIMIZATION
   - Unit tests: < 1s each target
   - Mock external services
   - Parallel-safe fixtures
   - No sleep/wait in tests

6. RUNNER OPTIMIZATION
   - Ubuntu-latest (fastest)
   - No Docker overhead
   - Sufficient vCPU (4 cores)
```

### 12.3 Fallback for Full Suite

```yaml
# .github/workflows/nightly.yml
# Runs complete test suite regardless of changes

name: Nightly Full Suite

on:
  schedule:
    - cron: "0 2 * * *"  # 2 AM daily
  workflow_dispatch:

jobs:
  full-test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        # Test all 50 packages across 25 runners (2 each)
        group: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: |
          # Run tests for assigned packages
          python scripts/run_test_group.py --group ${{ matrix.group }} --total 25
```

---

## 13. CLI Entry Points Preservation

### 13.1 Console Scripts Configuration

```toml
# packages/{pkg}/pyproject.toml

[project.scripts]
actuary = "actuaryussy.cli:main"
acumen = "acumenussy.cli:main"
swarm = "swarmussy.cli:main"
# ... etc

# After installation:
# $ uv pip install actuaryussy
# $ actuary --help
```

### 13.2 Development Entry Points

```bash
# Run CLI tool from source without installation
uv run --package actuaryussy actuary --help

# Or with explicit module
uv run --package actuaryussy python -m actuaryussy --help
```

---

## 14. Migration Plan

### Phase 1: Foundation (Week 1)
- [ ] Create monorepo structure
- [ ] Set up root pyproject.toml with uv workspace
- [ ] Migrate 5 pilot packages
- [ ] Implement basic CI workflow

### Phase 2: Tooling (Week 2)
- [ ] Add change detection script
- [ ] Implement test partitioning
- [ ] Configure caching strategy
- [ ] Add lint/typecheck jobs

### Phase 3: Scale (Weeks 3-4)
- [ ] Migrate remaining packages
- [ ] Optimize test timing
- [ ] Tune parallelization
- [ ] Add integration test pipeline

### Phase 4: Release (Week 5)
- [ ] Set up PyPI trusted publishing
- [ ] Implement release automation
- [ ] Document release process
- [ ] Train team on new workflow

---

## 15. Summary

This design provides:

- **Scalability**: Handles 50+ packages with room to grow
- **Speed**: < 5 minute full suite via aggressive parallelization
- **Efficiency**: Only tests changed packages in PRs
- **Simplicity**: Single tool (uv) for most operations
- **Reliability**: Caching, isolation, and comprehensive testing
- **Automation**: Fully automated releases with OIDC

The key decisions are:
1. **uv workspaces** for monorepo management
2. **GitHub Actions matrix** with dynamic partitioning
3. **Three-tier caching** for optimal performance
4. **pytest-xdist** for process-level parallelism
5. **Change detection** to avoid unnecessary work

This architecture will serve the ussyverse ecosystem well as it grows and evolves.
