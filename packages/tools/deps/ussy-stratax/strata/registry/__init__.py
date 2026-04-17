"""Community registry of behavioral probes."""

from strata.registry.local import LocalRegistry
from strata.registry.remote import RemoteRegistry

__all__ = ["LocalRegistry", "RemoteRegistry"]
