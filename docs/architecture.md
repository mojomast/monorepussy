# Ussyverse Architecture

## 1. Overview

The ussyverse is a unified monorepo consolidating ~50 Python CLI tools for code quality, security, forensics, and developer productivity. Originally 63 separate repositories on github.com/mojomast, these tools are now organized into a single codebase with shared libraries, unified CI/CD, and cross-tool integration.

**Design Goals:**
- **Developer velocity:** One clone, one sync, all tools available
- **Dependency minimalism:** ~22 packages installable with zero external dependencies
- **Backward compatibility:** Existing CLI commands continue to work
- **Cross-tool integration:** Shared libraries enable tools to compose cleanly

---

## 2. Monorepo Structure

### 2.1 Root Layout

```
ussyverse/
├── pyproject.toml              # Workspace root: uv workspace configuration
├── uv.lock                     # Unified dependency lockfile
├── README.md                   # Ecosystem overview and quickstart
├── LICENSE                     # License file
├── .python-version             # "3.11" (minimum Python version)
│
├── packages/                   # All Python packages
│   ├── libs/                   # Shared libraries (6 packages)
│   ├── tools/                  # CLI tools (~35 packages)
│   └── apps/                   # Applications (web dashboards, etc.)
│
├── docs/                       # Unified documentation
│   ├── architecture.md         # This file
│   ├── contributing.md         # Contributor guide
│   ├── migration-guide.md      # Migration timeline and details
│   └── adr/                    # Architecture Decision Records
│
├── tests/                      # Integration tests
│   └── integration/            # Cross-package integration tests
│
├── scripts/                    # Automation scripts
│   ├── bootstrap.sh            # One-command dev environment setup
│   ├── migrate-repo.sh         # git filter-repo wrapper for migrations
│   └── release.sh              # Per-package release automation
│
└── .github/
    └── workflows/
        ├── ci.yml              # Unified CI with change detection
        ├── release.yml         # Automated PyPI publishing
        ├── nightly.yml         # Full test suite + coverage
        └── docs.yml            # Documentation deployment
```

### 2.2 Package Organization

Packages are organized by **domain** rather than by tier or origin:

```
packages/
├── libs/                       # Shared libraries (no CLI entry points)
│   ├── ussy-core/              # Config, logging, path utilities
│   ├── ussy-cli/               # CLI framework and output formatting
│   ├── ussy-git/               # Git operations wrapper
│   ├── ussy-ast/               # AST parsing helpers
│   ├── ussy-sqlite/            # SQLite utilities and schema migration
│   └── ussy-report/            # Report formatting (JSON, SARIF, tables)
│
└── tools/                      # CLI tools (each has entry points)
    ├── forensics/              # Git forensics
    │   └── ussy-strata/        # stratagitussy + unconformity merged
    ├── security/               # Security scanners
    │   └── ussy-steno/         # stenographussy + stenography merged
    ├── visualization/          # Code visualization
    │   └── ussy-churn/         # churnmap (churnmapussy archived)
    ├── quality/                # Test suite quality
    │   └── ussy-calibre/       # calibre + acumen + lehr + marksman + levain
    ├── deps/                   # Dependency analysis (kept separate)
    │   ├── ussy-gridiron/      # gridironussy
    │   ├── ussy-chromato/      # chromatoussy
    │   ├── ussy-cambium/       # cambiumussy
    │   └── ussy-stratax/       # strataussy (renamed to avoid conflict)
    ├── triage/                 # Error forensics
    │   └── ussy-triage/        # triageussy
    ├── governance/             # Code governance
    │   ├── ussy-sentinel/      # sentinelussy
    │   └── ussy-parliament/    # parliamentussy
    ├── devtools/               # Developer tools
    │   ├── ussy-snapshot/      # snapshotussy
    │   ├── ussy-kintsugi/      # kintsugiussy
    │   ├── ussy-assay/         # assayussy
    │   └── ussy-petrichor/     # petrichorussy
    └── ...                     # Additional Tier 2 tools
```

### 2.3 Shared Libraries

Six shared libraries extract common patterns from across the ecosystem:

| Library | Purpose | Used By |
|---------|---------|---------|
| `ussy-core` | Config discovery, logging, path utilities | ~15 packages |
| `ussy-cli` | CLI boilerplate, subcommand dispatch, progress bars, color palettes | ~10 packages |
| `ussy-git` | Safe git execution, history traversal, reflog parsing | ~5 packages |
| `ussy-ast` | AST parsing, function/class extraction, complexity metrics | ~4 packages |
| `ussy-sqlite` | Schema migration, connection pooling, JSON serialization | ~8 packages |
| `ussy-report` | Table rendering, SARIF output, terminal width detection | ~6 packages |

Each shared library:
- Lives in `packages/libs/`
- Has its own `pyproject.toml`
- Is referenced as a workspace dependency by tools that need it
- Has comprehensive tests runnable in isolation

---

## 3. Build System

### 3.1 Tool Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Dependency Manager | `uv` | Rust-fast resolver, single lockfile, workspace support |
| Build Backend | `hatchling` | PEP 517/660 compliant, fast builds |
| Test Runner | `pytest` + `pytest-xdist` | Parallel test execution |
| Linter | `ruff` | Astral ecosystem, replaces flake8/isort/pydocstyle |
| Type Checker | `mypy` | Static type checking |
| Task Runner | `hatch` scripts | Local development tasks |
| Documentation | `mkdocs` + `mkdocstrings` | Markdown-native docs with API generation |

### 3.2 Workspace Configuration

The root `pyproject.toml` defines the uv workspace:

```toml
[tool.uv.workspace]
members = ["packages/*/*"]
exclude = ["packages/archive"]
```

All packages in `packages/*/*` are automatically workspace members. They can depend on each other via:

```toml
[project.dependencies]
ussy-core = { workspace = true }
```

### 3.3 Dependency Groups

Dependencies are organized into groups to minimize bloat:

- **Default:** No external dependencies (22 packages installable with stdlib only)
- **sci:** `numpy`, `scipy` (7 packages)
- **cli:** `click`, `rich` (7 packages)
- **git:** `gitpython` (2 packages)
- **graph:** `networkx` (2 packages)
- **web:** `requests`, `httpx`, `websockets` (4 packages)
- **config:** `pyyaml` (5 packages)
- **viz:** `matplotlib` (2 packages)
- **dev:** `pytest`, `pytest-cov`, `pytest-xdist`, `ruff`, `mypy` (development only)

Install modes:
```bash
uv sync                              # Zero-dep tools only (~22 packages)
uv sync --extra sci                  # Add scientific stack
uv sync --extra cli                  # Add CLI framework
uv sync --extra all                  # Everything
uv sync --extra all --group dev      # Everything + dev tools
```

---

## 4. Package Integration Model

### 4.1 Standalone Tools

Most tools are standalone packages with their own CLI entry point:

```python
# packages/tools/triage/ussy-triage/src/ussy_triage/cli.py
def main():
    parser = argparse.ArgumentParser()
    # ...

# pyproject.toml
[project.scripts]
ussy-triage = "ussy_triage.cli:main"
```

### 4.2 Merged Packages

Merged packages use subcommand dispatch:

```python
# packages/tools/quality/ussy-calibre/src/ussy_calibre/cli.py
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    
    measure_parser = subparsers.add_parser("measure", help="Metrological analysis")
    measure_parser.set_defaults(func=measure_main)
    
    hearing_parser = subparsers.add_parser("hearing", help="Audiological diagnostics")
    hearing_parser.set_defaults(func=hearing_main)
    
    # ...

# pyproject.toml
[project.scripts]
ussy-calibre = "ussy_calibre.cli:main"
```

### 4.3 Meta-Packages

Meta-packages provide unified interfaces over related tools:

```bash
# ussy-deps installs all 4 dependency analysis tools
pip install ussy-deps

# Runs all 4 analyses and combines report
ussy-deps analyze ./project
```

---

## 5. CI/CD Architecture

### 5.1 Change Detection

The CI pipeline uses `detect_changes.py` to identify which packages changed in a PR and which packages depend on them. Only affected packages are tested.

### 5.2 Parallel Execution

Tests are distributed across 20 parallel GitHub Actions runners using `partition_tests.py`, which implements a Longest Processing Time (LPT) algorithm to balance test execution time.

### 5.3 Timing Budget

| Phase | Time | Notes |
|-------|------|-------|
| Change detection | 5s | Single runner |
| Dependency sync | 15s | Cached (95% hit rate) |
| Lint (ruff) | 10s | Per runner, cached |
| Type check (mypy) | 30s | Per runner, cached |
| Test execution | 180s | 20 runners × pytest-xdist |
| Coverage aggregation | 10s | Single runner |
| **Total** | **~4m 30s** | |

### 5.4 Release Automation

- **Trigger:** Tag matching `ussy-<tool>-v*` pushed to main
- **Verification:** `release_checklist.py` validates tests, lint, typecheck
- **Publishing:** OIDC-based PyPI publishing (no long-lived tokens)
- **Artifacts:** Wheels cached for 30 days

---

## 6. Consolidation Clusters

### 6.1 Test Suite Quality (5 → 1)

**Package:** `ussy-calibre`
**Subcommands:**
- `measure` — Metrological measurement (calibreussy)
- `hearing` — Audiological diagnostics (acumenussy)
- `stabilize` — Glass annealing protocols (lehrussy)
- `precision` — Archery grouping analysis (marksmanussy)
- `health` — Fermentation lifecycle (levainussy)

**Rationale:** All five analyze test suite health using different scientific metaphors. They share CLI patterns, SQLite backends, and pytest integration. Merging eliminates maintenance sprawl while preserving all functionality via subcommands.

### 6.2 Steganography (2 → 1)

**Package:** `ussy-steno`
**Rationale:** `stenographussy` is the mature successor with 5 scanner types and SARIF output. `stenography` is a lightweight predecessor with minimal functionality. Unique lightweight detectors are ported to `ussy-steno --fast` mode.

### 6.3 Git Churn (2 → 1)

**Package:** `ussy-churn`
**Rationale:** `churnmap` is mature with PyDriller, NetworkX, and Voronoi tessellation. `churnmapussy` is early-stage with force-directed layout and ASCII renderer. Unique ASCII features are ported as alternative output modes.

### 6.4 Git Forensics (2 → 1)

**Package:** `ussy-strata`
**Subcommands:**
- `survey` — Geological visualization of git history (stratagitussy)
- `missing` — Detect missing history (unconformity)
- `timeline` — Combined chronological view

**Rationale:** `stratagitussy` surveys the record; `unconformity` detects gaps. They are complementary tools that belong together.

### 6.5 Dependency Analysis (4 keep separate)

**Packages:** `ussy-gridiron`, `ussy-chromato`, `ussy-cambium`, `ussy-stratax`
**Meta-Package:** `ussy-deps`

**Rationale:** These are genuinely complementary with different analysis dimensions (power-grid reliability, chromatography risk, grafting compatibility, behavioral seismic probing). Keeping them separate preserves their unique metaphors and user bases while the meta-package enables unified reporting.

---

## 7. Security Considerations

| Concern | Mitigation |
|---------|------------|
| snapshotussy plaintext env vars | Encryption-at-rest added; secrets filtered before persistence |
| mushinussy pickle cache | Replaced with JSON/msgpack; integrity verification added |
| plan9webplumbussy open WebSocket | Bound to localhost; authentication added |
| No CI/CD previously | Unified GitHub Actions with matrix testing across Python 3.11–3.13 |
| "ussy" naming | Retained as brand identity; `ussy-{tool}` prefix is professional and searchable |

---

## 8. Performance Targets

| Metric | Target | Implementation |
|--------|--------|---------------|
| `uv sync` time | <30s | Single lockfile, global uv cache |
| `pytest` full suite | <5 min | 20 parallel runners + pytest-xdist |
| `mkdocs build` | <60s | Markdown-native, no Sphinx autodoc overhead |
| Install size (zero-dep) | <50MB | 22 packages, stdlib only |
| Install size (full) | <200MB | All packages + optional deps |

---

---

**Related Documents:**
- [Contributing Guide](contributing.md)
- [Migration Guide](migration-guide.md)
- [ADRs](adr/index.md)

*Document Version: 1.0*
*Last Updated: April 2026*
