"""Avro gamut profiles."""

from __future__ import annotations

from typing import Any

from ussy_gamut.models import FieldType, TypeGamut
from ussy_gamut.systems.base import BaseProfiler


class AvroProfiler(BaseProfiler):
    """Gamut profiler for Apache Avro primitive and logical types."""

    system_name = "avro"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().lower()

        # Null
        if tn == "null":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.UNKNOWN,
                nullable=True,
            )

        # Boolean
        if tn == "boolean":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # Integer types
        if tn == "int":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-(2**31), max_value=2**31 - 1, precision=10, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "long":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=-(2**63), max_value=2**63 - 1, precision=19, scale=0,
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

        # Bytes / string
        if tn == "bytes":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "string":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Logical types
        if tn == "date" or (kwargs.get("logical_type") == "date"):
            return TypeGamut(
                system=self.system_name, type_name="date", field_type=FieldType.DATE,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "timestamp-millis" or (kwargs.get("logical_type") == "timestamp-millis"):
            return TypeGamut(
                system=self.system_name, type_name="timestamp-millis",
                field_type=FieldType.TIMESTAMP,
                timezone_aware=kwargs.get("timezone_aware", False), tz_precision=3,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "timestamp-micros" or (kwargs.get("logical_type") == "timestamp-micros"):
            return TypeGamut(
                system=self.system_name, type_name="timestamp-micros",
                field_type=FieldType.TIMESTAMP,
                timezone_aware=kwargs.get("timezone_aware", False), tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "local-timestamp-millis" or (kwargs.get("logical_type") == "local-timestamp-millis"):
            return TypeGamut(
                system=self.system_name, type_name="local-timestamp-millis",
                field_type=FieldType.TIMESTAMP,
                timezone_aware=False, tz_precision=3,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "local-timestamp-micros" or (kwargs.get("logical_type") == "local-timestamp-micros"):
            return TypeGamut(
                system=self.system_name, type_name="local-timestamp-micros",
                field_type=FieldType.TIMESTAMP,
                timezone_aware=False, tz_precision=6,
                nullable=kwargs.get("nullable", True),
            )

        # Decimal logical type
        if tn == "decimal" or (kwargs.get("logical_type") == "decimal"):
            prec = kwargs.get("precision", 38)
            scl = kwargs.get("scale", 18)
            max_val = float(10 ** (prec - scl) - 10 ** (-scl))
            return TypeGamut(
                system=self.system_name, type_name="decimal",
                field_type=FieldType.DECIMAL,
                min_value=-max_val, max_value=max_val, precision=prec, scale=scl,
                nullable=kwargs.get("nullable", True),
            )

        # Complex types
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
        if tn in ("record", "struct"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "enum":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ENUM,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("fixed",):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=kwargs.get("size"),
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
