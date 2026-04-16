"""Parquet gamut profiles."""

from __future__ import annotations

from typing import Any

from gamut.models import FieldType, TypeGamut
from gamut.systems.base import BaseProfiler


class ParquetProfiler(BaseProfiler):
    """Gamut profiler for Apache Parquet physical types."""

    system_name = "parquet"

    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        tn = type_name.strip().lower()

        # Boolean
        if tn == "boolean":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BOOLEAN,
                nullable=kwargs.get("nullable", True),
            )

        # Int types
        int_types = {
            "int32": (-(2**31), 2**31 - 1, 10),
            "int64": (-(2**63), 2**63 - 1, 19),
        }
        if tn in int_types:
            mn, mx, prec = int_types[tn]
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

        # Decimal (fixed_len_byte_array or binary backed)
        if tn.startswith("decimal"):
            # e.g. decimal(38,18)
            import re
            m = re.match(r"decimal\((\d+),\s*(\d+)\)", tn)
            if m:
                prec, scl = int(m.group(1)), int(m.group(2))
                max_val = float(10 ** (prec - scl) - 10 ** (-scl))
                return TypeGamut(
                    system=self.system_name, type_name=tn, field_type=FieldType.DECIMAL,
                    min_value=-max_val, max_value=max_val, precision=prec, scale=scl,
                    nullable=kwargs.get("nullable", True),
                )
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.DECIMAL,
                nullable=kwargs.get("nullable", True),
            )

        # Binary / string
        if tn == "binary":
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.BINARY,
                max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if tn in ("utf8", "string"):
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )

        # Logical types via kwarg
        logical = kwargs.get("logical_type", "")
        if logical:
            return self._resolve_logical(logical, **kwargs)

        # Int types with bit width
        bit_width = kwargs.get("bit_width")
        if bit_width:
            bw = int(bit_width)
            mn = -(2 ** (bw - 1))
            mx = 2 ** (bw - 1) - 1
            return TypeGamut(
                system=self.system_name, type_name=tn, field_type=FieldType.INTEGER,
                min_value=float(mn), max_value=float(mx), precision=bw, scale=0,
                nullable=kwargs.get("nullable", True),
            )

        # Fallback
        return TypeGamut(
            system=self.system_name, type_name=type_name, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )

    def _resolve_logical(self, logical: str, **kwargs: Any) -> TypeGamut:
        ll = logical.lower()
        if ll == "date":
            return TypeGamut(
                system=self.system_name, type_name=ll, field_type=FieldType.DATE,
                nullable=kwargs.get("nullable", True),
            )
        if "timestamp" in ll:
            is_tz = "utc" in ll or "tz" in kwargs.get("is_adjusted_to_utc", "").lower()
            return TypeGamut(
                system=self.system_name, type_name=ll, field_type=FieldType.TIMESTAMP,
                timezone_aware=is_tz,
                tz_precision=kwargs.get("tz_precision", 6),
                nullable=kwargs.get("nullable", True),
            )
        if ll == "string":
            return TypeGamut(
                system=self.system_name, type_name=ll, field_type=FieldType.STRING,
                charset="UTF-8", max_length=None,
                nullable=kwargs.get("nullable", True),
            )
        if ll == "enum":
            return TypeGamut(
                system=self.system_name, type_name=ll, field_type=FieldType.ENUM,
                nullable=kwargs.get("nullable", True),
            )
        return TypeGamut(
            system=self.system_name, type_name=logical, field_type=FieldType.UNKNOWN,
            nullable=kwargs.get("nullable", True),
        )
