# Portmore — Customs & Tariff Classification for Software License Compliance

**Portmore** applies customs and tariff classification — the international framework that determines how goods are classified, valued, and taxed at borders — to software license compliance. Customs officers face the same classification problems: multi-component goods, rules of origin, preferential treatment, valuation hierarchies, anti-dumping enforcement, and bonded warehousing. They've developed binding interpretative rules that map precisely to license compliance.

Named after the **Portmore** customs house — from Latin *portus* (harbor/gate) + *morare* (to delay/detain), reflecting how dependencies are classified and held at the boundary until their legal status is determined.

## Installation

```bash
pip install portmore
```

Or install from source:

```bash
git clone https://github.com/your-org/portmore.git
cd portmore
pip install -e .
```

## Usage

### Classify Licenses (GIRs)

Apply the 6 General Interpretative Rules to determine which license governs a multi-license work:

```bash
portmore classify ./my-project
portmore classify ./my-project --format json
```

### Determine Provenance (Rules of Origin)

Apply substantial transformation tests, de minimis thresholds, and value-added analysis:

```bash
portmore origin ./my-project --threshold 0.40 --deminimis 0.05
```

### Check Compatibility (PTA-Style Exceptions)

Analyze license compatibility with conditional exceptions, tariff rate quotas, and anti-circumvention detection:

```bash
portmore compatibility --from LGPL-2.1 --to Apache-2.0
portmore compatibility --from AGPL-3.0 --to Proprietary
portmore compatibility --from MIT --to GPL-3.0 --usage-type dynamic
```

### Assess Compliance Cost (Customs Valuation)

Compute compliance value using the 6-method sequential hierarchy:

```bash
portmore value --license GPL-3.0
portmore value --project ./my-project --project-value 100000 --development-cost 50000
```

### Assess Copyleft Contagion (Anti-Dumping)

Compute dumping margins, injury assessment, and minimal remedies:

```bash
portmore contagion --copyleft GPL-3.0 --ratio 0.70
portmore contagion --copyleft AGPL-3.0 --ratio 0.80 --linkage static
```

### Check Dependency Quarantine (Bonded Warehousing)

Classify dependencies into bonded (dev) and domestic (runtime) zones:

```bash
portmore quarantine ./my-project --check
```

## Architecture

```
portmore/
├── __init__.py         # Package init, version
├── __main__.py         # python -m support
├── cli.py              # argparse CLI interface
├── models.py           # Data models (dataclasses, enums)
├── hs_codes.py         # HS Code taxonomy & SPDX mapping
├── classifier.py       # GIR-based multi-license classification
├── origin.py           # Rules of origin & provenance determination
├── compatibility.py    # PTA-style license compatibility
├── valuation.py        # 6-method compliance cost assessment
├── contagion.py        # Anti-dumping / copyleft contagion containment
├── quarantine.py       # Bonded warehouse dependency quarantine
├── scanner.py          # Project directory scanner
├── storage.py          # SQLite persistence layer
└── formatter.py        # Output formatting (text/JSON)
```

### Core Concepts

1. **HS Codes → License Classification** — Hierarchical license taxonomy with 6 binding General Interpretative Rules (GIRs) for multi-license resolution.

2. **Rules of Origin → Provenance** — Wholly-obtained test, substantial transformation (CTC + value-added), de minimis, accumulation, and absorption.

3. **PTAs → Compatibility Exceptions** — Conditional compatibility, tariff rate quotas, license zone cumulation, negative lists, and anti-circumvention detection.

4. **Customs Valuation → Compliance Cost** — 6-method sequential hierarchy (transaction value → identical → similar → deductive → computed → fall-back) with Article 8 adjustments.

5. **Anti-Dumping → Copyleft Contagion** — Dumping margins, material injury tests, causal links, circumvention thresholds, lesser-duty remedies, and scope rulings.

6. **Bonded Warehousing → Dependency Quarantine** — Duty-deferred/duty-paid zones, export/domestic withdrawals, Class 5 manipulation rules, constructive warehouse, and in-bond movement.

## License

MIT
