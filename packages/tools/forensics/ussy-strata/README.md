# StrataGit 🏔️

**Geological metaphor for Git history visualization** — See your repository as layers of sedimentary rock, where commits are strata, file types are minerals, and deleted code is fossils.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    STRATIGRAPHIC CROSS-SECTION                              │
│                     McpUssy Geological Survey                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ pyrite   abc123f0  7d   ██████████████████████████████████████████████████  │
│ fluorite def456e2  3d   ██████████████████████████████████████████████████  │
│ clay     ghi789a1  1d   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
├──────────────────────────────────────────────────────────────────────────────┤
│ (oldest layers at bottom)                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Overview

StrataGit reimagines Git history through the lens of geology:

- **Strata** — Commits are geological layers, with thickness proportional to lines changed
- **Minerals** — File types map to mineral types (`.py` → pyrite, `.js` → fluorite, `.rs` → hematite)
- **Fossils** — Deleted code artifacts are excavated fossils with lifespans
- **Unconformities** — History gaps from rebases, squashes, and cherry-picks
- **Fault Lines** — Force pushes that rewrite geological history
- **Intrusions** — Branches that cut through strata like igneous rock
- **Carbon Dating** — Enhanced `git blame` that shows how long code has been deposited

## Installation

```bash
pip install -e .
```

## Usage

### Geological Survey

Get a full report of your repository's geology:

```bash
stratagit survey                    # Full survey of current directory
stratagit -C /path/to/repo survey  # Survey a specific repo
stratagit -n 100 survey            # Analyze last 100 commits only
```

### Cross-Section View

Visualize commit layers as a stratigraphic column:

```bash
stratagit cross-section            # Visual cross-section
stratagit cross-section -w 120     # Custom width
```

### Excavate Fossils

Find deleted code artifacts:

```bash
stratagit excavate                  # Find all fossils
stratagit excavate -p "handler"     # Filter by name pattern
stratagit excavate -g "*.py"        # Limit to Python files
```

### Detect Unconformities

Find history gaps and discontinuities:

```bash
stratagit unconformities
```

### Detect Fault Lines

Find evidence of history rewrites:

```bash
stratagit faults
```

### Carbon Date

Enhanced blame showing how long a line has existed:

```bash
stratagit carbon-date src/main.py 42
```

### Legend

Show the mineral color mapping:

```bash
stratagit legend
```

## Mineral Reference

| File Type | Mineral | Color |
|-----------|---------|-------|
| `.py` | Pyrite (Fool's Gold) | Yellow |
| `.js`, `.jsx` | Fluorite | Blue |
| `.ts`, `.tsx` | Topaz | Cyan |
| `.rs` | Hematite | Red |
| `.go` | Olivine | Green |
| `.c`, `.h` | Galena | White |
| `.cpp`, `.cc` | Malachite | Green |
| `.md`, `.rst` | Limestone | Gray |
| `.yml`, `.yaml` | Shale | Purple |
| `.json` | Calcite | Gray |
| `.sh`, `.bash` | Sandstone | Brown |
| Other | Clay | Default |

## Architecture

```
stratagit/
├── core/
│   ├── __init__.py      # Data models (Stratum, Fossil, Intrusion, etc.)
│   ├── parser.py        # Git log parser and strata extraction
│   ├── survey.py        # Repository-wide geological survey
│   ├── fossils.py       # Deleted code artifact detection
│   ├── unconformity.py  # History gap detection (rebases, squashes)
│   ├── fault.py         # Force push / rewrite detection
│   └── carbon_date.py   # Enhanced git blame
├── tui/
│   └── __init__.py      # Terminal rendering (cross-section, detail, legend)
└── cli.py               # Command-line interface
```

### Data Model

- **Stratum**: A single commit layer with density, thickness, mineral composition, and stability tier
- **Fossil**: A deleted code artifact (function, class, import) with lifespan and extinction data
- **Intrusion**: A branch that cuts through strata, classified as igneous (feature) or sedimentary (fix/docs)
- **Unconformity**: A gap in the geological record (rebase, squash, cherry-pick, orphan)
- **FaultLine**: Evidence of a history rewrite (force push)
- **GeologicalReport**: Complete survey with all analysis results

### Stability Tiers

| Tier | Age | Description |
|------|-----|-------------|
| Bedrock | >365 days | Ancient, foundational code |
| Mature | 180-365 days | Well-established, unlikely to change |
| Settling | 30-180 days | Stabilizing, still in recent memory |
| Active | 7-30 days | Recently deposited, may still shift |
| Volatile | <7 days | Fresh, highly likely to change |

## Dependencies

- Python 3.10+
- Git (must be available in PATH)
- No external Python packages required (stdlib only)

## License

MIT
