"""Auto-generate behavioral probes from package analysis."""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional

from ussy_stratax.models import Probe


class ProbeGenerator:
    """Automatically generate behavioral probes by inspecting a package's API."""

    def __init__(self, depth: int = 1):
        self.depth = depth  # How deep to inspect nested objects

    def generate_for_package(self, package_name: str) -> List[Probe]:
        """Generate probes for all public functions in a package."""
        try:
            module = __import__(package_name)
        except ImportError:
            alt_name = package_name.replace("-", "_")
            try:
                module = __import__(alt_name)
            except ImportError:
                return []

        probes = []
        public_names = [
            name for name in dir(module) if not name.startswith("_")
        ]

        for name in public_names:
            obj = getattr(module, name)
            probes.extend(self._generate_for_object(package_name, name, obj, depth=0))

        return probes

    def generate_for_function(
        self, package_name: str, function_name: str
    ) -> List[Probe]:
        """Generate probes for a specific function."""
        try:
            module = __import__(package_name)
        except ImportError:
            alt_name = package_name.replace("-", "_")
            try:
                module = __import__(alt_name)
            except ImportError:
                return []

        obj = getattr(module, function_name, None)
        if obj is None:
            return []

        return self._generate_for_object(package_name, function_name, obj, depth=0)

    def _generate_for_object(
        self, package_name: str, attr_name: str, obj: Any, depth: int
    ) -> List[Probe]:
        """Generate probes for a single object."""
        probes = []

        if callable(obj):
            probes.extend(self._generate_callable_probes(package_name, attr_name, obj))
        elif isinstance(obj, type):
            # It's a class — generate probes for its methods
            if depth < self.depth:
                for method_name in dir(obj):
                    if method_name.startswith("_"):
                        continue
                    method = getattr(obj, method_name)
                    if callable(method):
                        full_name = f"{attr_name}.{method_name}"
                        probes.extend(
                            self._generate_callable_probes(
                                package_name, full_name, method
                            )
                        )

        return probes

    def _generate_callable_probes(
        self, package_name: str, func_name: str, func: Any
    ) -> List[Probe]:
        """Generate probes for a callable based on its signature."""
        probes = []

        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            # Can't introspect — generate a basic existence probe
            probes.append(
                Probe(
                    name=f"{func_name} exists and is callable",
                    package=package_name,
                    function=func_name,
                )
            )
            return probes

        params = list(sig.parameters.keys())

        # Probe: function accepts expected signature
        probes.append(
            Probe(
                name=f"{func_name} accepts signature ({', '.join(params)})",
                package=package_name,
                function=func_name,
                custom_assertion=f"callable with params: {params}",
            )
        )

        # If no parameters, we can try calling it
        if not params:
            probes.append(
                Probe(
                    name=f"{func_name} returns without error",
                    package=package_name,
                    function=func_name,
                )
            )

        # Generate a probe for each parameter with a default value
        for param_name, param in sig.parameters.items():
            if param.default is not inspect.Parameter.empty:
                probes.append(
                    Probe(
                        name=f"{func_name} works without {param_name} (has default)",
                        package=package_name,
                        function=func_name,
                        custom_assertion=f"optional param: {param_name}={param.default}",
                    )
                )

        # If there are type hints, generate type-based probes
        return_annotation = sig.return_annotation
        if return_annotation is not inspect.Parameter.empty:
            type_name = getattr(return_annotation, "__name__", str(return_annotation))
            probes.append(
                Probe(
                    name=f"{func_name} returns {type_name}",
                    package=package_name,
                    function=func_name,
                    returns_type=type_name,
                )
            )

        return probes

    @staticmethod
    def generate_from_types(package_name: str, type_info: Dict[str, Any]) -> List[Probe]:
        """Generate probes from manually provided type information.

        Useful when introspection isn't available (e.g., C extensions).
        """
        probes = []
        for func_name, info in type_info.items():
            params = info.get("params", [])
            returns = info.get("returns")

            # Signature probe
            probes.append(
                Probe(
                    name=f"{func_name} accepts signature ({', '.join(params)})",
                    package=package_name,
                    function=func_name,
                    custom_assertion=f"callable with params: {params}",
                )
            )

            # Return type probe
            if returns:
                probes.append(
                    Probe(
                        name=f"{func_name} returns {returns}",
                        package=package_name,
                        function=func_name,
                        returns_type=returns,
                    )
                )

        return probes
