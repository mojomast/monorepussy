# Propriocept

**Proprioception and kinesthesia for developer environment awareness.**

Propriocept treats your workspace as a body with a neural body schema. It continuously maintains a somatic map of your projects, senses their state without you looking, tracks the velocity of your context switches, compresses repetitive command sequences into muscle memory, and detects **proprioceptive drift** when your assumed state diverges from actual state.

## Overview

Developer environments are complex, multi-process, multi-repo organisms. A single workspace may contain a dozen Git repositories, several background language servers, Docker containers, virtual environments, and hundreds of open files across multiple terminal sessions. Existing tools — shell prompts, `tmux` status bars, process managers — are fragmented and require *active* visual inspection. There is no passive, unified sense of workspace state.

Propriocept provides:

- **Body Schema** — a persisted JSON map of every project ("limb") in your workspace, annotated with Git state, virtual-environment presence, and process activity.
- **Passive Sense** — reads `/proc` (Linux) or `ps` (macOS) to find processes anchored to each limb, giving you a soma-map without `cd`-ing anywhere.
- **Kinesthesia** — parses shell history to compute context-switch velocity, directional bias, and flow-state indicators.
- **Muscle Memory** — extracts frequently repeated command sequences and suggests shell aliases to compress them.
- **Drift Detection** — compares your persisted body schema against ground truth and reports phantom limbs, branch drift, venv drift, and environment drift.

All in zero-dependency Python using only the standard library.

## Installation

```bash
pip install .
```

Or run directly from source:

```bash
python -m propriocept --help
```

## Usage

### Build the body schema

```bash
propriocept schema build --root ~/projects
```

This scans `~/projects`, detects Git repositories, virtual environments, and bare directories, and writes `body_schema.json`.

### Passive sense

```bash
propriocept sense --format ascii
```

Shows which limbs are active (processes running), dirty (uncommitted changes), or numb (no recent activity).

### Kinesthesia — context velocity

```bash
propriocept kinesthesia --window 1h --format json
```

Computes how rapidly you are switching contexts. A high velocity triggers a flow-guard warning.

### Muscle memory

```bash
propriocept muscle-memory --min-freq 5 --output aliases.sh
```

Scans shell history for repeated command sequences and emits suggested shell aliases.

### Drift detection

```bash
propriocept drift --threshold 0.3 --report
```

Compares the persisted schema against reality and reports mismatches such as:

- **Phantom limb** — a recorded project that no longer exists on disk.
- **Branch drift** — `.git/HEAD` differs from the stored ref.
- **Venv drift** — a recorded virtual environment has been deleted.
- **Env drift** — `$VIRTUAL_ENV` points to a deleted directory.

### Inspect a single limb

```bash
propriocept limb status ~/projects/api-server
```

## Architecture

```
propriocept/
├── cli.py          # argparse dispatch
├── schema.py       # body-schema builder
├── sense.py        # /proc and ps readers
├── kinesthesia.py  # shell-history parser & velocity metrics
├── muscle_memory.py# contiguous-sequence frequency analysis
└── drift.py        # model-reality mismatch detector
```

Every module is pure Python stdlib. No third-party dependencies are required.

## License

MIT
