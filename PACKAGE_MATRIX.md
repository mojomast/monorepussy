# Ussyverse Package Matrix

## Overview

This matrix maps all 63 repositories from github.com/mojomast to their monorepo disposition. Decisions are justified with references to the triage report.

**Legend:**
- **MERGED** — Code incorporated into another package
- **KEEP** — Migrated as standalone package
- **ARCHIVE** — Not migrated; repository archived on GitHub
- **P0-P3** — Migration priority (P0 = highest)

---

## Tier 1: Act Now (11 repos)

| # | Repo | Decision | Target Package | Path | Dependencies | Test Count | Priority | Justification |
|---|------|----------|----------------|------|--------------|------------|----------|---------------|
| 1 | triageussy | KEEP | ussy-triage | packages/tools/triage/ | stdlib only | ~8 | P0 | Tier 1, unique forensic methodology, zero deps, pilot candidate |
| 2 | stenographussy | MERGE | ussy-steno | packages/tools/security/ | stdlib only | ~10 | P0 | Tier 1, merge with stenography; full-featured successor with SARIF |
| 3 | sentinelussy | KEEP | ussy-sentinel | packages/tools/governance/ | stdlib only | ~8 | P0 | Tier 1, unique immunological governance, no overlap |
| 4 | gridironussy | KEEP | ussy-gridiron | packages/tools/deps/ | stdlib only | ~8 | P0 | Tier 1, dependency analysis cluster; power-grid reliability metaphor |
| 5 | parliamentussy | KEEP | ussy-parliament | packages/tools/governance/ | stdlib only | ~8 | P0 | Tier 1, unique agent governance domain, requires Python 3.11 |
| 6 | snapshotussy | KEEP | ussy-snapshot | packages/tools/devtools/ | stdlib only | ~8 | P0 | Tier 1, unique dev state management; fix secret storage in migration |
| 7 | strataussy | KEEP | ussy-stratax | packages/tools/deps/ | requests, pyyaml | ~8 | P0 | Tier 1, dependency analysis cluster; behavioral probing; renamed to avoid conflict with ussy-strata |
| 8 | kintsugiussy | KEEP | ussy-kintsugi | packages/tools/devtools/ | stdlib only | ~8 | P0 | Tier 1, unique bug repair annotation concept |
| 9 | assayussy | KEEP | ussy-assay | packages/tools/devtools/ | stdlib only | ~8 | P0 | Tier 1, unique metallurgical code grading metaphor |
| 10 | petrichorussy | KEEP | ussy-petrichor | packages/tools/devtools/ | stdlib only | ~8 | P0 | Tier 1, unique config drift detection; fix encryption in migration |
| 11 | unconformity | MERGE | ussy-strata | packages/tools/forensics/ | gitpython, click, rich | ~6 | P0 | Tier 1, merge with stratagitussy; complementary git forensics tools |

**Tier 1 Summary:** 11 repos → 10 packages (1 merge: unconformity → strata)

---

## Tier 2: Worth Developing (39 repos)

| # | Repo | Decision | Target Package | Path | Dependencies | Test Count | Priority | Justification |
|---|------|----------|----------------|------|--------------|------------|----------|---------------|
| 12 | proprioceptionussy | KEEP | ussy-propriocept | packages/tools/ | stdlib only | ~8 | P1 | Agent/swarm infrastructure; zero deps |
| 13 | curatorussy | KEEP | ussy-curator | packages/tools/ | stdlib only | ~8 | P1 | Documentation health; zero deps |
| 14 | operonussy | KEEP | ussy-operon | packages/tools/ | stdlib only | ~8 | P1 | Documentation health; zero deps |
| 15 | actuaryussy | KEEP | ussy-actuary | packages/tools/ | numpy, scipy | ~8 | P2 | Test suite quality; scientific stack |
| 16 | portmoreussy | KEEP | ussy-portmore | packages/tools/ | stdlib only | ~8 | P2 | Worth developing; zero deps |
| 17 | calibreussy | MERGE | ussy-calibre | packages/tools/quality/ | numpy, scipy | ~8 | P0 | Test suite quality cluster; primary merge target |
| 18 | acumenussy | MERGE | ussy-calibre | packages/tools/quality/ | stdlib only | ~8 | P1 | Test suite quality cluster; audiology diagnostics |
| 19 | cambiumussy | KEEP | ussy-cambium | packages/tools/deps/ | stdlib only | ~8 | P1 | Dependency analysis cluster; grafting compatibility |
| 20 | lehrussy | MERGE | ussy-calibre | packages/tools/quality/ | stdlib only | ~8 | P1 | Test suite quality cluster; glass annealing metaphor |
| 21 | clavisussy | KEEP | ussy-clavis | packages/tools/ | stdlib only | ~8 | P1 | Security & forensics; zero deps |
| 22 | marksmanussy | MERGE | ussy-calibre | packages/tools/quality/ | numpy, scipy | ~8 | P1 | Test suite quality cluster; archery precision |
| 23 | levainussy | MERGE | ussy-calibre | packages/tools/quality/ | stdlib only | ~8 | P1 | Test suite quality cluster; fermentation health |
| 24 | chromatoussy | KEEP | ussy-chromato | packages/tools/deps/ | stdlib only | ~8 | P1 | Dependency analysis cluster; chromatography risk |
| 25 | syntropussy | KEEP | ussy-syntrop | packages/tools/ | stdlib only | ~8 | P1 | Code quality & analysis; zero deps |
| 26 | coronerussy | KEEP | ussy-coroner | packages/tools/ | numpy, scipy | ~8 | P2 | CI/pipeline reliability; scientific stack |
| 27 | mintussy | KEEP | ussy-mint | packages/tools/ | stdlib only | ~8 | P2 | Worth developing; zero deps |
| 28 | fossilrecordussy | KEEP | ussy-fossilrecord | packages/tools/ | stdlib only | ~8 | P1 | Worth developing; zero deps |
| 29 | telegraphaussy | KEEP | ussy-telegrapha | packages/tools/ | stdlib only | ~8 | P1 | CI/pipeline reliability; zero deps |
| 30 | mushinussy | KEEP | ussy-mushin | packages/tools/ | stdlib only | ~8 | P1 | Config & drift; zero deps; fix pickle cache in migration |
| 31 | dosemateussy | KEEP | ussy-dosemate | packages/tools/ | stdlib only | ~8 | P2 | Worth developing; only setup.py repo — convert to pyproject.toml |
| 32 | cavityussy | KEEP | ussy-cavity | packages/tools/ | pyyaml | ~8 | P2 | CI/pipeline reliability; YAML config |
| 33 | gamutussy | KEEP | ussy-gamut | packages/tools/ | stdlib only | ~8 | P1 | CI/pipeline reliability; zero deps |
| 34 | aquiferussy | KEEP | ussy-aquifer | packages/tools/ | numpy | ~8 | P2 | CI/pipeline reliability; numpy dependency |
| 35 | cycloneussy | KEEP | ussy-cyclone | packages/tools/ | stdlib only | ~8 | P1 | CI/pipeline reliability; zero deps |
| 36 | isobarussy | KEEP | ussy-isobar | packages/tools/ | stdlib only | ~8 | P1 | Code quality & analysis; zero deps |
| 37 | circadiaussy | KEEP | ussy-circadia | packages/tools/ | stdlib only | ~8 | P1 | Agent/swarm infrastructure; zero deps |
| 38 | seralussy | KEEP | ussy-seral | packages/tools/ | click, rich | ~8 | P2 | Code quality & analysis; CLI tools |
| 39 | fatigueussy | KEEP | ussy-fatigue | packages/tools/ | stdlib only | ~8 | P1 | Worth developing; zero deps |
| 40 | endemicussy | KEEP | ussy-endemic | packages/tools/ | stdlib only | ~8 | P1 | Worth developing; zero deps |
| 41 | stemmaussy | KEEP | ussy-stemma | packages/tools/ | stdlib only | ~8 | P1 | Code quality & analysis; zero deps |
| 42 | plan9webplumbussy | KEEP | ussy-plan9webplumb | packages/tools/ | rich, pyyaml, websockets | ~8 | P2 | Code quality & analysis; web stack; fix security issue in migration |
| 43 | crystallossy | KEEP | ussy-crystallo | packages/tools/ | stdlib only | ~8 | P1 | Code quality & analysis; zero deps |
| 44 | terrariumussy | KEEP | ussy-terrarium | packages/tools/ | stdlib only | ~8 | P1 | Worth developing; zero deps |
| 45 | tarotussy | KEEP | ussy-tarot | packages/tools/ | stdlib only | ~8 | P1 | Worth developing; zero deps |
| 46 | stratagitussy | MERGE | ussy-strata | packages/tools/forensics/ | stdlib only | ~8 | P0 | Git forensics cluster; geological visualization; merge with unconformity |
| 47 | reverseoracleussy | KEEP | ussy-reverseoracle | packages/tools/ | click, rich, pyyaml, httpx | ~8 | P2 | Worth developing; requires external LLM API |
| 48 | timeloomussy | KEEP | ussy-timeloom | packages/tools/ | click, rich | ~8 | P2 | Worth developing; CLI tools |
| 49 | stenography | MERGE | ussy-steno | packages/tools/security/ | rich | ~8 | P0 | Steganography cluster; lightweight predecessor; archive after merge |
| 50 | churnmap | KEEP | ussy-churn | packages/tools/visualization/ | numpy, scipy, networkx, pydriller, matplotlib | ~8 | P0 | Git churn cluster; mature implementation; keep as base |

**Tier 2 Summary:** 39 repos → 33 packages (6 merges: calibre cluster ×5, stenography, stratagitussy)

---

## Tier 3: Archive/Ignore (13 repos)

| # | Repo | Decision | Reason | Reference |
|---|------|----------|--------|-----------|
| 51 | cartographerussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 52 | codelineageussy | ARCHIVE | .venv/ committed; security issue | Triage report: High severity — `.venv/` committed |
| 53 | churnmapussy | ARCHIVE | Early-stage, stub tests, .venv/ committed | Triage report: High severity — stub tests, `.venv/` committed |
| 54 | entrainussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 55 | escutcheonussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 56 | driftlineussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 57 | tellussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 58 | alembicussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 59 | hitchussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 60 | morsethussy | ARCHIVE | Games/edutainment | Triage report: "Games / Edutainment" category |
| 61 | kompressiussy | ARCHIVE | Maintenance mode, zstandard dep | Triage report: Low integration potential |
| 62 | inkblotussy | ARCHIVE | Privacy concerns (developer fingerprinting) | Triage report: Medium severity — privacy concerns |
| 63 | driftnetussy | ARCHIVE | No code — only specifications | Triage report: Zero utility until implemented |

**Tier 3 Summary:** 13 repos → 0 packages (all archived)

---

## Consolidation Summary

| Cluster | Repos | Result | Target Package | Test Count | Notes |
|---------|-------|--------|----------------|------------|-------|
| Test Suite Quality | calibreussy, acumenussy, lehrussy, marksmanussy, levainussy | 5 → 1 | ussy-calibre | ~40 | Subcommands: measure, hearing, stabilize, precision, health |
| Steganography | stenographussy, stenography | 2 → 1 | ussy-steno | ~18 | Archive stenography after porting unique detectors |
| Git Churn | churnmap, churnmapussy | 2 → 1 | ussy-churn | ~16 | Archive churnmapussy after porting ASCII renderer |
| Git Forensics | stratagitussy, unconformity | 2 → 1 | ussy-strata | ~14 | Subcommands: survey, missing, timeline |
| Dependency Analysis | gridironussy, chromatoussy, cambiumussy, strataussy | 4 → 4 + meta | ussy-gridiron, ussy-chromato, ussy-cambium, ussy-stratax + ussy-deps | ~32 | Keep separate; meta-package for unified CLI |

---

## Final Tally

| Metric | Count |
|--------|-------|
| Original repos | 63 |
| Migrated as standalone | 38 |
| Merged into other packages | 9 (from 14 repos) |
| Archived (not migrated) | 13 |
| **Final packages in monorepo** | **~47** (38 standalone + 4 merged packages + 1 meta-package + 6 shared libs + 1 root) |
| Shared libraries | 6 (ussy-core, ussy-cli, ussy-git, ussy-ast, ussy-sqlite, ussy-report) |
| Meta-packages | 1 (ussy-deps) |

---

## Dependency Analysis Summary

| Dependency | Frequency | Users (approximate) | Monorepo Group |
|-----------|-----------|---------------------|----------------|
| pytest | 13 repos | Various | dev dependency-group |
| pytest-cov | 10 repos | Various | dev dependency-group |
| rich | 7 repos | seral, plan9webplumb, codelineage, churnmap, churnmapussy, unconformity, stenography | cli optional |
| numpy | 7 repos | actuary, marksman, coroner, calibre, aquifer, codelineage, churnmap | sci optional |
| click | 5 repos | seral, reverseoracle, timeloom, codelineage, unconformity | cli optional |
| pyyaml | 5 repos | seral, strata, cavity, plan9webplumb, reverseoracle | config optional |
| scipy | 3 repos | actuary, marksman, churnmap | sci optional |
| gitpython | 2 repos | codelineage, unconformity | git optional |
| networkx | 2 repos | churnmap, churnmapussy | graph optional |
| matplotlib | 2 repos | codelineage, inkblot | viz optional |

**Conflict Status:** ZERO dependency conflicts detected. All version specs are compatible.

---

## Security Concerns Addressed in Migration

| Repo | Concern | Migration Fix |
|------|---------|---------------|
| snapshotussy | Plaintext SQLite storage of env vars | Add encryption-at-rest; filter secrets before persistence |
| mushinussy | Pickle-based object cache | Replace with JSON or msgpack; add integrity verification |
| plan9webplumbussy | WebSocket bound to all interfaces | Bind to localhost only; add authentication |
| codelineageussy | .venv/ committed | Archive repo; do not migrate |
| churnmapussy | .venv/ committed; stub tests | Archive repo; do not migrate |

---

*Document Version: 1.0*
*Last Updated: April 2026*
