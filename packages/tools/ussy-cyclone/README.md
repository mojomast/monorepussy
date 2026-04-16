# Cyclone — Vorticity-Based Data Pipeline Anomaly Detection

🌀 Detect "hurricanes" forming in your data pipelines before they become incidents.

Cyclone applies meteorological vorticity analysis to detect self-reinforcing retry/reprocessing loops in data pipelines. It maps concepts from atmospheric science — vorticity, CISK (Conditional Instability of the Second Kind), potential vorticity conservation, and the Saffir-Simpson scale — onto pipeline dynamics to predict and classify pipeline "storms."

## How It Works

| Meteorological Concept | Pipeline Analog |
|------------------------|-----------------|
| Vorticity (ζ) | Reprocessing fraction × scale — rotation = data cycling back |
| Coriolis parameter (f) | Base retry rate — tendency for data to "spin" |
| Absolute vorticity (η = ζ + f) | Total rotational tendency |
| CISK | Self-reinforcing retry loops (cycle gain > 1.0 = intensifying) |
| Potential vorticity (PV) | Conserved quantity across scaling changes |
| Richardson number | Stability at stage boundaries (shear vs. buoyancy) |
| Saffir-Simpson scale | Cyclone severity (Cat-0 Calm → Cat-5 Hurricane) |
| Divergence | Convergence = data accumulating at a stage |

### The Aha Moment

When a consumer falls behind, its retry queue grows, it reprocesses messages already handled downstream, those reprocessed messages trigger more failures, which cause more retries — a **positive feedback loop** that mirrors hurricane intensification via CISK. Cyclone detects these loops before they spiral out of control.

## Installation

```bash
pip install -e .
```

Zero external dependencies — pure Python stdlib.

## Usage

### Survey a Pipeline

```bash
cyclone survey pipeline.json
```

Discovers pipeline topology and computes velocity fields for each stage.

### Detect Cyclones

```bash
cyclone detect pipeline.json
```

Identifies active cyclonic formations with severity classification.

Output example:
```
⚡ CYCLONE DETECTION REPORT
==================================================
  🌀 Cat-3 Severe Storm
  ID: e4de785c
  Center: enrich
  Vorticity: ζ = +2.86
  Stages affected: enrich, ingest
  CISK cycle: enrich → enrich
  Cycle gain: 1.80x
  DLQ depth: 12,433 messages
  Detected: 2026-04-16 04:12 UTC
==================================================
```

### Vorticity Analysis

```bash
cyclone vorticity pipeline.json
```

Shows vorticity at each pipeline stage with a visual flow diagram.

### CISK Detection

```bash
cyclone cisk pipeline.json
```

Detects Conditional Instability of the Second Kind — positive feedback loops where error amplification > 1.0.

### Stability Analysis

```bash
cyclone stability pipeline.json
```

Computes Richardson number at each stage boundary. Values below 0.25 indicate turbulent mixing (unstable boundary).

### Potential Vorticity

```bash
cyclone pv pipeline.json
```

PV conservation analysis — predicts how scaling changes affect pipeline stability.

### Forecast

```bash
cyclone forecast pipeline.json
```

Pipeline weather forecast — extrapolates current vorticity trends.

### Category Report

```bash
cyclone category pipeline.json
```

Shows current Saffir-Simpson category for each stage.

## Pipeline Configuration

Define your pipeline topology as a JSON file:

```json
{
  "stages": [
    {
      "name": "ingest",
      "type": "kafka",
      "forward_rate": 5000.0,
      "reprocessing_rate": 50.0,
      "queue_depth": 200,
      "consumer_count": 4,
      "error_rate": 10.0,
      "dlq_depth": 100,
      "base_retry_rate": 5.0
    },
    {
      "name": "enrich",
      "type": "generic",
      "forward_rate": 2000.0,
      "reprocessing_rate": 800.0,
      "queue_depth": 5000,
      "consumer_count": 2,
      "error_rate": 200.0,
      "dlq_depth": 12433,
      "base_retry_rate": 20.0
    },
    {
      "name": "sink",
      "type": "generic",
      "forward_rate": 5000.0,
      "reprocessing_rate": 30.0,
      "queue_depth": 100,
      "consumer_count": 4
    }
  ],
  "edges": [["ingest", "enrich"], ["enrich", "sink"]],
  "retry_edges": [["enrich", "enrich", 1.8]]
}
```

## Architecture

```
src/cyclone/
├── __init__.py       # Package init
├── __main__.py       # python -m support
├── cli.py            # CLI entry point (argparse)
├── models.py         # Core data models (PipelineStage, CycloneDetection, etc.)
├── vorticity.py      # Vorticity computation (ζ, η, divergence, PV)
├── cisk.py           # CISK detection (positive feedback loops)
├── detect.py         # Cyclone detection and tracking
├── stability.py      # Richardson number stability analysis
├── pv.py             # Potential vorticity conservation
├── forecast.py       # Vorticity trend forecasting
├── survey.py         # Pipeline topology survey
└── category.py       # Saffir-Simpson classification
```

## Saffir-Simpson Pipeline Scale

| Category | ζ | Reprocessing % | Description |
|----------|---|----------------|-------------|
| Cat-0 Calm | ≤ 0 | < 1% | Pipeline running smoothly |
| Cat-1 Depression | > 0 | < 5% | Slight rotation detected |
| Cat-2 Storm | > 0.5 | 5–15% | Reprocessing elevated |
| Cat-3 Severe Storm | > 1.0 | 15–30% | CISK detected, intensifying |
| Cat-4 Cyclone | > 2.0 | 30–50% | Cascading across stages |
| Cat-5 Hurricane | > 3.0 | > 50% | Pipeline stalled |

## Testing

```bash
pip install pytest
pytest tests/ -v
```

85 tests covering all modules.

## License

MIT
