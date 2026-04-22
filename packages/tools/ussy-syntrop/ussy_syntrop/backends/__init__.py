"""Esolang backend compilers for Syntrop.

Each backend compiles the Syntrop IR into a different esoteric language,
imposing its own computational model and potentially revealing different
classes of semantic bugs.
"""

from ussy_syntrop.backends.intercal import IntercalBackend

BACKEND_REGISTRY: dict[str, type] = {
    "intercal": IntercalBackend,
}

__all__ = [
    "BACKEND_REGISTRY",
    "IntercalBackend",
]
