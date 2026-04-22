"""PostgreSQL gamut profiles."""

from __future__ import annotations

import re
from typing import Any

from ussy_gamut.models import FieldType, TypeGamut
from ussy_gamut.systems.base import BaseProfiler


class PostgreSQLProfiler(BaseProfiler):
    """Gamut profiler for PostgreSQL data types."""

    system_name = "postgresql"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().upper()

        # Integer types
        if tn in ("SMALLINT", "INT2"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-32768, max_value=32767, precision=5, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("INTEGER", "INT", "INT4"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-2147483648, max_value=2147483647, precision=10, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("BIGINT", "INT8"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-9223372036854775808, max_value=9223372036854775807,
                precision=19, scale=0,
                nullable=kwargs.get("nullable", True),
            )

        # Serial types (same range as integer counterparts)
        if tn in ("SERIAL", "SERIAL4"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=1, max_value=2147483647, precision=10, scale=0,
                nullable=False,
            )
        if tn in ("BIGSERIAL", "SERIAL8"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=1, max_value=9223372036854775807, precision=19, scale=0,
                nullable=False,
            )
        if tn == "SMALLSERIAL":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=1, max_value=32767, precision=5, scale=0,
                nullable=False,
            )

        # Float types
        if tn in ("REAL", "FLOAT4"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-3.4028235e38, max_value=3.4028235e38, precision=6, scale=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("DOUBLE PRECISION", "FLOAT8"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-1.7976931348623157e308, max_value=1.7976931348623157e308,
                precision=15, scale=None,
                nullable=kwargs.get("nullable", True),
            )

        # NUMERIC / DECIMAL
        numeric_match = re.match(
            r"(?:NUMERIC|DECIMAL)(?:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\))?", tn
        )
        if numeric_match:
            prec_str, scale_str = numeric_match.groups()
            if prec_str and scale_str:
                prec = int(prec_str)
                scl = int(scale_str)
            else:
                prec = 131072  # PG max
                scl = 16383
            max_val = float(10 ** (prec - scl) - 10 ** (-scl))
            min_val = -max_val
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DECIMAL,
                min_value=min_val, max_value=max_val, precision=prec, scale=scl,
                nullable=kwargs.get("nullable", True),
            )

        # String types
        if tn == "TEXT":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        varchar_match = re.match(r"(?:VARCHAR|CHARACTER VARYING)(?:\s*\(\s*(\d+)\s*\))?", tn)
        if varchar_match:
            ml = varchar_match.group(1)
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=int(ml) if ml else None,
                nullable=kwargs.get("nullable", True),
            )
        char_match = re.match(r"(?:CHAR|CHARACTER)(?:\s*\(\s*(\d+)\s*\))?", tn)
        if char_match:
            ml = char_match.group(1)
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=int(ml) if ml else 1,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "BPCHAR":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=1,
                nullable=kwargs.get("nullable", True),
            )

        # Binary
        if tn == "BYTEA":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Temporal types
        if tn == "DATE":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DATE,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=True, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("TIME", "TIME WITHOUT TIME ZONE"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIME,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("TIMETZ", "TIME WITH TIME ZONE"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIME,
                timezone_aware=True, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )

        # Boolean
        if tn == "BOOLEAN" or tn == "BOOL":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # UUID
        if tn == "UUID":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=36,
                nullable=kwargs.get("nullable", True),
            )

        # JSON types
        if tn in ("JSON", "JSONB"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Array
        if tn.endswith("[]"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ARRAY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
