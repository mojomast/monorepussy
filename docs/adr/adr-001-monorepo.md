# ADR-001: Migrate Ussyverse to Monorepo

## Status

**Accepted**

## Context

The ussyverse ecosystem consists of 63 Python repositories under github.com/mojomast. These repositories were created organically over time, each addressing a specific developer tooling need with a unique scientific metaphor (metrology, immunology, geology, etc.).

### Problems with the Current State

1. **Duplicated Infrastructure:** Each of the 63 repos maintains its own CI configuration (or lacks one), linting rules, and dependency management. No CI/CD is configured across any repo.
2. **Code Duplication:** Common patterns (CLI argument parsing, SQLite utilities, git operations, AST helpers) are reimplemented 10+ times across the ecosystem.
3. **Cross-Tool Integration is Difficult:** Tools that should compose (e.g., dependency analyzers producing reports for governance tools) cannot easily share code or data formats.
4. **Dependency Management Overhead:** 63 separate lockfiles, version pins, and release cycles create significant maintenance burden.
5. **Onboarding Friction:** New contributors must clone, set up, and understand 63 different project structures.
6. **Inconsistent Quality:** Test coverage, documentation, and code style vary widely across repos.

### Evidence from Triage Report

- **60 repos** have real working code; **3** are stubs
- **~15 repos** use stdlib only (excellent for CI embedding)
- **Zero dependency conflicts** detected across all repos
- **98.4%** use `pyproject.toml` (near-universal standards adoption)
- **5 consolidation clusters** identified with clear merge rationale

## Decision

We will consolidate the ussyverse ecosystem into a single monorepo (`github.com/mojomast/ussyverse`) with the following characteristics:

1. **Tool Stack:** `uv` workspace with `hatchling` build backend
2. **Package Count:** ~47 packages (down from 63 repos via merges and archives)
3. **Shared Libraries:** 6 extracted shared libraries (`ussy-core`, `ussy-cli`, `ussy-git`, `ussy-ast`, `ussy-sqlite`, `ussy-report`)
4. **Naming:** `ussy-{tool}` prefix for all packages and CLI commands
5. **History Preservation:** `git filter-repo` for all migrated repos
6. **Backward Compatibility:** Legacy CLI aliases with 12-month deprecation period
7. **Documentation:** MkDocs with mkdocstrings, complete before code migration

## Consequences

### Positive

1. **Unified CI/CD:** Single GitHub Actions configuration tests all packages with intelligent change detection and 20 parallel runners.
2. **Eliminated Duplication:** 6 shared libraries replace 20+ redundant implementations.
3. **Single Lockfile:** One `uv.lock` ensures dependency consistency across all tools.
4. **Cross-Tool Integration:** Tools can import from each other and from shared libraries cleanly.
5. **Faster Onboarding:** One clone, one sync, all tools available.
6. **Consistent Standards:** One ruff config, one mypy config, one pytest config.
7. **Simpler Releases:** Tag-based per-package releases with OIDC PyPI publishing.
8. **Reduced Maintenance:** Changes to shared libraries propagate to all consumers in a single PR.

### Negative

1. **Larger Clone Size:** Monorepo will be larger than individual repos (mitigated by sparse checkout support).
2. **Complexer Git History:** Merged histories from 50+ repos create a more complex graph (mitigated by `git filter-repo` subdirectory filtering).
3. **Broader Blast Radius:** Changes to shared libraries can affect many packages (mitigated by comprehensive integration tests).
4. **Permission Complexity:** Finer-grained access control is harder in a monorepo (mitigated by CODEOWNERS).
5. **Migration Effort:** ~15 weeks of engineering time to complete migration.

### Neutral

1. **"ussy" Naming:** Retained as brand identity, moved from suffix to prefix.
2. **Tier 3 Repos:** 13 repos archived, not migrated (games, stubs, security concerns).

## Alternatives Considered

### Alternative 1: Git Submodules

**Approach:** Keep repos separate, reference them from a meta-repo via git submodules.

**Rejected because:**
- Does not solve code duplication or shared library problem
- Submodules are painful to update and synchronize
- Still requires 63 separate CI configurations
- Cross-repo refactoring remains difficult

### Alternative 2: Meta-Repo with Scripts

**Approach:** Keep repos separate, use a meta-repo with scripts to coordinate builds and releases.

**Rejected because:**
- Scripts add complexity without solving core problems
- No unified dependency resolution
- Still requires cloning 63 repos for full development
- Cross-tool integration limited to script-based orchestration

### Alternative 3: Maintain Status Quo

**Approach:** Continue maintaining 63 separate repositories.

**Rejected because:**
- Maintenance burden is unsustainable as ecosystem grows
- No path to cross-tool integration
- Inconsistent quality and standards
- High barrier to contribution

## Implementation Plan

See [MIGRATION_PLAN.md](../MIGRATION_PLAN.md) for detailed timeline and checklist.

**Summary:**
- Phase 1 (Weeks 1-2): Foundation + pilot migration
- Phase 2 (Weeks 3-6): Tier 1 clusters and individual repos
- Phase 3 (Weeks 7-10): Tier 1 remaining + Tier 2 batch 1
- Phase 4 (Weeks 11-14): Tier 2 completion
- Phase 5 (Week 15+): Tier 3 archive + cleanup

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Developer setup | `uv sync` installs all tools in <30s |
| Test speed | `pytest` from root runs in <5 minutes |
| Documentation | `mkdocs serve` renders complete docs for all tools |
| History preservation | All migrated repos retain full git history |
| Backward compatibility | All legacy CLI commands work with deprecation warnings |
| Dependency minimization | 22+ packages installable with zero external deps |

## Related Decisions

- ADR-002: Package Naming Convention (`ussy-{tool}` prefix)
- ADR-003: Shared Library Extraction (6 libraries)
- ADR-004: CI/CD Architecture (uv + pytest-xdist + 20 parallel runners)
- ADR-005: Documentation Strategy (MkDocs + mkdocstrings)

## References

- [Ussyverse Triage Report](../../ussyverse_triage_report.md)
- [MONOREPO_DESIGN.md](../../MONOREPO_DESIGN.md)
- [MIGRATION_PLAN.md](../../MIGRATION_PLAN.md)
- [PACKAGE_MATRIX.md](../../PACKAGE_MATRIX.md)
- [uv Workspaces Documentation](https://docs.astral.sh/uv/concepts/workspaces/)
- [Hatchling Build Backend](https://hatch.pypa.io/latest/config/build/)

---

**Related Documents:**
- [Architecture](../architecture.md)
- [Contributing](../contributing.md)
- [Migration Guide](../migration-guide.md)
- [ADR Index](index.md)

*ADR Number: 001*
*Date: April 2026*
*Author: Platform Engineering Team*
*Status: Accepted*
