# Ussy Triage — Error Logs as Crime Scenes

> **Migration Notice:** This package was migrated from the standalone `triageussy` repository into the `ussyverse` monorepo. The package name is now `ussy-triage` and the Python import path is `ussy_triage`. The legacy `triage` command still works but emits a deprecation warning.

> Build failures are crime scenes. Triage is the detective.

Triage applies **forensic methodology** to error analysis, transforming walls of log noise into structured detective reports with suspects, evidence, motives, witness testimony, and recommended actions.

## The Problem

Build failures and error logs are walls of noise. A typical CI build log is 500+ lines of dependency resolution, compilation output, test runner chatter, and — buried on line 473 — the actual error that matters. Developers spend enormous cognitive energy **finding** the error, let alone understanding it.

## The Solution

Triage treats build failures as **crime scenes** and applies a 7-step forensic methodology:

1. **Secure the Scene** — Isolate the actual error from surrounding noise
2. **Identify the Victim** — What failed? (build, test, runtime, deployment)
3. **Locate the Suspect** — The specific line, function, or component responsible
4. **Gather Evidence** — Context lines, related files, git blame
5. **Establish Motive** — Root cause hypothesis — *why* did this fail?
6. **Witness Testimony** — Cross-reference with project history
7. **Closing Argument** — Recommended fix with confidence level

## Example Output

```
🔍 CRIME SCENE: Error #1

━━━ 🎯 THE SUSPECT ━━━
Missing trait implementation: AppError needs to implement From<SqlxError>
Location: src/api/handlers.rs:142

━━━ 📋 THE EVIDENCE ━━━
  Line 473: error[E0277]: the trait bound `AppError: From<SqlxError>` is not satisfied
  Context: let user = db.get_user(id)?;

━━━ 💡 THE MOTIVE ━━━
The function returns `Result<T, AppError>` but `sqlx::query` errors aren't automatically convertible. You added a new database call without updating the error conversion impl.

━━━ 👁️ WITNESS TESTIMONY ━━━
  — This error pattern has appeared 3 times before in this project
  — Previous: a3f7b2c — "Add From<SqlxError> for AppError"

━━━ 🔧 RECOMMENDED ACTION ━━━
Add `impl From<sqlx::Error> for AppError { ... }` or use a type that already implements From<SqlxError>

━━━ 📁 CASE CLOSED? ━━━
🟢 Confidence: 92% | Pattern: known | Severity: error
```

## Installation

```bash
pip install ussy-triage
```

Or for development inside the monorepo:
```bash
uv sync --package ussy-triage
```

## Usage

### Pipe any command's output through ussy-triage

```bash
# Rust
cargo build 2>&1 | ussy-triage

# Python
python app.py 2>&1 | ussy-triage

# Node.js
npm run build 2>&1 | ussy-triage

# Go
go build ./... 2>&1 | ussy-triage
```

### Analyze a saved log file

```bash
ussy-triage analyze build-log.txt
```

### Quick mode — just the fix

```bash
npm run build 2>&1 | ussy-triage --quick
# Output: [src/app.ts:42] Check the function signature and ensure arguments match expected types (confidence: 80%)
```

### Teaching mode — extended explanations

```bash
ussy-triage analyze error.log --teach
```

### JSON output for tool integration

```bash
ussy-triage analyze error.log --json
```

### Manage error patterns

```bash
# Add a custom pattern
ussy-triage pattern add --regex "CustomError: (.*)" --cause "Our custom error" --fix "Check the config"

# List patterns
ussy-triage pattern list

# Filter by language
ussy-triage pattern list --language python

# Remove a custom pattern
ussy-triage pattern remove 42
```

### Specify project directory for git context

```bash
ussy-triage analyze error.log --project /path/to/project
```

## Architecture

```
Raw Log/Stdin → ErrorExtractor → PatternMatcher → ContextEnricher → DiagnosisRenderer
                     ↓                  ↓                   ↓
              IsolatedError     ErrorPattern       EnrichedError
              {                 {                   {
                line: 473,       type: "rust_       git_blame: ...,
                content: "...",    compile",        similar_fixes: [...],
                context: [...]   confidence: 0.92   project_patterns: [...]
              }                 }                   }
```

### Components

| Module | Purpose |
|--------|---------|
| Module | Purpose |
|--------|---------|
| `extractor.py` | Multi-format log parser — isolates errors from noise |
| `patterns.py` | SQLite-backed pattern database with 50+ curated error patterns |
| `enricher.py` | Git blame, history search, and context gathering |
| `renderer.py` | Output formatting — detective, JSON, minimal, teaching modes |
| `models.py` | Shared data models (IsolatedError, EnrichedError, Diagnosis) |
| `cli.py` | CLI interface with argparse |
| `legacy.py` | Deprecation shim for the old `triage` entry point |

### Supported Error Types

- **Compilers**: Rust (rustc), Go, TypeScript (tsc), C/C++ (gcc/clang)
- **Runtimes**: Python (tracebacks), JavaScript (TypeError, ReferenceError, etc.)
- **Test frameworks**: pytest, jest, go test, cargo test
- **Build systems**: cargo, npm, pip, gradle, bazel
- **CI/CD**: GitHub Actions, GitLab CI, Jenkins
- **Runtime crashes**: panics, segfaults, OOM, stack overflow

## Requirements

- Python 3.11+
- `ussy-core` (workspace dependency)
- Git (optional, for git blame and history features)

## License

MIT
