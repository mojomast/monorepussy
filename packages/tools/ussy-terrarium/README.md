# 🌿 Terrarium — Your Codebase Is a Living Ecosystem

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
pip install -e .
```

## Usage

```bash
# View your codebase as a living ecosystem
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
# → Ecosystem Health: 72/100 (FAIR)
#   12 thriving, 5 stressed, 2 critical, 3 dead
#   Most critical: api/auth.py (health: 18/100)
#   Healthiest: utils/format.rs (health: 96/100)

# Wire external ussyverse data sources (optional)
terrarium watch ./my-project \
  --fatigue-data fatigue-scan.json \
  --endemic-data endemic-scan.json \
  --sentinel-data sentinel-check.json
```

## Architecture

```
File Changes → Metrics Engine → Ecosystem Model → Renderer
                     ↓              ↑                   ↓
               CodeMetrics    External Adapters     Terminal/Canvas
               {              (fatigue/endemic/     ┌──────────────┐
                 churn_rate: 0.3,  sentinel)        │ 🌳📁 api/    │
                 complexity: 12,  ↑                 │   🌿📄 auth.py│
                 test_coverage: 0.85,               │   🍂📄 old.py │
                 bug_count: 2,                      │ 🌲📁 core/   │
                 dependency_count: 5                │   🍄 hack.py │
               }                                    └──────────────┘
```

### Components

1. **Metrics Engine** (`terrarium/metrics/`): Multi-source health analysis
   - **Git churn**: Files changed frequently = stressed (wilting)
   - **Complexity**: Cyclomatic via Python AST (overgrown = tangled vines)
   - **Test coverage**: Via coverage report ingestion (no tests = no immune system)
   - **Dead code detection**: Unused exports, unreachable code (dead matter)
   - **Age + stability**: Old-growth vs seedling classification

2. **Ecosystem Model** (`terrarium/ecosystem/`): Maps metrics → biological properties
   - HealthScore = weighted average of churn penalty, complexity penalty, coverage bonus, etc.
   - OrganismType: Tree (entry point), Bush (library), Moss (config), Flower (test), Fungus (generated), DeadWood (deprecated)
   - Vitality: Thriving → Healthy → Stressed → Wilting → Dying → Dead

3. **External Adapters** (`terrarium/adapters/`): Optional ussyverse data sources
    - **fatigue**: Maps Paris' Law crack growth to organism wound levels
    - **endemic**: Maps SIR/SEIR infection states to contagion glow
    - **sentinel**: Maps anomaly detections to immune response markers
    - Auto-discovered and loaded; graceful degradation when absent

4. **Renderers** (`terrarium/renderers/`):
    - **Terminal**: ASCII/Unicode art with emoji organisms and ANSI colors
    - **Static export**: Text and SVG snapshots for CI reports
    - **Seasons**: Timeline view showing ecosystem evolution

5. **File Watcher** (`terrarium/watcher.py`): Polling-based file change detection

5. **Diagnosis Engine** (`terrarium/ecosystem/diagnosis.py`): Natural-language health reports with symptoms, diagnosis, treatment, and prognosis

## External Data Sources (Ussyverse Adapters)

Terrarium can optionally ingest live data from three external **ussyverse** tools to enrich organism health visualization. All adapters are optional — Terrarium runs fine with zero external data.

| Adapter | Source | Data File Flag | Effect on Organism |
|---------|--------|---------------|-------------------|
| `fatigue` | [fatigueussy](https://github.com/mojomast/fatigueussy) | `--fatigue-data` | Crack intensity → cracked bark / wilting |
| `endemic` | [endemicussy](https://github.com/mojomast/endemicussy) | `--endemic-data` | Infection state (S/E/I/R) → contagion glow |
| `sentinel` | [sentinelussy](https://github.com/mojomast/sentinelussy) | `--sentinel-data` | Anomaly detection → immune response marker |

### Adapter JSON Formats

**fatigueussy** — accepts the native `fatigue scan --format json` output:
```json
{
  "stress_intensities": {
    "src/auth.py": {"K": 150.0, "delta_K": 10.0}
  }
}
```

**endemicussy** — accepts a JSON file with module infection states:
```json
{
  "modules": [
    {"path": "src/auth.py", "compartment": "I"},
    {"path": "src/utils.py", "compartment": "S"}
  ]
}
```
Or a flat mapping:
```json
{
  "src/auth.py": {"compartment": "I"}
}
```

**sentinelussy** — accepts a JSON file with per-file anomaly reports:
```json
{
  "files": {
    "src/auth.py": {
      "anomaly_score": 0.73,
      "is_anomalous": true,
      "detections": [{"false_positive_rate": 0.2}]
    }
  }
}
```
Detectors with a false-positive rate > 0.5 are suppressed as background noise.

### Health Score Calculation

Health scores (0-100) are computed as:
- Start at 100
- Subtract penalties for high churn (>5/month), high complexity (>15), low coverage (<80%), bugs, dead/deprecated status
- Add bonuses for low complexity, good coverage, stability
- Additional penalties from external adapters:
  - Crack intensity × 30
  - Infected (I) −20, Exposed (E) −10, Recovered (R) −5
  - Active anomaly −15

### Module Role → Organism Type Mapping

| Role | Organism | Description |
|------|----------|-------------|
| entry_point | 🌳 Tree | Foundational |
| library | 🌿 Bush | Supportive |
| config | 🍀 Moss | Ground cover |
| test | 🌸 Flower | Blooms when passing |
| generated | 🍄 Fungus | Grows fast, no roots |
| deprecated | 🪵 DeadWood | Decaying |
| (new code) | 🌱 Seedling | Small, fragile |

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Run with verbose output
pytest -v
```

## License

MIT
