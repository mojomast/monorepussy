"""Base adapter interface for external ussyverse data sources."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from ..ecosystem.model import OrganismHealthState


class BaseAdapter(ABC):
    """Abstract base class for health data adapters."""

    name: str = ""

    def __init__(self, data_path: Optional[str] = None) -> None:
        """Initialize the adapter with an optional data file path."""
        self.data_path = data_path

    @abstractmethod
    def load(self) -> Dict[str, OrganismHealthState]:
        """Load health state data and return a mapping of path to state.

        Returns:
            Dict mapping file path to OrganismHealthState.
        """
        ...

    def is_available(self) -> bool:
        """Check if this adapter has data available to load.

        Returns True if the adapter is in STUB_MODE (always available)
        or if a data_path has been configured.
        """
        return getattr(self, "STUB_MODE", False) or self.data_path is not None
