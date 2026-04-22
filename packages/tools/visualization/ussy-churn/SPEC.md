# ChurnMap — Code Change Impact Territory Map

## Overview

ChurnMap generates a **territory map** (think: Risk/Civilization game map) of your codebase from git history. It performs co-change analysis — detecting which modules frequently change together — and renders the result as a visually rich game-map where each territory represents a code module, adjacent territories are coupled, and colors encode change frequency.

**This is NOT a dependency graph.** Dependency graphs show import structure. ChurnMap shows *behavioral* coupling — what actually changes together in practice, revealing hidden architectural problems that no import graph can surface.

## Problem Statement

Coupling and cohesion are invisible. Developers can't *see* that modules A and B always change together (high coupling) or that module C is an island nobody touches. Code reviews miss the "these 5 files always change together" patterns because nobody cross-references git history. Existing tools (Code Maat, Gource) produce data tables or abstract graphs — nothing that makes coupling *visceral and obvious*.

## Architecture

```
git repo → PyDriller (commit mining) → co-change matrix → NetworkX graph
                                                              ↓
                                                        Louvain communities
                                                              ↓
                                                    force-directed layout
                                                              ↓
                                                    Voronoi tessellation
                                                              ↓
                                              ASCII territory map (terminal)
                                              SVG territory map (optional)
```

## Core Components

### 1. Git Mining (`churnmap/mining.py`)
- Use PyDriller to parse git log
- Extract: commit hash, timestamp, list of modified files per commit
- Support `--since` and `--until` date ranges
- Support `--max-commits N` to limit analysis
- Group files by module (directory path up to configurable depth, default: top-level dir)
- Return structured data: list of (commit_hash, timestamp, [module_paths])

### 2. Co-Change Analysis (`churnmap/cochange.py`)
- Build a co-occurrence matrix: for each commit, increment the co-change count for every pair of modules modified in that commit
- Compute normalized coupling strength: Jaccard similarity between module change sets
- Apply minimum threshold (`--min-cochanges`, default: 3) to prune noise
- Return weighted graph (NetworkX) where nodes = modules, edges = co-change strength

### 3. Community Detection (`churnmap/communities.py`)
- Apply Louvain community detection on the co-change graph
- Each community = a "territory" on the map
- Compute per-territory stats: total files, total commits, active authors, change frequency
- Compute per-module stats: change frequency (hot/warm/stable/dead)
- Assign territories descriptive names from their most-changed subdirectory

### 4. Map Layout & Rendering (`churnmap/layout.py`)
- Position territory centroids using force-directed layout (NetworkX spring_layout)
- Apply Voronoi tessellation on centroids to compute territory borders
- Map Voronoi cells to a character grid (configurable width/height, default: 80x40)
- Fill each cell with territory color/character based on change frequency:
  - 🔴 Hot (frequent changes): red ANSI, `█` character
  - 🟠 Warm: yellow ANSI, `▓` character
  - 🔵 Stable (rare changes): blue ANSI, `▒` character
  - ⚪ Dead (no recent changes): grey ANSI, `░` character
- Draw borders between territories using Unicode box-drawing: `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`

### 5. Map Rendering (`churnmap/render.py`)
- **ASCII mode** (default): Render territory map to terminal using Rich library
  - Color-coded territories with legend
  - Territory labels (abbreviated names)
  - Summary stats panel alongside the map
  - Border conflicts (high coupling between adjacent territories) shown as `╳` markers
- **SVG mode** (`--format svg`): Render as SVG file for web viewing
  - Colored polygons for territories
  - Labels, legend, hover tooltips
  - Output to file: `churnmap.svg`

### 6. CLI (`churnmap/cli.py`)
- Main entry point using Click or argparse
- Single command: `churnmap <repo-path>`
- Options:
  - `--since DATE` — only analyze commits after this date
  - `--until DATE` — only analyze commits before this date
  - `--max-commits N` — limit to last N commits (default: 1000)
  - `--depth N` — module grouping depth (default: 1 = top-level dirs)
  - `--min-cochanges N` — minimum co-change count to consider (default: 3)
  - `--format FORMAT` — output format: `ascii` (default) or `svg`
  - `--output FILE` — output file path (default: stdout for ascii, churnmap.svg for svg)
  - `--width N` — map width in characters (default: 80)
  - `--height N` — map height in characters (default: 40)
  - `--no-color` — disable ANSI colors
  - `--verbose` — show analysis progress

## CLI Surface

```
$ churnmap .                          # Analyze current repo, show territory map
$ churnmap /path/to/repo              # Analyze specific repo
$ churnmap . --since 2024-01-01       # Only recent history
$ churnmap . --depth 2                # Group by second-level directories
$ churnmap . --format svg --output map.svg  # Generate SVG
$ churnmap . --min-cochanges 5        # Require stronger coupling evidence
$ churnmap . --width 120 --height 60  # Larger map
$ churnmap . --no-color               # Pipe-friendly output
```

## Project File Structure

```
ChurnMap/
├── pyproject.toml           # Project config, dependencies, entry point
├── README.md                # Full documentation with examples
├── SPEC.md                  # This spec
├── LICENSE                  # MIT
├── .gitignore
├── churnmap/
│   ├── __init__.py          # Package init, version
│   ├── cli.py               # CLI entry point (argparse)
│   ├── mining.py            # Git commit mining with PyDriller
│   ├── cochange.py          # Co-change matrix + graph construction
│   ├── communities.py       # Louvain community detection + stats
│   ├── layout.py            # Force layout + Voronoi tessellation
│   ├── render.py            # ASCII/SVG rendering
│   └── colors.py            # ANSI color definitions, SVG color palette
├── tests/
│   ├── __init__.py
│   ├── test_mining.py       # Test git mining with fixture repo
│   ├── test_cochange.py     # Test co-change matrix construction
│   ├── test_communities.py  # Test community detection
│   ├── test_layout.py       # Test layout computation
│   └── test_render.py       # Test rendering output
└── examples/
    └── sample_output.txt    # Example ASCII map output
```

## Dependencies

```toml
[project]
name = "churnmap"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pydriller>=2.6",
    "networkx>=3.0",
    "python-louvain>=0.16",  # community detection
    "scipy>=1.10",           # Voronoi tessellation
    "rich>=13.0",            # Terminal rendering
    "numpy>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[project.scripts]
churnmap = "churnmap.cli:main"
```

## Data Flow

```
1. Mining:
   git log → [{commit: str, timestamp: datetime, modules: [str]}]

2. Co-Change:
   commits → {(module_a, module_b): co_change_count} → NetworkX.Graph

3. Communities:
   Graph → {community_id: [modules]} + {module: stats}

4. Layout:
   communities → {community_id: (x, y)} + Voronoi regions

5. Render:
   layout + communities + stats → ASCII grid or SVG
```

## Change Frequency Classification

| Category | Commits (percentile) | Color | Character | Meaning |
|----------|---------------------|-------|-----------|---------|
| Hot | > 75th percentile | Red | `█` | Frequently changed, high risk |
| Warm | 50th-75th | Yellow | `▓` | Moderately active |
| Stable | 25th-50th | Blue | `▒` | Rarely changed, low risk |
| Dead | < 25th | Grey | `░` | Orphaned/dead code |

## Border Conflict Visualization

When two adjacent territories have high coupling (Jaccard > 0.3), their shared border is rendered with `╳` markers to indicate a "conflict" — this is a coupling hotspot that needs attention.

## Quality Gates / Acceptance Criteria

- [x] `churnmap .` generates territory map from current git repo
- [x] Co-change analysis correctly identifies coupled modules
- [x] ASCII rendering produces readable territory visualization with colors
- [x] Dead code (grey territories) correctly identified
- [x] Works on any git repo with 50+ commits
- [x] SVG output generates valid SVG with colored territories
- [x] CLI flags work as documented
- [x] Tests pass for mining, co-change, communities, layout, and render
- [x] No hardcoded paths — works from any directory
- [x] Proper error messages for: non-git directory, empty repo, no commits in range

## Naming Conventions

- Module names: snake_case
- Class names: PascalCase
- Function names: snake_case
- Constants: UPPER_SNAKE_CASE
- CLI flags: kebab-case (e.g., `--min-cochanges`)

## Style

- Python 3.10+ with type hints
- Docstrings on all public functions/classes
- f-strings preferred
- `if __name__ == "__main__"` guard in cli.py
- Use `pathlib.Path` for all file paths
- Rich for all terminal output (no bare print statements)
