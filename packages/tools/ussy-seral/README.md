# Seral — Codebase Successional Stage Detection with Governance Prescriptions

Seral analyzes your git repository and classifies every module into an ecological successional stage — from **pioneer** (bare rock, fast iteration) through **seral** (growing, emerging standards) to **climax** (stable, mature, strict control) — then generates concrete governance rules appropriate to each stage.

**The key insight: Applying climax governance to pioneer code kills it. Applying pioneer governance to climax code kills everyone.** Seral detects the stage and prescribes the rules.

## 🌱🌿🌳🔥 Stage Detection

| Stage | Emoji | Characteristics | Governance |
|-------|-------|----------------|------------|
| Pioneer | 🌱 | New, high churn, few tests, few contributors | Light: fast merge, experimental freedom |
| Seral | 🌿 | Growing, increasing contributors, emerging structure | Moderate: code review, boundary enforcement |
| Climax | 🌳 | Stable, low churn, high coverage, many dependents | Strict: architectural review, RFC for changes |
| Disturbed | 🔥 | Recently reset (major refactor/deletion) | Reset to pioneer-mode temporarily |

## Installation

```bash
pip install seral
```

Or from source:

```bash
git clone https://github.com/mojomast/seralussy.git
cd seralussy
pip install -e .
```

## Usage

### Scan your codebase

```bash
seral scan
```

Classifies every module into successional stages using git metrics (age, commit frequency, contributor count, churn rate, test ratio, dependants).

### Generate governance rules

```bash
seral prescribe src/auth/
```

Outputs stage-appropriate governance rules for a specific module or directory.

### Initialize configuration

```bash
seral init
```

Creates a `.seral/` config directory with default stage thresholds and rule templates.

### Compare governance between stages

```bash
seral diff pioneer climax
```

Shows what governance rules change when a module transitions between stages.

### Detect disturbance events

```bash
seral disturbances
```

Identifies ecological reset events — major refactors, mass deletions, or architectural overhauls that reset succession.

### View successional timeline

```bash
seral timeline
```

Shows how module stages have evolved over time with trajectory projection.

### Continuous monitoring

```bash
seral watch
```

Monitors for stage transitions and alerts when modules shift between stages.

## Architecture

```
seral/
├── models.py       # Data models: Stage, ModuleMetrics, GovernancePrescription
├── git_utils.py    # Git log parsing, metric extraction
├── scanner.py      # Stage classification engine
├── config.py       # Configuration loading (.seral/ config)
├── prescribe.py    # Governance rule generation per stage
├── disturbances.py # Disturbance event detection
├── timeline.py     # Historical trajectory analysis
├── diff.py         # Governance diff between stages
└── cli.py          # Click-based CLI interface
```

### Stage Detection Algorithm

Stage detection uses deterministic git metrics — no LLM needed:

1. **Age** — Days since first commit
2. **Commit frequency** — Commits per week
3. **Contributor count** — Unique authors
4. **Churn rate** — Lines added + removed per week
5. **Test-to-code ratio** — Test files vs source files
6. **Dependants** — Modules that import this one
7. **File-type diversity** — Number of distinct file types

Each metric is weighted and scored against configurable thresholds to classify modules into pioneer, seral (early/mid/late), climax, or disturbed stages.

### Governance Prescriptions

Seral generates stage-appropriate rules from built-in templates in `.seral/rules/`:

- **Pioneer**: Fast merge, no review required, experimental freedom, no coverage requirement
- **Seral**: Code review required, emerging standards, boundary enforcement, growing coverage
- **Climax**: 2+ reviewers, integration tests mandatory, ADR for dependencies, RFC for breaking changes, CI on all dependents
- **Disturbed**: Reset to pioneer governance temporarily, with documented transition plan

## Configuration

Seral creates a `.seral/` directory in your project root with:

- `config.yaml` — Stage thresholds and weights
- `rules/` — Governance rule templates per stage (YAML)

## Requirements

- Python 3.10+
- click >= 8.0
- rich >= 13.0
- pyyaml >= 6.0

## License

MIT
