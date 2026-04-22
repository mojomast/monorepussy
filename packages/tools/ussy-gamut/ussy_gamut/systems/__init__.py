"""System-specific gamut profile registries."""

from ussy_gamut.systems.postgresql import PostgreSQLProfiler
from ussy_gamut.systems.bigquery import BigQueryProfiler
from ussy_gamut.systems.parquet import ParquetProfiler
from ussy_gamut.systems.protobuf import ProtobufProfiler
from ussy_gamut.systems.json_system import JSONProfiler
from ussy_gamut.systems.avro import AvroProfiler
from ussy_gamut.systems.spark import SparkProfiler

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
