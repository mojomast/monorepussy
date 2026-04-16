# Mint — Numismatic Package Provenance & Version Classification

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Mint** applies numismatics — mint mark identification, die variety classification, metal composition analysis, Sheldon grading, counterfeiting detection, hoard analysis, provenance chains, and debasement curves — to classify, grade, and verify software package versions.

Every package version is a coin struck by a maintainer. Its value depends on where it was struck (registry), how it was struck (build fingerprint), what it contains (dependency alloy), and what condition it's in (quality grade).

## Installation

```bash
pip install .
# Or in development mode:
pip install -e .
```

## Usage

### Grade a Package

Assign a Sheldon numismatic grade (1-70) to a package version:

```bash
mint grade lodash@4.17.21
# → lodash@4.17.21: MS-62 (Mint State)
#   Strike: 65/70  Surface: 60/70  Luster: 58/70  Eye Appeal: 64/70
#   Fineness: 0.962  Origin: npm/publisher:lodash-team  Provenance: Level 0
```

### Analyze a Lockfile (Hoard Analysis)

Identify dependency clusters in a lockfile:

```bash
mint hoard package-lock.json
# → Hoard Analysis: 12 packages across 3 cluster(s)
#   🟢 Cluster "express" (4 pkgs, contamination: 0.12, common maintainers: none)
#   🟢 Cluster "mongoose" (3 pkgs, contamination: 0.25, common maintainers: none)
#   🟢 Cluster "lodash" (1 pkgs, contamination: 0.15, common maintainers: none)
```

### Authenticate a Package

Detect counterfeits (typosquatting, dependency confusion, account takeover):

```bash
mint authenticate xpress
# → ✗ xpress — Typosquat of "express" (Levenshtein distance=1) (confidence: 85.7%)

mint authenticate --lockfile package-lock.json
# → Scanning 12 packages...
#   ✗ xpress — Typosquat of "express" (Levenshtein distance=1)
```

### Track Debasement

Track how a package's quality degrades over versions:

```bash
mint debasement lodash
# → lodash debasement curve:
#   lodash@4.0.0 (2020) Mint State 65 █████████████████████████████▍
#   lodash@4.5.0 (2020) Mint State 63 ███████████████████████████
#   ...
#   Rate: +0.83 grade/month
#   Projected P-1: 2025-09
#   Recoinage events: None
```

### Python API

```python
from mint.sheldon import sheldon_grade, grade_breakdown
from mint.composition import compute_fineness
from mint.counterfeit import authenticate_package
from mint.debasement import analyze_debasement
from mint.hoard import analyze_hoard
from mint.lockfile import parse_package_lock_json

# Sheldon grading
grade = sheldon_grade(0.9, 0.8, 0.85, 0.75)  # Returns 1-70

# Fineness (purity)
fineness = compute_fineness(own_loc=5000, vendored_loc=200)  # Returns 0.0-1.0

# Counterfeit detection
findings = authenticate_package("xpress", known_packages=["express"])

# Hoard analysis
packages = parse_package_lock_json("package-lock.json")
hoards = analyze_hoard(packages)
```

## Architecture

```
MINT ENGINE
├── mint/          Core package
│   ├── models.py         Data models (MintMark, Composition, Hoard, etc.)
│   ├── sheldon.py        Sheldon grading (1-70 scale)
│   ├── composition.py    Fineness & alloy analysis
│   ├── counterfeit.py    Counterfeit detection (typosquat, dep confusion, etc.)
│   ├── debasement.py     Debasement curve tracking
│   ├── hoard.py          Lockfile cluster analysis (connected-components)
│   ├── provenance.py     Provenance chain verification
│   ├── lockfile.py       Lockfile parsing (package-lock.json)
│   ├── distance.py       Pure Python Levenshtein distance
│   ├── cli.py            CLI interface (argparse)
│   └── __main__.py       python -m mint support
└── tests/         Test suite
```

### Core Mapping

| Numismatics | Mint (Software) |
|---|---|
| **Coin** | A resolved package version |
| **Mint mark** | Provenance: registry + publisher + build signature |
| **Metal composition** | Dependency alloy: transitive dependency mix |
| **Fineness** | Purity ratio: own code vs. vendored/bundled |
| **Sheldon scale (1-70)** | Version quality grade |
| **Counterfeiting** | Supply chain attack (typosquatting, account takeover) |
| **Hoard** | Dependency cluster in a lockfile |
| **Debasement** | Quality degradation over versions |
| **Provenance chain** | Chain of custody: source → build → publish |

### Key Formulas

- **Sheldon Grade**: `harmonic_mean(strike, surface, luster, eye_appeal) × 70`
- **Fineness**: `own_loc / (own_loc + vendored_loc + bundled_loc)`
- **Debasement Rate**: `Σ(grade_i - grade_{i+1}) / Σ(time_{i+1} - time_i)`
- **Contamination Risk**: `overlap×0.4 + grade_vulnerability×0.3 + provenance_gaps×0.3`

## Dependencies

**Zero external dependencies** — Mint uses only Python 3.11+ stdlib. This is intentional: a provenance tool should itself have MS-70 grade purity.

## License

MIT
