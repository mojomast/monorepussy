# SPEC: TimeLoom — Code History as Woven Textile

## Overview

TimeLoom renders a repository's git history as a literal woven textile pattern. Each file is a warp thread (vertical); time is the weft (horizontal). Every commit "passes the shuttle" across specific warp threads, creating a visible interlock pattern. Files that change together in the same commit produce woven crossings. Files that never co-change remain separate threads.

## Problem Statement

Git history is always visualized as linear timelines, node graphs, or flat logs. These treat code changes as discrete, independent events — but changes in one file "pull" on related files. Current visualizations lose the *texture* of development: the rhythm of iteration, the tight coupling that binds certain files together, and the periods of stability vs. churn. Nobody has closed the loop from Jacquard loom (which inspired computing) back to textile rendering of code.

## Architecture

### Core Components

```
timeloom/
├── __init__.py
├── cli.py              # CLI entry point (click-based)
├── git_parser.py       # Parse git log → co-change matrix
├── weave_engine.py     # Co-change matrix → weave draft (warp/weft grid)
├── analysis.py         # Structural analysis (floats, selvedge, pattern repeats)
├── renderers/
│   ├── __init__.py
│   ├── svg.py          # SVG textile renderer
│   ├── terminal.py     # ASCII/Unicode terminal renderer
│   └── wif.py          # WIF (Weaving Interchange Format) export
└── color.py            # Commit-type → color mapping
```

### Data Flow

```
git log --name-status
        │
        ▼
  ┌──────────────┐
  │  git_parser   │  →  CoChangeMatrix (files × commits)
  └──────────────┘
        │
        ▼
  ┌──────────────┐
  │  weave_engine │  →  WeaveDraft (grid: warp-over vs weft-over)
  └──────────────┘
        │
        ├──→ SVG renderer
        ├──→ Terminal renderer
        ├──→ WIF exporter
        └──→ Structural analysis
```

### Data Model

```python
@dataclass
class CoChangeMatrix:
    """files × commits binary matrix: 1 = file changed in commit, 0 = not"""
    files: list[str]           # ordered list of file paths (warp threads)
    commits: list[CommitInfo]  # ordered list of commits (weft passes)
    matrix: list[list[int]]    # matrix[file_idx][commit_idx]

@dataclass
class CommitInfo:
    hash: str
    message: str
    author: str
    timestamp: datetime
    change_type: str  # "feature" | "fix" | "refactor" | "delete" | "other"

@dataclass
class WeaveDraft:
    """Standard weave draft notation: grid of crossings"""
    width: int                  # number of warp threads (files)
    height: int                 # number of weft passes (commits)
    cells: list[list[int]]      # 1 = warp raised (crossing), 0 = weft over
    thread_colors: list[str]    # color per warp thread position
    row_colors: list[str]       # color per weft row (commit type)

@dataclass
class AnalysisResult:
    float_threads: list[FloatInfo]    # threads with long floats (inactive files)
    selvedge_integrity: float         # 0-1 score for edge stability
    pattern_repeats: list[PatternRepeat]  # detected recurring patterns
    coupling_clusters: list[CouplingCluster]  # groups of tightly-coupled files
    total_crossings: int
    density: float  # crossing density (0-1)
```

## CLI Surface

```
timeloom weave <repo-path> [OPTIONS]
  --last N              Only analyze last N commits (default: all)
  --output PATH         Output file path (detected by extension: .svg, .txt, .wif)
  --max-files N         Limit to N most-changed files (default: 100)
  --min-crossings N     Filter out files with fewer than N crossings (default: 1)
  --color-scheme NAME   Color scheme: warm, cool, neon, monochrome (default: warm)
  --width N             SVG width in pixels (default: 1200)
  --thread-gap N        Pixels between warp threads (default: 2)
  --no-legend           Omit the legend from SVG output

timeloom analyze <repo-path> [OPTIONS]
  --last N              Only analyze last N commits
  --find-patterns       Run pattern repeat detection
  --find-floats         Find long floats (inactive files)
  --check-selvedge      Check edge stability
  --min-float-length N  Minimum rows to count as a float (default: 10)
  --json                Output results as JSON

timeloom export <repo-path> [OPTIONS]
  --format FORMAT       Output format: wif, pes (default: wif)
  --output PATH         Output file path
  --last N              Only analyze last N commits

timeloom heatmap <repo-path> [OPTIONS]
  --last N              Only analyze last N commits
  --output PATH         Output file path (.svg)
  --max-files N         Limit to N most-changed files
```

## Implementation Details

### 1. Git Parser (`git_parser.py`)

Use `subprocess` to run `git log --name-status --format=...` and parse the output:
- Parse each commit's hash, message, author, date
- Parse changed files with status (Added/Modified/Deleted/Renamed)
- Classify commit type by message keywords:
  - `feature|feat|add|new|implement` → "feature" (warm: #E85D3A)
  - `fix|bug|patch|hotfix|repair` → "fix" (cool: #3A8DE8)
  - `refactor|restructure|reorganize|clean|move|rename` → "refactor" (neutral: #8D8D8D)
  - `delete|remove` → "delete" (black: #1A1A1A)
  - everything else → "other" (beige: #C4A882)
- Build binary matrix: matrix[file_idx][commit_idx] = 1 if file changed
- Sort files by total change count (most-changed = leftmost warp threads)
- Filter to top N most-changed files

### 2. Weave Engine (`weave_engine.py`)

Convert co-change matrix to weave draft:
- For each cell (file, commit): if file changed in commit, that's a crossing (warp raised = 1)
- If file NOT changed in commit: weft over (0)
- Thread colors: assigned based on file directory grouping (files in same dir = same hue family)
- Row colors: based on commit change_type
- Compute crossing density = total_ones / total_cells

### 3. Structural Analysis (`analysis.py`)

- **Float detection**: Scan each column (file). A "float" is a consecutive run of 0s longer than `min_float_length`. Record start row, end row, file name.
- **Selvedge integrity**: Check the outermost N files (edges). Stability = fraction of rows where edge threads have the same state as their neighbors. High selvedge integrity = stable foundational code.
- **Pattern repeat detection**: Use autocorrelation on each file's change column. Find periods where the pattern repeats. Look for multi-file coordinated repeats.
- **Coupling clusters**: Group files that cross together frequently. Two files are coupled if they share >50% of their crossings (Jaccard similarity on change sets).

### 4. SVG Renderer (`renderers/svg.py`)

- Canvas with configurable width, auto-calculated height
- Each warp thread = vertical strip of colored rectangles
- Crossing cells (1) rendered as raised warp (darker shade of thread color)
- Non-crossing cells (0) rendered as weft-over (lighter shade of row color)
- Alternating visual texture to simulate actual woven look:
  - Warp-over cells have slight vertical emphasis (taller, darker)
  - Weft-over cells have slight horizontal emphasis (wider, lighter)
- Legend showing color meanings
- Thread labels on left side (file paths, truncated)
- Commit info on hover (via SVG title elements)
- Scaling: for large repos, group commits into buckets (e.g., 10 commits per weft row)

### 5. Terminal Renderer (`renderers/terminal.py`)

- Use Unicode block elements: █ (full), ▓ (dark), ▒ (medium), ░ (light)
- Crossing = █ or ▓ (dark), non-crossing = ░ or space
- Color via ANSI escape codes
- One row per commit, one column per file
- Truncate to terminal width

### 6. WIF Export (`renderers/wif.py`)

- WIF (Weaving Interchange Format) is a standard text format for weaving patterns
- Output the weave draft grid in WIF format
- Include thread colors as RGB values
- This can be loaded by weaving software or sent to digital looms

### 7. Color System (`color.py`)

- Map commit types to colors
- Map file directories to hue families
- Support multiple color schemes (warm, cool, neon, monochrome)
- Provide hex/RGB conversion utilities

## Project File Structure

```
timeloom/
├── pyproject.toml
├── README.md
├── SPEC.md
├── .gitignore
├── src/
│   └── timeloom/
│       ├── __init__.py
│       ├── cli.py
│       ├── git_parser.py
│       ├── weave_engine.py
│       ├── analysis.py
│       ├── color.py
│       └── renderers/
│           ├── __init__.py
│           ├── svg.py
│           ├── terminal.py
│           └── wif.py
└── tests/
    ├── __init__.py
    ├── test_git_parser.py
    ├── test_weave_engine.py
    ├── test_analysis.py
    └── test_renderers.py
```

## Dependencies

- `click` — CLI framework
- `gitpython` — Git repository interaction (alternative: subprocess calls to git)
- No other external dependencies needed. SVG generated via string templates (no svgwrite dependency).

## Quality Gates / Acceptance Criteria

1. `timeloom weave` produces valid SVG from any git repo
2. `timeloom analyze` correctly identifies high-coupling file groups
3. `timeloom export --format wif` produces valid WIF output
4. Terminal renderer produces readable ASCII textile
5. Can handle repos with 10K+ commits in under 30 seconds
6. All Python files pass `ast.parse()`
7. Test suite with at least 80% coverage on core modules

## Naming Conventions & Style

- Python 3.10+ with type hints
- `src/timeloom/` layout with `pyproject.toml`
- Click for CLI
- Dataclasses for data models
- Docstrings on all public functions
- snake_case for functions/variables, PascalCase for classes
