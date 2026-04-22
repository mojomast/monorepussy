"""Adapter auto-discovery and loading for external ussyverse data sources.

Each adapter module in this package is auto-discovered and loaded.
Adapters should subclass :class:`~terrarium.adapters.base.BaseAdapter`
and define a ``name`` class attribute.

Usage::

    from terrarium.adapters import load_adapters, merge_health_states

    adapters = load_adapters(fatigue_data="fatigue.json")
    merged = merge_health_states(adapters)
"""

import importlib
import os
from typing import Dict, List, Optional

from .base import BaseAdapter
from ..ecosystem.model import OrganismHealthState


def _discover_adapter_classes() -> List[type[BaseAdapter]]:
    """Discover all BaseAdapter subclasses in this package."""
    classes: List[type[BaseAdapter]] = []
    package_dir = os.path.dirname(__file__)

    for filename in os.listdir(package_dir):
        if filename.startswith("_") or not filename.endswith(".py"):
            continue
        module_name = f"terrarium.adapters.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseAdapter)
                and attr is not BaseAdapter
                and hasattr(attr, "name")
                and attr.name
            ):
                classes.append(attr)

    return classes


# Cache discovered classes
_ADAPTER_CLASSES: Optional[List[type[BaseAdapter]]] = None


def _get_adapter_classes() -> List[type[BaseAdapter]]:
    global _ADAPTER_CLASSES
    if _ADAPTER_CLASSES is None:
        _ADAPTER_CLASSES = _discover_adapter_classes()
    return _ADAPTER_CLASSES


def load_adapters(
    fatigue_data: Optional[str] = None,
    endemic_data: Optional[str] = None,
    sentinel_data: Optional[str] = None,
) -> List[BaseAdapter]:
    """Load all available adapters based on provided data paths.

    Args:
        fatigue_data: Path to fatigueussy JSON output.
        endemic_data: Path to endemicussy JSON output.
        sentinel_data: Path to sentinelussy JSON output.

    Returns:
        List of initialized adapters with data available.
    """
    adapters: List[BaseAdapter] = []
    data_map = {
        "fatigue": fatigue_data,
        "endemic": endemic_data,
        "sentinel": sentinel_data,
    }

    for cls in _get_adapter_classes():
        data_path = data_map.get(cls.name)
        adapter = cls(data_path=data_path)
        if adapter.is_available():
            adapters.append(adapter)

    return adapters


def merge_health_states(adapters: List[BaseAdapter]) -> Dict[str, OrganismHealthState]:
    """Merge health states from all adapters into a single mapping.

    Args:
        adapters: List of loaded adapters.

    Returns:
        Dict mapping file path to merged OrganismHealthState.
    """
    merged: Dict[str, OrganismHealthState] = {}

    for adapter in adapters:
        states = adapter.load()
        for path, state in states.items():
            if path not in merged:
                merged[path] = state
            else:
                existing = merged[path]
                merged[path] = OrganismHealthState(
                    path=path,
                    vitality=min(existing.vitality, state.vitality),
                    crack_intensity=max(
                        existing.crack_intensity, state.crack_intensity
                    ),
                    infection_state=state.infection_state
                    if state.infection_state != "S"
                    else existing.infection_state,
                    anomaly_active=existing.anomaly_active or state.anomaly_active,
                )

    return merged
