# Crystallo — Crystallographic Symmetry Detection in Code Structure

Crystallo applies crystallographic symmetry group theory to Python code structure. It parses ASTs, extracts structural fingerprints, and classifies the symmetry operations (rotational, reflection, translational, glide, broken) that relate code units to each other.

## Overview

Static analysis tools treat code as flat text with local patterns. Crystallo treats code as a crystal lattice — detecting **structural symmetry** that reveals deep architectural intent or accidental duplication:

- **Rotational symmetry**: Functions/classes with identical structure but different roles (e.g., `create_user` and `create_order`)
- **Reflection symmetry**: Mirror-image modules (e.g., `client.py` and `server.py`)
- **Translational symmetry**: Repeated patterns across files (copy-paste candidates)
- **Glide symmetry**: Patterns repeated with systematic transformation (e.g., `test_*.py` mirrors `*.py`)
- **Broken symmetry**: Modules that should match but diverge (missing methods, extra features)

Crystallo assigns each module a **space group** (P1 triclinic → Pa3 cubic) describing its structural identity, just as crystallographers classify crystals.

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Usage

### Scan — Extract and Analyze

```bash
crystallo scan src/
```

### Symmetry — List Symmetry Operations

```bash
crystallo symmetry src/api/
crystallo symmetry --type rotational src/
crystallo symmetry --threshold 0.6 src/
```

### Defects — Find Broken & Accidental Symmetry

```bash
crystallo defects src/
crystallo defects --defect-threshold 0.5 src/models/
```

### Classify — Assign Space Groups

```bash
crystallo classify src/
```

### Unit Cell — Show Repeating Patterns

```bash
crystallo unit-cell src/models/
```

### Python Module

```bash
python -m crystallo scan src/
```

## Architecture

```
src/crystallo/
├── __init__.py       # Package init, version
├── __main__.py       # python -m support
├── models.py         # Data models (fingerprints, symmetry types, space groups)
├── parser.py         # AST parsing and feature extraction
├── similarity.py     # Pairwise similarity and symmetry classification
├── classify.py       # Space group assignment and unit cell detection
├── defects.py        # Broken symmetry and accidental duplication detection
├── report.py         # Human-readable output formatting
└── cli.py            # CLI entry point (argparse)
```

### Core Data Flow

1. **Parse** → `parser.py` reads Python files, extracts `StructuralFingerprint` objects
2. **Compare** → `similarity.py` computes pairwise similarity (cosine + Jaccard) and classifies symmetry type
3. **Classify** → `classify.py` assigns space groups and detects unit cells (repeating clusters)
4. **Detect** → `defects.py` finds broken symmetry and accidental duplication
5. **Report** → `report.py` formats output for the terminal

### Symmetry Classification Heuristics

| Symmetry Type | Detection Criteria |
|---|---|
| Rotational | Shared base class + high method overlap |
| Reflection | Mirror naming (client/server) + high method overlap |
| Translational | High similarity without shared abstraction |
| Glide | Test naming convention (test_ prefix or test/ path) |
| Broken | Shared base class + divergent method sets |

### Space Group Assignment

| Group | Crystal System | Criteria |
|---|---|---|
| P1 | Triclinic | Low total symmetry |
| Pm | Monoclinic | Reflection dominant |
| P2 | Monoclinic | Rotational dominant |
| P2/m | Monoclinic | Both rotation and reflection |
| P4 | Tetragonal | 4+ rotational pairs |
| P6 | Hexagonal | 3+ translational groups |
| Pa3 | Cubic | Multi-axis symmetry (3+ rotation, 2+ reflection, 2+ translation) |

## Dependencies

- Python 3.10+ (stdlib only — no external dependencies)

## License

MIT
