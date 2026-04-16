# Gamut — Color Science Gamut Mapping for Data Pipeline Fidelity

> **"Compatible ≠ Faithful"**

Data pipelines silently lose information at every stage boundary. A `TIMESTAMPTZ` becomes a `TIMESTAMP` (timezone gone). A `NUMERIC(38,18)` becomes a `FLOAT64` (precision lost). Schema compatibility tools say "these types are compatible" — but **compatible doesn't mean faithful**.

**Gamut** applies color science's gamut mapping framework to data pipelines: type systems are **color spaces**, type conversions are **gamut transforms**, and silent data loss is **gamut clipping**. Just as a photo's colors get crushed when moving from Adobe RGB to sRGB, your data gets distorted when moving from PostgreSQL to BigQuery.

## How It Works

| Color Science Concept | Data Pipeline Analogue |
|---|---|
| Color space | Type system (PostgreSQL, BigQuery, Avro, etc.) |
| Gamut | Representable range of a type |
| Gamut clipping | Silent data loss (precision, timezone, range) |
| Delta E (ΔE) | Information loss severity (0–100 scale) |
| Rendering intent | Error handling strategy |
| Perceptual intent | Round/graceful degradation |
| Absolute intent | Error on any loss |
| Saturation intent | Clamp to bounds |

### Rendering Intents → Error Strategies

- **Perceptual**: Round gracefully, preserve relationships (e.g., BIGINT → INT rounds large values)
- **Absolute**: Reject any conversion that loses information (strict mode)
- **Saturation**: Clamp to target bounds (e.g., out-of-range dates → MAX_DATE)

## Installation

```bash
pip install -e .
```

No external dependencies — pure Python stdlib.

## Quick Start

```bash
# Analyze a pipeline definition for clipping risks
gamut analyze pipeline.json

# Analyze with detailed ASCII diagrams
gamut analyze pipeline.json --detailed

# Profile a specific data system's type gamut
gamut profile --system postgresql --type-name NUMERIC

# Profile a type across multiple systems
gamut profile --system bigquery --type-name BIGNUMERIC

# Visualize gamut overlap between two systems
gamut visualize pipeline.json

# Sample real data for actual clipping detection
gamut sample pipeline.json --data-dir ./data/
```

## Pipeline Definition Format

Create a JSON or YAML file describing your pipeline:

```json
{
  "name": "etl_pipeline",
  "stages": [
    {
      "name": "postgres_source",
      "system": "postgresql",
      "fields": {
        "id": "BIGINT",
        "amount": "NUMERIC(38,18)",
        "created_at": "TIMESTAMPTZ",
        "status": "VARCHAR(50)",
        "metadata": "JSONB"
      }
    },
    {
      "name": "json_api",
      "system": "json",
      "fields": {
        "id": "number",
        "amount": "number",
        "created_at": "string",
        "status": "string",
        "metadata": "object"
      }
    },
    {
      "name": "bigquery_dest",
      "system": "bigquery",
      "fields": {
        "id": "INT64",
        "amount": "FLOAT64",
        "created_at": "TIMESTAMP",
        "status": "STRING",
        "metadata": "JSON"
      }
    }
  ]
}
```

## Architecture

```
gamut/
├── models.py          # Core data models (GamutProfile, ClippingResult, RenderingIntent)
├── systems/           # Type system profiles (PostgreSQL, BigQuery, Avro, Parquet, JSON, Protobuf, Spark)
│   ├── base.py        # Base SystemProfile with resolution logic
│   ├── postgresql.py  # PostgreSQL type gamut with range/precision
│   ├── bigquery.py    # BigQuery type gamut
│   ├── avro.py        # Apache Avro type gamut
│   ├── parquet.py     # Parquet type gamut
│   ├── protobuf.py    # Protocol Buffers type gamut
│   ├── json_system.py # JSON type gamut
│   └── spark.py       # Apache Spark type gamut
├── profiler.py        # Type gamut profiling engine
├── analyzer.py        # Pipeline clipping analyzer with Delta E computation
├── visualizer.py      # ASCII CIE-style gamut diagram renderer
├── dag_parser.py      # Pipeline DAG parsing (JSON/YAML/directory)
├── sampler.py         # Runtime data sampling for empirical clipping detection
└── cli.py             # Command-line interface
```

### Delta E Computation

Gamut computes a Delta E (ΔE) score for each field conversion, measuring information loss on a 0–100 scale:

- **0–5**: Imperceptible loss (e.g., VARCHAR(50) → STRING)
- **5–15**: Minor loss (e.g., BIGINT → INT64, within safe range)
- **15–30**: Moderate loss (e.g., NUMERIC → FLOAT64 precision loss)
- **30–50**: Severe loss (e.g., TIMESTAMPTZ → TIMESTAMP, timezone stripped)
- **50–100**: Catastrophic loss (e.g., NUMERIC(38,18) → INT32, massive truncation)

### Supported Systems

| System | Key Types Profiled |
|---|---|
| PostgreSQL | BIGINT, INTEGER, NUMERIC(p,s), REAL, DOUBLE, TEXT, VARCHAR, TIMESTAMPTZ, TIMESTAMP, DATE, JSONB, UUID, BOOLEAN |
| BigQuery | INT64, FLOAT64, NUMERIC, BIGNUMERIC, STRING, TIMESTAMP, DATETIME, DATE, BOOL, JSON, BYTES |
| Avro | long, int, float, double, string, bytes, boolean, logical types |
| Parquet | INT32, INT64, FLOAT, DOUBLE, BYTE_ARRAY, FIXED_LEN_BYTE_ARRAY, BOOLEAN |
| Protobuf | int32, int64, sfixed32, sfixed64, float, double, string, bytes, bool |
| JSON | number, string, boolean, object, array, null |
| Spark | IntegerType, LongType, FloatType, DoubleType, StringType, TimestampType, DateType |

## Example Output

```
Pipeline: etl_pipeline
======================================================================

  Stages: postgres_source → json_api → bigquery_dest

  Boundary: postgres_source → json_api
    Fields analyzed : 5
    Clipping fields : 3
    Critical fields : 1
    Max ΔE          : 25.00

    ⚠ id
      postgresql:BIGINT → json:number
      ΔE=5.26  risk=high  intent=perceptual
      · precision loss: 19 → 15 digits (4 lost)

    ⚠ amount
      postgresql:NUMERIC(38,18) → json:number
      ΔE=15.13  risk=high  intent=perceptual
      · precision loss: 38 → 15 digits (23 lost)

    ⚠ created_at
      postgresql:TIMESTAMPTZ → json:string
      ΔE=25.00  risk=critical  intent=perceptual
```

## Testing

```bash
python -m pytest tests/ -v    # 145 tests
```

## License

MIT
