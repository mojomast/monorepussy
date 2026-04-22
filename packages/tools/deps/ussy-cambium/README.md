# ussy-cambium — Horticultural Grafting Science for Dependency Compatibility Analysis

> **Migrated**: This package was originally `cambiumussy` and has been migrated into the [ussyverse monorepo](https://github.com/mojomast/ussyverse).

## Overview

ussy-cambium applies **horticultural grafting science** to dependency compatibility analysis. Instead of binary semver pass/fail, it produces a **Graft Compatibility Index (GCI)** — a time-dependent, multi-dimensional compatibility score that provides continuous, predictive assessment of dependency health.

### Key Innovations

| Dimension | Traditional Tool | ussy-cambium |
|-----------|-----------------|--------------|
| Compatibility | Binary semver pass/fail | Continuous 0-1 API surface match score |
| Interface alignment | Type checker pass/fail | Multi-dimensional alignment with heatmap |
| Adapter quality | Not measured | Callus formation model with trajectory |
| Drift prediction | None | Predictive time-to-breakage forecast |
| Bond strength | CI pass/fail at one point | Longitudinal trajectory with decay detection |
| Dwarfing detection | Not measured | Capability throughput analysis |

## Installation

```bash
pip install ussy-cambium
```

Requires Python 3.11+. No external runtime dependencies (stdlib only).

## Usage Examples

### Scan a project

```bash
# Full GCI assessment for all dependencies
ussy-cambium scan ./myproject

# JSON output
ussy-cambium --json scan ./myproject
```

> **Legacy alias**: The `cambium` command is deprecated and will be removed in a future release. Please use `ussy-cambium`.

### Compatibility analysis

```bash
# Detailed scion/rootstock compatibility between two modules
ussy-cambium compatibility consumer.py provider.py

# Named modules (uses synthetic analysis)
ussy-cambium compatibility authlib requests
```

### Interface alignment

```bash
# Cambium alignment score with heatmap
ussy-cambium alignment consumer.py provider.py

# JSON output
ussy-cambium --json alignment consumer.py provider.py
```

### Drift forecasting

```bash
# Predictive drift breakage timeline
ussy-cambium drift-forecast my-dependency

# Custom drift parameters
ussy-cambium drift-forecast my-dependency \
  --delta-behavior 0.05 \
  --delta-contract 0.03 \
  --delta-environment 0.02 \
  --lambda-s 8.0 \
  --d-critical 1.5
```

### Bond trajectory

```bash
# Integration bond strength trajectory
ussy-cambium bond-traj my-dependency

# Custom bond parameters
ussy-cambium bond-traj my-dependency --b-max 0.9 --k-b 0.25 --t50 4.0
```

### Dwarfing analysis

```bash
# Find dwarfing dependencies in a project
ussy-cambium dwarfing ./myproject
```

### GCI history

```bash
# GCI trend over time from stored data
ussy-cambium gci-history my-dependency --limit 20
```

### Python module support

```bash
python -m ussy_cambium scan ./myproject
```

## Architecture

```
src/ussy_cambium/
├── __init__.py         # Package init
├── __main__.py         # python -m ussy_cambium support
├── legacy.py           # Deprecated cambium CLI alias
├── models.py           # Core data models (CompatibilityScore, AlignmentScore, etc.)
├── extractor.py        # AST-based interface extraction
├── compatibility.py    # Scion/rootstock API surface match
├── alignment.py        # Interface cambium alignment score
├── callus.py           # Adapter generation dynamics (callus formation model)
├── drift.py            # Predictive drift breakage analysis
├── bond.py             # Integration bond strength trajectory
├── dwarfing.py         # Constraint propagation / dwarfing detection
├── gci.py              # Unified Graft Compatibility Index
├── scanner.py          # Full project scanning
├── storage.py          # JSON + SQLite persistence
└── cli.py              # Command-line interface
```

### Core Models

- **CompatibilityScore** — API surface match: `C(a,b) = Σ(α_i · compat_i(a, b))`
- **AlignmentScore** — Interface precision: `A = w₁·A_name + w₂·A_signature + w₃·A_semantic`
- **CallusDynamics** — Adapter trajectory: `M(t) = K / (1 + (K/M₀ - 1) · e^(-r·t))`
- **DriftDebt** — Drift prediction: `t_break = -λ · ln(1 - D_critical / (Δ₀ · λ))`
- **BondStrength** — Bond trajectory: `B(t) = B_max / (1 + e^(-k·(t - t₅₀)))`
- **DwarfFactor** — Constraint propagation: `D = Capability_with / Capability_without`
- **GCISnapshot** — Unified metric: `GCI = C · A · Q · (1-D/D_c) · B/B_max · V`

### Key Property

GCI is **multiplicative** — any zero component kills the entire score, modeling the real property that one failed dimension destroys the integration, just like a failed graft.

## License

MIT
