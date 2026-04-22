# Dosemate — Pharmacokinetic ADME Modeling for Code Change Propagation

Code changes enter a system, spread through it, get transformed, and eventually fade away — exactly like drugs in a human body. **Dosemate** applies the mathematical science of pharmacokinetics (Absorption, Distribution, Metabolism, Excretion) to model how code changes propagate through a software system.

## The Metaphor

| Pharmacokinetics | Software Change Lifecycle |
|---|---|
| Drug dose | A code change (commit, PR, config edit) |
| Absorption (ka) | Merge rate: how fast a change enters the main codebase |
| Volume of distribution (Vd) | Change reach: how many modules a change spreads across |
| First-pass effect | CI/review "metabolism": fraction of change transformed before merge |
| Michaelis-Menten saturation | CI throughput saturation under high change volume |
| Excretion / Clearance (CL) | Code deprecation/removal rate |
| Half-life (t½) | Time for a change's influence to drop by 50% |
| Bioavailability (F) | Fraction of intended change reaching production unchanged |
| Drug-drug interaction (DDI) | Concurrent PR interference or amplification |
| Steady state (Css) | Equilibrium change pressure in the codebase |
| Loading dose / Maintenance dose | Bootstrap effort vs. ongoing incremental changes |

## Installation

```bash
pip install -e .
```

Or run directly with Python:

```bash
python -m dosemate --help
```

No external dependencies required — Dosemate uses only the Python standard library.

## Usage Examples

### Analyze ADME parameters for recent changes
```bash
dosemate analyze --repo . --since 7d
dosemate analyze --repo . --since 30d --json
```

### Compute PK profile for recent changes
```bash
dosemate profile --repo . --since 30d
```

### Detect drug-drug interactions between concurrent PRs
```bash
dosemate interact --repo . --since 7d
dosemate interact --repo . --since 7d --json
```

### Analyze CI/CD saturation (Michaelis-Menten kinetics)
```bash
dosemate saturate --repo . --since 30d
```

### Compute steady-state change pressure
```bash
dosemate steady-state --repo . --sprint 2w --since 90d
dosemate steady-state --repo . --sprint 2w --json
```

### Python API
```python
from dosemate.pk_fitter import PKModelFitter, report_to_dict

fitter = PKModelFitter("/path/to/repo")
report = fitter.analyze(since="30 days ago")
data = report_to_dict(report)

# Access individual components
for pr_id, pk in report.change_pk.items():
    print(f"{pr_id}: half-life = {pk.excretion.t_half:.1f} weeks")
    print(f"  bioavailability = {pk.metabolism.bioavailability_F:.2%}")
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                Dosemate Engine                    │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Git      │  │ CI/CD    │  │ Dependency│       │
│  │ History  │  │ Metrics  │  │ Graph     │       │
│  │ Parser   │  │ Collector│  │ Analyzer  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │
│       └──────────────┴──────────────┘              │
│                      │                             │
│              ┌───────▼───────┐                     │
│              │  PK Model     │                     │
│              │  Fitter       │                     │
│              └───────┬───────┘                     │
│                      │                             │
│       ┌──────┬──────┼──────┬──────┐               │
│       ▼      ▼      ▼      ▼      ▼               │
│     Absorp- Distri- Meta-  Excre-  DDI           │
│     tion    bution  bolism  tion    Interactions  │
│       │      │      │      │      │               │
│       └──────┴──────┴──────┴──────┘               │
│                      │                             │
│              ┌───────▼───────┐                     │
│              │  Forecast &   │                     │
│              │  Steady-State │                     │
│              └───────────────┘                     │
└─────────────────────────────────────────────────┘
```

### Module Overview

- **`git_parser.py`**: Parses git log output to extract commit data, synthesizes PR-like objects from merge commits
- **`dependency_graph.py`**: Analyzes import/dependency relationships between modules, computes coupling coefficients
- **`ci_collector.py`**: Collects CI/CD throughput metrics from git history patterns
- **`absorption.py`**: Models merge rate kinetics (ka), lag time, and fraction absorbed
- **`distribution.py`**: Computes volume of distribution (Vd), tissue partition coefficient (Kp), and unbound fraction (fu)
- **`metabolism.py`**: Models first-pass effect, total bioavailability (F), and Michaelis-Menten CI saturation
- **`excretion.py`**: Computes clearance rate (CL), elimination rate (ke), and half-life (t½)
- **`ddi.py`**: Detects drug-drug interactions between concurrent PRs using competitive inhibition and enzyme induction models
- **`steady_state.py`**: Computes steady-state concentration (Css), accumulation factor (R), and loading/maintenance dose plans
- **`two_compartment.py`**: Models deep dependency propagation with biexponential decay (alpha/beta phases)
- **`pk_fitter.py`**: Orchestrates all ADME computations into a complete PK report
- **`cli.py`**: Command-line interface with analyze, profile, interact, saturate, and steady-state subcommands

## Key Metrics

| Metric | Formula | Meaning |
|---|---|---|
| ka | ln(2) / median_time_to_merge | Absorption rate constant |
| Vd | total_dependent_modules / change_density | Volume of distribution |
| F | f_absorption × f_lint × f_review | Total bioavailability |
| t½ | 0.693 × Vd / CL | Change influence half-life |
| Css | (F × Dose) / (CL × τ) | Steady-state change pressure |
| R | 1 / (1 - e^(-ke × τ)) | Accumulation factor |
| AUC_ratio | 1 + [I] / Ki | DDI amplification |

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
