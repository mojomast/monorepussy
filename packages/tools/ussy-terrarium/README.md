# 🌿 Terrarium — Your Codebase Is a Living Ecosystem

[![Demo](https://img.shields.io/badge/demo-live-4f98a3?style=flat-square)](https://terrarium.ussyco.de)

Terrarium renders your codebase as a living ecosystem where modules are organisms, dependencies are food chains, and code health is visible as biological vitality.

- **Healthy modules** are lush, green organisms 🌳
- **Stressed modules** (high churn, many bugs) are wilting, discolored 🥀
- **Dead code** is visibly decaying — brown, brittle 🪵
- **Dependencies** are root systems connecting organisms
- **Tech debt** appears as parasitic growths 🍄
- **New code** is seedlings — small, fragile 🌱
- **Stable code** is old-growth trees — massive, foundational 🏔️

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# View your codebase as a living ecosystem (legacy renderer)
terrarium watch ./my-project

# Diagnose a specific module
terrarium diagnose ./my-project/src/auth.py

# Generate a snapshot for CI
terrarium snapshot --format text --output report.txt ./my-project
terrarium snapshot --format svg --output terrarium-report.svg ./my-project

# See ecosystem evolve over time
terrarium seasons ./my-project --since "6 months ago"

# Get a compact health report
terrarium health ./my-project

# New: Rich dashboard from adapter data (stub mode works without siblings)
terrarium dashboard

# New: Live watch mode with Rich
terrarium watch-live --interval 5

# New: Export metrics to JSON/CSV
terrarium export --format json --output metrics.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Terrarium CLI (Click)                   │
├─────────────────────────────────────────────────────────────┤
│  Legacy Commands    │    New Engine Commands                 │
│  watch/diagnose/    │    dashboard / watch-live / export      │
│  snapshot/seasons/  │                                         │
│  health             │                                         │
├─────────────────────────────────────────────────────────────┤
│              TerrariumEngine (collect + score)               │
│                      ↓              ↑                        │
│               HealthScore    ←   Adapters                    │
├─────────────────────────────────────────────────────────────┤
│  Adapters (8 pluggable data sources)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ fatigue │ │ endemic │ │ sentinel│ │kompressi│          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │churnmap │ │  seral  │ │proprio- │ │snapshot │          │
│  └─────────┘ └─────────┘ │ception  │ └─────────┘          │
│                          └─────────┘                        │
├─────────────────────────────────────────────────────────────┤
│  Legacy Ecosystem Model (preserved)                          │
│  MetricsEngine → Organism → Ecosystem → Renderers            │
└─────────────────────────────────────────────────────────────┘
```

## Health Scoring

Terrarium computes a 0.0–1.0 **overall health score** from seven dimensions. Each dimension is normalized so that:

- **1.0** = perfect health / no issues detected
- **0.0** = critical / maximum issues detected

| Dimension | Weight | Source | 1.0 means… | 0.0 means… |
|-----------|--------|--------|------------|------------|
| `fatigue` | 0.20 | fatigue adapter | No stress cracks | Every file at max crack intensity |
| `epidemic` | 0.20 | endemic adapter | No infections | Every file infected |
| `anomaly` | 0.20 | sentinel adapter | No anomalies | Every file anomalous |
| `drift` | 0.15 | any adapter with vitality < 1.0 | No drift | All files drifting |
| `complexity` | 0.15 | kompressi adapter | Zero complexity | Max complexity everywhere |
| `churn` | 0.10 | churnmap adapter | No active churn | Every file actively churning |
| `overall` | 1.00 | weighted average | Ecosystem thriving | Ecosystem critical |

The `overall` score is a weighted average of the six sub-scores. Missing adapters default to 1.0 (perfect health) so the engine degrades gracefully.

## Data Sources

| Adapter | Source | Status | What it measures |
|---------|--------|--------|------------------|
| `fatigue` | [fatigueussy](https://github.com/mojomast/fatigueussy) | ✅ Real + Stub | Paris' Law crack growth (stress intensity) |
| `endemic` | [endemicussy](https://github.com/mojomast/endemicussy) | ✅ Real + Stub | SIR/SEIR infection spread |
| `sentinel` | [sentinelussy](https://github.com/mojomast/sentinelussy) | ✅ Real + Stub | Anomaly detection activations |
| `kompressi` | [kompressiussy](https://github.com/mojomast/kompressiussy) | ✅ Real + Stub | Kolmogorov complexity (info density) |
| `churnmap` | [churnmap](https://github.com/mojomast/churnmap) | ✅ Real + Stub | Co-change territory clusters |
| `seral` | [seralussy](https://github.com/mojomast/seralussy) | ✅ Real + Stub | Ecological succession stages |
| `proprioception` | [proprioceptionussy](https://github.com/mojomast/proprioceptionussy) | ✅ Real + Stub | Workspace drift / body schema |
| `snapshot` | [snapshotussy](https://github.com/mojomast/snapshotussy) | ✅ Real + Stub | Dev state memory pressure |

Every adapter has a `STUB_MODE` flag. If the sibling package is not installed, the adapter falls back to reading JSON data files and returns synthetic/demo data. Terrarium runs fine with **zero** sibling packages installed.

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_adapters.py -v
```

## Contributing

### Adding a New Adapter in 3 Steps

1. **Create the adapter module** at `terrarium/adapters/<name>.py`:
   ```python
   from .base import BaseAdapter
   from ..ecosystem.model import OrganismHealthState

   class MyAdapter(BaseAdapter):
       name = "myadapter"
       STUB_MODE = False

       def load(self):
           # Return Dict[str, OrganismHealthState]
           pass
   ```

2. **Add fixture data** at `tests/fixtures/<name>.json` and tests in `tests/test_adapters.py`.

3. **Register CLI flags** in `terrarium/cli.py` and `terrarium/adapters/__init__.py`.

See `docs/adapters.md` for the full adapter contract.

## License

MIT
