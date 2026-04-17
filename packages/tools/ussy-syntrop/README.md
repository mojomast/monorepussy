# Syntrop

**Cross-language behavioral fuzzing via esolang compilation and semantic probes.**

Traditional fuzzing generates random *inputs* to find crashes. Syntrop fuzzes the *execution semantics* itself — compiling your code through radically different computational models and comparing observable behavior. Any divergence reveals an implicit assumption that one execution model violates but another doesn't.

## Overview

Syntrop operates in two modes:

### 1. Semantic Probes (Practical / CI-friendly)

Lightweight transformations that apply one esolang-inspired semantic twist to your Python code:

| Probe | Inspired By | What It Reveals |
|---|---|---|
| `randomize-iteration` | Brainfuck | Hidden dependencies on iteration order |
| `shuffle-evaluation-order` | INTERCAL | Dependencies on argument evaluation order |
| `alias-state` | Befunge | Identity vs. equality bugs (shared state) |
| `nondeterministic-timing` | INTERCAL | Timing/atomicity assumptions |

### 2. Esolang Backend Compilation (Research)

Compile your code through esoteric languages with genuinely different computational models:

- **INTERCAL backend**: Random COME FROM control flow reveals hidden control-flow assumptions
- *(Brainfuck, Befunge backends: future work)*

## Installation

```bash
# From source
pip install -e .

# With Rich for pretty terminal output
pip install -e ".[rich]"

# Development dependencies
pip install -e ".[dev]"
```

## Usage

### Run semantic probes on a file

```bash
# Run all probes
syntrop probe --file my_code.py

# Run a specific probe
syntrop probe --file my_code.py --probes randomize-iteration

# Specify the function to test
syntrop probe --file my_code.py --function process --probes randomize-iteration,alias-state
```

### Scan a project directory

```bash
# Scan current directory
syntrop scan

# Scan a specific directory
syntrop scan --directory ./src

# Only run specific probes
syntrop scan --directory ./src --probes randomize-iteration
```

### Compare behavior across probe modes

```bash
# Diff all probes
syntrop diff --file my_code.py

# Diff specific probes
syntrop diff --file my_code.py --probes randomize-iteration,shuffle-evaluation-order
```

### Use as a Python module

```python
from syntrop.runner import run_probe, run_all_probes, diff_probes

source = '''
def main():
    result = []
    for item in [1, 2, 3]:
        result.append(item * 2)
    return result
'''

# Run a single probe
result = run_probe(source, "randomize-iteration", "main")
print(f"Diverged: {result.diverged}")
print(f"Type: {result.divergence_type}")
print(f"Explanation: {result.explanation}")

# Compare across all probes
diff = diff_probes(source)
print(f"Consistent: {diff.consistent}")
```

### Python module invocation

```bash
python -m syntrop probe --file my_code.py
```

## Architecture

```
syntrop/
├── __init__.py          # Package init, version
├── __main__.py          # python -m syntrop entry point
├── cli.py               # CLI with probe/scan/diff subcommands
├── ir.py                # Intermediate Representation layer
├── analyzer.py          # AST-based behavioral assumption scanner
├── runner.py            # Orchestrates probe execution
├── probes/
│   ├── __init__.py      # Probe registry
│   ├── base.py          # BaseProbe ABC
│   ├── randomize_iteration.py   # Shuffle loop/iteration order
│   ├── shuffle_eval_order.py    # Randomize arg evaluation order
│   ├── alias_state.py           # Introduce state aliasing
│   └── nondeterministic_timing.py # Inject random delays
└── backends/
    ├── __init__.py      # Backend registry
    └── intercal.py      # INTERCAL backend (proof-of-concept)
```

### How Probes Work

1. **Transform**: The probe's AST transformer modifies the source code to apply the semantic twist
2. **Execute**: Both original and transformed code are executed in isolated namespaces
3. **Compare**: Results are compared, with divergence detection specific to each probe type
4. **Explain**: Each divergence is explained in natural language

### How the Analyzer Works

The `AssumptionScanner` walks the Python AST and detects patterns that rely on implicit assumptions:

- `for` loops over dicts/sets (iteration-order)
- Function calls with multiple arguments (eval-order)
- Augmented assignments (timing-atomicity)
- Multiple assignment targets (state-aliasing)
- Dict literals with duplicate keys
- List comprehensions
- Modification during iteration

## Example Output

```
Syntrop: Running probes on process.py
Probes: randomize-iteration, shuffle-evaluation-order, alias-state, nondeterministic-timing
============================================================
  Probe: randomize-iteration  [DIVERGED] [warning]
  Type: order-flip
  Explanation: Result elements are the same but in different order —
  the code has a hidden dependency on iteration order
  Original: [1, 2, 3]
  Probed:   [3, 1, 2]

  Probe: shuffle-evaluation-order  [OK]
  Results match — no evaluation-order dependency detected

============================================================
FOUND 1 divergence(s) across 4 probe(s)
```

## License

MIT
