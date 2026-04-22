# Ussyverse Monorepo CI/CD - Quick Reference

## Architecture Overview

```
PR/Push → Detect Changes → Lint → Typecheck → Test (Parallel) → Build → Report
                ↓              ↓         ↓           ↓
            [Matrix]       [ruff]    [mypy]   [pytest-xdist]
```

## Key Workflows

### CI (`.github/workflows/ci.yml`)
- **Triggers**: PR to main, push to main
- **Jobs**:
  1. `detect-changes` - Identifies which packages need testing
  2. `lint` - ruff check + format check (~10s)
  3. `typecheck` - mypy per changed package (~30s each)
  4. `test` - Parallel test execution with pytest-xdist (~3min)
  5. `coverage` - Aggregate coverage from all test jobs
  6. `build` - Build wheels for changed packages
  7. `integration-test` - Integration tests on main branch

### Release (`.github/workflows/release.yml`)
- **Triggers**: Tag push (`*/v*`), manual dispatch
- **Features**:
  - Package-specific releases: `actuaryussy/v1.2.3`
  - Monorepo-wide releases: `v2024.03.15`
  - Dry-run support
  - OIDC PyPI publishing (no tokens)

### Nightly (`.github/workflows/nightly.yml`)
- **Schedule**: 2 AM UTC daily
- **Purpose**: Full test suite regardless of changes
- **Jobs**: Test all packages + full lint + typecheck + build

## Scripts

### `scripts/detect_changes.py`
Detects which packages changed and generates test matrix.

```bash
# Usage
python scripts/detect_changes.py --base HEAD~1 --head HEAD --output-json

# Outputs
# - packages: JSON array of changed packages
# - matrix: Partitioned groups for parallel execution
# - any-python: Whether any Python files changed
```

### `scripts/partition_tests.py`
Partitions packages into balanced groups using LPT algorithm.

```bash
# Usage
python scripts/partition_tests.py \
  --packages '["pkg1", "pkg2", "pkg3"]' \
  --groups 5 \
  --algorithm lpt
```

### `scripts/release_checklist.py`
Validates package readiness for release.

```bash
# Usage
python scripts/release_checklist.py actuaryussy 1.2.3
```

## Caching Strategy

### Three-Tier Cache

| Tier | Location | Content | Key |
|------|----------|---------|-----|
| UV Global | `~/.cache/uv` | Wheels, packages | `uv-{os}-{lock-hash}` |
| Venv | `packages/*/.venv` | Installed deps | `venv-{pkg}-{pyver}-{deps-hash}` |
| Test | `.pytest_cache/` | Test artifacts | `test-{pkg}-{files-hash}` |

### Cache Hit Rates (Expected)
- UV Global: ~99%
- Venv: ~95%
- Test artifacts: ~90%

## Timing Budget

| Phase | Target | Strategy |
|-------|--------|----------|
| Setup | 30s | Cached uv, shallow clone |
| Lint | 10s | ruff (parallel) |
| Typecheck | 30s | mypy incremental |
| Test | 180s | 20 parallel runners × 4 workers |
| Build | 30s | Only changed packages |
| **Total** | **~300s** | **< 5 minutes** |

## Commands

### Development

```bash
# Install all dependencies
uv sync

# Run tests for specific package
uv run --package actuaryussy pytest packages/actuaryussy/tests

# Run all tests
uv run pytest packages/ -n auto

# Run with coverage
uv run pytest packages/ --cov=packages --cov-report=html

# Lint all packages
uv run ruff check packages/
uv run ruff format packages/

# Typecheck specific package
uv run --package actuaryussy mypy packages/actuaryussy/src
```

### Release

```bash
# Tag-based release
git tag actuaryussy/v1.2.3
git push origin actuaryussy/v1.2.3

# Manual release (via GitHub UI)
# Actions → Release → Run workflow
# Enter package name and version
```

## Package Structure

```
packages/{name}/
├── pyproject.toml          # Package config + dependencies
├── src/
│   └── {name}/
│       ├── __init__.py
│       └── ...
├── tests/
│   ├── __init__.py
│   ├── test_module1.py
│   └── test_module2.py
└── CHANGELOG.md            # Required for releases
```

### Example pyproject.toml

```toml
[project]
name = "actuaryussy"
version = "0.1.0"
description = "Actuarial vulnerability risk quantification"
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.24",
    "ussy-core",  # Workspace dependency
]

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-xdist>=3.5",
    "pytest-cov>=4.1",
]

[project.scripts]
actuary = "actuaryussy.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
ussy-core = { workspace = true }
```

## Troubleshooting

### Tests are slow
- Check pytest-xdist is installed: `uv run pytest -n auto`
- Verify cache is working in CI logs
- Use `--durations=10` to find slow tests

### Cache misses
- Check cache key matches in logs
- Verify `uv.lock` is committed
- Clear cache via Actions tab if needed

### Import errors
- Ensure `PYTHONPATH` includes `packages/`
- Check workspace dependencies in `pyproject.toml`
- Run `uv sync` to update lockfile

### Release fails
- Check `release_checklist.py` passes locally
- Verify version is bumped in `pyproject.toml`
- Ensure CHANGELOG.md exists and is updated
