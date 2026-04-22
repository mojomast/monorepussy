# Petrichor — Configuration Drift Detection Through Soil Memory

> *Petrichor: the scent of rain on dry earth — the soil's memory of water.*

Configuration drift is invisible until it breaks things. A server gets a manual hotfix, a developer tweaks a config file "just for testing," a ConfigMap gets updated without CI — and suddenly production behaves differently from staging. By the time you notice, the drift has been accumulating for weeks.

Current drift detection tools do point-in-time comparison against a desired state, but they have no **memory** of how drift accumulated. Petrichor maintains a **soil memory** — a layered, historical baseline that records not just the desired state, but the full history of how configuration has drifted and self-corrected over time.

## Key Insight: Drift IS the Correction

The killer feature of Petrichor is detecting when "drift" is actually a **correction**. If a config file keeps drifting back to the same "wrong" value, it's probably because the desired state is itself wrong. Petrichor detects this pattern and tells you to update your desired state, not fight it.

## Features

- **Soil Layers** — Every config state change is recorded as a timestamped soil layer with full diff, actor, and context
- **Drift Detection** — SHA-256 content hash comparison, fast and with zero false positives
- **Rain Gauge** — Drift frequency analysis: which files drift, how often, and whether they're converging or diverging
- **Groundwater** — Three-layer state comparison: declared (file) vs. effective (runtime) vs. intended (IaC)
- **Scent** — Predictive drift based on temporal patterns (day-of-week, actor correlation, recurrence)
- **Soil Profile** — Layered history visualization showing the full story of how drift evolved
- **Correction Detection** — Identifies when recurring "drift" means the desired state is wrong

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Usage

### Initialize

```bash
# Initialize soil memory for a directory
petrichor init /etc/nginx/ --desired-state=git://infra/nginx/
```

### Snapshot

```bash
# Record current state as a soil layer
petrichor snapshot /etc/nginx/
```

### Check for Drift

```bash
# Check for drift with full history
petrichor drift /etc/nginx/nginx.conf
```

### Rain Gauge (Drift Frequency)

```bash
# Run the rain gauge over the last 30 days
petrichor gauge --days=30
```

### Groundwater (Latent Drift)

```bash
# Check declared vs. effective vs. intended
petrichor groundwater /etc/nginx/nginx.conf
```

### Predict Future Drift

```bash
# Predict likely drifts in the next 7 days
petrichor scent --days=7
```

### Soil Profile (Layered History)

```bash
# Get full soil profile with 10 layers
petrichor profile /etc/nginx/nginx.conf --depth=10
```

### Export

```bash
# Export drift history as JSON
petrichor export --format=json --days=90

# Export as text
petrichor export --format=text --days=90
```

### Set Desired State

```bash
# From a file
petrichor desired /etc/nginx/nginx.conf --from-file=desired.conf

# From a hash
petrichor desired /etc/nginx/nginx.conf --hash=abc123...
```

## Architecture

```
petrichor/
├── cli.py          # CLI interface (argparse)
├── db.py           # SQLite storage layer (.petrichor/soil.db)
├── soil.py         # Soil layer management (snapshot, drift detection, correction detection)
├── gauge.py        # Rain gauge (drift frequency, convergence/divergence)
├── groundwater.py  # Groundwater (declared vs. effective vs. intended)
├── scent.py        # Predictive drift (day-of-week, recurrence patterns)
├── profile.py      # Soil profile visualization
├── export.py       # Export drift history (JSON, text)
├── hash.py         # SHA-256 content hashing
└── diff.py         # Diff computation (unified diff, changed key extraction)
```

### Storage

Petrichor uses a SQLite database (`.petrichor/soil.db`) with three tables:

- **soil_layers** — Timestamped state snapshots with content hash, diff, actor, context, and drift flag
- **desired_state** — The intended configuration state for each tracked path
- **tracked_paths** — Registry of paths being monitored

### Drift Detection

Content hashes (SHA-256) are compared against the desired state. When a hash differs, the change is recorded as a drift layer with a full unified diff and metadata about who made the change and why.

### Pattern Detection

Time-series analysis on drift events — day-of-week frequency, actor correlation, drift direction (converging/diverging). Uses simple statistical methods (moving averages, autocorrelation). No ML needed.

### Correction Detection

When the same drift value recurs multiple times for a path, Petrichor flags it as a potential correction — the desired state may be wrong, and the "drift" is actually the right value.

## Dependencies

**Zero external dependencies** — Petrichor uses only the Python standard library:

- `sqlite3` for storage
- `hashlib` for SHA-256 hashing
- `difflib` for diff computation
- `argparse` for CLI
- `json` for data export
- `collections` for statistical analysis
- `datetime` for timestamps (timezone-aware throughout)

## License

MIT
