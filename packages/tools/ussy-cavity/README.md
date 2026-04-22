# Cavity — Acoustic Resonance Analysis for Concurrent Pipeline Deadlock & Livelock Detection

## Overview

**Cavity** applies acoustic resonance physics — standing waves, natural frequencies, Fourier analysis, and damping theory — to detect and predict deadlocks, livelocks, and oscillating backpressure in concurrent data pipelines. It treats your pipeline topology as a resonant cavity and computes its acoustic properties:

- **Natural frequencies** → potential deadlock patterns from topology eigenvalues
- **Standing wave signatures** → active deadlock cycles via STFT
- **Resonance amplitudes** → livelock severity via beat frequency analysis
- **Q-factors** → oscillation persistence
- **Impedance mismatches** → backpressure hot-spots at stage boundaries

### The Metaphor Mapping

| Acoustic Physics | Concurrent Pipeline |
|---|---|
| Resonant cavity | Pipeline topology (workers, queues, locks) |
| Natural frequency | Topology-inherent deadlock pattern |
| Standing wave | Active deadlock (persistent circular wait) |
| Beat frequency | Livelock (competing retry patterns) |
| Impedance mismatch | Throughput discontinuity (fast producer → slow consumer) |
| Damping (ζ) | Backoff/timeout effectiveness |
| Q-factor | Deadlock persistence |

## Installation

```bash
pip install -e .
```

Requires Python 3.11+ with numpy and PyYAML.

## Usage

### CLI Commands

#### Predict Deadlocks from Topology

```bash
cavity modes pipeline.yaml
```

Output shows resonance modes ranked by risk:
```
Mode 0: f=0.1592Hz, ζ=0.0000 (UNDAMPED), Q=∞
  Involved: worker_a → lock_x → worker_b → lock_y
Mode 1: f=0.1592Hz, ζ=0.0000 (UNDAMPED), Q=∞
```

Options:
- `--all-modes` — Show all modes including well-damped
- `--dt FLOAT` — Time step for frequency calculation (default: 1.0)
- `--json` — Output in JSON format

#### Analyze Backpressure (Impedance)

```bash
cavity impedance pipeline.yaml
```

Shows impedance at each stage boundary, reflection coefficients, and mismatch warnings:
```
producer → transformer: Z₁=500000.0, Z₂=160000.0, R=-0.515, T=0.485 ⚠ MISMATCH
transformer → consumer: Z₁=160000.0, Z₂=60000.0, R=-0.455, T=0.545
```

Options:
- `--target-zeta FLOAT` — Target damping ratio (default: 1.0)
- `--json` — JSON output

#### Temporal Analysis (Standing Waves & Livelocks)

```bash
cavity monitor timeseries.json
```

Detects standing waves and beat frequencies from wait-duration time series data.

Options:
- `--fs FLOAT` — Sampling frequency in Hz (default: 1.0)
- `--window INT` — STFT window size (default: 256)
- `--json` — JSON output

#### Full Report

```bash
cavity report pipeline.yaml [--timeseries data.json]
```

Generates a comprehensive resonance analysis report combining all analyses.

Options:
- `--timeseries PATH` — Time series data for temporal analysis
- `--target-zeta FLOAT` — Target damping ratio
- `--json` — JSON output

### Python API

```python
from cavity.topology import PipelineTopology
from cavity.modes import predict_deadlocks
from cavity.impedance import analyze_impedance_mismatches
from cavity.report import generate_report

# Load pipeline topology
topo = PipelineTopology.from_file("pipeline.yaml")

# Predict potential deadlocks
modes = predict_deadlocks(topo.adjacency_matrix, topo.node_names)
for mode in modes:
    print(f"Mode {mode.index}: {mode.risk_level.value}, f={mode.frequency:.4f}Hz")

# Analyze impedance mismatches
profile = analyze_impedance_mismatches(topo)
for boundary in profile.mismatches:
    print(f"Mismatch: {boundary.upstream} → {boundary.downstream}")

# Generate full report
report = generate_report(topo, pipeline_name="my_pipeline")
print(report.to_text())
```

### Pipeline Topology Format

Define your pipeline in YAML:

```yaml
stages:
  producer:
    rate: 1000      # items/sec
    buffer: 500     # buffer capacity
    depends_on: []
    locks: []

  transformer:
    rate: 800
    buffer: 200
    depends_on: [producer]
    locks: [schema_mutex]

  consumer:
    rate: 600
    buffer: 100
    depends_on: [transformer]
    locks: [db_connection_pool]

locks:
  schema_mutex:
    type: exclusive
    holders: [transformer, validator]

  db_connection_pool:
    type: semaphore
    capacity: 10
    holders: [consumer, writer]
```

## Architecture

```
cavity/
├── topology.py       # Pipeline topology parsing & adjacency matrix construction
├── modes.py          # Eigenvalue decomposition for natural frequencies
├── standing_wave.py  # STFT-based standing wave (deadlock) detection
├── beat_frequency.py # Beat frequency livelock detection
├── impedance.py      # Impedance mismatch & backpressure analysis
├── damping.py        # Damping coefficient computation & recommendations
├── report.py         # Full report generation
└── cli.py            # Command-line interface
```

### Key Algorithms

1. **Natural Frequency Computation**: Eigenvalue decomposition of the adjacency matrix → complex eigenvalues → frequency = |λ|/(2πΔt), damping ratio = -Re(λ)/|λ|

2. **Standing Wave Detection**: Short-Time Fourier Transform (STFT) of wait-duration signal → persistent spectral peaks = standing waves

3. **Beat Frequency Detection**: Autocorrelation of wait signal → periodic peaks → FFT for competing frequencies → beat frequency = |f₁ - f₂| → livelock if throughput ≈ 0

4. **Impedance Analysis**: Z = rate × buffer at each stage → reflection coefficient R = (Z₂-Z₁)/(Z₂+Z₁) → mismatch if |R| > 0.5

5. **Damping Classification**: ζ = c/(2√(km)) where c=backoff rate, k=contention strength, m=work inertia → UNDAMPED (ζ≈0), UNDERDAMPED (ζ<1), CRITICALLY DAMPED (ζ≈1), OVERDAMPED (ζ>1)

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
