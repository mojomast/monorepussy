# 🛡️ Sentinel — Immunological Self/Non-Self Code Governance

Sentinel applies the **Negative Selection Algorithm** from artificial immune systems to build codebase-specific governance that emerges from the code itself — no manually-written rules required.

## Overview

Traditional code governance tools impose rules from the outside in. Linters enforce generic style rules. Static analyzers flag known anti-patterns. These rules know nothing about *your* codebase's specific identity, conventions, or evolutionary trajectory.

**Sentinel** learns what "normal" looks like for *your specific codebase* and flags deviations from that learned norm. It treats code governance as an immunological problem — distinguishing self (your codebase's native patterns) from non-self (anomalous patterns).

### The Immunological Metaphor

| Biological Immune System | Sentinel |
|--------------------------|---------|
| Self proteins | Code patterns native to your codebase |
| Non-self pathogens | Anomalous code patterns not in your codebase's identity |
| Thymus (T-cell training) | Training phase: learn "self" from git history |
| Negative selection | Discard detectors that match "self" → only keep non-self detectors |
| Affinity maturation | Refine detectors based on false positive feedback |
| Memory cells | Persist effective detectors across sessions |
| Autoimmune disease | Over-sensitive governance (too many false positives) |

## Installation

```bash
pip install -e .
```

Zero external dependencies — uses only Python stdlib.

## Usage

### 1. Initialize a project

```bash
sentinel init ./my-project --source ./src
```

### 2. Train a self-profile

Learn what "normal" looks like for your codebase:

```bash
sentinel train ./src --name my-project --granularity function
```

Optionally include git history:

```bash
sentinel train ./src --history 6m --name my-project
```

### 3. Generate detectors

Use negative selection to create a population of anomaly detectors:

```bash
sentinel generate --detectors 1000 --matching-threshold 0.3 --seed 42
```

### 4. Check code for anomalies

```bash
sentinel check ./src/new_feature.py --explain
sentinel check ./src/ --threshold 0.5
```

Output example:
```
🛡️  SENTINEL REPORT: new_feature.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANOMALY SCORE: 0.73 / 1.0 (ELEVATED)

Detectors Fired:
  [D-0028] complex_function at line 15 (dist=0.187, strength=0.38)
  [D-0047] VeryBadName at line 22 (dist=0.221, strength=0.26)
```

### 5. Provide feedback (Affinity Maturation)

Mark detections as true or false positives to improve the detector population:

```bash
sentinel feedback D-0028 --true-positive    # Good catch!
sentinel feedback D-0047 --false-positive   # This was actually fine
```

### 6. View the self-profile

```bash
sentinel profile --name my-project
```

### 7. Export/Import detectors

```bash
sentinel export --output detectors.json
sentinel import detectors.json --name production-detectors
```

## Architecture

```
sentinel/
├── __init__.py       # Package metadata
├── extractor.py      # AST pattern extraction from Python source
├── distance.py       # Distance metrics (Euclidean, Manhattan, Hamming, Cosine)
├── profile.py        # Self-profile building (from files or git history)
├── detectors.py      # Negative selection detector generation & feedback
├── checker.py        # Anomaly scoring and report generation
├── db.py             # SQLite persistence for profiles and detectors
└── cli.py            # Command-line interface (argparse)
```

### Core Algorithm: Negative Selection

1. **Self-Definition**: Extract feature vectors from the codebase (imports, naming, complexity, control flow shapes, etc.)
2. **Detector Generation**: Randomly generate candidate pattern vectors. Discard any that match the self-corpus within a threshold (autoreactive). Keep only non-self detectors.
3. **Surveillance**: When new code is checked, extract its patterns and test against the detector population. Detectors that fire indicate anomalous patterns.
4. **Affinity Maturation**: Developer feedback adjusts detector thresholds — true positives make detectors more sensitive, false positives make them less sensitive.

### Feature Vector Dimensions

Each code pattern is encoded as a 25-dimensional feature vector:

- **Naming** (6): name length, entropy, snake_case, camelCase, avg variable name length, variable name entropy
- **Complexity** (7): cyclomatic complexity, nesting depth, statements, returns, raises, loops, conditionals
- **Structure** (5): arguments, defaults, docstring, decorators, local variables
- **Control Flow Shape** (4): linear, branching, looping, exception ratios
- **Imports** (3): import count, stdlib ratio, local ratio

All features are normalized to [0, 1] for distance computation.

## Test Suite

Run with pytest:

```bash
pytest tests/ -v
```

The test suite includes 60+ tests covering:
- Pattern extraction from AST fixtures
- Distance metric correctness
- Self-profile building and serialization
- Negative selection algorithm (property: detectors must not match self)
- Anomaly scoring and severity classification
- SQLite persistence roundtrips
- CLI command handling
- End-to-end integration tests

## License

MIT
