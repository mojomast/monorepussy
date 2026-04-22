# Mushin

**Persistent live workspace for code exploration** — a Smalltalk-image-like persistence layer for any language, at the exploration layer.

> *Mushin* (無心) is Japanese for "no-mind" — the state of flow where action and awareness become one.

## The Problem

Every coding session starts from scratch. You open files, inspect variables, build mental models — then close the laptop and it all evaporates. The gap between *"I was in the middle of understanding this codebase"* and *"I can resume where I left off"* costs developers an estimated 15–20 minutes per context switch.

## What Mushin Does

Mushin captures and restores your **full development context** as a first-class object:

- **Evaluation journal** — Every expression you evaluate is recorded with timestamp, input, output, and context. Replayable to reconstruct your workspace state.
- **Workspace save/restore** — `mushin save` snapshots your session; `mushin resume` brings it back exactly as it was.
- **Workspace branching** — Fork your exploration state like git branches. Try an approach without losing your current understanding.
- **Spatial bookmarks** — "I was here" markers that capture file, line, scroll position, visible code range, and annotations.
- **Live object cache** — Serialize and restore Python objects (DataFrames, models, in-memory graphs) between sessions.
- **Workspace diff** — Compare what changed between sessions or between branches.

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Quick Start

```bash
# Initialize mushin in your project
mushin init

# Save your current workspace
mushin save -n "exploring-auth"

# Record evaluation entries
mushin record "import pandas as pd" -o "imported pandas"
mushin record "df = pd.read_csv('data.csv')" -o "DataFrame with 1000 rows"

# View the journal
mushin journal

# Create a branch to try an alternative approach
mushin branch alternative -p <workspace-id>

# Set a spatial bookmark
mushin bookmark auth-entry -f auth/handler.py -l 42 -a "Login handler starts here"

# Resume where you left off
mushin resume <workspace-id>

# Compare two workspaces
mushin diff <left-id> <right-id>

# View project info
mushin info
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `mushin init` | Initialize `.mushin` in the project directory |
| `mushin save [-n NAME] [-d DESC]` | Save current workspace |
| `mushin resume [WORKSPACE_ID]` | Resume a workspace |
| `mushin list` | List all workspaces |
| `mushin delete WORKSPACE_ID` | Delete a workspace |
| `mushin record EXPR [-o OUTPUT]` | Record a journal entry |
| `mushin journal [WORKSPACE_ID]` | Show the evaluation journal |
| `mushin replay [WORKSPACE_ID]` | Replay the journal |
| `mushin branch NAME [-p PARENT]` | Create a workspace branch |
| `mushin branches` | List branches |
| `mushin bookmark NAME [-f FILE] [-l LINE]` | Create a spatial bookmark |
| `mushin bookmarks` | List bookmarks |
| `mushin diff LEFT RIGHT` | Compare two workspaces |
| `mushin info` | Show active workspace info |

All commands accept `-C DIR` / `--project-dir DIR` to specify the project directory (default: current working directory).

You can also run mushin as a Python module:

```bash
python -m mushin --version
python -m mushin init
```

## Architecture

```
mushin/
├── __init__.py       # Package version
├── __main__.py       # python -m mushin support
├── cli.py            # argparse-based CLI with subcommands
├── storage.py        # Low-level JSON/binary persistence, atomic writes
├── journal.py        # Evaluation journal (append-only, replayable)
├── workspace.py      # Workspace create/save/load/resume, object cache
├── branching.py      # Workspace branching (fork exploration state)
├── bookmarks.py      # Spatial bookmarks with context
├── objects.py        # Live object cache (pickle-backed)
└── diff.py           # Workspace diff/comparison
```

### Data Layout

All data is stored under `.mushin/` in the project root:

```
.mushin/
├── active              # Currently active workspace ID
├── branches.json       # Branch registry
├── journals/           # One JSON file per workspace
│   └── <ws-id>.json
├── workspaces/         # Workspace metadata
│   └── <ws-id>/
│       └── meta.json
├── objects/            # Pickled Python objects
│   └── <ws-id>/
│       ├── model.pkl
│       └── dataframe.pkl
└── bookmarks/
    └── bookmarks.json
```

### Design Principles

1. **Zero external dependencies** — stdlib only (pickle, json, argparse, dataclasses)
2. **Atomic writes** — All file writes go through temp-file + rename for crash safety
3. **Append-only journal** — Never mutates history; always adds new entries
4. **Content-addressed branches** — Branches inherit parent state and diverge
5. **Graceful degradation** — Unpicklable objects are stored as repr() placeholders

## Running Tests

```bash
pip install pytest
pytest
```

## License

MIT
