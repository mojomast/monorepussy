Build TimeLoom — a CLI tool that renders git repository history as woven textile patterns.

IMPLEMENT EVERYTHING in the SPEC.md file attached. This is a Python CLI tool using:
- Click for CLI
- src/timeloom/ layout with pyproject.toml
- Dataclasses for data models
- String templates for SVG (no svgwrite)
- subprocess calls to git (no gitpython)

Key features to implement:
1. `timeloom weave <repo>` — produces SVG, terminal ASCII, or WIF textile output
2. `timeloom analyze <repo>` — structural analysis (floats, selvedge, pattern repeats, coupling)
3. `timeloom export <repo>` — export to WIF format for digital looms
4. `timeloom heatmap <repo>` — co-change heatmap SVG

The git parser must:
- Run `git log --name-status` via subprocess
- Classify commits by type (feature/fix/refactor/delete/other) using message keywords
- Build a binary co-change matrix (files × commits)
- Sort files by total change count
- Support --last N commits and --max-files N filters

The weave engine must:
- Convert co-change matrix to weave draft (1=warp raised, 0=weft over)
- Assign thread colors by directory grouping
- Assign row colors by commit type
- Compute crossing density

The SVG renderer must:
- Draw warp threads as vertical strips with alternating texture (darker for crossings, lighter for weft-over)
- Include thread labels, legend, and SVG title elements for hover
- Support configurable width, thread gap, and color schemes
- Group commits into buckets for large repos

The terminal renderer must:
- Use Unicode block elements (█ ▓ ▒ ░)
- One row per commit, one column per file
- ANSI color codes

The analysis must:
- Detect floats (consecutive 0-runs in columns)
- Check selvedge integrity (edge stability)
- Find pattern repeats via autocorrelation
- Group coupled files via Jaccard similarity

Color schemes: warm, cool, neon, monochrome — each maps commit types and directory groups differently.

Write comprehensive tests in tests/ for all modules. Use pytest.
