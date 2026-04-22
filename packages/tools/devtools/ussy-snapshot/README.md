# ussy-snapshot — Freeze and Thaw Your Entire Development State

**ussy-snapshot** brings Smalltalk's image-based persistence to modern development. It freezes your **entire development state** — IDE, terminals, running processes, environment, and even a brief note about what you were thinking — into a named snapshot, and thaws it back on demand.

## Why?

Context switching between tasks destroys developer productivity. When you switch from feature A to an urgent bug fix, you lose: open files, cursor positions, running processes, debugger state, terminal history, unsaved scratch buffers, environment variables, and most critically — your **mental state** (what you were about to type next, what you just figured out, what was about to work). Studies show it takes 15-25 minutes to fully recover context after an interruption.

Snapshot solves this by capturing your complete development state as an atomic unit and restoring it on demand.

## Installation

```bash
pip install ussy-snapshot
```

Or in the ussyverse monorepo:

```bash
uv sync
```

## Usage

### Save your current state

```bash
# Save everything — terminals, files, processes, environment, and a note
ussy-snapshot save "feature-auth-oauth"
ussy-snapshot save "feature-auth-oauth" --note "Was about to wire up the callback handler in auth.py:47"
```

### Load a saved state

```bash
# Restore everything and get a reminder of what you were doing
ussy-snapshot load "feature-auth-oauth"
# → 🧠 MENTAL CONTEXT REMINDER
# → 📝 Note: Was about to wire up the callback handler in auth.py:47
# → 🌿 Branch: feature-auth-oauth
```

### Start fresh

```bash
# Create a clean environment snapshot
ussy-snapshot new "hotfix-prod-502"
```

### List snapshots

```bash
ussy-snapshot list
ussy-snapshot list --sort name
ussy-snapshot list --verbose
```

### Peek at a snapshot

```bash
# Show what's in a snapshot without loading it
ussy-snapshot peek "feature-auth-oauth"
```

### Diff two snapshots

```bash
# See what changed between two development states
ussy-snapshot diff "monday-morning" "wednesday-afternoon"
```

### Prune old snapshots

```bash
ussy-snapshot prune --older-than 7d
ussy-snapshot prune --keep-last 5
ussy-snapshot prune --older-than 30d --dry-run
```

### Export & Import

```bash
# Export for sharing with a colleague
ussy-snapshot export "feature-auth-oauth" --output snapshot.tar.gz

# Import a colleague's snapshot
ussy-snapshot import snapshot.tar.gz --name "colleagues-state"
```

### Tag snapshots

```bash
# Tag for long-term retention
ussy-snapshot tag "feature-auth-oauth" milestone-v2-release
ussy-snapshot untag "feature-auth-oauth" milestone-v2-release
```

### Run as module

```bash
python -m ussy_snapshot save "test-snap"
python -m ussy_snapshot list
```

## Architecture

```
ussy_snapshot/
├── __init__.py          # Package init, version
├── __main__.py          # python -m support
├── cli.py               # argparse CLI with all subcommands
├── core.py              # Core operations: save, load, new, peek, tag, untag
├── models.py            # Dataclasses: Snapshot, TerminalState, EditorState, etc.
├── storage.py           # Read/write snapshots to ~/.local/share/ussy-snapshot/
├── terminal.py          # Terminal state capture (tmux, current terminal)
├── editor.py            # IDE/editor state capture (VS Code, Vim, JetBrains)
├── process.py           # Process state capture and restart
├── environment.py       # Environment variable capture and restore
├── context.py           # Mental context capture (notes, git state, auto-suggestions)
├── diff.py              # Snapshot diffing (terminals, files, env, processes)
├── export.py            # Export/import to portable tar.gz archives
└── prune.py             # Pruning old or excess snapshots
```

### State Dimensions

Each snapshot captures five dimensions of development state:

1. **Terminal State** — Working directory, environment variables, command history, running processes, screen buffer, foreground command. Supports tmux sessions.

2. **Editor State** — Open files, cursor positions, breakpoints, layout. Supports VS Code, Vim/Neovim, and JetBrains IDEs.

3. **Process State** — Running development processes (servers, watchers, REPLs). Records startup commands for restart on thaw.

4. **Environment State** — Project-relevant environment variables (secrets excluded by default), PATH entries, .env file discovery.

5. **Mental Context** — Explicit notes about current thinking, auto-suggested context from git state (branch, status, last commit).

### Storage

Snapshots are stored in `~/.local/share/ussy-snapshot/<name>/` as JSON files:
- `snapshot.json` — Complete snapshot data
- `metadata.json` — Lightweight metadata for fast listing

Override the storage directory with the `USSY_SNAPSHOT_DIR` environment variable.

### Dependencies

- `ussy-core` — shared utilities from the ussyverse monorepo

## Running Tests

```bash
uv run pytest tests/ -v
```

## License

MIT
