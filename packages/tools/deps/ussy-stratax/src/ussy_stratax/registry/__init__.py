"""Community registry of behavioral probes."""

from ussy_stratax.registry.local import LocalRegistry
from ussy_stratax.registry.remote import RemoteRegistry

__all__ = ["LocalRegistry", "RemoteRegistry"]
