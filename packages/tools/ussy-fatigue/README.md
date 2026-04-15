# Fatigue — Fracture Mechanics for Code Decay Prediction

**Fatigue** applies fracture mechanics — specifically Paris' Law of fatigue crack growth — to model and predict code decay. It detects "cracks" (flaws, workarounds, tech debt markers), measures "stress intensity" (coupling × change frequency × complexity), models crack growth rate using a Paris' Law-derived equation, and predicts time-to-failure for each module.

## Overview

Static analysis tools treat code quality as a snapshot — "this module has complexity 47" — with no model for how quality *degrades over time under repeated changes*. Fatigue closes this gap by applying the physics of fatigue crack growth to software:

- **Crack initiation** = the first introduction of a flaw (`# HACK`, a 20-argument function, a circular dependency)
- **Crack propagation** = how flaws grow under cyclic loading (each commit = a load cycle)
- **Stress intensity factor (K)** = coupling × churn × complexity / coverage — captures the *environmental stress* acting on a flaw
- **Fracture toughness (K_Ic)** = the threshold beyond which debt grows uncontrollably with every change
- **Endurance limit (K_e)** = the stress level below which a module can be modified indefinitely without accumulating accelerating debt
- **Crack arrest** = a structural intervention (refactoring, interface extraction, test coverage) that reduces stress intensity below K_Ic

### Key Formula

```
K = (coupling × churn_rate × complexity) / (test_coverage + 0.1)
da/dN = C × (ΔK)^m   (Paris' Law)
```

Where:
- **K** = stress intensity factor
- **da/dN** = crack growth rate (debt per load cycle)
- **ΔK** = stress intensity range (change in K)
- **C** = crack growth coefficient (codebase-specific material constant)
- **m** = stress exponent (brittleness: m > 3 is brittle, m ≈ 1-2 is ductile)

## Installation

```bash
# From source
git clone <repo-url>
cd fatigue
pip install -e .

# Or directly
pip install .
```

**Zero external dependencies** — uses only Python's standard library:
- `ast` for code parsing
- `subprocess` for git commands
- `math` for numerical computation
- `argparse` for CLI

## Usage Examples

### Scan for Cracks

```bash
# Scan a directory for cracks and compute stress intensity
fatigue scan src/

# JSON output for integration
fatigue scan src/ --format json
```

Output includes:
- Crack types and counts (TODO/FIXME/HACK, high complexity, missing error handling, circular dependencies, god classes)
- Average severity per crack type
- Critical cracks (K > K_Ic) with stress intensity and growth rate

### Predict Decay

```bash
# Predict decay trajectory for a module
fatigue predict src/payments/stripe/ --horizon 6

# With custom material constants
fatigue predict src/payments/ --C 0.02 --m 3.0 --K-Ic 35.0
```

Output includes:
- Current debt magnitude and stress intensity
- Growth rate (da/dN)
- Projected decay trajectory over the horizon
- Time to critical debt
- Recommended crack arrest strategies

### What-If Analysis

```bash
# Simulate extracting an interface
fatigue what-if src/payments/stripe/ --refactor extract_interface --in 2

# Available interventions:
#   extract_interface — reduces coupling
#   add_tests — increases coverage, reduces stress
#   break_god_class — reduces complexity
#   reduce_churn — stabilizes change frequency
#   full_refactor — comprehensive refactoring
```

Output includes:
- Debt at horizon WITHOUT intervention
- Debt at horizon WITH intervention
- ROI (debt prevented by intervention)

### Calibrate Material Constants

```bash
# Calibrate from project directory
fatigue calibrate src/

# With historical data file
fatigue calibrate src/ --data calibration_data.json
```

Calibration data format (JSON):
```json
[
  {"delta_K": 5.0, "growth_rate": 0.05},
  {"delta_K": 10.0, "growth_rate": 0.25},
  {"delta_K": 20.0, "growth_rate": 1.50}
]
```

Output includes:
- Calibrated C and m values
- Endurance limit and fracture toughness
- Model fit (R²)

## Architecture

```
fatigue/
├── __init__.py          # Package metadata, default constants
├── __main__.py          # python -m fatigue support
├── models.py            # Data models (Crack, ModuleMetrics, StressIntensity, etc.)
├── scanner.py           # Crack detection via AST parsing
│   ├── TODO/FIXME/HACK detection (regex on comments)
│   ├── High complexity detection (cyclomatic complexity via ast)
│   ├── Missing error handling detection (risky calls without try/except)
│   ├── God class detection (too many methods/complexity)
│   ├── Circular dependency detection (graph DFS)
│   └── Module metrics computation (LOC, complexity, nesting, fan-out)
├── stress.py            # Stress intensity calculation
│   ├── K = coupling × churn × complexity / (coverage + 0.1)
│   ├── Coupling from import graph
│   ├── Churn rate from git log
│   ├── Test coverage estimation
│   └── Vicinity churn (2-hop dependency graph)
├── paris.py             # Paris' Law calibration
│   ├── da/dN = C × (ΔK)^m
│   ├── Log-linear regression for C and m calibration
│   ├── Endurance limit estimation
│   ├── Fracture toughness estimation
│   └── Per-module calibration
├── predictor.py         # Decay prediction
│   ├── Trajectory projection
│   ├── Time-to-failure calculation
│   ├── Debt estimation from cracks
│   └── Crack arrest strategy recommendations
├── whatif.py            # What-if analysis
│   ├── Intervention simulation (extract interface, add tests, etc.)
│   ├── ROI computation
│   └── Before/after comparison
├── monitor.py           # Structural health monitoring
│   ├── Git commit change detection
│   ├── K history tracking
│   └── Alert formatting
└── cli.py               # Command-line interface
    ├── scan — detect cracks and compute stress
    ├── predict — forecast decay trajectory
    ├── what-if — simulate interventions
    └── calibrate — determine material constants
```

### The Fracture Mechanics Metaphor (Functional, Not Decorative)

| Materials Science | Fatigue (Code) |
|---|---|
| Crack | TODO, FIXME, HACK, high complexity, god class |
| Load cycle | Git commit touching the module |
| Stress intensity K | coupling × churn × complexity / coverage |
| Fracture toughness K_Ic | Threshold for catastrophic debt growth |
| Endurance limit K_e | Threshold below which no fatigue occurs |
| Paris' Law da/dN = C(ΔK)^m | Debt growth rate per commit cycle |
| Crack arrest | Refactoring, interface extraction, test coverage |

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_scanner.py -v
```

## License

MIT
