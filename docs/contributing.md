# Contributing to Ussyverse

Thank you for your interest in contributing to the ussyverse! This guide covers everything you need to get started developing in the monorepo.

---

## 1. Prerequisites

- **Python:** 3.11 or higher (3.12 recommended)
- **Git:** 2.30 or higher
- **uv:** Latest version ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Operating System:** Linux, macOS, or Windows with WSL

---

## 2. Development Setup

### 2.1 Quick Start (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/mojomast/ussyverse/main/scripts/bootstrap.sh | bash
```

This script:
1. Clones the repository
2. Installs the correct Python version via uv
3. Syncs all dependencies
4. Runs the test suite to verify your setup

### 2.2 Manual Setup

```bash
# 1. Clone the repository
git clone https://github.com/mojomast/ussyverse.git
cd ussyverse

# 2. Install Python 3.11 (if not already installed)
uv python install 3.11

# 3. Sync all dependencies
uv sync --extra all --group dev

# 4. Verify setup
uv run pytest --version
uv run ruff --version
uv run mypy --version
```

### 2.3 IDE Setup

**VS Code:**
- Install the Python extension
- Set Python interpreter to `.venv/bin/python`
- Enable Ruff and MyPy linting

**PyCharm:**
- Open the project root
- Set Project Interpreter to the `.venv` virtual environment
- Enable Mypy and Ruff under Settings → Tools

---

## 3. Development Workflow

### 3.1 Branch Naming

```
feature/ussy-triage-add-json-output
bugfix/ussy-calibre-fix-coverage-calculation
docs/update-migration-guide
refactor/ussy-core-extract-logging
```

### 3.2 Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(ussy-triage): add SARIF output format
fix(ussy-calibre): correct precision calculation for edge cases
docs: update architecture diagram
test(ussy-steno): add benchmark for large repos
refactor(ussy-core): extract path utilities into dedicated module
```

### 3.3 Pull Request Process

1. **Create a branch** from `main`
2. **Make your changes** with tests
3. **Run local checks:**
   ```bash
   uv run ruff check .          # Lint
   uv run ruff format .          # Format
   uv run mypy packages/         # Type check
   uv run pytest                 # Tests
   ```
4. **Push and open a PR** with:
   - Clear description of changes
   - Link to related issue (if any)
   - Screenshots/logs for UI or CLI changes
5. **Wait for CI** — all checks must pass
6. **Request review** from at least one maintainer
7. **Merge** once approved (squash merge preferred)

---

## 4. Running Tests

### 4.1 Full Test Suite

```bash
# From repository root — runs all tests across all packages
uv run pytest

# With coverage report
uv run pytest --cov=packages --cov-report=html

# Parallel execution (recommended for local development)
uv run pytest -n auto
```

**Target time:** Full suite should complete in under 5 minutes.

### 4.2 Package-Specific Tests

```bash
# Run tests for a specific package
uv run --package ussy-triage pytest packages/tools/triage/ussy-triage/

# Run tests for a specific test file
uv run pytest packages/tools/triage/ussy-triage/tests/test_cli.py

# Run with verbose output
uv run pytest packages/tools/triage/ussy-triage/ -v
```

### 4.3 Test Isolation

Every package must have tests that pass:
- **In isolation:** `uv run --package ussy-triage pytest`
- **In full suite:** `uv run pytest` (from root)

This ensures no hidden cross-package dependencies.

### 4.4 Writing Tests

- Use `pytest` fixtures for setup/teardown
- Place shared fixtures in `conftest.py`
- Mock external services (network, filesystem) when possible
- Aim for >80% coverage on new code
- Name tests descriptively: `test_calculate_precision_returns_correct_value_for_valid_input`

---

## 5. Adding a New Package

### 5.1 When to Add a New Package

Add a new package when:
- The tool has a distinct domain and user base
- It needs independent versioning and release cycles
- It introduces new external dependencies not used by existing tools

Do **not** add a new package when:
- The functionality fits within an existing tool as a subcommand
- It shares >80% of its code with an existing tool

### 5.2 Package Template

```bash
# Use the scaffolding script
./scripts/scaffold-package.sh ussy-mytool packages/tools/category/
```

This creates:
```
packages/tools/category/ussy-mytool/
├── pyproject.toml
├── README.md
├── src/
│   └── ussy_mytool/
│       ├── __init__.py
│       ├── cli.py
│       └── core.py
└── tests/
    ├── __init__.py
    ├── test_cli.py
    └── test_core.py
```

### 5.3 Required pyproject.toml Fields

```toml
[project]
name = "ussy-mytool"
version = "0.1.0"
description = "Brief description of what this tool does"
requires-python = ">=3.11"
dependencies = [
    "ussy-core",  # if needed
]

[project.scripts]
ussy-mytool = "ussy_mytool.cli:main"

[project.optional-dependencies]
# Only if you need external deps beyond stdlib

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 5.4 Registration Checklist

- [ ] Package placed in correct `packages/` subdirectory
- [ ] `pyproject.toml` has correct metadata and entry points
- [ ] README.md includes install instructions and usage examples
- [ ] Tests pass in isolation: `uv run --package ussy-mytool pytest`
- [ ] Tests pass in full suite: `uv run pytest`
- [ ] Added to root README.md package index
- [ ] Documentation updated (if applicable)
- [ ] CI passes on your PR

---

## 6. Coding Standards

### 6.1 Style Guide

- **Formatter:** `ruff format` (Black-compatible)
- **Line length:** 100 characters
- **Import style:** `isort` profile (enforced by ruff)
- **Docstrings:** Google style (enforced by ruff pydocstyle rules)

### 6.2 Type Hints

- All new code must have type hints
- Use `from __future__ import annotations` for forward references
- Run `mypy` before committing: `uv run mypy packages/`

### 6.3 Error Handling

- Use custom exceptions in `ussy_core.exceptions`
- Catch exceptions at CLI boundaries, not in library code
- Provide actionable error messages

### 6.4 Logging

- Use `ussy_core.logging.get_logger(__name__)` for all logging
- Log levels: DEBUG (internal), INFO (user-facing progress), WARNING (recoverable), ERROR (fatal)
- Never log secrets or sensitive data

### 6.5 CLI Design

- Use `ussy-cli` for consistent argument parsing and output
- Support `--json` for machine-readable output
- Support `--no-color` for piping
- Return appropriate exit codes (0 = success, 1 = general error, 2 = invalid usage, 3 = tool-specific error)

---

## 7. Shared Libraries

### 7.1 Using Shared Libraries

```python
from ussy_core import config, logging
from ussy_cli import parser, output
from ussy_git import repository
```

Add to your `pyproject.toml`:
```toml
dependencies = [
    "ussy-core",
    "ussy-cli",
]
```

### 7.2 Contributing to Shared Libraries

Shared libraries affect all packages. Changes require:
- **Backward compatibility:** All existing consumers must continue to work
- **Tests:** Comprehensive tests for new functionality
- **Documentation:** Update docstrings and architecture docs
- **Review:** Approval from 2+ maintainers

---

## 8. Documentation

### 8.1 Package README

Every package must have a `README.md` with:
- Description and purpose
- Installation instructions
- Usage examples
- Configuration options
- Link to full documentation

### 8.2 API Documentation

API docs are auto-generated from docstrings using `mkdocstrings`. Ensure your docstrings follow Google style:

```python
def analyze_repository(path: Path, depth: int = 3) -> Report:
    """Analyze a repository for code quality issues.
    
    Args:
        path: Path to the repository root.
        depth: Maximum recursion depth for directory traversal.
    
    Returns:
        A Report object containing all findings.
    
    Raises:
        RepositoryNotFoundError: If the path is not a valid git repository.
    """
```

### 8.3 Building Documentation Locally

```bash
# Serve docs with live reload
uv run mkdocs serve

# Build static site
uv run mkdocs build

# Deploy (maintainers only)
uv run mkdocs gh-deploy
```

---

## 9. Getting Help

- **Questions:** Open a [GitHub Discussion](https://github.com/mojomast/ussyverse/discussions)
- **Bugs:** Open a [GitHub Issue](https://github.com/mojomast/ussyverse/issues) with reproduction steps
- **Security:** Email security@mojomast.dev (do not open public issues)
- **Chat:** #ussyverse-dev on Slack (invite link in repository description)

---

## 10. Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

---

---

**Related Documents:**
- [Architecture](architecture.md)
- [Migration Guide](migration-guide.md)
- [ADRs](adr/index.md)

*Document Version: 1.0*
*Last Updated: April 2026*
