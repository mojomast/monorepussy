# Aquifer — Darcy's Law Groundwater Flow Modeling for Data Pipeline Bottleneck Analysis

Aquifer applies **Darcy's Law** from hydrogeology to model data pipeline bottlenecks. It treats microservices as porous rock layers, message queues as aquifers, and uses physics-based flow simulation to predict pressure buildup and cascading failures.

## Why Aquifer?

Standard monitoring tells you *that* a service is slow — Aquifer tells you *why pressure is building up* and *where it will cascade next*. By modeling your pipeline as a groundwater flow system:

- **Hydraulic conductivity (K)** represents each service's intrinsic processing capacity
- **Hydraulic head (h)** represents queue depth × processing latency (pressure)
- **Darcy flux (q)** represents actual data throughput between services
- **Cone of depression** models how a single bottleneck's impact propagates spatially and attenuates with distance

This is fundamentally different from anomaly detection tools (like Cyclone's vorticity model) — Aquifer does **capacity planning and predictive degradation**, not anomaly detection.

## Installation

```bash
pip install -e .
```

Requires Python 3.9+ and NumPy.

## Quick Start

```bash
# Generate a sample topology to see the format
aquifer sample --output my_pipeline.json

# Analyze flow and find bottlenecks
aquifer analyze my_pipeline.json

# Generate ASCII contour map of hydraulic head
aquifer contour my_pipeline.json

# What-if: drill a well (add capacity) to a service
aquifer whatif my_pipeline.json --drill transformer --capacity 500

# Predict system behavior over time (Theis equation)
aquifer predict my_pipeline.json --duration 3600
```

## Topology Format

Define your pipeline as a JSON file:

```json
{
  "name": "my_pipeline",
  "services": {
    "ingestion": {
      "hydraulic_conductivity": 1000.0,
      "specific_storage": 0.01,
      "queue_depth": 10,
      "processing_latency": 0.005,
      "replicas": 3,
      "is_recharge": true
    },
    "transformer": {
      "hydraulic_conductivity": 200.0,
      "specific_storage": 0.02,
      "queue_depth": 50,
      "processing_latency": 0.05,
      "replicas": 2
    },
    "db_writer": {
      "hydraulic_conductivity": 150.0,
      "specific_storage": 0.03,
      "queue_depth": 100,
      "processing_latency": 0.1,
      "replicas": 1,
      "is_discharge": true
    }
  },
  "connections": [
    {"source": "ingestion", "target": "transformer", "connection_type": "porous"},
    {"source": "transformer", "target": "db_writer", "connection_type": "porous"}
  ]
}
```

## Architecture

```
aquifer/
├── topology.py    — Service and connection definitions, JSON load/save
├── darcy.py       — Darcy's Law solver (q = -K × dh/dl)
├── grid.py        — 2D finite-difference grid model with Gauss-Seidel solver
├── theis.py       — Theis equation for transient drawdown prediction
├── drawdown.py    — Cone of depression modeling for cascading failures
├── whatif.py      — What-if scenario engine (drill wells, add capacity)
├── contour.py     — ASCII contour maps and flow vector visualization
└── cli.py         — Command-line interface (argparse)
```

## Key Concepts

### Darcy's Law
```
q = -K × (dh/dl)
```
Where:
- **q** = Darcy flux (data flow rate, req/s)
- **K** = Hydraulic conductivity (service processing capacity, req/s)
- **dh/dl** = Hydraulic gradient (pressure difference between services)

### Theis Equation
Predicts time-to-saturation under sustained load:
```
s(r,t) = (Q / 4πT) × W(u)
where u = r²S / 4Tt
```

### Cone of Depression
Models how a single bottleneck propagates through the system:
- Drawdown decreases with distance (inverse relationship)
- Multiple cones can superpose (multiple concurrent bottlenecks)
- Recovery time depends on specific storage and transmissivity

## Tests

```bash
pip install pytest
pytest tests/ -v
```

167 tests covering all modules.

## License

MIT
