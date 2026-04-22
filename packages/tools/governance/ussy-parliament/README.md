# Parliament — Parliamentary Procedure for Agent Self-Governance

Parliament models the codebase as a **legislative chamber** where agents (CI workers, review bots, security scanners, human developers) are delegates. Every significant action is a **motion** that must traverse the canonical parliamentary workflow: introduction, seconding, amendment (if any), quorum verification, voting, and recording in the journal.

## Overview

Modern software systems are governed by decentralized agents with overlapping or conflicting authority. Parliament applies **parliamentary procedure** (Robert's Rules of Order) to agent interactions, ensuring that collective decisions are deliberate, legitimate, and auditable.

Core concepts:
- **Motions** ↔ Proposals for operational changes (deploy, merge, config change, rollbacks).
- **Seconding** ↔ Sponsorship threshold requiring support from multiple agents before debate.
- **Amendments** ↔ Structured revisions with **germaneness** tests.
- **Quorum** ↔ Minimum participation weighted by operational criticality.
- **Points of order** ↔ Procedural challenges that halt execution pending ruling.
- **Journal** ↔ Append-only, hash-linked record of all proceedings.

## Installation

```bash
git clone <repo>
cd parliament
pip install -e .
```

Requires Python 3.11+.

## Usage Examples

### Initialize a chamber
```bash
parliament init ./my-chamber
```

### Register agents
```bash
parliament agent register deploy-bot orchestration --weight 1.0
parliament agent register canary-bot validation --weight 0.9
```

### Create and second a motion
```bash
parliament motion create --agent deploy-bot --action "scale:prod:10x" --scope prod
parliament motion second MP-XXXX --agent canary-bot
```

### Propose an amendment
```bash
parliament amend MP-XXXX --agent canary-bot --action "scale:prod:8x" --scope prod
parliament amend-second AMP-XXXX --agent security-scanner
```

### Call to order and verify quorum
```bash
parliament session call-to-order MP-XXXX --agents deploy-bot,canary-bot,security-scanner
```

### Open voting and cast votes
```bash
parliament vote open MP-XXXX --method supermajority
parliament vote cast MP-XXXX --agent deploy-bot --aye
parliament vote cast MP-XXXX --agent rollback-bot --nay
parliament vote close MP-XXXX
```

### Raise a point of order
```bash
parliament point-of-order MP-XXXX --agent rollback-bot --violation quorum_deficit
parliament rule POO-XXXX
```

### View journal and verify integrity
```bash
parliament journal view MP-XXXX
parliament journal verify
```

### Generate minutes
```bash
parliament minutes MP-XXXX
```

## Architecture

```
parliament/
├── models.py          # Core dataclasses (Motion, Vote, Agent, JournalEntry, etc.)
├── motion.py          # Motion & Seconding Engine
├── amendment.py       # Amendment Processor with germaneness testing
├── quorum.py          # Quorum & Call-to-Order
├── voting.py          # Voting Methods Engine (majority, supermajority, consensus)
├── points_of_order.py # Points of Order & Appeals
├── journal.py         # Journal & Minutes (hash-linked chain)
├── session.py         # ParliamentSession orchestrates all engines
├── storage.py         # SQLite store for state, flat file for journal
└── cli.py             # argparse CLI
```

### Storage
- **Journal**: Append-only flat file with SHA-256 chaining.
- **Session state**: SQLite for active motions, amendments, and votes.
- **Agent registry**: SQLite table mapping agent IDs to weights and public keys.

### Voting Methods
- **Majority**: > 50% weighted approval.
- **Supermajority**: ≥ 2/3 weighted approval.
- **Consensus**: ≥ 80% and no veto (weight > threshold).

### Dynamic Thresholds
- `required_seconds = max(1, ceil(ln(impact_score + 1)))` capped by policy.
- `quorum_required = ceil((0.3 + 0.4 * tier/5) * total_active)`.

## Zero External Dependencies

Parliament uses only the Python standard library: `argparse`, `hashlib`, `sqlite3`, `datetime`, `dataclasses`, `pathlib`, `json`, `tempfile`, and `uuid`.
