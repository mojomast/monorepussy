"""BigQuery gamut profiles."""

from __future__ import annotations

import re
from typing import Any

from ussy_gamut.models import FieldType, TypeGamut
from ussy_gamut.systems.base import BaseProfiler


class BigQueryProfiler(BaseProfiler):
    """Gamut profiler for Google BigQuery data types."""

    system_name = "bigquery"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().upper()

        # Integer
        if tn == "INT64":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-9223372036854775808, max_value=9223372036854775807,
                precision=19, scale=0,
                nullable=kwargs.get("nullable", True),
            )

        # Float
        if tn == "FLOAT64":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-1.7976931348623157e308, max_value=1.7976931348623157e308,
                precision=15, scale=None,
                nullable=kwargs.get("nullable", True),
            )

        # Numeric / BIGNUMERIC
        numeric_match = re.match(
            r"(?:NUMERIC|BIGNUMERIC)(?:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\))?", tn
        )
        if numeric_match:
            prec_str, scale_str = numeric_match.groups()
            if tn.startswith("BIGNUMERIC"):
                default_prec, default_scale = 76, 38
            else:
                default_prec, default_scale = 38, 9
            prec = int(prec_str) if prec_str else default_prec
            scl = int(scale_str) if scale_str else default_scale
            max_val = float(10 ** (prec - scl) - 10 ** (-scl))
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DECIMAL,
                min_value=-max_val, max_value=max_val, precision=prec, scale=scl,
                nullable=kwargs.get("nullable", True),
            )

        # String
        if tn == "STRING":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Bytes
        if tn == "BYTES":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Bool
        if tn == "BOOL":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # Date
        if tn == "DATE":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DATE,
                nullable=kwargs.get("nullable", True),
            )

        # Temporal
        if tn == "DATETIME":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "TIMESTAMP":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=True, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "TIME":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIME,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )

        # Struct / Array
        if tn.startswith("STRUCT") or tn.startswith("RECORD"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )
        if tn.startswith("ARRAY"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ARRAY,
                nullable=kwargs.get("nullable", True),
            )

        # Geography
        if tn == "GEOGRAPHY":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.UNKNOWN,
                nullable=kwargs.get("nullable", True),
            )

        # JSON
        if tn == "JSON":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
