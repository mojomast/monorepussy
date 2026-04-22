# Migration Guide

## 1. Overview

This guide documents the migration of 63 Python repositories from github.com/mojomast into the `ussyverse` monorepo. Whether you are an existing user of one of the original tools or a new contributor, this guide will help you navigate the transition.

**Migration Status:** In Progress (Phase 1)
**Target Completion:** Week 15 (approx. mid-July 2026)

---

## 2. What Changed

### 2.1 Before (63 Separate Repos)

```bash
# Install each tool separately
pip install triageussy
pip install stenographussy
pip install sentinelussy
# ... 60 more times

# Clone multiple repos
git clone https://github.com/mojomast/triageussy.git
git clone https://github.com/mojomast/stenographussy.git
# ... 60 more times
```

### 2.2 After (1 Monorepo)

```bash
# Clone once, get all tools
git clone https://github.com/mojomast/ussyverse.git
cd ussyverse
uv sync --extra all        # Install all tools

# Or install specific tools only
uv sync --package ussy-triage
uv sync --package ussy-steno
```

### 2.3 Package Name Changes

| Old Name | New Package Name | CLI Command |
|----------|-----------------|-------------|
| triageussy | `ussy-triage` | `ussy-triage` |
| stenographussy | `ussy-steno` | `ussy-steno` |
| sentinelussy | `ussy-sentinel` | `ussy-sentinel` |
| gridironussy | `ussy-gridiron` | `ussy-gridiron` |
| parliamentussy | `ussy-parliament` | `ussy-parliament` |
| snapshotussy | `ussy-snapshot` | `ussy-snapshot` |
| strataussy | `ussy-stratax` | `ussy-stratax` |
| kintsugiussy | `ussy-kintsugi` | `ussy-kintsugi` |
| assayussy | `ussy-assay` | `ussy-assay` |
| petrichorussy | `ussy-petrichor` | `ussy-petrichor` |
| calibreussy | `ussy-calibre` | `ussy-calibre` |
| chromatoussy | `ussy-chromato` | `ussy-chromato` |
| cambiumussy | `ussy-cambium` | `ussy-cambium` |
| churnmap | `ussy-churn` | `ussy-churn` |
| stratagitussy | `ussy-strata` | `ussy-strata` |

**Merged packages:**
- `calibreussy + acumenussy + lehrussy + marksmanussy + levainussy` → `ussy-calibre`
- `stenographussy + stenography` → `ussy-steno`
- `churnmap + churnmapussy` → `ussy-churn`
- `stratagitussy + unconformity` → `ussy-strata`

---

## 3. For Existing Users

### 3.1 Installing from the Monorepo

```bash
# Install everything
pip install ussyverse[all]

# Install specific tools
pip install ussy-triage
pip install ussy-steno

# Install with optional dependencies
pip install ussyverse[sci]      # Tools requiring numpy/scipy
pip install ussyverse[cli]      # Tools requiring click/rich
```

### 3.2 Backward Compatibility

All existing CLI commands continue to work during a **12-month transition period**:

```bash
# Old commands still work (with deprecation warning)
triage analyze log.txt           # → redirects to ussy-triage
stenography scan ./src           # → redirects to ussy-steno
calibre measure tests/           # → redirects to ussy-calibre
```

You will see a warning:
```
Warning: 'triage' is deprecated. Use 'ussy-triage' instead.
This alias will be removed in ussyverse 2026.12.0.
```

### 3.3 Migrating Your Scripts

Replace old commands with new ones:

```bash
# Before
triage analyze log.txt | jq '.issues[]'

# After
ussy-triage analyze log.txt | jq '.issues[]'
```

For merged packages, use subcommands:

```bash
# Before
calibre measure tests/
acumen diagnose tests/
marksman group tests/

# After
ussy-calibre measure tests/
ussy-calibre hearing tests/
ussy-calibre precision tests/
```

### 3.4 Configuration Migration

Most tools read configuration from `pyproject.toml` in the project root:

```toml
[tool.ussy-triage]
patterns = ["ERROR", "FAILURE"]
output_format = "json"

[tool.ussy-calibre]
threshold_coverage = 80.0
```

If you previously had tool-specific config files, move the settings to `pyproject.toml` under the appropriate `[tool.ussy-*]` section.

---

## 4. For Contributors

### 4.1 Repository Structure

```
ussyverse/
├── packages/
│   ├── libs/           # Shared libraries (ussy-core, ussy-cli, etc.)
│   └── tools/          # Individual CLI tools
├── docs/               # Documentation
├── tests/              # Integration tests
└── scripts/            # Automation scripts
```

### 4.2 Finding Code

Each original repo now lives in `packages/tools/<category>/`:

| Original Repo | New Location |
|--------------|--------------|
| triageussy | `packages/tools/triage/ussy-triage/` |
| stenographussy | `packages/tools/security/ussy-steno/` |
| sentinelussy | `packages/tools/governance/ussy-sentinel/` |
| gridironussy | `packages/tools/deps/ussy-gridiron/` |
| parliamentussy | `packages/tools/governance/ussy-parliament/` |

### 4.3 Development Workflow

See [Contributing Guide](contributing.md) for full details.

Quick start:
```bash
# Sync dependencies
uv sync --extra all --group dev

# Run tests for a specific package
uv run --package ussy-triage pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy packages/
```

---

## 5. Migration Timeline

| Phase | Dates | Repos | Status |
|-------|-------|-------|--------|
| Phase 1 | Apr 2026 | Foundation + pilot (triageussy) | 🔄 In Progress |
| Phase 2 | May 2026 | Tier 1 clusters (11 repos) | ⏳ Planned |
| Phase 3 | Jun 2026 | Tier 1 remaining + Tier 2 batch 1 | ⏳ Planned |
| Phase 4 | Jul 2026 | Tier 2 completion | ⏳ Planned |
| Phase 5 | Aug 2026 | Tier 3 archive + cleanup | ⏳ Planned |

### 5.1 Migrated Repositories

| Repo | Migration Date | New Location | Status |
|------|---------------|--------------|--------|
| triageussy | TBD | `packages/tools/triage/ussy-triage/` | ⏳ Planned |

### 5.2 Archived Repositories

| Repo | Archive Date | Reason |
|------|-------------|--------|
| stenography | TBD | Merged into ussy-steno |
| churnmapussy | TBD | Merged into ussy-churn |
| cartographerussy | TBD | Games/edutainment |
| codelineageussy | TBD | Security issue (.venv committed) |
| driftnetussy | TBD | No code (specifications only) |

---

## 6. Troubleshooting

### 6.1 Import Errors

**Problem:** `ModuleNotFoundError: No module named 'ussy_triage'`

**Solution:** Ensure you are running from the virtual environment:
```bash
uv sync --package ussy-triage
uv run ussy-triage --help
```

### 6.2 CLI Alias Not Found

**Problem:** `triage: command not found`

**Solution:** Legacy aliases require the full install:
```bash
uv sync --extra all
# Or install the specific package
uv sync --package ussy-triage
```

### 6.3 Tests Failing After Migration

**Problem:** Tests pass in isolation but fail in full suite

**Solution:** Check for cross-package contamination:
```bash
# Run specific package tests
uv run --package ussy-triage pytest packages/tools/triage/ussy-triage/

# Check for shared state in conftest.py or fixtures
```

### 6.4 Dependency Conflicts

**Problem:** `uv sync` fails with dependency resolution error

**Solution:** Update the lockfile:
```bash
uv lock --upgrade
```

If the conflict persists, check [PACKAGE_MATRIX.md](../PACKAGE_MATRIX.md) for known dependency groups.

---

## 7. FAQ

### Q: Why monorepo?
**A:** The 63 separate repos shared significant code but were maintained independently. A monorepo enables:
- Cross-tool integration (e.g., `ussy-deps` meta-package)
- Unified CI/CD and testing
- Single dependency lockfile
- Easier refactoring across tools

### Q: Will old repos remain available?
**A:** Migrated repos will be archived (read-only) with deprecation notices. Tier 3 repos will also be archived. No code is deleted.

### Q: Can I still install individual tools?
**A:** Yes. Each tool is an independent package:
```bash
pip install ussy-triage
pip install ussy-steno
```

### Q: What happened to the "ussy" suffix?
**A:** It became a prefix (`ussy-{tool}`) for better PyPI discoverability and CLI consistency.

### Q: How do I report a bug in a migrated tool?
**A:** Open an issue in the `ussyverse` monorepo, not the archived source repo.

### Q: Can I contribute to just one tool?
**A:** Yes. Fork the monorepo, make changes in `packages/tools/<category>/<package>/`, and open a PR.

---

## 8. Getting Help

- **Questions:** [GitHub Discussions](https://github.com/mojomast/ussyverse/discussions)
- **Bugs:** [GitHub Issues](https://github.com/mojomast/ussyverse/issues)
- **Documentation:** [Full Docs](https://mojomast.github.io/ussyverse/)
- **Chat:** #ussyverse-dev on Slack

---

---

**Related Documents:**
- [Architecture](architecture.md)
- [Contributing Guide](contributing.md)
- [ADRs](adr/index.md)

*Document Version: 1.0*
*Last Updated: April 2026*
