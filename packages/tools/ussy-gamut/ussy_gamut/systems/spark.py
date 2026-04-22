"""Spark DataFrame gamut profiles."""

from __future__ import annotations

import re
from typing import Any

from ussy_gamut.models import FieldType, TypeGamut
from ussy_gamut.systems.base import BaseProfiler


class SparkProfiler(BaseProfiler):
    """Gamut profiler for Apache Spark DataFrame types."""

    system_name = "spark"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().lower()

        # Integer types
        if tn == "byte" or tn == "tinyint":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-128, max_value=127, precision=3, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "short" or tn == "smallint":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-32768, max_value=32767, precision=5, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("int", "integer"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-2147483648, max_value=2147483647, precision=10, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "long" or tn == "bigint":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-9223372036854775808, max_value=9223372036854775807,
                precision=19, scale=0,
                nullable=kwargs.get("nullable", True),
            )

        # Float types
        if tn == "float":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-3.4028235e38, max_value=3.4028235e38, precision=6, scale=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "double":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-1.7976931348623157e308, max_value=1.7976931348623157e308,
                precision=15, scale=None,
                nullable=kwargs.get("nullable", True),
            )

        # Decimal
        decimal_match = re.match(r"decimal\((\d+),\s*(\d+)\)", tn)
        if decimal_match:
            prec, scl = int(decimal_match.group(1)), int(decimal_match.group(2))
            max_val = float(10 ** (prec - scl) - 10 ** (-scl))
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DECIMAL,
                min_value=-max_val, max_value=max_val, precision=prec, scale=scl,
                nullable=kwargs.get("nullable", True),
            )

        # String / binary
        if tn in ("string", "varchar", "char"):
            max_len = kwargs.get("length")
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=self._safe_int(max_len),
                nullable=kwargs.get("nullable", True),
            )
        if tn == "binary":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                nullable=kwargs.get("nullable", True),
            )

        # Boolean
        if tn == "boolean":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # Temporal
        if tn == "date":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DATE,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "timestamp":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=kwargs.get("timezone_aware", False), tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "timestamp_ntz":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "timestamp_ltz":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=True, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )

        # Complex
        if tn == "array":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ARRAY,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "map":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.MAP,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "struct":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
