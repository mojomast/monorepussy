"""Protobuf gamut profiles."""

from __future__ import annotations

from typing import Any

from ussy_gamut.models import FieldType, TypeGamut
from ussy_gamut.systems.base import BaseProfiler


class ProtobufProfiler(BaseProfiler):
    """Gamut profiler for Protocol Buffers scalar and well-known types."""

    system_name = "protobuf"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().lower()

        # Integer types
        int_map = {
            "int32": (-(2**31), 2**31 - 1, 10),
            "int64": (-(2**63), 2**63 - 1, 19),
            "sint32": (-(2**31), 2**31 - 1, 10),
            "sint64": (-(2**63), 2**63 - 1, 19),
            "sfixed32": (-(2**31), 2**31 - 1, 10),
            "sfixed64": (-(2**63), 2**63 - 1, 19),
            "uint32": (0, 2**32 - 1, 10),
            "uint64": (0, 2**64 - 1, 20),
            "fixed32": (0, 2**32 - 1, 10),
            "fixed64": (0, 2**64 - 1, 20),
        }
        if tn in int_map:
            mn, mx, prec = int_map[tn]
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=float(mn), max_value=float(mx), precision=prec, scale=0,
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

        # Bool
        if tn == "bool":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # String / bytes
        if tn == "string":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "bytes":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Well-known types
        if tn == "google.protobuf.timestamp":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.TIMESTAMP,
                timezone_aware=True, tz_precision=9,  # nanosecond
                nullable=kwargs.get("nullable", True),
            )
        if tn == "google.protobuf.duration":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.UNKNOWN,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "google.protobuf.any":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Enum
        if tn == "enum":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ENUM,
                min_value=0, max_value=2**31 - 1, precision=10, scale=0,
                nullable=kwargs.get("nullable", True),
            )

        # Map / repeated
        if tn == "map":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.MAP,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("repeated", "list"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ARRAY,
                nullable=kwargs.get("nullable", True),
            )

        # Message (struct)
        if tn in ("message", "struct"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
