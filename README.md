# Ussyverse (monorepussy)

The Ussyverse Monorepo — 50+ Python tools for code quality, security, and forensics.

## Quickstart

```bash
# Clone the monorepo
git clone https://github.com/mojomast/monorepussy.git
cd monorepussy

# Install everything
uv sync --extra all --group dev

# Run all tests
pytest

# Serve documentation locally
mkdocs serve
```

## Package Index

| Category | Package | Description | Tests |
|----------|---------|-------------|-------|
| **Shared Libraries** | `ussy-core` | Config, logging, path utilities | — |
| | `ussy-cli` | CLI framework and output formatting | — |
| | `ussy-git` | Git operations wrapper | — |
| | `ussy-ast` | AST parsing helpers | — |
| | `ussy-sqlite` | SQLite utilities and schema migration | — |
| | `ussy-report` | Report formatting (JSON, SARIF, tables) | — |
| **Forensics** | `ussy-strata` | Git forensics (stratagitussy + unconformity) | 153 |
| **Security** | `ussy-steno` | Steganography scanners | 70 |
| **Visualization** | `ussy-churn` | Git churn visualization | 6 |
| **Quality** | `ussy-calibre` | Test suite quality (5 repos merged) | 124 |
| **Dependencies** | `ussy-gridiron` | Power-grid reliability analysis | 162 |
| | `ussy-chromato` | Chromatography risk profiling | 144 |
| | `ussy-cambium` | Grafting compatibility analysis | 187 |
| | `ussy-stratax` | Behavioral stability probing | 155 |
| | `ussy-deps` | Meta-package (unified CLI) | — |
| **Triage** | `ussy-triage` | Error forensics | 160 |
| **Governance** | `ussy-sentinel` | Immunological code governance | 117 |
| | `ussy-parliament` | Agent governance | 120 |
| **DevTools** | `ussy-snapshot` | Dev state management | 220 |
| | `ussy-kintsugi` | Bug repair annotation | 121 |
| | `ussy-assay` | Code grading | 163 |
| | `ussy-petrichor` | Config drift detection | 140 |
| **Tier 2 Tools** | `ussy-propriocept` | Agent/swarm infrastructure | 81 |
| | `ussy-curator` | Documentation health | 140 |
| | `ussy-operon` | Documentation health | 207 |
| | `ussy-portmore` | Dependency analysis | 298 |
| | `ussy-syntrop` | Code quality analysis | 135 |
| | `ussy-fossilrecord` | Test suite archaeology | 152 |
| | `ussy-telegrapha` | CI/pipeline reliability | 213 |
| | `ussy-mushin` | Config & drift | 135 |
| | `ussy-gamut` | CI/pipeline reliability | 145 |
| | `ussy-cyclone` | CI/pipeline reliability | 85 |
| | `ussy-isobar` | Code quality analysis | 152 |
| | `ussy-circadia` | Agent/swarm infrastructure | 107 |
| | `ussy-fatigue` | Fatigue analysis | 129 |
| | `ussy-endemic` | Endemic code detection | 170 |
| | `ussy-stemma` | Stemma analysis | 102 |
| | `ussy-crystallo` | Crystallography analysis | 124 |
| | `ussy-terrarium` | Ecosystem health | 254 |
| | `ussy-tarot` | Bayesian estimation | 140 |
| | `ussy-actuary` | Risk analysis | 141 |
| | `ussy-coroner` | CI forensics | 176 |
| | `ussy-mint` | Dependency provenance | 210 |
| | `ussy-dosemate` | CI pharmacokinetics | 130 |
| | `ussy-cavity` | Cavity analysis | 172 |
| | `ussy-aquifer` | Aquifer analysis | 167 |
| | `ussy-seral` | Seral analysis | 110 |
| | `ussy-plan9webplumb` | WebSocket plumbing | 57 |
| | `ussy-reverseoracle` | LLM evaluation | 12 |
| | `ussy-timeloom` | Git timeline | 16 |

## Architecture

```
monorepussy/
├── packages/
│   ├── libs/              # Shared libraries (6 packages)
│   ├── tools/
│   │   ├── forensics/     # Git forensics
│   │   ├── security/      # Security scanners
│   │   ├── visualization/ # Data visualization
│   │   ├── quality/       # Test quality
│   │   ├── deps/          # Dependency analysis
│   │   ├── triage/        # Error triage
│   │   ├── governance/    # Code governance
│   │   ├── devtools/      # Developer tools
│   │   └── ussy-*/        # Tier 2 tools (28 packages)
│   └── archive/           # Archived repos (13 stubs)
├── docs/                  # Documentation
├── scripts/               # Automation scripts
└── pyproject.toml         # Workspace configuration
```

## Development

```bash
# Run tests for a specific package
uv run --package ussy-triage pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy packages/
```

## Contributing

See [docs/contributing.md](docs/contributing.md) for development setup and contribution guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*The Ussyverse — 63 repos consolidated into 1 unified monorepo.*
