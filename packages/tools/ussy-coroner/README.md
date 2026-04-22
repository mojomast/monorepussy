# Coroner 🔬 — Forensic Trace Evidence Analysis for CI/CD Pipeline Failure Diagnosis

Every failed CI/CD build is a digital crime scene. Coroner treats it like one.

Applying forensic science principles — Locard's Exchange Principle, blood spatter reconstruction, ballistic striation matching, luminol-style hidden state detection, and chain-of-custody provenance — Coroner diagnoses WHY your pipeline failed with quantified confidence scores, not just stack traces.

## Installation

```bash
pip install -e .
```

Requires Python 3.10+. Only external dependency: `numpy` (for cross-correlation in striation matching).

## Quick Start

```bash
# Full forensic investigation of a failed run
coroner investigate run-42

# With bidirectional trace analysis (check upstream contamination)
coroner investigate run-42 --bidirectional

# Compare with the last 3 runs
coroner investigate run-42 --compare-last 3

# Individual analysis modules
coroner traces run-42            # Locard's Exchange Principle trace analysis
coroner spatter run-42           # Error origin reconstruction (blood spatter)
coroner striation run-42         # Cross-build error signature matching
coroner luminol run-42           # Hidden state detection (stale caches, undeclared env)
coroner custody run-42           # Artifact provenance / chain of custody

# Full autopsy report
coroner report run-42
```

## How It Works

### 1. Trace Evidence Analysis (`coroner traces`)

Based on **Locard's Exchange Principle**: "Every contact leaves a trace." When two pipeline stages interact, they exchange:

- **Fibers** — Shared dependency versions that diverge between stages
- **DNA** — Environment variables propagated across stages
- **Fingerprints** — Artifact usage patterns (shared files between stages)
- **Soil** — Working directory residue (path overlaps)
- **Tool marks** — Compiler/toolchain version mismatches
- **Glass fragments** — Partial output artifacts
- **Paint layers** — Nested configuration values

Each trace gets a **suspicion score** weighted by trace persistence (DNA degrades slower than soil in forensics — and env vars persist longer than working-directory residue in CI).

### 2. Blood Spatter Reconstruction (`coroner spatter`)

Treats error patterns as blood stains at a crime scene:

- **Impact angle** = arcsin(breadth / depth) — Wide, shallow errors are high-velocity (catastrophic); narrow, deep errors are low-velocity (gradual degradation)
- **Convergence zone** — Backtracks error origins using least-squares reconstruction
- **Origin depth estimation** — "Root cause is 2.3 stages before first observed error"
- **Velocity classification** — HIGH (OOM, segfault), MEDIUM (assertion/type errors), LOW (gradual degradation)

### 3. Ballistic Striation Matching (`coroner striation`)

Compares error signatures across builds to find same-root-cause failures:

- Normalizes error messages (strips timestamps, PIDs, memory addresses)
- Computes cross-correlation of error signature vectors
- Matches builds with >0.7 correlation as "same ballistic signature"
- Answers: "Is this the SAME bug that failed build #38?"

### 4. Luminol Hidden State Detection (`coroner luminol`)

Two-phase detection for invisible pipeline problems:

- **Cache luminol** — Compares artifact hashes against expected values (detects stale caches, corrupted artifacts)
- **Ninhydrin scan** — Finds undeclared environment variables affecting builds
- **Confirmatory testing** — Second pass to eliminate false positives (like real forensic luminol)

### 5. Chain of Custody (`coroner custody`)

Hash-chain provenance tracking for artifact integrity:

- Builds `H_n = SHA256(H_{n-1} || handler || timestamp || action)` chain
- Compares chains across runs to detect:
  - **Input divergence** — Different inputs at the same stage
  - **Process divergence** — Different toolchain/environment
  - **Nondeterminism** — Same inputs + same process, different outputs

## Architecture

```
coroner/
├── models.py        # Data models (TraceEvidence, ErrorStain, CustodyEntry, etc.)
├── db.py            # SQLite storage for runs, traces, and findings
├── scanner.py       # CI pipeline data ingestion (JSON + directory scan)
├── traces.py        # Locard's Exchange Principle trace analysis
├── spatter.py       # Blood spatter reconstruction
├── striation.py     # Ballistic striation matching
├── luminol.py       # Hidden state detection (cache + env luminol)
├── custody.py       # Hash-chain provenance tracking
├── investigate.py   # Full investigation orchestrator
├── report.py        # Rich terminal autopsy report generation
└── cli.py           # argparse CLI interface
```

## Input Format

Coroner ingests CI pipeline data as JSON:

```json
{
  "run_id": "build-42",
  "stages": [
    {
      "name": "checkout",
      "index": 0,
      "status": "success",
      "env_vars": {"DEP_VERSION": "1.0.0"},
      "artifact_hashes": {"src/": "a1b2c3d4"}
    },
    {
      "name": "build",
      "index": 1,
      "status": "success",
      "log_content": "BUILD SUCCESSFUL",
      "env_vars": {"DEP_VERSION": "1.0.0", "CC": "gcc"},
      "artifact_hashes": {"dist/": "e5f6g7h8"}
    },
    {
      "name": "test",
      "index": 2,
      "status": "failure",
      "log_content": "FAILED: AssertionError: expected 200 but got 401",
      "env_vars": {"DEP_VERSION": "1.0.0"}
    }
  ]
}
```

Or point `coroner` at a directory containing `run.json`, stage logs, and `env_dump.json`.

## Example Output

```
$ coroner investigate build-42 --bidirectional

🔬 CORONER — Forensic Investigation: build-42
══════════════════════════════════════════════

📋 TRACE EVIDENCE (Locard's Exchange Principle)
  ⚠️  BIDIRECTIONAL CONTAMINATION DETECTED
  Forward: build → test: TOOL_MARKS (CC=gcc vs CC=clang)
  Reverse: test → build: DNA (NODE_VERSION present only in test)
  Suspicion score: 0.87 (HIGH)

🩸 SPATTER ANALYSIS
  Velocity: MEDIUM (assertion failure pattern)
  Impact angle: 48.6° (breadth=3, depth=4)
  Origin: 2.3 stages BEFORE first observed error (σ²=0.4, confidence=0.71)

🔗 STRIATION MATCHING
  Build #38: correlation=0.84 ★ SAME ROOT CAUSE
  Build #41: correlation=0.31 (different signature)

🔦 LUMINOL SCAN
  Cache integrity: PRESUMPTIVE_POSITIVE → CONFIRMED
  Stale cache: dist/bundle.js (expected e5f6g7h8, found a1b2c3d4)
  Undeclared vars: SECRET_KEY (affects build non-deterministically)

📜 CHAIN OF CUSTODY
  Divergence at: build stage
  Cause: Process divergence (different toolchain)
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

176 tests covering all analysis modules, models, database, scanner, and CLI.

## License

MIT
