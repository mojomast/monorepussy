"""Base class for system-specific gamut profilers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ussy_gamut.models import FieldProfile, StageProfile, TypeGamut, FieldType


class BaseProfiler(ABC):
    """Abstract base for system-specific gamut profilers."""

    system_name: str = "unknown"

    @abstractmethod
    def resolve_type(self, type_name: str, **kwargs: Any) -> TypeGamut:
        """Resolve a native type name to a TypeGamut."""
        ...

    def profile_stage(
        self, stage_name: str, schema: dict[str, dict[str, Any]]
    ) -> StageProfile:
        """Build a StageProfile from a schema dict.

        schema format: { "field_name": {"type": "TYPE_NAME", ...}, ... }
        """
        fields: list[FieldProfile] = []
        for fname, fmeta in schema.items():
            type_name = fmeta.get("type", "unknown")
            extra = {k: v for k, v in fmeta.items() if k != "type"}
            gamut = self.resolve_type(type_name, **extra)
            fields.append(
                FieldProfile(
                    name=fname, gamut=gamut, source_type_raw=type_name
                )
            )
        return StageProfile(name=stage_name, system=self.system_name, fields=fields)

    def _safe_float(self, val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, val: Any) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
