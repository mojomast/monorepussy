# Strata — Geological Semver for Codebase Archeology

> Treat your dependency tree as a geological formation. Measure behavioral stability, detect seismic activity, and watch for erosion across versions.

## What is Strata?

Strata applies geological metaphors to software dependency analysis. Instead of just checking version numbers, it runs **behavioral probes** against actual API surfaces to measure:

- **🪨 Bedrock Score** — How consistently has a function behaved across versions? (0-100)
- **⚡ Seismic Hazard** — How frequently does behavior shift between versions?
- **🌋 Fault Lines** — Boundaries between rock-solid and unstable API regions in the same package
- **🏜️ Erosion** — Slow, gradual deprecation where features silently break across versions

## Stability Tiers

| Tier | Score | Icon | Meaning |
|------|-------|------|---------|
| Bedrock | 90-100 | █ | Rock-solid, never changed |
| Stable | 65-89 | ▊ | Mostly stable, rare quakes |
| Hazard | 35-64 | ▄ | Frequent behavioral changes |
| Quicksand | 15-34 | ▂ | Unstable, avoid relying on this |
| Deprecated | 0-14 | ▁ | Effectively dead |

## Installation

```bash
pip install strata
```

Or from source:

```bash
git clone https://github.com/mojomast/strataussy.git
cd strataussy
pip install -e ".[dev]"
```

## Quick Start

### Scan a lockfile for hazards

```bash
# Scan npm, pip, yarn, or poetry lockfiles
strata scan package-lock.json
strata scan requirements.txt
strata scan Pipfile.lock
strata scan poetry.lock
```

Output:
```
Found 12 dependencies in package-lock.json

🪨 STABLE ZONES
  lodash@4.17.21      ████░  Stable (85/100)
  express@4.18.2      ████░  Stable (78/100)

⚡ SEISMIC HAZARDS
  react@18.2.0        ▓▓▓░░  Moderate quakes (0.22/version)

🌋 FAULT LINES
  lodash vs lodash/fp — Bedrock (95) vs Hazard (35)

🏜️ EROSION WARNINGS
  moment@2.29.4       Declining: 100% → 70% pass rate
```

### Generate behavioral probes

```bash
# Auto-generate probes for a package
strata probe numpy

# Target a specific function
strata probe json --function dumps

# Save to file
strata probe numpy --output probes.json

# Save to local registry
strata probe numpy --save
```

### Run probes against a version

```bash
# Run auto-generated probes
strata run numpy --version 1.24.0

# Run from a probe file
strata run numpy --probes-file probes.json --version 1.24.0

# Save results
strata run numpy --version 1.24.0 --output results.json
```

### Analyze a package's stability

```bash
# Full stratigraphic analysis
strata analyze numpy --data probe_results.json
```

### Compare two versions

```bash
# Diff behavioral profiles
strata diff numpy 1.23.0 1.24.0 --data probe_results.json
```

### View the geological legend

```bash
strata legend
```

## Architecture

```
strata/
├── models.py              # Core data models (Probe, BedrockReport, etc.)
├── cli.py                 # CLI interface (scan, analyze, diff, probe, run, legend)
├── diff.py                # Version comparison engine
├── analysis/
│   ├── bedrock.py         # Stability scoring (0-100)
│   ├── seismic.py         # Behavioral change detection
│   ├── faults.py          # Fault line identification
│   ├── erosion.py         # Gradual deprecation detection
│   └── stratigraphic.py   # Orchestrator combining all analyses
├── scanner/
│   ├── scanner.py         # Project-wide dependency scanning
│   └── lockfile.py        # Multi-format lockfile parser
├── probes/
│   ├── generator.py       # Auto-generate probes via inspection
│   ├── runner.py          # Execute probes (live + simulated)
│   └── loader.py          # Load probe definitions from YAML
├── render/
│   └── ascii.py           # Terminal visualization with Unicode blocks
└── registry/
    ├── local.py           # Local filesystem probe registry
    └── remote.py          # Remote community registry client
```

## Geological Concepts

### Bedrock Score
Computed from three factors:
- **Version stability (60%)** — Percentage of versions where all probes passed
- **Consistency (25%)** — Ratio of non-change transitions across the timeline
- **Time (15%)** — How long the API has been consistently stable

### Seismic Hazard
Measures behavioral **quakes** — transitions where a probe goes from pass→fail or fail→pass between versions. Reported as quakes per version:
- **Dormant** (< 0.05) — Essentially no changes
- **Minor** (0.05-0.15) — Occasional shifts
- **Moderate** (0.15-0.35) — Regular behavioral changes
- **Major** (0.35-0.60) — Frequent breakage
- **Catastrophic** (> 0.60) — Nearly every version changes behavior

### Fault Lines
A **fault line** exists when two functions in the same package have dramatically different bedrock scores (default gap: 40+ points). This indicates the package has regions of bedrock stability alongside quicksand — use the stable parts, avoid the unstable ones.

### Erosion
**Erosion** is detected when a function's probe pass rate steadily declines across versions. Unlike quakes (sudden shifts), erosion is a slow, quiet deprecation — features that gradually break over time. Detected via linear regression on pass rates.

## Probe Format

Probes are defined in YAML:

```yaml
package: json
function: dumps
probes:
  - name: json_dumps_list
    input:
      obj: [1, 2, 3]
    output: "[1, 2, 3]"
    returns_type: str

  - name: json_dumps_dict
    input:
      obj:
        key: value
    returns_type: str
```

## Output Formats

All commands support `--json` for machine-readable output and `--no-color` for piping.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
