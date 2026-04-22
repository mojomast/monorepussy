# Operon — Gene Regulation for Documentation Generation

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Apply gene regulation biology as a functional model for documentation generation. Operon identifies natural documentation clusters, analyzes generation triggers, manages deprecation suppression, discovers cross-references, enables conditional generation, and tracks documentation state across commits.

## Overview

Documentation systems are often reactive and fragmented. Operon models documentation using biological concepts proven over 3.8 billion years:

- **Operons** — clusters of co-regulated genes → co-documented feature sets
- **Promoters** — DNA binding sites → documentation generation triggers
- **Repressors** — transcription blockers → deprecation and suppression
- **Enhancers** — distant boosters → cross-reference connections
- **Transcription Factors** — conditional activators/repressors → audience-specific docs
- **Epigenetic Marks** — persistent state → documentation state tracking

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python -m operon --help
```

## Usage Examples

### Discover Operons

Identify natural documentation clusters in your codebase:

```bash
operon map ./src --threshold 0.7
```

### Analyze Documentation Triggers

Check the strength of a documentation generation trigger:

```bash
operon promote public_api_change --json
```

### Suppress Documentation

Set repression for a deprecated feature:

```bash
operon repress old_module.py --type inducible
```

### Find Cross-Reference Enhancers

Discover distant but relevant module connections:

```bash
operon enhance ./src --top 10
```

### Generate Conditional Documentation

Generate audience-specific documentation for an operon:

```bash
operon express operon_0 --audience beginner --context web
```

### View Epigenetic State

Track documentation freshness and archival state:

```bash
operon epigenetics --json
```

## Architecture

```
operon/
├── __init__.py          # Package exports
├── __main__.py          # python -m operon entry point
├── cli.py               # argparse CLI implementation
├── models.py            # Data models (Gene, Operon, Promoter, etc.)
├── storage.py           # SQLite persistence layer
├── mapper.py            # Operon Mapper — co-documented feature discovery
├── promoter.py          # Promoter Detector — doc generation triggers
├── repressor.py         # Repressor Manager — deprecation/suppression
├── enhancer.py          # Enhancer Scanner — cross-reference discovery
├── transcription.py     # Transcription Factor Registry — conditional docs
└── epigenetics.py       # Epigenetic State Tracker — doc state persistence
```

### Data Flow

1. **Mapping**: `OperonMapper` parses Python source files using `ast`, analyzes import graphs, and clusters modules into operons via community detection.
2. **Promotion**: `PromoterDetector` scores change types by documentation urgency.
3. **Repression**: `RepressorManager` creates LacI-type (inducible), TrpR-type (corepressor-dependent), and constitutive repressors.
4. **Enhancement**: `EnhancerScanner` finds transitive relationships and calculates semantic similarity with distance decay.
5. **Expression**: `TranscriptionFactorRegistry` activates/represses genes based on audience and context.
6. **Epigenetics**: `EpigeneticStateTracker` applies methylation (archived), acetylation (recently reviewed), and chromatin remodeling marks.

## Design Decisions

- **Zero external dependencies**: Uses only the Python standard library (`argparse`, `sqlite3`, `ast`, `json`, `datetime`).
- **SQLite storage**: All entities persist to a local database for state tracking across runs.
- **AST-based parsing**: Pure Python parsing avoids external parser dependencies.
- **Connected components clustering**: Simple, deterministic community detection without graph libraries.
