# Welcome to Ussyverse

The **ussyverse** is a unified monorepo consolidating ~50 Python CLI tools for code quality, security, forensics, and developer productivity.

## What is Ussyverse?

Originally 63 separate repositories on github.com/mojomast, these tools are now organized into a single codebase with shared libraries, unified CI/CD, and cross-tool integration.

**Design Goals:**
- **Developer velocity:** One clone, one sync, all tools available
- **Dependency minimalism:** ~22 packages installable with zero external dependencies
- **Backward compatibility:** Existing CLI commands continue to work
- **Cross-tool integration:** Shared libraries enable tools to compose cleanly

## Quickstart

```bash
# Clone the repository
git clone https://github.com/mojomast/ussyverse.git
cd ussyverse

# Install all tools
uv sync --extra all
```

## Package Categories Overview

| Category | Packages | Description |
|----------|----------|-------------|
| **Libraries** | 6 | Shared libraries: core, CLI, git, AST, SQLite, report |
| **Forensics** | 2 | Git forensics: ussy-strata, ussy-churn |
| **Security** | 1 | Steganography scanner: ussy-steno |
| **Quality** | 1 | Test suite quality: ussy-calibre |
| **Dependencies** | 4 | Dependency analysis: ussy-gridiron, ussy-chromato, ussy-cambium, ussy-stratax |
| **Governance** | 2 | Code governance: ussy-sentinel, ussy-parliament |
| **Developer Tools** | 4 | Dev utilities: ussy-snapshot, ussy-kintsugi, ussy-assay, ussy-petrichor |

## Learn More

- [Architecture](architecture.md) — Monorepo structure, build system, and CI/CD design
- [Contributing](contributing.md) — Development setup, workflow, and coding standards
- [Migration Guide](migration-guide.md) — Timeline and details for migrating from 63 separate repos
- [ADRs](adr/index.md) — Architecture Decision Records
