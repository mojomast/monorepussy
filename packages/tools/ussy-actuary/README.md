# Actuary — Actuarial Vulnerability Risk Quantification

**Apply insurance mathematics to software vulnerability risk.**

Security vulnerability management treats risk as a static snapshot. Every tool gives you what IS known — CVE scores, exploit prediction scores, vulnerability counts — but none answer the questions that actually matter for resource allocation. Actuary applies 300 years of actuarial science to vulnerability populations: life tables, chain ladder projections, credibility blending, IBNR reserves, copula aggregation, and moral hazard quantification.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# CVE exploit survival table (actuarial life table)
actuary survival --cohort Q1-2025

# Vulnerability backlog projection (chain ladder)
actuary backlog --repo ./my-project --quarters 8

# Internal/external threat intel blending (Bühlmann credibility)
actuary credibility --org mycompany --n-obs 52

# Latent vulnerability estimation (IBNR)
actuary ibnr --reported 3 --density 15.2 --kloc 10.0

# Correlated risk aggregation (copula models)
actuary aggregate --assets 100 --copula clayton --alpha 2 --var 0.99

# Security incentive misalignment (moral hazard)
actuary moral-hazard --loss 1000000 --coverage 0.8
```

All commands support `--json` for machine-readable output.

## Architecture

### 6 Core Modules

| Module | Actuarial Concept | Security Application |
|--------|------------------|---------------------|
| `survival` | Mortality table | CVE exploit survival table — age-conditional hazard rates |
| `backlog` | Chain ladder | Vulnerability backlog projection with confidence intervals |
| `credibility` | Bühlmann credibility | Optimal internal/external threat intel blending |
| `ibnr` | IBNR reserves | Latent vulnerability estimation (unknown-but-existing CVEs) |
| `aggregate` | Copula risk model | Correlated vulnerability aggregation with TVaR |
| `moral_hazard` | Moral hazard | Security incentive quantification from SLAs/insurance |

### Data Flow

```
CVE Data → Survival Table → Hazard Rates → Backlog Projection → Reserve Estimates
                                                                      ↓
Internal Data + EPSS → Credibility Blending → Per-CVE Scores   → IBNR Estimation
                                                                      ↓
Asset Inventory → Copula Simulation → VaR/TVaR → Aggregate Risk → Moral Hazard
```

### Storage

SQLite database (`~/.actuary/actuary.db`) with tables for:
- `cve_cohorts` — CVE disclosure and exploitation data
- `life_tables` — Computed survival table rows
- `development_triangles` — Vulnerability discovery over time
- `credibility_params` — Bühlmann credibility parameters
- `ibnr_reserves` — IBNR estimates per repository
- `copula_models` — Aggregate risk simulation results

## Key Concepts

### 1. Survival Table (Life Table)

Models the probability of CVE exploitation at each age since disclosure:

```
Age(v)  l_v    d_v    q_v      μ_v      e_v
  0     847     12   0.0142   0.0143   287.3
 30     812     28   0.0345   0.0351   142.7
 60     741     45   0.0607   0.0626    89.1
```

With Whittaker-Henderson graduation for smoothing raw rates.

### 2. Chain Ladder (Backlog Projection)

Projects future vulnerability discovery from a development triangle:

```
                Development Quarter
 Cohort         0     1     2     3     4
 Q1-2024       12    28    41    48    52
 Q2-2024       15    33    49    57    61.7*
```

Includes Mack's variance for confidence intervals.

### 3. Bühlmann Credibility (Data Blending)

Mathematically optimal weight for blending internal and external data:

```
Z = n / (n + K)   where K = EPV / VHM

Org with 52 weeks → Z ≈ 0.95 (trust internal data)
Org with 4 weeks  → Z ≈ 0.57 (trust EPSS more)
```

### 4. IBNR (Latent Vulnerabilities)

Estimates vulnerabilities that exist but haven't been found:

```
Bornhuetter-Ferguson: BF_reserve = μ × (1 - reported/μ)
Library: 3 reported CVEs, μ=20 → 17 latent CVEs estimated
```

### 5. Copula Models (Correlated Risk)

Models tail dependence in exploit scenarios:

```
100 assets, 1% exploit probability:
  Independent: P(≥10 exploits) ≈ 0.001%
  Clayton (α=2): P(≥10 exploits) ≈ 0.4%
  Gumbel (β=2):  P(≥10 exploits) ≈ 1.2%
```

### 6. Moral Hazard (Incentive Analysis)

Quantifies how SLAs/insurance reduce security effort:

```
Effort reduction = coverage fraction (α)
80% coverage → 80% effort reduction
Optimal coinsurance minimizes welfare loss
```

## Dependencies

- Python 3.10+
- numpy, scipy (for statistical distributions and copula simulation)
- sqlite3 (stdlib)

No LLM dependency — all analysis is deterministic actuarial mathematics.

## License

MIT
