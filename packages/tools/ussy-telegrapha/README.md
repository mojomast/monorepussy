# Telegrapha — Signal Corps Telegraphy for Data Pipeline Fidelity Analysis

Telegrapha applies 19th-century telegraphy and Signal Corps practices to model data pipeline fidelity, reliability, and capacity with rigorous mathematical frameworks. It computes cumulative message degradation across routes, theoretical throughput ceilings, and formal retry-vs-redundancy decisions that no existing tool provides.

## Installation

```bash
pip install -e .
```

## Usage

### Attenuation Budget — Cumulative Fidelity Decay
```bash
telegrapha attenuation 'order->payment->fraud-check->ledger' \
  --degradations '0.005,0.03,0.02,0.04'
```

### Relay Chain — Service Mesh Reliability
```bash
telegrapha relay-chain 'api->auth->service->db' \
  --reliabilities '0.9999,0.9995,0.9998,0.9999'
```

### Shannon-Hartley Capacity — Theoretical Throughput Ceiling
```bash
telegrapha capacity --bandwidth 1000 --signal-rate 500 --noise-rate 50
```

### Precedence — Priority Queue Optimization (M/G/1)
```bash
telegrapha precedence --topology pipeline.yaml
```

### Hamming Analysis — FEC vs ARQ Decision Framework
```bash
telegrapha hamming --route 'src->transform->sink' \
  --per-hop-error-rate 0.01 --retry-cost 50 --redundancy-cost 30
```

### Dead Letter Office — DLQ as Analytical Instrument
```bash
telegrapha dlo --dlq-path dlq.json
```

### Dashboard — All Analyses Combined
```bash
telegrapha dashboard --topology pipeline.yaml
```

## Architecture

```
telegrapha/
├── models.py        # Data models (Hop, Route, PipelineTopology, etc.)
├── topology.py      # YAML/JSON topology loading with built-in YAML parser
├── attenuation.py   # Attenuation budget — multiplicative fidelity decay
├── relay_chain.py   # Relay chain reliability — series/parallel models
├── capacity.py      # Shannon-Hartley capacity — theoretical throughput ceiling
├── precedence.py    # Message precedence — M/G/1 priority queue optimization
├── hamming.py       # Hamming analysis — FEC vs ARQ decision framework
├── dlo.py           # Dead Letter Office — DLQ health scoring
├── dashboard.py     # Comprehensive dashboard combining all analyses
└── cli.py           # Command-line interface using argparse
```

## Key Concepts

| Telegraphy Concept | Pipeline Analogy |
|---|---|
| Attenuation budget | Cumulative message fidelity decay across hops |
| Relay station | Service mesh hop with reliability budget |
| Shannon-Hartley theorem | Theoretical throughput ceiling for a pipeline |
| Hamming codes | FEC vs ARQ retry strategy decision |
| Message precedence (FLASH/IMMEDIATE/PRIORITY/ROUTINE) | Priority queue class optimization |
| Dead Letter Office | DLQ health analysis and recovery scoring |
| Heaviside condition | Distortionless pipeline flow detection |
| Loading coil | Validation injection to boost signal fidelity |

## Zero External Dependencies

Telegrapha uses Python stdlib only — no numpy, no pyyaml, no external packages. The built-in YAML parser handles the subset needed for pipeline topology definitions.

## License

MIT
