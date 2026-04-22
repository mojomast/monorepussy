# Adapter API Reference

## BaseAdapter

```python
class BaseAdapter(ABC):
    name: str = ""

    def __init__(self, data_path: Optional[str] = None)
    def load(self) -> Dict[str, OrganismHealthState]
    def is_available(self) -> bool
```

## FatigueAdapter

**Source:** [fatigueussy](https://github.com/mojomast/fatigueussy)

**JSON Input:**
```json
{
  "stress_intensities": {
    "src/auth.py": {"K": 150.0, "delta_K": 10.0}
  }
}
```

**Mapping:** `K` normalized against `max_k_ceiling` (default 100.0) → `crack_intensity`

**Vitality Impact:** `vitality = 1.0 - crack_intensity`

## EndemicAdapter

**Source:** [endemicussy](https://github.com/mojomast/endemicussy)

**JSON Input:**
```json
{
  "modules": [
    {"path": "src/auth.py", "compartment": "I"}
  ]
}
```

**Mapping:** `compartment` → `infection_state` (S/E/I/R)

**Vitality Impact:** S=1.0, E=0.7, I=0.3, R=0.8

## SentinelAdapter

**Source:** [sentinelussy](https://github.com/mojomast/sentinelussy)

**JSON Input:**
```json
{
  "files": {
    "src/auth.py": {
      "anomaly_score": 0.73,
      "is_anomalous": true,
      "detections": [{"false_positive_rate": 0.2}]
    }
  }
}
```

**Mapping:** `is_anomalous` → `anomaly_active`. Detectors with `false_positive_rate > 0.5` are suppressed.

**Vitality Impact:** `vitality = 1.0 - anomaly_score`

## KompressiAdapter

**Source:** [kompressiussy](https://github.com/mojomast/kompressiussy)

**JSON Input:**
```json
[
  {"path": "src/auth.py", "id": 10.15}
]
```

**Mapping:** `id` (info density) normalized to batch max → `complexity_score`

**Vitality Impact:** `vitality = 1.0 - complexity_score * 0.2`

## ChurnmapAdapter

**Source:** [churnmap](https://github.com/mojomast/churnmap)

**JSON Input:**
```json
{
  "files": {
    "src/auth.py": {"territory_id": "core-api"}
  }
}
```

**Mapping:** `territory_id` → `territory_id` (visual only, no vitality impact)

## SeralAdapter

**Source:** [seralussy](https://github.com/mojomast/seralussy)

**JSON Input:**
```json
{
  "src/auth.py": "climax"
}
```

**Mapping:** Stages mapped to `pioneer` / `seral` / `climax` (visual only)

## ProprioceptionAdapter

**Source:** [proprioceptionussy](https://github.com/mojomast/proprioceptionussy)

**JSON Input:**
```json
{
  "root": "./my-project",
  "limbs": [
    {"path": "./my-project/src", "type": "git-repo", "state": {"dirty": true}}
  ]
}
```

**Mapping:** Ratio of dirty limbs → drift score

**Vitality Impact:** `vitality = 1.0 - drift_score * 0.3`

## SnapshotAdapter

**Source:** [snapshotussy](https://github.com/mojomast/snapshotussy)

**JSON Input:**
```json
{
  "name": "before-refactor",
  "open_files": [{"path": "src/auth.py", "modified": true}],
  "processes": [{"command": "pytest"}],
  "env_var_count": 12
}
```

**Mapping:** Open files + processes + env vars → memory pressure score

**Vitality Impact:** `vitality = 1.0 - pressure * 0.25` (modified files get extra 0.8 multiplier)
