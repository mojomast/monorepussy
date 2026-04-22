# Tarot — Probabilistic Risk Divination for Architecture Decisions

> 🏚️ "Your architecture has a 62% chance of a major incident within 6 months."

Tarot treats Architecture Decision Records (ADRs) as probability distributions and runs Monte Carlo simulations to predict cascading consequences. Each decision is a "card" with outcome probabilities; a "spread" runs thousands of simulations of your architecture's future.

## Why?

Architecture Decision Records are static documents. They capture *what was decided* and *why*, but not *what's probably going to happen next*. "We chose PostgreSQL over MongoDB" — but what's the probability that schema rigidity becomes a bottleneck? What happens when that bottleneck cascades into the microservices migration decision?

Tarot answers these questions using **real mathematics** (Monte Carlo simulation over interdependent probability distributions), packaged in a tarot metaphor that makes probabilistic risk tangible and communicable.

## The Five Readings

Every `tarot spread` produces a five-card reading:

| Card | Name | Reveals |
|------|------|---------|
| 🏚️ | **The Tower** | Highest-severity risk cluster — which decisions combine to create the most dangerous outcomes |
| 🎡 | **The Wheel** | Cascade patterns — which decisions are most likely to cascade into other decisions |
| 🧙 | **The Hermit** | Orphaned decisions — decisions with no mitigations, floating alone in risk space |
| ⭐ | **The Star** | Risk reducers — decisions that mitigate other risks (invest here!) |
| 💀 | **Death** | Decisions to reverse — high-probability negative outcomes that should be reconsidered |

## Installation

```bash
pip install -e .
```

No external dependencies — pure Python stdlib.

## Quick Start

### 1. Create Decision Cards

Create a `decisions/` directory with markdown files for each ADR:

```markdown
---
adr_id: ADR-001
title: PostgreSQL for session storage
confidence: High
outcomes:
  - "Schema rigidity:35%"
  - "No issues:65%"
cascades:
  - "ADR-003:Redis cluster needed:60%"
interactions:
  - "ADR-002:AMPLIFY:1.3"
tags:
  - database
  - storage
---

# ADR-001: PostgreSQL for session storage

We chose PostgreSQL for session storage over Redis.
```

**Key fields:**
- `outcomes`: Name:Probability% pairs (must sum to ~100%)
- `cascades`: TargetADR:Description:TriggerProbability% — what other decisions this one triggers
- `interactions`: OtherADR:AMPLIFY|MITIGATE:Strength — how decisions affect each other

### 2. Run a Spread

```bash
# Full reading with 10,000 simulations
tarot spread --cards ./decisions --sims 10000

# Quick reading (fewer sims)
tarot spread --cards ./decisions --sims 1000

# JSON output for automation
tarot spread --cards ./decisions --json

# Reproducible results
tarot spread --cards ./decisions --seed 42
```

### 3. Explore Your Decisions

```bash
# List all decision cards with risk indicators
tarot cards --cards-dir ./decisions list

# Detailed view of a specific card
tarot cards --cards-dir ./decisions show ADR-001

# Verbose listing with outcome breakdowns
tarot cards --cards-dir ./decisions list --verbose
```

### 4. Query Community Data

```bash
# What do other organizations experience?
tarot community search "Redis"

# Available decision types
tarot community types

# Database statistics
tarot community stats
```

### 5. Feed Evidence

```bash
# Load incident data
tarot evidence incidents incidents.json

# Evidence summary for a decision
tarot evidence summary ADR-001 --incidents incidents.json
```

## Architecture

```
tarot/
├── __init__.py         # Version
├── __main__.py         # python -m tarot entry
├── cli.py              # CLI interface (argparse)
├── cards.py            # DecisionCard model, CardRegistry, YAML parsing
├── engine.py           # MonteCarloEngine, SpreadResult, SimulationResult
├── readings.py         # ReadingGenerator, 5 reading types, format_reading()
├── bayesian.py         # BayesianUpdater, BetaDistribution, probability calibration
├── evidence.py         # EvidenceCollector, IncidentRecord, git/blog/incident sources
└── community.py        # CommunityDatabase (SQLite), seed data, anonymous submissions
```

### Core Concepts

**Decision Cards** — Each ADR becomes a card with:
- Probability distributions over outcomes (e.g., "Schema rigidity: 35%", "No issues: 65%")
- Cascade rules (when this card triggers, what other decisions are affected?)
- Interaction rules (AMPLIFY = makes another decision riskier, MITIGATE = reduces risk)

**Monte Carlo Simulation** — For each of N simulations:
1. Sample outcomes from each card's probability distribution
2. Apply interaction modifiers (amplifications/mitigations)
3. Propagate cascades recursively (max depth 5 to prevent infinite loops)
4. Track co-occurrences, cascade frequencies, and risk event counts

**Bayesian Updating** — Observed outcomes (from incidents, community data, expert estimates) update prior probabilities using Beta distributions. The system gets more accurate as you feed it evidence.

**Community Database** — SQLite-backed anonymous outcome sharing. Seed data from real-world architecture decisions (microservices migration, caching strategies, deployment patterns) provides baseline priors.

## Example Output

```
============================================================
  TAROT READING — Architecture Risk Divination
============================================================

🏚️  THE TOWER — Highest-Severity Risk Cluster
   Risk cluster: ADR-005 (Single AZ deployment) and ADR-002 (Microservices migration) — 62% chance of concurrent negative outcomes
   Severity: CRITICAL
   Probability: 62%

🎡  THE WHEEL — Cascade Patterns
   ADR-001 (PostgreSQL for session storage) will cascade to 0.3 new decisions on average per simulation run
   → ADR-003 (Redis cluster needed)

🧙  THE HERMIT — Orphaned Decisions
   1 orphaned decision(s) with no mitigations. Highest risk: ADR-005 (Single AZ deployment) at 70% probability
   ⚠ ADR-005

⭐  THE STAR — Risk Reducers
   ADR-003 (Redis cluster for caching) mitigates 1 other risk(s). Strengthening it could reduce overall risk by ~15%
   ✦ ADR-003 (Redis cluster for caching)

💀  DEATH — Decisions to Reverse
   1 decision(s) should be considered for reversal. Highest: ADR-005 (Single AZ deployment) at 70% probability of negative outcomes
   ✗ ADR-005

============================================================
📊 Simulation Summary
   Simulations: 10,000
   Horizon: 24 months
   Avg risk events per sim: 1.23
   Cards analyzed: 5
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

140 tests covering all modules: cards, engine, readings, bayesian updater, evidence collector, community database, and CLI.

## License

MIT
