# Chromato

**Chromatographic Dependency Separation & Profiling Tool**

Chromato applies liquid chromatography metaphors to dependency analysis — dependencies pass through a virtual "column" and emerge at different "retention times" based on coupling depth, update frequency, and risk profile. The resulting chromatogram reveals the true composition of your dependency mixture.

## Overview

Package managers show dependencies as flat lists or tree graphs. Chromato separates them into a **chromatogram** — a time-series of "peaks" where each peak represents a dependency cluster with measurable properties:

- **Retention Time**: How long a dependency is "retained" in the column (risk indicator)
- **Peak Shape**: Diagnoses dependency health (focused, bloated, transitioning, dragging)
- **Co-elution**: Detects entangled dependencies (circular deps, version conflicts)
- **Gradient Profiling**: Multiple analysis "solvents" (coupling, risk, freshness, license)

## Installation

```bash
pip install -e .
```

## Usage Examples

### Generate full chromatogram
```bash
chromato scan ./requirements.txt --format chromatogram
```

### Run specific solvent analysis
```bash
chromato scan ./package.json --solvent risk
```

### Compare two versions (differential chromatography)
```bash
chromato diff ./requirements.txt ./requirements-new.txt
```

### Detect co-elutions (entangled dependencies)
```bash
chromato coelute ./package.json --threshold 0.3
```

### Profile peak shapes (dependency health check)
```bash
chromato peaks ./Cargo.toml --diagnose
```

### Export as JSON for CI integration
```bash
chromato scan ./go.mod --format json --exit-on-risk 0.8
```

### Run as module
```bash
python -m chromato scan ./requirements.txt
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 CHROMATO ENGINE                   │
├──────────┬──────────────┬────────────────────────┤
│  Sample  │  Column      │  Detector              │
│  Injector│  (Separation)│  (Peak Identification) │
├──────────┴──────────────┴────────────────────────┤
│          Dependency Graph Parser                  │
│  (requirements.txt, package.json, Cargo.toml,    │
│   go.mod, pom.xml, gemspec)                      │
├──────────────────────────────────────────────────┤
│          Retention Time Calculator                │
│  (coupling depth × risk weight × freshness)      │
├──────────────────────────────────────────────────┤
│          Chromatogram Renderer                    │
│  (ASCII chart, JSON)                             │
└──────────────────────────────────────────────────┘
```

### Metaphor Mapping

| Liquid Chromatography | Chromato (Software) |
|---|---|
| Complex chemical mixture | Project dependency graph |
| Chromatography column | Dependency separation pipeline |
| Mobile phase (solvent flow) | Analysis traversal of the dependency graph |
| Stationary phase (column packing) | Coupling/risk analysis rules |
| Analytes (chemical species) | Individual dependencies |
| Retention time | Emergence rank (low coupling = fast, high coupling = slow) |
| Peak area | Dependency "mass" (dependents × risk weight) |
| Peak width | Dependency "purity" (narrow = single-purpose, wide = multi-concern) |
| Co-elution | Dependencies that cannot be cleanly separated |
| Gradient elution | Changing analysis depth mid-scan |

### Supported File Formats

- `requirements.txt` (Python / pip)
- `package.json` (Node.js / npm)
- `Cargo.toml` (Rust / cargo)
- `go.mod` (Go modules)
- `pom.xml` (Java / Maven)
- `*.gemspec` (Ruby gems)
