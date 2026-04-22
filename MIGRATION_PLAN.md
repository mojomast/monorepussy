# Ussyverse Monorepo Migration Plan

## 1. Overview

This document provides a step-by-step migration plan for consolidating 63 Python repositories from github.com/mojomast into the `ussyverse` monorepo. The migration is organized into **5 phases** over approximately **15 weeks**.

**Key Constraints:**
- Documentation must be complete before any code migration begins
- Git history must be preserved for all migrated repos
- CLI backward compatibility must be maintained
- Tier 3 repos are archived, not migrated

---

## 2. Migration Timeline

```
Week 1-2:   Phase 1 — Foundation + Pilot
Week 3-6:   Phase 2 — Tier 1 Clusters (11 repos)
Week 7-10:  Phase 3 — Tier 1 Remaining + Tier 2 (batch 1)
Week 11-14: Phase 4 — Tier 2 Completion (batch 2)
Week 15+:   Phase 5 — Tier 3 Archive + Cleanup
```

### 2.1 Phase 1: Foundation (Weeks 1-2)

**Goal:** Establish monorepo structure and migrate one pilot repo to validate the process.

**Tasks:**
1. Create monorepo repository (`github.com/mojomast/ussyverse`)
2. Set up root `pyproject.toml` with uv workspace configuration
3. Configure GitHub Actions workflows (CI, release, docs)
4. Create shared library scaffolding (`ussy-core`, `ussy-cli`)
5. Write all documentation (`docs/architecture.md`, `docs/contributing.md`, `docs/migration-guide.md`, `docs/adr/adr-001-monorepo.md`)
6. **Pilot migration:** Migrate `triageussy` (Tier 1, stdlib-only, well-tested)
7. Verify pilot: `uv sync`, `pytest`, `mkdocs serve` all work
8. Document lessons learned and update migration templates

**Deliverables:**
- Monorepo repository with CI/CD
- All documentation reviewed and approved
- Pilot repo fully migrated and tested

### 2.2 Phase 2: Tier 1 Clusters (Weeks 3-6)

**Goal:** Migrate all Tier 1 repos, including cluster merges.

**Week 3-4: Cluster Merges**
- **Cluster 1 (Test Suite Quality):** Merge `calibreussy + acumenussy + lehrussy + marksmanussy + levainussy` → `ussy-calibre`
- **Cluster 2 (Steganography):** Merge `stenographussy + stenography` → `ussy-steno`, archive `stenography`
- **Cluster 3 (Git Churn):** Migrate `churnmap` → `ussy-churn`, archive `churnmapussy`
- **Cluster 4 (Git Forensics):** Merge `stratagitussy + unconformity` → `ussy-strata`
- **Cluster 5 (Dependency Analysis):** Migrate `gridironussy`, `chromatoussy`, `cambiumussy`, `strataussy` as separate packages

**Week 5-6: Tier 1 Individual Repos**
- Migrate: `sentinelussy`, `parliamentussy`, `snapshotussy`, `kintsugiussy`, `assayussy`, `petrichorussy`

**Deliverables:**
- All Tier 1 repos migrated
- Cluster merges completed with subcommands
- All Tier 1 tests passing in monorepo

### 2.3 Phase 3: Tier 1 Remaining + Tier 2 Batch 1 (Weeks 7-10)

**Goal:** Complete Tier 1 and begin Tier 2 migration.

**Week 7-8:**
- Migrate remaining Tier 1: `triageussy` (if not pilot), `unconformity` (if not in cluster)
- Begin Tier 2 batch 1 (least dependencies first):
  - `proprioceptionussy`, `curatorussy`, `operonussy`, `acumenussy` (if not merged)
  - `portmoreussy`, `clavisussy`, `cambiumussy` (if not separate)
  - `syntropussy`, `fossilrecordussy`, `telegraphaussy`

**Week 9-10:**
- Continue Tier 2 batch 1:
  - `mushinussy`, `dosemateussy`, `gamutussy`, `cycloneussy`
  - `isobarussy`, `circadiaussy`, `fatigueussy`, `endemicussy`
  - `stemmaussy`, `crystallossy`, `terrariumussy`, `tarotussy`

**Deliverables:**
- ~30 repos migrated
- Dependency patterns validated
- CI performance optimized

### 2.4 Phase 4: Tier 2 Completion (Weeks 11-14)

**Goal:** Migrate remaining Tier 2 repos.

**Week 11-12:**
- `actuaryussy`, `coronerussy`, `mintussy`, `cavityussy`
- `aquiferussy`, `seralussy`, `plan9webplumbussy`
- `reverseoracleussy`, `timeloomussy`

**Week 13-14:**
- `calibreussy` (if not merged), `lehrussy` (if not merged), `marksmanussy` (if not merged)
- `levainussy` (if not merged), `chromatoussy` (if not separate)
- Address any issues from earlier phases
- Final integration testing

**Deliverables:**
- All Tier 2 repos migrated
- Full test suite passing
- Performance targets met (<5 min)

### 2.5 Phase 5: Tier 3 Archive + Cleanup (Week 15+)

**Goal:** Archive Tier 3 repos and finalize documentation.

**Tasks:**
1. Add `[ARCHIVED]` prefix to all Tier 3 repo descriptions
2. Add deprecation notices to Tier 3 READMEs pointing to monorepo
3. Create `ARCHIVED_REPOS.md` documenting rationale per repo
4. Final documentation review and updates
5. Publish first wave of packages to PyPI
6. Announce migration completion

**Tier 3 Repos to Archive:**
- cartographerussy, codelineageussy, churnmapussy, entrainussy
- escutcheonussy, driftlineussy, tellussy, alembicussy
- hitchussy, morsethussy, kompressiussy, inkblotussy
- driftnetussy

**Deliverables:**
- All Tier 3 repos archived
- Monorepo documentation finalized
- First PyPI releases published

---

## 3. Per-Repo Migration Checklist

### 3.1 Pre-Migration

```markdown
## Pre-Migration: [repo-name]

- [ ] Verify all commits pushed to source repo
- [ ] Create final release/tag in source repo (e.g., `v1.2.3-final`)
- [ ] Document all CLI entry points and their behavior
- [ ] List all external dependencies with version specs
- [ ] Identify test files and estimate test count
- [ ] Identify breaking changes needed (renames, import path changes)
- [ ] Determine target package name and monorepo path
- [ ] Identify merge partners (if part of a cluster)
- [ ] Update MIGRATION_PLAN.md with specific timeline
```

### 3.2 Migration Execution

```markdown
## Migration: [repo-name]

### History Preservation
- [ ] Run git filter-repo with path rewrite:
  ```bash
  git filter-repo --to-subdirectory-filter packages/[category]/[package-name]
  ```
- [ ] Verify history preserved: `git log --oneline --graph --all | head -50`
- [ ] Verify no large binary files or .venv/ committed

### Package Restructuring
- [ ] Update `pyproject.toml`:
  - [ ] Change package name to `ussy-[tool]`
  - [ ] Update version to match monorepo scheme (if needed)
  - [ ] Add `ussy-core`, `ussy-cli` workspace dependencies (if applicable)
  - [ ] Update entry points to new CLI command
  - [ ] Add legacy entry point aliases with deprecation warnings
- [ ] Restructure source code into `src/ussy_[tool]/` layout
- [ ] Update all internal imports for new paths
- [ ] Move tests to `tests/` directory
- [ ] Migrate README.md with deprecation notice and new install instructions

### CI/CD Integration
- [ ] Remove old `.github/workflows/` (if any)
- [ ] Verify package builds with `uv build --package ussy-[tool]`
- [ ] Add package to root `pyproject.toml` workspace members (if not globbed)

### Testing
- [ ] Run tests in isolation: `uv run --package ussy-[tool] pytest`
- [ ] Run tests in full suite: `uv run pytest packages/[category]/[package-name]/`
- [ ] Verify CLI entry points: `uv run ussy-[tool] --help`
- [ ] Verify legacy aliases: `uv run [old-command] --help` (should show deprecation warning)
- [ ] Verify no import errors or missing dependencies
```

### 3.3 Post-Migration

```markdown
## Post-Migration: [repo-name]

- [ ] Update root README.md package index
- [ ] Update docs/migration-guide.md with migration date
- [ ] Update PACKAGE_MATRIX.md status to "Migrated"
- [ ] Add deprecation notice to source repo README:
  ```markdown
  > **DEPRECATED**: This repository has been migrated to the [ussyverse monorepo](https://github.com/mojomast/ussyverse/tree/main/packages/[category]/[package-name]).
  > No further updates will be made here.
  ```
- [ ] Archive source repo (GitHub settings → Archive)
- [ ] Verify PyPI redirect (if package was published) or plan new publication
- [ ] Notify stakeholders (if any external users)
- [ ] Close all open issues in source repo with migration notice
```

---

## 4. Rollback Plan

### 4.1 Trigger Conditions

Rollback is triggered if any of the following occur during or after migration:
- Critical test failures that cannot be resolved within 24 hours
- Broken CLI entry points affecting user workflows
- Data loss in git history
- Dependency conflicts blocking CI/CD
- Performance regression (full suite >10 minutes)

### 4.2 Immediate Rollback Steps

```bash
# 1. Stop all work on the affected package
# 2. Identify the merge commit in monorepo
git log --oneline --grep="Merge [repo-name]" | head -5

# 3. Revert the merge commit
git revert -m 1 <merge-commit-hash>

# 4. Verify monorepo state is clean
git status
git log --oneline -5

# 5. Remove package directory if partially migrated
rm -rf packages/[category]/[package-name]

# 6. Update documentation to reflect rollback
```

### 4.3 Recovery Options

| Option | When to Use | Steps |
|--------|------------|-------|
| **Fix Forward** | Minor issues fixable in monorepo | Create PR with fixes, re-run tests |
| **Re-migrate** | History corruption or major issues | Restore source repo from tag, re-run migration script |
| **Temporary Separate** | Urgent fix needed while investigating | Maintain source repo unarchived temporarily, sync critical fixes |

### 4.4 Verification Checklist

```markdown
## Rollback Verification

- [ ] Source repo is unarchived and functional
- [ ] Monorepo builds without the affected package
- [ ] No orphaned commits or dangling refs in monorepo
- [ ] CI passes on monorepo main branch
- [ ] Documentation updated to reflect current state
- [ ] Team notified of rollback and next steps
```

---

## 5. Migration Priority Matrix

| Priority | Criteria | Repos | Action |
|----------|----------|-------|--------|
| **P0** | Active development, cross-dependencies, Tier 1 | triageussy, stenographussy, sentinelussy, gridironussy, parliamentussy, snapshotussy, strataussy, kintsugiussy, assayussy, petrichorussy, unconformity | Migrate first (Phase 2) |
| **P1** | Stable, used by others, low dependency count | proprioceptionussy, curatorussy, operonussy, acumenussy, cambiumussy, clavisussy, chromatoussy, syntropussy, fossilrecordussy, telegraphaussy, mushinussy, gamutussy, cycloneussy, isobarussy, circadiaussy, fatigueussy, endemicussy, stemmaussy, crystallossy, terrariumussy, tarotussy | Migrate after P0 (Phase 3-4) |
| **P2** | Maintenance mode, moderate complexity | actuaryussy, portmoreussy, lehrussy, marksmanussy, levainussy, coronerussy, mintussy, dosemateussy, cavityussy, aquiferussy, seralussy, plan9webplumbussy, reverseoracleussy, timeloomussy, stratagitussy | Migrate when convenient (Phase 4) |
| **P3** | Unused/deprecated, Tier 3 | cartographerussy, codelineageussy, churnmapussy, entrainussy, escutcheonussy, driftlineussy, tellussy, alembicussy, hitchussy, morsethussy, kompressiussy, inkblotussy, driftnetussy | Archive only (Phase 5) |

---

## 6. Cluster-Specific Migration Notes

### 6.1 Cluster 1: Test Suite Quality (5 → 1)

**Merged Package:** `ussy-calibre`
**Subcommands:**
- `ussy-calibre measure` (calibreussy)
- `ussy-calibre hearing` (acumenussy)
- `ussy-calibre stabilize` (lehrussy)
- `ussy-calibre precision` (marksmanussy)
- `ussy-calibre health` (levainussy)

**Migration Steps:**
1. Migrate `calibreussy` as base package
2. Port `acumenussy` code into `ussy_calibre/hearing.py`
3. Port `lehrussy` code into `ussy_calibre/stabilize.py`
4. Port `marksmanussy` code into `ussy_calibre/precision.py`
5. Port `levainussy` code into `ussy_calibre/health.py`
6. Create unified CLI dispatcher in `ussy_calibre/cli.py`
7. Add legacy entry point aliases
8. Archive 4 source repos after verification

### 6.2 Cluster 2: Steganography (2 → 1)

**Merged Package:** `ussy-steno`
**Migration Steps:**
1. Migrate `stenographussy` as base package
2. Review `stenography` for unique lightweight detectors
3. Port any unique detectors into `ussy-steno --fast` mode
4. Archive `stenography` repo

### 6.3 Cluster 3: Git Churn (2 → 1)

**Merged Package:** `ussy-churn`
**Migration Steps:**
1. Migrate `churnmap` as base package
2. Review `churnmapussy` for unique ASCII renderer or territorial-map features
3. Port unique features as alternative output modes
4. Archive `churnmapussy` repo

### 6.4 Cluster 4: Git Forensics (2 → 1)

**Merged Package:** `ussy-strata`
**Subcommands:**
- `ussy-strata survey` (stratagitussy)
- `ussy-strata missing` (unconformity)
- `ussy-strata timeline` (combined view)

**Migration Steps:**
1. Migrate `stratagitussy` as base package
2. Port `unconformity` code into `ussy_strata/missing.py`
3. Create combined `timeline` subcommand
4. Archive `unconformity` repo

### 6.5 Cluster 5: Dependency Analysis (4 keep separate)

**Packages:** `ussy-gridiron`, `ussy-chromato`, `ussy-cambium`, `ussy-stratax`
**Meta-Package:** `ussy-deps`

**Migration Steps:**
1. Migrate all 4 as separate packages in `packages/tools/deps/`
2. Create `ussy-deps` meta-package with unified CLI
3. No archiving needed

---

## 7. Communication Plan

### 7.1 Internal Communication

- **Week 1:** Announce migration plan to team, assign repo owners
- **Phase transitions:** Weekly standup updates on migration progress
- **Blockers:** Escalate in #ussyverse-dev Slack channel within 4 hours

### 7.2 External Communication

- **Week 1:** Pin migration notice to all source repo READMEs
- **Phase 2 start:** Publish blog post / GitHub Discussion announcing monorepo
- **Phase 5:** Final announcement with PyPI publication links
- **Ongoing:** Monitor archived repos for issues and redirect to monorepo

### 7.3 Stakeholder Notification Template

```markdown
## Migration Notice: [repo-name] → ussyverse Monorepo

**What:** The `[repo-name]` repository is being migrated into the `ussyverse` monorepo.

**Why:** Consolidated development, unified CI/CD, cross-tool integration.

**Where:** New location: `github.com/mojomast/ussyverse/tree/main/packages/[category]/[package-name]`

**When:** Migration completed on [date].

**Impact:**
- Existing pip installs continue to work (backward compatibility)
- New development happens in the monorepo
- Issues and PRs should be opened in the monorepo

**Questions:** Open a Discussion in the monorepo repository.
```

---

*Document Version: 1.0*
*Last Updated: April 2026*
