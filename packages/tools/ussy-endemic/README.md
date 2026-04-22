# Endemic — Epidemiological Analysis of Code Pattern Propagation

Anti-patterns don't just exist in isolation — they *spread*. A developer copies a try/except block that swallows errors, and suddenly that pattern appears in 15 files across 3 modules. **Endemic** applies SIR/SEIR epidemiological models to track, predict, and control the spread of code patterns through a repository.

## Overview

Endemic treats code patterns like pathogens in an epidemiological model:

- **Pathogen** = a code pattern (bad = anti-pattern, good = best practice)
- **Susceptible (S)** = modules without the pattern but structurally similar to infected ones
- **Infected (I)** = modules containing the pattern and actively propagating it
- **Recovered (R)** = modules where the pattern was refactored away with immunity
- **R0** = basic reproduction number — if R0 > 1, the pattern spreads; if R0 < 1, it dies out
- **Superspreader** = a module or developer that disproportionately propagates the pattern
- **Herd immunity** = fraction of modules that need "vaccination" (refactoring) to stop spread
- **Zoonotic jump** = a pattern crossing architectural boundaries (e.g., web → data pipeline)

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python -m endemic --help
```

## Usage

### Scan for Propagating Patterns

```bash
endemic scan src/ --history 6months
```

Detects all propagating patterns, calculates R0, identifies superspreaders, and warns about critical patterns.

### Trace Pattern Transmission

```bash
endemic trace --pattern bare-except --path .
```

Builds a transmission tree from git history showing how a pattern spread through the codebase.

### Simulate Pattern Spread

```bash
endemic simulate --pattern bare-except --r0 3.2 --horizon 6months
endemic simulate --r0 3.0 --intervention-r0 0.8 --population 50
```

Runs a discrete-time SIR simulation showing projected pattern spread with and without intervention.

### Calculate Herd Immunity

```bash
endemic herd-immunity --pattern bare-except --r0 3.2
endemic herd-immunity --pattern bare-except --path src/
```

Calculates the herd immunity threshold and recommends vaccination (refactoring) strategies.

### Monitor for Zoonotic Jumps

```bash
endemic watch src/ --zoonotic
```

Detects patterns that have crossed architectural boundaries and flags high-risk spills.

### Promote Good Patterns

```bash
endemic promote --pattern structured-logging --seed src/core/
endemic promote --pattern type-hinted-returns --path src/
```

Analyzes how to accelerate the spread of best practices and calculates cross-protection against bad patterns.

## Architecture

```
endemic/
├── __init__.py          # Package init with version
├── __main__.py          # python -m endemic support
├── cli.py               # CLI interface (argparse)
├── models.py            # Core data models (dataclasses)
├── scanner.py           # Pattern detection (AST + regex)
├── git_tracer.py        # Git history mining for transmission events
├── r0.py                # R0 estimation from transmission trees
├── sir_model.py         # Discrete-time SIR simulation
├── herd_immunity.py     # Herd immunity threshold & vaccination strategies
├── superspreader.py     # Superspreader identification
├── zoonotic.py          # Cross-domain pattern spill detection
├── promote.py           # Good pathogen promotion analysis
└── report.py            # Terminal report formatting
```

### Key Design Decisions

- **stdlib-only**: No external dependencies — uses `ast` for Python pattern detection, `re` for regex patterns, and `subprocess` for git integration
- **Discrete-time SIR**: Uses discrete compartmental model instead of ODEs to avoid scipy dependency
- **Git-based tracing**: Uses `git log` and `git blame` via subprocess for transmission event reconstruction
- **Built-in patterns**: Ships with 11 built-in patterns (8 bad, 3 good) covering common anti-patterns and best practices

### Epidemiological Model

The SIR model follows standard compartmental equations:

```
S(t+1) = S(t) - β × S(t) × I(t) / N
I(t+1) = I(t) + β × S(t) × I(t) / N - γ × I(t)
R(t+1) = R(t) + γ × I(t)
```

Where β = R0 × γ (transmission rate) and γ is the recovery rate.

### Built-in Patterns

**Bad pathogens:**
- `bare-except` — bare except: clauses
- `broad-except` — except Exception: clauses
- `pass-in-except` — except blocks with only pass
- `god-class` — classes with >15 methods
- `print-debugging` — print() in production code
- `no-type-hints` — functions without type annotations
- `test-skip-no-reason` — @pytest.mark.skip without reason
- `todo-forever` — TODO comments

**Good pathogens:**
- `structured-logging` — uses logging module
- `type-hinted-returns` — functions with return type hints
- `custom-exceptions` — defines custom exception classes

## License

MIT
