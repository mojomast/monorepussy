# ussy-kintsugi — Visible Repair History That Makes Code Stronger at the Scars

> **Migrated**: This package was formerly `kintsugiussy` and is now part of the [ussyverse monorepo](https://github.com/mojomast/ussyverse).

> *In Japanese kintsugi, the crack is filled with gold — the repair is the most beautiful part.*

## Overview

Kintsugi annotates your codebase with **golden joints** — visible, queryable markers at every site where a bug was repaired. Each joint carries the full context of the break and the fix: what broke, why, how it was repaired, and what would happen if the repair were removed. Unlike code comments, golden joints are **structured data** that can be queried, tested, and monitored.

Bug fixes are invisible. A developer writes `fix: null check on user.email`, commits, and the scar disappears. Six months later, someone removes the null check — "it's redundant" — and the same crash returns. Kintsugi prevents this by making every repair a visible, structural mark.

### Core Concepts

- **Golden Joints**: Structured annotations at bug repair sites with full context
- **Scar Map**: Visual density map showing where bugs cluster — revealing structural weakness
- **Stress Testing**: Inverse mutation testing — remove historical fixes to verify they're still load-bearing
- **Archaeology**: Reconstruct fracture history of a file from joint data

## Installation

```bash
pip install ussy-kintsugi
```

Or from the monorepo:

```bash
git clone https://github.com/mojomast/ussyverse
cd ussyverse
uv sync
```

## Usage

### Mark a bug fix as a golden joint

```bash
ussy-kintsugi mark --bug PROJ-892 --severity critical \
  --break-desc "user.email was None when OAuth returned empty dict" \
  --repair "Added None guard before .lower()" \
  --removal-impact "TypeError crash on login for OAuth users with no email" \
  --test test_oauth_null_email_crash \
  src/auth/login.py:42
```

This:
1. Creates a structured joint record in `.kintsugi/joints.jsonl`
2. Inserts a visible annotation comment in the source file above the repair line

### Generate a scar map

```bash
ussy-kintsugi map src/
```

Output:
```
src/auth/
  ├── login.py          ⛩️⛩️⛩️  3 joints (2 critical, 1 warning)
  ├── oauth.py          ⛩️      1 joint (warning)
  └── session.py                   (intact)
```

Scar density reveals **structural weakness** — modules with many golden joints are fragile.

### Stress test all joints (CI integration)

```bash
ussy-kintsugi stress --junit-output=kintsugi-results.xml
```

For each joint, Kintsugi:
1. Temporarily removes the repair code
2. Runs the joint's referenced test
3. If the test PASSES → the joint is **hollow** (repair is redundant)
4. If the test FAILS → the joint is **solid gold** (repair still needed)

### Archaeology on a file

```bash
ussy-kintsugi archaeology src/payments/charge.py
```

Reconstructs the fracture history with patterns and refactoring suggestions.

### Find hollow joints

```bash
ussy-kintsugi hollow
```

Lists all joints where the repair may be redundant.

### List all joints

```bash
ussy-kintsugi list
```

## Architecture

```
ussy_kintsugi/
├── __init__.py        # Package version
├── joint.py           # Joint data model and JSONL storage
├── scanner.py         # Source file scanner (reads/writes inline annotations)
├── scar_map.py        # Scar density map generation
├── stress.py          # Stress testing engine (AST-based inverse mutation testing)
├── archaeology.py     # Fracture history reconstruction
├── cli.py             # CLI interface (argparse)
└── legacy.py          # Deprecated 'kintsugi' entry point
```

### Storage

Joints are stored in `.kintsugi/joints.jsonl` — one JSON line per joint, committed to the repo. Inline annotations are also written as comments in source files for visibility during code review.

### Joint Schema

```json
{
  "id": "j-20240315-proj892",
  "file": "src/auth/login.py",
  "line": 42,
  "timestamp": "2024-03-15T10:30:00+00:00",
  "bug_ref": "PROJ-892",
  "severity": "critical",
  "break_description": "user.email was None when OAuth provider returned empty dict",
  "repair_description": "Added None guard before .lower() call",
  "removal_impact": "TypeError crash on login for OAuth users with no email",
  "test_ref": "test_oauth_null_email_crash",
  "status": "solid_gold",
  "last_stress_tested": "2024-03-20T08:00:00+00:00"
}
```

### Why This Is Different

| Tool | What it shows |
|------|--------------|
| `git blame` | WHO changed a line (no WHY) |
| `git log --follow` | WHEN a line changed (no structural meaning) |
| Code comments | Unstructured, rot, no verification |
| ADRs | Architectural decisions, not bug repairs |
| Mutation testing | Tests your tests with synthetic bugs |
| **Kintsugi** | Documents real bugs, marks repair sites, verifies repairs are still load-bearing |

## Dependencies

Zero external dependencies — pure Python stdlib only. Python 3.11+.

## License

MIT
