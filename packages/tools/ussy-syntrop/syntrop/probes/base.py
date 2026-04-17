"""Base class for semantic probes."""

from __future__ import annotations

import abc
from typing import Any, Callable

from syntrop.ir import ProbeResult


class BaseProbe(abc.ABC):
    """Base class for all semantic probes.

    A semantic probe applies a specific semantic twist to Python code
    and checks whether the behavior diverges from normal execution.
    """

    name: str = "base"
    description: str = "Base probe class"
    twist_type: str = "semantic"

    @abc.abstractmethod
    def transform_source(self, source: str) -> str:
        """Transform the source code to apply the semantic twist.

        Args:
            source: Original Python source code.

        Returns:
            Transformed source code with the semantic twist applied.
        """
        ...

    @abc.abstractmethod
    def check_divergence(
        self, original_result: Any, probed_result: Any, metadata: dict[str, Any] | None = None
    ) -> ProbeResult:
        """Check whether the probed result diverges from the original.

        Args:
            original_result: Result from executing the original code.
            probed_result: Result from executing the probed code.
            metadata: Optional metadata about the execution.

        Returns:
            A ProbeResult describing any divergence.
        """
        ...

    def run(self, source: str, func_name: str = "main", *args: Any, **kwargs: Any) -> ProbeResult:
        """Run the probe: transform source, execute both versions, compare.

        Args:
            source: Original Python source code.
            func_name: Name of the function to call.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            A ProbeResult describing any divergence.
        """
        # Execute original
        original_result, original_error = self._execute_source(source, func_name, args, kwargs)

        # Transform and execute
        probed_source = self.transform_source(source)
        probed_result, probed_error = self._execute_source(probed_source, func_name, args, kwargs)

        # Check divergence
        if original_error and probed_error:
            return ProbeResult(
                probe_name=self.name,
                original_output=None,
                probed_output=None,
                diverged=False,
                divergence_type="both-error",
                explanation="Both original and probed code raised errors",
                severity="info",
                metadata={
                    "original_error": str(original_error),
                    "probed_error": str(probed_error),
                },
            )

        if original_error:
            return ProbeResult(
                probe_name=self.name,
                original_output=None,
                probed_output=probed_result,
                diverged=True,
                divergence_type="original-error",
                explanation="Original code raised an error but probed code did not",
                severity="warning",
                metadata={"original_error": str(original_error)},
            )

        if probed_error:
            return ProbeResult(
                probe_name=self.name,
                original_output=original_result,
                probed_output=None,
                diverged=True,
                divergence_type="probe-error",
                explanation=f"Probed code raised error: {probed_error}",
                severity="warning",
                metadata={"probed_error": str(probed_error)},
            )

        return self.check_divergence(original_result, probed_result)

    @staticmethod
    def _execute_source(
        source: str, func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[Any, Exception | None]:
        """Execute a source string and call a function in it.

        Returns:
            Tuple of (result, error). If error occurred, result is None.
        """
        namespace: dict[str, Any] = {}
        try:
            exec(compile(source, "<probe>", "exec"), namespace)
            func = namespace.get(func_name)
            if func is None:
                return None, NameError(f"Function '{func_name}' not found in source")
            result = func(*args, **kwargs)
            return result, None
        except Exception as exc:
            return None, exc
