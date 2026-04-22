# SPEC — Terrarium Monorepo Technical Specification

## HealthScore Schema

```python
@dataclass
class HealthScore:
    overall: float      # 0.0–1.0 weighted average of all dimensions
    fatigue: float      # 1.0 - mean(crack_intensity)
    epidemic: float     # ratio of non-infected files
    anomaly: float      # ratio of non-anomalous files
    drift: float        # 1.0 - mean(vitality_damage)
    churn: float        # reserved for future git-churn adapter
    complexity: float   # 1.0 - mean(complexity_score)
    territory: str      # visual biome ID (from churnmap)
    succession: str     # pioneer | seral | climax (from seral)
    raw: Dict           # per-adapter raw metrics for debugging
```

## Adapter Contract

Every adapter must:

1. Subclass `BaseAdapter` from `terrarium.adapters.base`
2. Define `name: str` class attribute (used for auto-discovery)
3. Define `STUB_MODE: bool` (set in `__init__` based on import success)
4. Implement `load(self) -> Dict[str, OrganismHealthState]`
5. Return an empty dict `{}` if `self.data_path` is `None`
6. Gracefully handle missing/invalid JSON files

### Availability

`BaseAdapter.is_available()` returns `True` when either `STUB_MODE` is `True` or `data_path` is not `None`. The engine calls `is_available()` before `load()` to skip adapters that have no data source, producing an explicit `{"error": "adapter not available", "stub": True}` record rather than swallowing exceptions.

### OrganismHealthState Fields

```python
@dataclass
class OrganismHealthState:
    path: str
    vitality: float = 1.0              # 0.0–1.0 (1.0 = perfect)
    crack_intensity: float = 0.0       # fatigueussy
    infection_state: str = "S"         # endemicussy (S/E/I/R)
    anomaly_active: bool = False       # sentinelussy
    complexity_score: float = 0.0      # kompressiussy
    territory_id: Optional[str] = None # churnmap
    succession_stage: str = "seral"    # seralussy
```

## Engine Scoring Algorithm

The `TerrariumEngine.score()` method computes sub-scores as follows:

1. **Collect** all adapter data via `engine.collect()`
2. For each dimension, compute the inverse of damage signals:
   - `fatigue = 1.0 - mean(crack_intensity)` across all files reported by fatigue adapter
   - `epidemic = 1.0 - (infected_count / total_files)` from endemic adapter
   - `anomaly = 1.0 - (anomalous_count / total_files)` from sentinel adapter
   - `drift = 1.0 - mean(1.0 - vitality)` across all adapters reporting vitality < 1.0
   - `complexity = 1.0 - mean(complexity_score)` from kompressi adapter
   - `churn = 1.0 - (churning_count / total_files)` from churnmap adapter, where a file is "churning" if it has a non-null/non-empty `territory_id`
3. Compute `overall` as weighted average:
   ```
   overall = (
       0.20 * fatigue +
       0.20 * epidemic +
       0.20 * anomaly +
       0.15 * drift +
       0.15 * complexity +
       0.10 * churn
   )
   ```
4. If an adapter is missing or unavailable, its dimension defaults to `1.0` (perfect health)

## Merge Strategy

When multiple adapters report data for the same file path, `merge_health_states()` applies:

- `vitality`: `min()` — worst vitality wins
- `crack_intensity`: `max()` — worst crack wins
- `infection_state`: non-S value wins (I > E > R > S)
- `anomaly_active`: `or` — any true means true
- `complexity_score`: `max()` — worst complexity wins
- `territory_id`: first non-None wins
- `succession_stage`: most advanced wins (climax > seral > pioneer)

## CLI Commands

| Command | Description | Engine |
|---------|-------------|--------|
| `watch` | Legacy ecosystem view | MetricsEngine + Ecosystem |
| `diagnose` | Module health report | MetricsEngine + Ecosystem |
| `snapshot` | CI snapshot export | MetricsEngine + Ecosystem |
| `seasons` | Seasonal timeline | MetricsEngine + Ecosystem |
| `health` | Compact health report | MetricsEngine + Ecosystem |
| `dashboard` | Rich one-shot dashboard | TerrariumEngine |
| `watch-live` | Rich live watch | TerrariumEngine + Live |
| `export` | JSON/CSV metrics export | TerrariumEngine |

## Dependencies

- `click >= 8.0` — CLI framework
- `rich >= 13.0` — Terminal visualization
- `pytest >= 9.0` — Test runner (dev)
- `pytest-cov` — Coverage (dev)

All sibling ussyverse packages are **optional**. Terrarium runs in stub mode if they are not installed.
