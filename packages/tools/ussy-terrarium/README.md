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
```

## Architecture

```
File Changes → Metrics Engine → Ecosystem Model → Renderer
                    ↓                                  ↓
              CodeMetrics                        Terminal/Canvas
              {                                  ┌──────────────┐
                churn_rate: 0.3,                 │ 🌳📁 api/    │
                complexity: 12,                  │   🌿📄 auth.py│
                test_coverage: 0.85,             │   🍂📄 old.py │
                bug_count: 2,                    │ 🌲📁 core/   │
                dependency_count: 5              │   🍄 hack.py │
              }                                  └──────────────┘
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

3. **Renderers** (`terrarium/renderers/`):
   - **Terminal**: ASCII/Unicode art with emoji organisms and ANSI colors
   - **Static export**: Text and SVG snapshots for CI reports
   - **Seasons**: Timeline view showing ecosystem evolution

4. **File Watcher** (`terrarium/watcher.py`): Polling-based file change detection

5. **Diagnosis Engine** (`terrarium/ecosystem/diagnosis.py`): Natural-language health reports with symptoms, diagnosis, treatment, and prognosis

### Health Score Calculation

Health scores (0-100) are computed as:
- Start at 100
- Subtract penalties for high churn (>5/month), high complexity (>15), low coverage (<80%), bugs, dead/deprecated status
- Add bonuses for low complexity, good coverage, stability

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
