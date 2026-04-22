# Stemma — Philological Code Variant Reconstruction

Reconstruct the family tree of code variants using methods from textual criticism — identifying which version was the "original," which differences are bugs vs. intentional changes, and which code was copied from multiple sources — all **without requiring any git history**.

## The Key Insight

When developers copy-paste code and introduce errors, they are doing *exactly* what medieval scribes did when copying manuscripts. The same philological methods that reconstruct the genealogy of ancient texts — shared errors indicate common descent, *lectio difficilior* (the harder reading is original), contamination detection — apply directly to code variant analysis.

## Installation

```bash
pip install -e .
```

## Usage

### Collate — Align Variants and Display Collation Table

```bash
stemma collate path/to/variants/
```

Displays a collation table showing all witnesses aligned line-by-line, with variation units highlighted.

### Build — Reconstruct Stemma Tree

```bash
stemma build path/to/variants/
```

Reconstructs the stemma (family tree) of code variants based on shared errors. Witnesses that share unique errors must descend from a common ancestor.

### Classify — Classify Variants as Errors vs. Intent

```bash
stemma classify path/to/variants/
```

Classifies each variation as either a **scribal error** (copy mistake) or a **conscious modification** (intentional change), using:
- Known error patterns (off-by-one, typo, missing negation, etc.)
- *Lectio difficilior* — the harder reading is more likely original
- Consistency scoring — semantic similarity between variants

### Reconstruct — Output Archetype

```bash
stemma reconstruct path/to/variants/
```

Reconstructs the archetype (original code) using Lachmannian method: prefer majority reading, break ties with *lectio difficilior*, flag contaminated readings.

### Contaminate — Detect Contaminated Witnesses

```bash
stemma contaminate path/to/variants/
```

Detects witnesses that can't be placed on a simple tree — code that was copied from multiple sources (contamination in philological terms).

### Export — Graphviz DOT Output

```bash
stemma export path/to/variants/
```

Exports the stemma as a Graphviz DOT diagram for visualization.

## Architecture

```
stemma/
├── models.py         # Data models: Witness, VariationUnit, StemmaTree, etc.
├── alignment.py      # Needleman-Wunsch sequence alignment for code lines
├── collation.py      # Multi-witness alignment and variation detection
├── classify.py       # Scribal error vs. conscious modification classification
├── stemma_builder.py # Tree reconstruction from shared errors
├── reconstruct.py    # Archetype reconstruction (Lachmannian method)
├── contaminate.py    # Contamination detection (witnesses with multiple sources)
├── export.py         # Graphviz DOT and text tree export
├── display.py        # Rich terminal output formatting
├── storage.py        # SQLite persistence for analysis results
└── cli.py            # Argparse CLI interface
```

## Key Concepts

| Philological Term | Code Meaning |
|---|---|
| **Witness** | A code variant (file/function) |
| **Archetype** | The original code (reconstructed) |
| **Scribal error** | A copy-paste bug (off-by-one, typo, omission) |
| **Conscious modification** | An intentional change (rename, refactor) |
| **Lectio difficilior** | "The harder reading is original" — complex code is less likely to be a copy error |
| **Contamination** | Code that was influenced by multiple sources |
| **Hyparchetype** | An intermediate ancestor in the stemma tree |
| **Variation unit** | A line where witnesses disagree |

## Zero External Dependencies

Stemma uses only Python stdlib. No git, no AST parsing libraries, no external tools required. It works purely from the text of the code itself.

## Tests

```bash
pytest tests/ -v
```

102 tests covering alignment, collation, classification, stemma building, reconstruction, contamination detection, and export.
