"""JSON system gamut profiles."""

from __future__ import annotations

from typing import Any

from gamut.models import FieldType, TypeGamut
from gamut.systems.base import BaseProfiler


class JSONProfiler(BaseProfiler):
    """Gamut profiler for JSON data types.

    JSON has a very small type system: number, string, boolean, null, array, object.
    JSON numbers are IEEE 754 double-precision when parsed by most runtimes.
    """

    system_name = "json"

    # IEEE 754 double: safe integer range
    _SAFE_INT_MIN = -(2**53)
    _SAFE_INT_MAX = 2**53

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().lower()

        if tn == "number":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.FLOAT,
                min_value=-1.7976931348623157e308, max_value=1.7976931348623157e308,
                precision=15, scale=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "integer":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=float(self._SAFE_INT_MIN), max_value=float(self._SAFE_INT_MAX),
                precision=15, scale=0,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "string":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "boolean":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )
        if tn == "null":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.UNKNOWN,
                nullable=True,
            )
        if tn == "array":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.ARRAY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("object", "struct"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRUCT,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
