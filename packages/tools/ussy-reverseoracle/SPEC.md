# SPEC: ReverseOracle — Counterfactual Code Decision Explorer

## Overview

ReverseOracle generates and evaluates counterfactual implementations of past architectural decisions. You describe a decision point ("at commit abc123, we chose Redis for caching; what if we'd used Memcached?"), and it reconstructs the decision context, generates a counterfactual implementation via LLM, runs tests against it, and produces a quantified comparison report.

## Architecture

### Core Components

```
reverseoracle/
├── __init__.py
├── cli.py              # Click CLI entry point
├── context.py          # Decision context reconstruction from git
├── generator.py        # LLM-powered counterfactual code generation
├── evolution.py        # Temporal evolution simulator
├── evaluator.py        # Test runner + metrics collection
├── reporter.py         # Decision audit report generation (text/HTML/JSON)
├── marks.py            # Decision point marking/storage
└── llm.py              # LLM provider abstraction (OpenAI-compatible API)
```

### Data Flow

```
Git Repo → context.py → Decision Context (interface, tests, deps)
                                ↓
           generator.py → Counterfactual Implementation (LLM)
                                ↓
           evolution.py → Evolved Counterfactual (LLM per-commit)
                                ↓
           evaluator.py → Metrics (test pass rate, complexity, etc.)
                                ↓
           reporter.py → Decision Audit Report
```

## CLI Surface

```
reverseoracle mark <repo> <commit> --description "chose X over Y"
reverseoracle list-marks <repo>
reverseoracle analyze <repo> --decision "Redis vs Memcached" --at-commit abc123
reverseoracle analyze <repo> --mark-id <uuid>
reverseoracle compare --counterfactual ./counterfactual/ --baseline ./my-repo
reverseoracle report --format html --output decision-audit.html
```

### Commands

1. **mark**: Mark a commit as a decision point. Stores in `.reverseoracle/marks.json` inside the repo. Includes description, commit hash, timestamp, and the alternative choice.

2. **list-marks**: Show all marked decision points in a repo.

3. **analyze**: The main pipeline. Takes a repo + decision description + commit hash (or mark ID). Reconstructs context, generates counterfactual, evolves it, evaluates, and produces report.

4. **compare**: Compare a counterfactual directory against a baseline repo. Useful when you've already generated the counterfactual and want to re-evaluate.

5. **report**: Generate a formatted report from a previous analysis. Reads from `.reverseoracle/reports/<id>.json`.

## Configuration

### `.reverseoracle/config.yaml`

```yaml
llm:
  provider: openai  # or "ollama", "anthropic"
  model: gpt-4
  base_url: https://api.openai.com/v1  # Override for custom endpoints
  api_key_env: OPENAI_API_KEY  # Environment variable name
  
analysis:
  max_evolution_commits: 50  # Max commits to evolve counterfactual through
  test_timeout: 120  # Seconds per test run
  min_test_pass_rate: 0.0  # Don't abort below this rate
  
generation:
  temperature: 0.2  # Low temp for code generation
  max_tokens: 4096
```

### Environment Variables

- `OPENAI_API_KEY` — API key for LLM provider
- `REVERSEORACLE_LLM_BASE_URL` — Override base URL
- `REVERSEORACLE_LLM_MODEL` — Override model

## Detailed Component Specs

### context.py — Decision Context Reconstruction

Inputs:
- `repo_path`: Path to git repository
- `commit_hash`: Target commit
- `module_path`: Optional path to the specific module affected by the decision

Outputs a `DecisionContext` dataclass:
```python
@dataclass
class DecisionContext:
    commit_hash: str
    description: str
    alternative: str
    interface_files: list[str]  # Files defining the interface contract
    test_files: list[str]       # Test files at that commit
    dependencies: list[str]     # Requirements/imports at that commit
    requirements_text: str      # Commit messages + PR context as text
    file_contents: dict[str, str]  # Contents of interface files
    test_contents: dict[str, str]  # Contents of test files
```

How it works:
1. `git show <commit>:<path>` to extract file contents at that commit
2. `git log --format="%s%n%b" <commit>^..<commit>` for commit messages
3. Parse `requirements.txt`, `pyproject.toml`, or `package.json` for dependencies
4. If `module_path` specified, find interface files there; otherwise infer from the commit's changed files
5. Identify test files by convention (`test_*.py`, `*_test.py`, `*.test.*`)

### generator.py — Counterfactual Code Generation

Inputs:
- `DecisionContext`
- Alternative technology/choice description

Process:
1. Build a prompt containing:
   - The interface contract (types, function signatures)
   - The current implementation (as reference for interface compliance)
   - The test suite (as specification)
   - The alternative technology description
2. Send to LLM via `llm.py`
3. Parse the response: extract code blocks
4. Validate: check that generated code parses (`ast.parse` for Python, `tsc --noEmit` for TS)
5. Write counterfactual to `.reverseoracle/counterfactuals/<id>/`

### evolution.py — Temporal Evolution Simulator

Inputs:
- Counterfactual implementation
- List of post-decision commits that touched the relevant module
- LLM provider

Process:
1. Get list of commits after the decision point that touch the relevant files: `git log <decision>..HEAD -- <module_path>`
2. For each commit (up to `max_evolution_commits`):
   a. Extract the commit's diff: `git show <commit> -- <module_path>`
   b. Build a prompt: "Here is the counterfactual code. Here is a diff from the real timeline. Apply the *intent* of this diff to the counterfactual."
   c. LLM generates updated counterfactual
   d. Validate the update parses
   e. Write updated counterfactual
3. Result: An evolved counterfactual that represents the parallel timeline

### evaluator.py — Test Runner + Metrics

Inputs:
- Baseline repo path
- Counterfactual directory path
- Test configuration

Process:
1. **Test execution**: 
   - Run `pytest` on both baseline and counterfactual
   - Capture pass/fail/skip counts and timing
   - Use subprocess with timeout
2. **Complexity metrics**:
   - Count lines of code (LOC) in relevant modules
   - Count cyclomatic complexity via `radon cc` (if available) or simple heuristic
   - Count function/class definitions
3. **Dependency analysis**:
   - Parse imports from both codebases
   - Count unique external dependencies
4. **Diff summary**:
   - Count added/removed/modified lines between baseline and counterfactual

Output: `EvaluationResult` dataclass with all metrics.

### reporter.py — Report Generation

Formats:
1. **text** (default): Human-readable terminal output
2. **json**: Machine-readable JSON
3. **html**: Styled HTML report with tables and metrics

Report sections:
1. Decision Summary (what was decided, what the alternative was)
2. Test Comparison (baseline vs counterfactual pass rates)
3. Code Metrics Comparison (LOC, complexity, dependencies)
4. Evolution Timeline (commits applied to counterfactual)
5. Verdict (overall assessment of whether the alternative was better)

### marks.py — Decision Point Storage

Storage format: `.reverseoracle/marks.json` in the repo root.

```json
[
  {
    "id": "uuid",
    "commit": "abc123",
    "description": "Chose Redis for caching over Memcached",
    "alternative": "Memcached",
    "module_path": "src/cache/",
    "created_at": "2026-04-09T15:00:00Z"
  }
]
```

Also supports git notes as an alternative storage backend.

### llm.py — LLM Provider Abstraction

Simple OpenAI-compatible client:

```python
def call_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Call LLM provider with system + user messages. Returns response text."""
```

Supports:
- OpenAI API (default)
- Any OpenAI-compatible endpoint (via `base_url` override)
- Ollama (via `http://localhost:11434/v1`)
- Anthropic (via adapter or direct)

Uses `httpx` for HTTP calls. No heavy SDKs.

## Project File Structure

```
reverseoracle/
├── .gitignore
├── pyproject.toml
├── README.md
├── SPEC.md
├── src/
│   └── reverseoracle/
│       ├── __init__.py
│       ├── cli.py
│       ├── context.py
│       ├── generator.py
│       ├── evolution.py
│       ├── evaluator.py
│       ├── reporter.py
│       ├── marks.py
│       └── llm.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_context.py
    ├── test_generator.py
    ├── test_evolution.py
    ├── test_evaluator.py
    ├── test_reporter.py
    ├── test_marks.py
    ├── test_llm.py
    └── test_cli.py
```

## Quality Gates

1. All CLI commands execute without errors on a real git repo
2. `mark` and `list-marks` work end-to-end without LLM
3. `analyze` works with a mock LLM provider (for testing)
4. Test suite passes with ≥90% pass rate
5. `ast.parse` succeeds on all source files
6. HTML report renders valid HTML5
7. Context reconstruction correctly identifies interface files and tests

## Naming Conventions

- Module: `reverseoracle` (lowercase, no hyphens)
- CLI command: `reverseoracle`
- Config dir: `.reverseoracle/`
- Data classes: PascalCase (e.g., `DecisionContext`, `EvaluationResult`)
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE

## Style

- Python 3.10+
- Click for CLI
- dataclasses for data models
- httpx for HTTP (no OpenAI SDK — keeps it provider-agnostic)
- subprocess for git commands (no gitpython)
- No external code analysis dependencies (radon is optional)
