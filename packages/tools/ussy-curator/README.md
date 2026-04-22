# Curator — Library Science for Documentation Health

Curator applies principles from library science and museology to software documentation. It treats documentation as a curated collection requiring structured metadata, hierarchical classification, conservation monitoring, provenance tracking, contextual surfacing, and active maintenance.

## Overview

Documentation collections decay like un-curated museum holdings. Curator provides six instruments to combat this:

1. **MARC Cataloger** — Structured metadata extraction and completeness scoring
2. **Classification System** — Hierarchical faceted organization (DDC/LCC-inspired)
3. **Conservation Report** — Freshness tracking with deterioration curves
4. **Provenance Tracker** — Accession numbers and authorship lineage
5. **Exhibition Curator** — Selective doc surfacing for specific audiences
6. **Weeding Engine** — MUSTIE-based deaccession proposals

## Installation

```bash
pip install .
```

Requires Python 3.10+.

## Usage

### Catalog a document

```bash
curator catalog docs/README.md
```

### Classify a document

```bash
curator classify docs/README.md
```

### Generate a conservation report

```bash
curator condition docs/README.md
```

### View provenance

```bash
curator provenance docs/README.md
```

### Curate an exhibition

```bash
curator exhibit --theme "onboarding" --audience beginner --target docs/
```

### Weed the collection

```bash
curator weed --threshold 0.6 --target docs/
```

### Browse the shelf

```bash
curator shelf --facet AUD:expert --target docs/
```

### Full audit

```bash
curator audit --json --target docs/
```

## Architecture

```
curator/
├── __init__.py
├── __main__.py
├── cli.py              # argparse CLI
├── models.py           # Document, Link data models
├── storage.py          # SQLite persistence layer
├── utils.py            # Shared parsing and analysis utilities
├── catalog.py          # MARCRecord, ControlledVocabulary
├── classification.py   # FacetedClassification, DDC mapping
├── conservation.py     # ConservationReport with Arrhenius decay
├── provenance.py       # ProvenanceTracker, accession numbers
├── exhibition.py       # Exhibition curation and rotation
└── weeding.py          # WeedingEngine with MUSTIE criteria
```

All modules use only the Python standard library (sqlite3, pathlib, datetime, argparse, json, re, math).
