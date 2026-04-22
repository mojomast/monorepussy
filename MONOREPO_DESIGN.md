# Ussyverse Monorepo Design Document

## Executive Summary

This document describes the architecture for consolidating 63 Python repositories from github.com/mojomast (the "ussyverse" ecosystem) into a unified monorepo. The design prioritizes developer velocity, dependency minimization, and backward compatibility while enabling cross-tool integration.

**Key Decisions:**
- **Build Tool:** `uv` workspace with `Hatch` build backend
- **Test Framework:** `pytest` with `pytest-xdist` for parallel execution
- **Documentation:** `MkDocs` with `mkdocstrings` for API docs
- **CI/CD:** GitHub Actions with 20 parallel runners and intelligent change detection
- **Target:** `pytest` from root runs all tests in under 5 minutes

---

## 1. Architecture Overview

### 1.1 Design Principles

1. **Zero external dependency bloat** — Every external dependency must be justified. ~15 repos currently use stdlib only; we preserve this capability.
2. **Backward compatibility** — All existing CLI entry points continue to work.
3. **Git history preservation** — Use `git filter-repo` to migrate each repository with full commit history intact.
4. **Isolation + Integration** — Each package tests in isolation, but the full suite validates cross-package compatibility.
5. **Documentation-first** — All documentation is written and reviewed before any code migration begins.

### 1.2 High-Level Structure

```
ussyverse/
├── pyproject.toml              # Workspace root: uv workspace config
├── uv.lock                     # Unified dependency lockfile
├── README.md                   # Ecosystem overview
├── LICENSE
├── .python-version             # "3.11" (workspace Python minimum)
│
├── packages/                   # All Python packages (~50 packages)
│   ├── libs/                   # Shared libraries (6 packages)
│   │   ├── ussy-core/          # Config, logging, path utilities
│   │   ├── ussy-cli/           # CLI framework (argparse + rich patterns)
│   │   ├── ussy-git/           # Git operations wrapper
│   │   ├── ussy-ast/           # AST parsing helpers
│   │   ├── ussy-sqlite/        # SQLite utilities and schema migration
│   │   └── ussy-report/        # Output formatting (JSON, SARIF, tables)
│   │
│   ├── tools/                  # Standalone CLI tools (~35 packages)
│   │   ├── forensics/          # Git forensics cluster
│   │   │   └── ussy-strata/    # stratagitussy + unconformity merged
│   │   ├── security/           # Steganography cluster
│   │   │   └── ussy-steno/     # stenographussy + stenography merged
│   │   ├── visualization/      # Git churn visualization
│   │   │   └── ussy-churn/     # churnmap (churnmapussy archived)
│   │   ├── quality/            # Test suite quality cluster
│   │   │   └── ussy-calibre/   # calibre + acumen + lehr + marksman + levain
│   │   ├── deps/               # Dependency analysis (kept separate)
│   │   │   ├── ussy-gridiron/  # gridironussy
│   │   │   ├── ussy-chromato/  # chromatoussy
│   │   │   ├── ussy-cambium/   # cambiumussy
│   │   │   └── ussy-stratax/   # strataussy (renamed to avoid conflict)
│   │   ├── triage/             # Error forensics
│   │   │   └── ussy-triage/    # triageussy
│   │   ├── governance/         # Code governance
│   │   │   ├── ussy-sentinel/  # sentinelussy
│   │   │   └── ussy-parliament/# parliamentussy
│   │   ├── devtools/           # Developer tools
│   │   │   ├── ussy-snapshot/  # snapshotussy
│   │   │   ├── ussy-kintsugi/  # kintsugiussy
│   │   │   ├── ussy-assay/     # assayussy
│   │   │   └── ussy-petrichor/ # petrichorussy
│   │   └── ...                 # Tier 2 tools (see PACKAGE_MATRIX.md)
│   └── apps/                   # Applications (web dashboards, etc.)
│
├── docs/                       # Unified documentation
│   ├── architecture.md
│   ├── contributing.md
│   ├── migration-guide.md
│   ├── adr/
│   │   └── adr-001-monorepo.md
│   └── api/                    # Auto-generated API docs
│
├── tests/                      # Integration tests
│   └── integration/
│
├── scripts/                    # Automation scripts
│   ├── bootstrap.sh            # One-command dev environment setup
│   ├── migrate-repo.sh         # git filter-repo wrapper
│   └── release.sh              # Per-package release automation
│
└── .github/
    └── workflows/
        ├── ci.yml              # Unified CI (change detection + parallel test)
        ├── release.yml         # Automated PyPI publishing
        ├── nightly.yml         # Full test suite + coverage
        └── docs.yml            # Documentation deployment
```

### 1.3 Workspace Configuration

The root `pyproject.toml` defines the uv workspace:

```toml
[project]
name = "ussyverse"
version = "2025.1.0"
description = "The Ussyverse — 50+ Python tools for code quality, security, and forensics"
requires-python = ">=3.11"
dependencies = []

[tool.uv.workspace]
members = ["packages/*/*"]
exclude = ["packages/archive"]

[tool.uv.sources]
ussy-core = { workspace = true }
ussy-cli = { workspace = true }
ussy-git = { workspace = true }
ussy-ast = { workspace = true }
ussy-sqlite = { workspace = true }
ussy-report = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "pytest-xdist>=3.5",
    "pytest-asyncio>=0.21",
    "ruff>=0.5",
    "mypy>=1.10",
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
    "mkdocstrings[python]>=0.25",
]
```

---

## 2. Package Naming Conventions

### 2.1 Decision: Keep "ussy" as Namespace Prefix

The "ussy" suffix is the ecosystem's brand identity. All 45 Python repos end in "ussy" by design. We preserve this as a **prefix** (`ussy-{tool}`) for:
- **PyPI discoverability** — `ussy-triage` is instantly recognizable
- **CLI consistency** — all commands follow `ussy-<tool>` pattern
- **Import paths** — `from ussy_triage import ...` (PEP 8 compliant)

### 2.2 Naming Table (Selected Examples)

| Old Name | New Package Name | CLI Command | Decision |
|----------|-----------------|-------------|----------|
| triageussy | `ussy-triage` | `ussy-triage` | Keep |
| stenographussy | `ussy-steno` | `ussy-steno` | Merge (with stenography) |
| sentinelussy | `ussy-sentinel` | `ussy-sentinel` | Keep |
| gridironussy | `ussy-gridiron` | `ussy-gridiron` | Keep |
| parliamentussy | `ussy-parliament` | `ussy-parliament` | Keep |
| snapshotussy | `ussy-snapshot` | `ussy-snapshot` | Keep |
| strataussy | `ussy-stratax` | `ussy-stratax` | Keep (renamed to avoid conflict) |
| kintsugiussy | `ussy-kintsugi` | `ussy-kintsugi` | Keep |
| assayussy | `ussy-assay` | `ussy-assay` | Keep |
| petrichorussy | `ussy-petrichor` | `ussy-petrichor` | Keep |
| calibreussy | `ussy-calibre` | `ussy-calibre` | Merge (5 repos → 1) |
| acumenussy | *(merged)* | *(subcommand)* | Merge into calibre |
| lehrussy | *(merged)* | *(subcommand)* | Merge into calibre |
| marksmanussy | *(merged)* | *(subcommand)* | Merge into calibre |
| levainussy | *(merged)* | *(subcommand)* | Merge into calibre |
| chromatoussy | `ussy-chromato` | `ussy-chromato` | Keep |
| cambiumussy | `ussy-cambium` | `ussy-cambium` | Keep |
| churnmap | `ussy-churn` | `ussy-churn` | Keep (churnmapussy archived) |
| stratagitussy | `ussy-strata` | `ussy-strata` | Merge (with unconformity) |
| unconformity | *(merged)* | *(subcommand)* | Merge into strata |
| stenography | *(merged)* | *(subcommand)* | Archive (merged into steno) |

### 2.3 Backward Compatibility

Legacy CLI entry points are preserved as deprecated aliases during a 12-month transition period:

```toml
# In merged package pyproject.toml
[project.scripts]
# New unified command
ussy-calibre = "ussy_calibre.cli:main"
# Legacy aliases (emit deprecation warning)
calibre = "ussy_calibre.legacy:calibre_alias"
acumen = "ussy_calibre.legacy:acumen_alias"
lehr = "ussy_calibre.legacy:lehr_alias"
marksman = "ussy_calibre.legacy:marksman_alias"
levain = "ussy_calibre.legacy:levain_alias"
```

---

## 3. Dependency Strategy

### 3.1 Audit Summary

- **pyproject.toml adoption:** 62/63 repos (98.4%)
- **setup.py legacy:** 1 repo (dosemateussy) — converted during migration
- **Zero external deps:** ~15 repos (25%) — these must remain installable with zero external dependencies
- **Dependency conflicts:** **ZERO** — all version specs are compatible

### 3.2 Unified Dependency Resolution

All external dependencies are organized into **optional dependency groups** in the root `pyproject.toml`:

```toml
[project.optional-dependencies]
# Core scientific stack (7 repos)
sci = ["numpy>=1.24", "scipy>=1.10"]

# CLI framework (7 repos)
cli = ["click>=8.1", "rich>=13.0", "rich-click>=1.0"]

# Git forensics (2 repos)
git = ["gitpython>=3.1"]

# Network/graph (2 repos)
graph = ["networkx>=3.0"]

# Web/data (4 repos)
web = ["requests>=2.25", "httpx>=0.24", "websockets>=11.0"]

# Config/serialization (5 repos)
config = ["pyyaml>=6.0"]

# Visualization (2 repos)
viz = ["matplotlib>=3.7"]

# Compression (1 repo)
compress = ["zstandard>=0.20"]

# Git mining (1 repo)
mining = ["pydriller>=2.6"]

# All extras
all = ["ussyverse[sci,cli,git,graph,web,config,viz,compress,mining]"]
```

### 3.3 Shared Library Extraction

Six shared libraries are extracted to eliminate duplication:

| Library | Extracted From | Purpose |
|---------|---------------|---------|
| `ussy-core` | triageussy, sentinelussy, gridironussy, parliamentussy | Config discovery, logging, path utilities |
| `ussy-cli` | triageussy, stenographussy, gridironussy, parliamentussy | CLI boilerplate, subcommand dispatch, output formatting |
| `ussy-git` | churnmap, stratagitussy, unconformity, snapshotussy | Safe git execution, history traversal, reflog parsing |
| `ussy-ast` | sentinelussy, assayussy, kintsugiussy | AST parsing, function extraction, complexity metrics |
| `ussy-sqlite` | triageussy, sentinelussy, gridironussy, parliamentussy, assayussy, petrichorussy | Schema migration, connection pooling, JSON serialization |
| `ussy-report` | triageussy, stenographussy, gridironussy | Table rendering, SARIF output, terminal width detection |

### 3.4 Zero-Dependency Preservation

For the ~15 stdlib-only repos, we enforce:
- **No mandatory external dependencies** in their `pyproject.toml`
- **Conditional imports** with stdlib fallbacks:
  ```python
  try:
      import rich
      CONSOLE = rich.console.Console()
  except ImportError:
      CONSOLE = SimpleConsole()  # stdlib fallback
  ```
- **Lazy imports** — scientific libraries imported only when functions are called

---

## 4. CI/CD Design

### 4.1 Architecture

```
PR opened/pushed
    ↓
[ci.yml] detect_changes.py — identify changed packages + dependents
    ↓
partition_tests.py — distribute packages across 20 parallel runners
    ↓
Runner N:
  - uv sync (cached)
  - ruff check (cached)
  - mypy (cached)
  - pytest -n auto (pytest-xdist)
    ↓
Aggregate coverage → Codecov
    ↓
Build wheels → Cache artifacts
    ↓
PR merged → release.yml (optional per-package publish)
```

### 4.2 Timing Budget (<5 minutes target)

| Phase | Time | Parallelization |
|-------|------|----------------|
| Change detection | 5s | Single runner |
| Dependency sync (uv) | 15s | Cached (95% hit rate) |
| Lint (ruff) | 10s | Per runner, cached |
| Type check (mypy) | 30s | Per runner, cached |
| Test execution | 180s | 20 runners × pytest-xdist (auto) |
| Coverage aggregation | 10s | Single runner |
| **Total** | **~4m 30s** | **Full parallelization** |

### 4.3 Caching Strategy

1. **Global uv cache** — `~/.cache/uv` cached via `actions/cache` keyed by `uv.lock` hash
2. **Per-package venv** — `.venv/` cached per package, keyed by `packages/<name>/pyproject.toml` hash
3. **Test artifacts** — `.pytest_cache/` and coverage data cached between runs
4. **Build cache** — Hatch build artifacts cached to avoid rebuilds

### 4.4 Release Automation

- **Versioning:** Each package versions independently via semantic versioning
- **Publishing:** OIDC-based PyPI publishing (no long-lived tokens)
- **Trigger:** Release workflow runs when a tag matching `ussy-<tool>-v*` is pushed
- **Verification:** `release_checklist.py` validates tests, lint, typecheck before publishing

### 4.5 Nightly Suite

Full test suite runs daily at 2 AM UTC:
- No change detection (tests everything)
- Generates coverage reports
- Runs integration tests
- Publishes nightly docs build

---

## 5. Consolidation Justification

### 5.1 Cluster 1: Test Suite Quality (5 → 1)

**Merged into `ussy-calibre`**

| Repo | Subcommand | Justification |
|------|-----------|---------------|
| calibreussy | `ussy-calibre measure` | Primary package — metrological measurement science is the most comprehensive framework |
| acumenussy | `ussy-calibre hearing` | Audiological diagnostics — different lens, same target (test quality) |
| lehrussy | `ussy-calibre stabilize` | Glass annealing for stabilization — adds stabilization protocol generation |
| marksmanussy | `ussy-calibre precision` | Archery precision for grouping analysis — adds statistical rigor |
| levainussy | `ussy-calibre health` | Fermentation science for lifecycle health — adds maintenance cadence tracking |

**Triage Report Reference:** *"All five analyze test suite health using different scientific metaphors... They share similar CLI patterns, SQLite backends, and pytest integration."*

### 5.2 Cluster 2: Steganography Scanners (2 → 1)

**Merged into `ussy-steno`**

| Repo | Decision | Justification |
|------|----------|---------------|
| stenographussy | **KEEP** | More mature, 5 scanner types, SARIF output, CI-ready |
| stenography | **ARCHIVE** | Lightweight predecessor (~8 test files); all functionality superseded |

**Action:** Port any unique lightweight detectors from `stenography` into `ussy-steno --fast` mode.

**Triage Report Reference:** *"`stenography` is the lightweight predecessor while `stenographussy` is the full-featured successor."*

### 5.3 Cluster 3: Git Churn Visualization (2 → 1)

**Merged into `ussy-churn`**

| Repo | Decision | Justification |
|------|----------|---------------|
| churnmap | **KEEP** | Mature (PyDriller, NetworkX, scipy, Voronoi tessellation) |
| churnmapussy | **ARCHIVE** | Early-stage (force-directed layout, ASCII/SVG, stub tests) |

**Action:** Port `churnmapussy`'s territorial-map metaphor and ASCII renderer into `churnmap` as alternative output modes.

**Triage Report Reference:** *"`churnmap` is mature while `churnmapussy` is early-stage... Port unique features then archive."*

### 5.4 Cluster 4: Git Forensics (2 → 1)

**Merged into `ussy-strata`**

| Repo | Subcommand | Justification |
|------|-----------|---------------|
| stratagitussy | `ussy-strata survey` | Geological visualization of git history — surveys the record |
| unconformity | `ussy-strata missing` | Detects missing history (force-pushes, squash merges) — detects gaps |

**Triage Report Reference:** *"They are complementary — one surveys the record, the other detects gaps."*

### 5.5 Cluster 5: Dependency Analysis (4 → Keep Separate)

| Repo | Decision | Justification |
|------|----------|---------------|
| gridironussy | **KEEP** `ussy-gridiron` | Power-grid reliability metaphor — unique analysis dimension |
| chromatoussy | **KEEP** `ussy-chromato` | Chromatography risk profiling — different from others |
| cambiumussy | **KEEP** `ussy-cambium` | Grafting compatibility — predictive, time-dependent |
| strataussy | **KEEP** `ussy-stratax` | Behavioral stability probing — distinct from all three |

**Unification:** Create `ussy-deps` meta-package that installs all four and provides unified CLI:
```bash
pip install ussy-deps
ussy-deps analyze ./project  # Runs all 4 analyses and combines report
```

**Triage Report Reference:** *"These are genuinely complementary... Keep as separate packages but create a unified meta-package."*

---

## 6. Tier 1 Individual Decisions

| Repo | Decision | Package Name | Justification |
|------|----------|--------------|---------------|
| triageussy | Keep | `ussy-triage` | Unique forensic methodology, standalone value |
| stenographussy | Merge → `ussy-steno` | See Cluster 2 |
| sentinelussy | Keep | `ussy-sentinel` | Immunological governance — unique, no overlap |
| gridironussy | Keep | `ussy-gridiron` | See Cluster 5 |
| parliamentussy | Keep | `ussy-parliament` | Agent governance — unique domain |
| snapshotussy | Keep | `ussy-snapshot` | Dev state management — unique |
| strataussy | Keep | `ussy-stratax` | See Cluster 5 (renamed to avoid conflict with `ussy-strata`) |
| kintsugiussy | Keep | `ussy-kintsugi` | Bug repair annotation — unique concept |
| assayussy | Keep | `ussy-assay` | Code grading — unique metallurgical metaphor |
| petrichorussy | Keep | `ussy-petrichor` | Config drift detection — unique |
| unconformity | Merge → `ussy-strata` | See Cluster 4 |

---

## 7. Tier 2 & Tier 3 Strategy

### Tier 2 (39 repos)
- Migrate to monorepo as individual packages
- Evaluate for additional merge candidates during Phase 2
- Group by theme into `packages/tools/` subdirectories

### Tier 3 (13 repos)
- **Do not migrate** — archive on GitHub only
- Add `[ARCHIVED]` prefix to repository descriptions
- Include in `ARCHIVED_REPOS.md` with rationale
- No code migration, no history preservation needed

**Tier 3 Repos:** cartographerussy, codelineageussy, churnmapussy, entrainussy, escutcheonussy, driftlineussy, tellussy, alembicussy, hitchussy, morsethussy, kompressiussy, inkblotussy, driftnetussy

---

## 8. Success Criteria Validation

| Criteria | Implementation |
|----------|---------------|
| `uv sync` installs all tools | Root `pyproject.toml` with workspace members; `uv sync` resolves entire dependency graph into single venv |
| `pytest` from root runs in <5 min | 20 parallel GitHub Actions runners + pytest-xdist auto; local runs use `pytest -n auto` |
| `mkdocs serve` renders all docs | `mkdocs-monorepo` plugin includes all package READMEs; API docs generated via `mkdocstrings` |
| Git history preserved | `git filter-repo --to-subdirectory-filter` migrates each repo with full history |
| CLI backward compatibility | Legacy entry points aliased with deprecation warnings for 12-month transition |
| Zero dependency bloat | Optional dependency groups; ~22 packages installable with zero external deps |

---

*Document Version: 1.0*
*Last Updated: April 2026*
