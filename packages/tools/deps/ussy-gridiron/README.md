# Gridiron — Power Grid Reliability Engineering for Dependency Ecosystem Health

**Gridiron** applies power grid reliability engineering — the mathematical framework that keeps electrical grids from collapsing — to dependency ecosystem health analysis. Every concept in grid reliability maps to a dependency health dimension that existing tools don't measure.

## Overview

Dependency health tools treat packages as independent units, not as an interconnected system where failure propagates. Gridiron models your dependency ecosystem as a power grid and runs the same analyses that grid operators use to prevent blackouts:

| Power Grid Concept | Dependency Equivalent | Gridiron Output |
|---|---|---|
| N-1 contingency | Single-point-of-failure via component removal | N-1 compliance score + SPOF register |
| Frequency regulation (droop/AGC) | Three-tier response to version shocks | Frequency deviation report + droop map |
| Optimal power flow | Minimum-risk dependency selection | Optimal dispatch + congestion report |
| Protection coordination | Error handling timing across layers | CTI violations + zone coverage map |
| Voltage collapse / QV curves | Capability margin and collapse proximity | Health voltage map + Q margin |
| IEEE 1547 interconnection | Formal API compliance certification | Grid code compliance report |

## Installation

```bash
pip install -e .
```

Or install from source:

```bash
git clone <repo-url>
cd gridiron
pip install -e .
```

**Requirements**: Python 3.9+ (zero external dependencies — stdlib only).

## Usage

### CLI Commands

```bash
# N-1 contingency analysis — find single points of failure
gridiron n1 /path/to/project

# Frequency monitoring — analyze version shock response
gridiron frequency /path/to/project
gridiron frequency /path/to/project --shock react

# Optimal dependency dispatch — find minimum-risk package set
gridiron dispatch /path/to/project --optimize

# Protection coordination — check error handler timing
gridiron relay /path/to/project

# Voltage/capability analysis — detect approaching collapse
gridiron voltage /path/to/project

# Grid code inspection — IEEE 1547 compliance check
gridiron inspect /path/to/project
gridiron inspect /path/to/project --package specific-pkg

# Full Grid Reliability Assessment
gridiron report /path/to/project --full

# JSON output
gridiron --format json n1 /path/to/project
```

### Python API

```python
from gridiron.graph import DependencyGraph
from gridiron.models import PackageInfo, DependencyEdge
from gridiron.instruments.contingency import ContingencyAnalyzer

# Build a dependency graph
graph = DependencyGraph()
graph.add_package(PackageInfo(name="my-app", version="1.0.0"))
graph.add_package(PackageInfo(name="flask", version="3.0.0", is_direct=True))
graph.add_edge(DependencyEdge(source="my-app", target="flask"))

# Run N-1 contingency analysis
analyzer = ContingencyAnalyzer(graph)
report = analyzer.analyze()
print(f"N-1 Compliance: {report.compliance_score:.1f}%")
for spof in report.spof_register:
    print(f"  SPOF: {spof.removed_package} (blast radius: {spof.blast_radius})")
```

### Input Formats

Gridiron parses dependency manifests from:
- **package.json** (Node.js) — `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`
- **requirements.txt** (Python) — with full version specifier support
- **pyproject.toml** (Python) — PEP 621 and Poetry formats

Point the CLI at a project directory and it will auto-discover manifests.

## Architecture

```
gridiron/
├── __init__.py          # Package metadata
├── __main__.py          # python -m gridiron support
├── cli.py               # Argparse CLI with 7 subcommands
├── models.py            # Data models (dataclasses, enums)
├── graph.py             # DependencyGraph with traversal & matrix ops
├── db.py                # SQLite storage for analysis results
├── report.py            # Text and JSON report formatting
├── parsers/
│   ├── package_json.py  # package.json parser
│   ├── requirements_txt.py  # requirements.txt parser
│   └── pyproject_toml.py    # pyproject.toml parser
└── instruments/
    ├── contingency.py   # Instrument 1: N-1 SPOF analysis
    ├── frequency.py     # Instrument 2: Version shock response
    ├── flow_optimizer.py # Instrument 3: Optimal dependency dispatch
    ├── relay.py         # Instrument 4: Protection coordination
    ├── voltage.py       # Instrument 5: Capability & collapse
    └── grid_code.py     # Instrument 6: IEEE 1547 compliance
```

### The Six Instruments

1. **Contingency Analyzer** — Removes each dependency one at a time and checks if the system survives. Computes N-1 compliance score and identifies Single Points of Failure ranked by blast radius.

2. **Frequency Monitor** — Models version shock dynamics using three-tier frequency regulation: primary (automatic semver resolution), secondary (lockfile updates), tertiary (manual migration). Computes frequency deviation and droop compliance.

3. **Flow Optimizer** — Formulates dependency selection as optimal power flow: minimize total risk subject to import demand constraints and coupling limits. Identifies congested packages and overcoupled pairs.

4. **Relay Coordinator** — Maps error handlers to protection relays and checks coordination time intervals. Detects CTI violations, blind spots (uncovered failures), and TCC overlaps (colliding retry schedules).

5. **Voltage Analyst** — Computes health voltage per package using maintainer activity, release frequency, and quality signals. Calculates QV margin and Collapse Proximity Index (CPI). Identifies packages approaching nose-point collapse.

6. **Grid Code Inspector** — Applies IEEE 1547 interconnection standard to package APIs: voltage regulation (semver bounds), frequency ride-through (version bump tolerance), power quality (side-effect ratio), reactive capability (metadata completeness), and category certification (I/II/III).

### Key Mappings

| Power Grid | Dependency Ecosystem |
|---|---|
| Bus | Package |
| Transmission line | Dependency edge |
| Generator output | Package export capacity |
| Load demand | Import demand |
| Frequency | Version resolution success rate |
| Voltage | Package health score |
| Reactive power | Capability support (types, docs, tests) |
| Reactance | API churn / semantic distance |
| Fault current | Error signal magnitude |
| Relay / breaker | Error handler |
| CTI | Handler timing gap |
| IEEE 1547 category | API compliance tier |

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pip install pytest
pytest tests/ -v

# Run with Python module
python -m gridiron n1 /path/to/project
```

## License

MIT
