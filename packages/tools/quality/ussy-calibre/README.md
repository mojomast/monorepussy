# Calibre — Metrological Measurement Science for Test Suite Quality Analysis

**Every test run is a measurement. It's time to treat it like one.**

Calibre applies the rigorous framework of metrological measurement science — the same science that ensures physical measurements are trustworthy — to test suite quality analysis. No tool has ever computed uncertainty budgets, Gauge R&R studies, or process capability indices for test suites. Calibre does.

## Overview

Test suites are measurement instruments that nobody calibrates. Calibre fixes this by producing a **Metrological Characterization Report** that quantifies how trustworthy test results are, using six instruments grounded in measurement science:

| # | Instrument | Metrology Concept | What It Measures |
|---|-----------|-------------------|------------------|
| 1 | **Uncertainty Budget** | GUM Combined Standard Uncertainty | Combined test result uncertainty from all sources (flakiness, environment, timing, data staleness, mock fidelity) |
| 2 | **R&R Study** | Gauge Repeatability & Reproducibility | ANOVA variance decomposition: test code vs. environment vs. codebase |
| 3 | **Capability Index** | Process Capability Cp/Cpk | Whether the test suite is a good enough instrument to trust |
| 4 | **Uncertainty Classifier** | Type A vs. Type B Uncertainty | Random vs. systematic flakiness — tells you whether to retry or rewrite |
| 5 | **Drift Detector** | Instrument Drift with CUSUM | Temporal drift of test expectations, zombie test detection |
| 6 | **Traceability Auditor** | Calibration Traceability Chain | Assertion → requirement traceability with cumulative chain uncertainty |

## Installation

```bash
pip install -e .
```

Requires Python 3.9+ with numpy and scipy.

## Usage

### Seed Demo Data

```bash
calibre seed
```

### Uncertainty Budget

```bash
calibre budget auth
```

### Gauge R&R Study

```bash
calibre rr auth --builds 5 --envs 3
```

### Capability Analysis

```bash
calibre capability auth --usl 5% --lsl 0%
```

### Flakiness Classification

```bash
calibre classify test_login
```

### Drift Detection

```bash
calibre drift auth --mpe 10%
```

### Traceability Audit

```bash
calibre trace test_login
```

### Full Report

```bash
calibre report auth --full --mpe 10%
```

### Import Test Results

```bash
calibre import results.json
```

## Architecture

```
src/calibre/
├── __init__.py         # Package metadata
├── __main__.py         # python -m calibre support
├── cli.py              # Argparse CLI with 8 commands
├── db.py               # SQLite storage layer
├── models.py           # Data models (dataclasses)
├── budget.py           # GUM Uncertainty Budget
├── rr.py               # Gauge R&R ANOVA study
├── capability.py       # Cp/Cpk process capability
├── classifier.py       # Type A/B uncertainty classifier
├── drift.py            # CUSUM drift detector
├── traceability.py     # Traceability chain auditor
└── report.py           # Full report generator
```

### Core Analogy Map

| Metrology Concept | Test Suite Equivalent | Calibre Output |
|---|---|---|
| GUM combined uncertainty u_c(y) | Combined test result uncertainty | Uncertainty budget per module |
| Gauge R&R | Test code vs environment vs codebase variance | R&R study with %GRR and ndc |
| Process capability Cp/Cpk | Test suite capability as measurement instrument | Capability index per quality characteristic |
| Type A vs Type B uncertainty | Random vs systematic flakiness | Classification with remediation guidance |
| Instrument drift d(t) | Test expectation drift over time | Drift rate α with CUSUM detection |
| Calibration traceability chain | Assertion → requirement traceability | Chain integrity score + orphan detection |

## Key Metrics

- **%GRR**: Gauge R&R percentage — <10% acceptable, 10-30% conditional, >30% unacceptable
- **ndc**: Number of distinct categories — how many meaningful quality distinctions the suite can make
- **Cpk**: Process capability index — <1.0 incapable, ≥1.33 capable, ≥2.0 excellent
- **α**: Drift rate — how fast test expectations become stale
- **u_chain**: Cumulative traceability chain uncertainty

## License

MIT
