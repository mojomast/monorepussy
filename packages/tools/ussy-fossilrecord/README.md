# FossilRecord

**Esolang stress testing for developer tools** — mutation testing for tool robustness.

If your tool can handle Brainfuck, Befunge, and Malbolge, it can handle anything.

## Overview

Modern developer tools (IDEs, linters, formatters, AI assistants) are built and tested against conventional code. But real-world codebases contain generated code, minified bundles, embedded DSLs, metaprogramming, and legacy patterns. When tools encounter code outside their training distribution, they often fail silently or catastrophically.

**FossilRecord** uses esoteric programming languages as extreme test cases for developer tools. Just as fossils are extreme organisms that test our understanding of biology, esolangs are extreme programming paradigms that test our tools' understanding of code.

### Key Features

- **Curated Esolang Corpus**: 20+ programs across Brainfuck, Befunge, Whitespace, Malbolge, INTERCAL, Shakespeare, GolfScript, and more
- **Tool Stress Test Harness**: Plugin architecture for testing parsers, linters, formatters, and AI tools
- **Fossil Score**: A 0-100 robustness score for developer tools, broken down by category
- **Living Fossil Generator**: Creates hybrid test cases by embedding esolang code in conventional languages
- **Tool Comparison**: Compare robustness across tool versions or competing tools

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Usage

### Browse the Esolang Corpus

```bash
fossil corpus                        # List all programs
fossil corpus --list-languages       # List languages
fossil corpus --list-categories      # List stress categories
fossil corpus --language Brainfuck   # Filter by language
fossil corpus --category whitespace  # Filter by category
```

### Run a Stress Test

```bash
fossil test                          # Test against full corpus
fossil test --tool my-linter         # Name the tool being tested
fossil test --language Brainfuck     # Test only Brainfuck programs
fossil test --category whitespace    # Test only whitespace-stress programs
fossil test --min-difficulty 3       # Only hard programs
fossil test --timeout 30             # 30s timeout per plugin
fossil test --output results.json    # Save results
```

### Get a Fossil Score

```bash
fossil score --tool my-linter --version 2.1
fossil score --results-file results.json  # Score from saved results
fossil score --output score.json          # Save score
```

The Fossil Score (0-100) is computed as:

```
fossil_score = weighted_sum(
    parse_rate * 0.2,
    analysis_accuracy * 0.3,
    crash_resistance * 0.3,
    memory_efficiency * 0.1,
    ai_comprehension * 0.1
) * 100
```

### Generate Living Fossils

```bash
fossil generate --count 50              # Generate 50 hybrid test cases
fossil generate --category 2d --count 20  # Generate 2D-stress tests
fossil generate --seed 42               # Reproducible generation
fossil generate --output fossils.json   # Save to file
```

### Compare Tools

```bash
fossil compare score_v1.json score_v2.json
fossil leaderboard score1.json score2.json score3.json
```

## Architecture

```
fossilrecord/
├── __init__.py              # Package metadata
├── __main__.py              # python -m fossilrecord
├── cli.py                   # CLI (argparse-based, `fossil` command)
├── corpus/
│   ├── __init__.py
│   ├── loader.py            # CorpusLoader, EsolangProgram, StressCategory
│   └── data/
│       └── corpus.json      # 25 esolang programs across 12+ languages
├── harness/
│   ├── __init__.py
│   ├── plugins.py           # Plugin architecture (Parser, Linter, Formatter, AI)
│   ├── runner.py            # HarnessRunner, TestResult, TestSuiteResult
│   └── result.py            # Re-exports
├── generator/
│   ├── __init__.py
│   └── living_fossil.py     # LivingFossilGenerator, GenerationConfig
├── scoring/
│   ├── __init__.py
│   └── fossil_score.py      # FossilScore, compute_fossil_score, historical tracking
└── compare/
    ├── __init__.py
    └── comparator.py        # ToolComparator, ComparisonResult, leaderboard
```

### Plugin Architecture

The test harness uses a plugin system. Each plugin type tests a different aspect of tool robustness:

| Plugin | Tests | Default Behavior (no command) |
|--------|-------|-------------------------------|
| `ParserPlugin` | Can the tool parse the code? | Checks source non-empty, reports metrics |
| `LinterPlugin` | Does the linter crash? | Simulates linting, reports warnings |
| `FormatterPlugin` | Can the formatter handle it? | Checks formatting properties |
| `AIPlugin` | Can AI explain the code? | Simulates comprehension scoring |

To test real tools, pass a command to the plugin:

```python
from fossilrecord.harness.plugins import ParserPlugin

# Test Python's ast module as a parser
plugin = ParserPlugin(command=["python", "-c", "import ast, sys; ast.parse(sys.stdin.read())"])
```

### Stress Categories

| Category | What It Tests | Example Esolangs |
|----------|---------------|------------------|
| `whitespace` | Invisible code / non-standard characters | Whitespace |
| `2d` | Non-linear control flow | Befunge-93 |
| `self-modifying` | Self-modifying / encrypted semantics | Malbolge |
| `visual` | Image-based / visual programming | Piet |
| `natural-language` | Natural language syntax | Shakespeare, Chef |
| `parody` | Intentional absurdity | INTERCAL |
| `concise` | Extreme conciseness / symbol overload | GolfScript, APL, Jelly |
| `obfuscated` | Intentional obfuscation | Malbolge, Brainfuck |
| `minimalistic` | Extremely few instructions | Brainfuck |

## Dependencies

**Zero external dependencies** — Python stdlib only. Requires Python 3.9+.

## License

MIT
