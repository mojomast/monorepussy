# Assay — Metallurgical Code Grading

> Separate precious logic from slag

Assay analyzes source code the way a metallurgist assays ore — determining its composition, grade, and quality. It separates code into structural categories (the "elements"), measures the ratio of precious logic to slag, detects alloys (mixed concerns), and produces a grading report that tells you where your codebase's value actually lives.

## Installation

```bash
pip install -e .
```

Or use directly:

```bash
python -m assay grade src/
```

## Usage

### Grade Report — Measure precious logic percentage

```bash
assay grade src/
```

Shows each function's "grade" — what percentage of its lines are pure domain/business logic vs. infrastructure (validation, logging, error handling, framework calls, or outright slag).

### Composition Breakdown — Elemental analysis per function

```bash
assay compose src/payment/process.py
```

Breaks down each function into its constituent elements: 💎 Business, 🛡️ Validation, 📝 Logging, 🔌 Framework, ⚠️ Error Handling, 🗑️ Slag.

### Alloy Detection — Find mixed-concern functions

```bash
assay alloy src/
```

Detects "alloyed" functions — those with 3+ concerns interleaved. Suggests extraction refactoring to improve grade.

### Crucible Map — Locate most valuable code

```bash
assay crucible src/
```

Ranks functions by value density (grade × caller count), showing which functions are your most valuable assets and which are unstable low-grade code.

### Slag Report — Identify removable waste

```bash
assay slag src/
```

Finds reachable but valueless code: debug logging, TODO/FIXME comments, unreachable error branches, commented-out code.

### Continuous Monitoring

```bash
assay watch src/ --interval 5
```

Watches for file changes and re-analyzes on modification.

## Architecture

```
assay/
├── __init__.py        # Package init, version
├── __main__.py        # python -m support
├── cli.py             # Argparse CLI with subcommands
├── classifier.py      # AST-based statement classification engine
├── models.py          # Data models (Category, FunctionAnalysis, etc.)
├── scanner.py         # File/directory scanning
├── grade.py           # Grade calculation and trend tracking
├── compose.py         # Composition analysis
├── alloy.py           # Alloy (mixed-concern) detection
├── crucible.py        # Crucible map — value ranking
├── slag.py            # Slag detection
├── storage.py         # SQLite persistence for historical runs
└── formatter.py       # Text report formatting
```

### Classification Engine

The core of Assay is the AST-based classifier (`classifier.py`):

1. **AST parsing**: Each Python file is parsed into an AST. Function definitions are extracted.
2. **Statement classification**: Each line is classified into one of six categories:
   - **Business** 💎: Domain logic, computations, state transitions
   - **Validation** 🛡️: Input checks, guard clauses, assertions
   - **Error Handling** ⚠️: try/except, raise, error construction
   - **Logging** 📝: logger calls, print statements
   - **Framework** 🔌: DB queries, HTTP calls, ORM operations, decorators
   - **Slag** 🗑️: Debug logging, TODO/FIXME comments, unreachable branches, commented-out code
3. **Heuristic rules** (deterministic, no ML): Pattern matching on AST nodes and line content.

### Alloy Detection

A function is "alloyed" when it contains 3+ concern categories that are interleaved (not just sequential). Interleaving is measured by counting category transitions in the statement sequence.

### Grade Calculation

Grade = (business logic lines / total lines) × 100%. Higher is better.

### Storage

Results are persisted in SQLite (`.assay.db`) per project, enabling trend tracking across runs.

## Dependencies

- Python 3.10+
- No external dependencies (stdlib only: `ast`, `sqlite3`, `argparse`, `dataclasses`, etc.)

## License

MIT
