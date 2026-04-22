"""Handler registry and dispatch for Plan9-WebPlumb.

Loads handler configurations, matches incoming messages against rules,
and executes the appropriate handler commands.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from typing import Optional

from ussy_plan9webplumb.config import Config
from ussy_plan9webplumb.models import DispatchResult, Handler, HandlerRule, PlumbMessage

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Registry of handlers and rules, responsible for matching and dispatching."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self._handlers: dict[str, Handler] = {}
        self._rules: list[HandlerRule] = []
        self._dispatch_history: list[DispatchResult] = []

    def load(self) -> None:
        """Load all handlers and rules from config."""
        self._handlers.clear()
        self._rules.clear()
        for handler in self.config.load_handlers():
            self._handlers[handler.name] = handler
        self._rules = self.config.load_rules()
        # Sort by priority (higher = more important)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(
            "Loaded %d handlers and %d rules",
            len(self._handlers), len(self._rules),
        )

    def reload(self) -> None:
        """Reload handlers and rules from config (hot-reload)."""
        self.load()

    @property
    def handlers(self) -> dict[str, Handler]:
        """Access registered handlers."""
        return dict(self._handlers)

    @property
    def rules(self) -> list[HandlerRule]:
        """Access registered rules."""
        return list(self._rules)

    @property
    def dispatch_history(self) -> list[DispatchResult]:
        """Access dispatch history."""
        return list(self._dispatch_history)

    def add_handler(self, handler: Handler) -> None:
        """Register a handler and persist it."""
        self._handlers[handler.name] = handler
        self.config.save_handler(handler)

    def remove_handler(self, name: str) -> bool:
        """Remove a handler by name."""
        if name in self._handlers:
            del self._handlers[name]
            return self.config.remove_handler(name)
        return self.config.remove_handler(name)

    def add_rule(self, rule: HandlerRule) -> None:
        """Register a rule and persist it."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self.config.save_rule(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        self._rules = [r for r in self._rules if r.name != name]
        return self.config.remove_rule(name)

    def find_matching_rules(self, message: PlumbMessage) -> list[HandlerRule]:
        """Find all rules that match a given message, sorted by priority."""
        return [rule for rule in self._rules if rule.matches(message)]

    def find_handler(self, name: str) -> Optional[Handler]:
        """Find a handler by name."""
        return self._handlers.get(name)

    def test_match(self, message: PlumbMessage) -> list[tuple[HandlerRule, Optional[Handler]]]:
        """Test which rules and handlers would fire for a message (dry run)."""
        results: list[tuple[HandlerRule, Optional[Handler]]] = []
        for rule in self.find_matching_rules(message):
            handler = self._handlers.get(rule.handler)
            results.append((rule, handler))
        return results

    async def dispatch(self, message: PlumbMessage) -> list[DispatchResult]:
        """Dispatch a message to all matching handlers.

        Returns a list of dispatch results, one per matched rule.
        """
        matching = self.find_matching_rules(message)
        if not matching:
            logger.debug("No matching rules for message %s", message.id)
            return []

        results: list[DispatchResult] = []
        for rule in matching:
            handler = self._handlers.get(rule.handler)
            if not handler:
                logger.warning("Rule '%s' references unknown handler '%s'", rule.name, rule.handler)
                result = DispatchResult(
                    handler_name=rule.handler,
                    rule_name=rule.name,
                    success=False,
                    error=f"Handler '{rule.handler}' not found",
                    message_id=message.id,
                )
                self._dispatch_history.append(result)
                results.append(result)
                continue

            if not handler.enabled:
                logger.debug("Handler '%s' is disabled, skipping", handler.name)
                continue

            result = await self._execute_handler(handler, message, rule)
            self._dispatch_history.append(result)
            results.append(result)

        return results

    async def _execute_handler(
        self, handler: Handler, message: PlumbMessage, rule: HandlerRule
    ) -> DispatchResult:
        """Execute a handler command for a message."""
        # Build command with message data as environment-like substitution
        command = handler.command
        command = command.replace("{data}", message.data)
        command = command.replace("{url}", message.url)
        command = command.replace("{title}", message.title)
        command = command.replace("{src}", message.src)
        command = command.replace("{type}", message.msg_type.value)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=handler.working_dir or None,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=handler.timeout
            )
            success = proc.returncode == 0
            output = stdout.decode("utf-8", errors="replace").strip()
            error = stderr.decode("utf-8", errors="replace").strip()

            if success:
                logger.info(
                    "Handler '%s' executed successfully for message %s",
                    handler.name, message.id,
                )
            else:
                logger.warning(
                    "Handler '%s' exited with code %d: %s",
                    handler.name, proc.returncode, error,
                )

            return DispatchResult(
                handler_name=handler.name,
                rule_name=rule.name,
                success=success,
                output=output,
                error=error,
                message_id=message.id,
            )

        except asyncio.TimeoutError:
            logger.error("Handler '%s' timed out after %.1fs", handler.name, handler.timeout)
            return DispatchResult(
                handler_name=handler.name,
                rule_name=rule.name,
                success=False,
                error=f"Timeout after {handler.timeout}s",
                message_id=message.id,
            )
        except Exception as exc:
            logger.error("Handler '%s' failed: %s", handler.name, exc)
            return DispatchResult(
                handler_name=handler.name,
                rule_name=rule.name,
                success=False,
                error=str(exc),
                message_id=message.id,
            )
