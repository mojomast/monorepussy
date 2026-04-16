"""System-specific gamut profile registries."""

from gamut.systems.postgresql import PostgreSQLProfiler
from gamut.systems.bigquery import BigQueryProfiler
from gamut.systems.parquet import ParquetProfiler
from gamut.systems.protobuf import ProtobufProfiler
from gamut.systems.json_system import JSONProfiler
from gamut.systems.avro import AvroProfiler
from gamut.systems.spark import SparkProfiler

SYSTEM_PROFILERS = {
    "postgresql": PostgreSQLProfiler(),
    "bigquery": BigQueryProfiler(),
    "parquet": ParquetProfiler(),
    "protobuf": ProtobufProfiler(),
    "json": JSONProfiler(),
    "avro": AvroProfiler(),
    "spark": SparkProfiler(),
}

__all__ = [
    "PostgreSQLProfiler",
    "BigQueryProfiler",
    "ParquetProfiler",
    "ProtobufProfiler",
    "JSONProfiler",
    "AvroProfiler",
    "SparkProfiler",
    "SYSTEM_PROFILERS",
]
