# ChurnMap — Code Change Impact Territory Map

> *See your codebase as a game map. Territories that change together sit next to each other. Hot zones glow red. Dead code fades to grey.*

ChurnMap generates a **territory map** (think: Risk/Civilization) of your codebase from git history. It performs **co-change analysis** — detecting which modules frequently change together — and renders the result as a visually rich map where:

- Each **territory** represents a module/directory
- Adjacent territories are **coupled** (they change together frequently)
- Territory **color** encodes change frequency: 🔴 Hot → 🟠 Warm → 🔵 Stable → ⚪ Dead
- **Border conflicts** (╳) mark high-coupling boundaries that need attention
- **Unclaimed territory** shows orphaned/dead code

**This is NOT a dependency graph.** Dependency graphs show imports. ChurnMap shows *behavioral* coupling — what actually changes together in practice, revealing hidden architectural problems.

## Install

```bash
pip install .
# or with dev dependencies
pip install ".[dev]"
```

Requires Python 3.10+, git, and a git repository to analyze.

## Usage

```bash
# Analyze current repo, show territory map
churnmap .

# Analyze a specific repository
churnmap /path/to/repo

# Only recent history
churnmap . --since 2024-01-01

# Group by second-level directories
churnmap . --depth 2

# Generate SVG for web viewing
churnmap . --format svg --output map.svg

# Require stronger coupling evidence (default: 3)
churnmap . --min-cochanges 5

# Larger map
churnmap . --width 120 --height 60

# Pipe-friendly (no ANSI colors)
churnmap . --no-color

# Show analysis progress
churnmap . --verbose
```

## Example Output

```
╭──────────────────────────────────── ChurnMap ────────────────────────────────────╮
│ ██████████▓▓▓▓▓▓▒▒▒▒░░░░                                                          │
│ █████████▓▓▓╳╳▓▓▒▒▒░░░░░                                                          │
│ ████████▓▓╳╳╳╳▓▒▒▒░░░░░░   ← Border conflict = high coupling!                   │
│ ███████▓▓╳╳▓▓▓▒▒▒░░░░░░░                                                          │
│ ██████▓▓▓▓▒▒▒░░░░░░░░░░░                                                          │
│ ████▓▓▒▒░░░░░░░░░░░░░░░░                                                          │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─────────────────── Legend ───────────────────╮
│ █  Hot        Frequently changed, high risk  │
│ ▓  Warm       Moderately active              │
│ ▒  Stable     Rarely changed, low risk       │
│ ░  Dead       Orphaned/dead code             │
╰──────────────────────────────────────────────╯
```

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--since DATE` | (all) | Only analyze commits after this date |
| `--until DATE` | (all) | Only analyze commits before this date |
| `--max-commits N` | 1000 | Limit to last N commits |
| `--depth N` | 1 | Module grouping depth (1 = top-level dirs) |
| `--min-cochanges N` | 3 | Minimum co-change count to consider |
| `--format FORMAT` | ascii | Output format: `ascii` or `svg` |
| `--output FILE` | (stdout) | Output file path |
| `--width N` | 80 | Map width in characters |
| `--height N` | 40 | Map height in characters |
| `--no-color` | false | Disable ANSI colors |
| `--verbose` | false | Show analysis progress |

## How It Works

```
git log → PyDriller (commit mining)
       → Co-change matrix (which modules change together?)
       → NetworkX graph (weighted by co-change strength)
       → Louvain community detection (group into territories)
       → Force-directed layout + Voronoi tessellation (compute borders)
       → ASCII or SVG rendering (game-map visualization)
```

### Co-Change Analysis

For each commit, ChurnMap records which modules were modified. If modules A and B appear in the same commit, their co-change count increases. The Jaccard similarity between their change sets determines coupling strength.

### Community Detection

The Louvain algorithm groups modules into communities (territories) based on co-change patterns. Each community represents a cluster of code that tends to change as a unit.

### Change Frequency Classification

| Category | Percentile | Color | Meaning |
|----------|-----------|-------|---------|
| Hot | > 75th | Red `█` | Frequently changed, high risk |
| Warm | 50th-75th | Yellow `▓` | Moderately active |
| Stable | 25th-50th | Blue `▒` | Rarely changed, low risk |
| Dead | < 25th | Grey `░` | Orphaned/dead code |

## Architecture

```
churnmap/
├── __init__.py      # Package init
├── cli.py           # CLI entry point (argparse)
├── mining.py        # Git commit mining (PyDriller + git CLI fallback)
├── cochange.py      # Co-change matrix + graph construction
├── communities.py   # Louvain community detection + stats
├── layout.py        # Force layout + Voronoi tessellation
├── render.py        # ASCII/SVG rendering
└── colors.py        # ANSI color definitions, SVG color palette
```

## Development

```bash
# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -v

# Run on any repo
churnmap /path/to/repo --verbose
```

## License

MIT
