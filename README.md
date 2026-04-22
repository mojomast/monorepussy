# Ussyverse

The Ussyverse is a unified monorepo consolidating 50+ Python CLI tools for code quality, security, forensics, and developer productivity.

## Quickstart

```bash
# Install everything
uv sync --extra all

# Run all tests
pytest

# Serve documentation locally
mkdocs serve
```

## Package Index

| Category | Package | Description |
|----------|---------|-------------|
| **Shared Libraries** | `ussy-core` | Config, logging, path utilities |
| | `ussy-cli` | CLI framework and output formatting |
| | `ussy-git` | Git operations wrapper |
| | `ussy-ast` | AST parsing helpers |
| | `ussy-sqlite` | SQLite utilities and schema migration |
| | `ussy-report` | Report formatting (JSON, SARIF, tables) |
| **Forensics** | `ussy-strata` | Git forensics (stratagitussy + unconformity) |
| **Security** | `ussy-steno` | Steganography scanners |
| **Visualization** | `ussy-churn` | Git churn visualization |
| **Quality** | `ussy-calibre` | Test suite quality (5 repos merged) |
| **Dependencies** | `ussy-gridiron` | Power-grid reliability analysis |
| | `ussy-chromato` | Chromatography risk profiling |
| | `ussy-cambium` | Grafting compatibility analysis |
| | `ussy-stratax` | Behavioral stability probing |
| **Triage** | `ussy-triage` | Error forensics |
| **Governance** | `ussy-sentinel` | Immunological code governance |
| | `ussy-parliament` | Agent governance |
| **DevTools** | `ussy-snapshot` | Dev state management |
| | `ussy-kintsugi` | Bug repair annotation |
| | `ussy-assay` | Code grading |
| | `ussy-petrichor` | Config drift detection |

## Contributing

See [docs/contributing.md](docs/contributing.md) for development setup and contribution guidelines.
