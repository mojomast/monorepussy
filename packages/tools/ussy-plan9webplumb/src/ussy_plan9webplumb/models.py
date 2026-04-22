"""Data models for Plan9-WebPlumb messages, handlers, and rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of messages that can be sent through the plumber."""
    TEXT = "text"
    URL = "url"
    DOM_ELEMENT = "dom_element"
    CLIPBOARD = "clipboard"


class HandlerAction(str, Enum):
    """Action types for handlers."""
    EXEC = "exec"
    PIPE = "pipe"
    NOTIFY = "notify"


@dataclass
class PlumbMessage:
    """A message sent through the plumber pipeline.

    Represents data piped from the browser extension to local handlers.
    Modeled after Plan 9's plumb message format with src, dst, type, data, etc.
    """
    src: str = "browser"
    dst: str = ""
    msg_type: MessageType = MessageType.TEXT
    data: str = ""
    url: str = ""
    title: str = ""
    tab_id: int = -1
    timestamp: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def matches(self, pattern: str) -> bool:
        """Check if this message matches a regex pattern against data or url."""
        try:
            compiled = re.compile(pattern)
            return bool(
                compiled.search(self.data) or compiled.search(self.url)
            )
        except re.error:
            return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize message to a dictionary."""
        return {
            "id": self.id,
            "src": self.src,
            "dst": self.dst,
            "msg_type": self.msg_type.value,
            "data": self.data,
            "url": self.url,
            "title": self.title,
            "tab_id": self.tab_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlumbMessage:
        """Deserialize a message from a dictionary."""
        msg_type = d.get("msg_type", "text")
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        return cls(
            id=d.get("id", ""),
            src=d.get("src", "browser"),
            dst=d.get("dst", ""),
            msg_type=msg_type,
            data=d.get("data", ""),
            url=d.get("url", ""),
            title=d.get("title", ""),
            tab_id=d.get("tab_id", -1),
            timestamp=d.get("timestamp", ""),
        )


@dataclass
class HandlerRule:
    """A pattern-matching rule that determines which handler fires for a message.

    Each rule has a regex pattern matched against message data/URL,
    and specifies which handler to invoke on match.
    """
    name: str = ""
    pattern: str = ""
    handler: str = ""
    msg_type: str = ""
    priority: int = 0
    enabled: bool = True

    def matches(self, message: PlumbMessage) -> bool:
        """Check if a message matches this rule."""
        if not self.enabled:
            return False
        if self.msg_type and self.msg_type != message.msg_type.value:
            return False
        if not self.pattern:
            return True  # empty pattern matches everything
        return message.matches(self.pattern)

    def to_dict(self) -> dict[str, Any]:
        """Serialize rule to a dictionary."""
        return {
            "name": self.name,
            "pattern": self.pattern,
            "handler": self.handler,
            "msg_type": self.msg_type,
            "priority": self.priority,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> HandlerRule:
        """Deserialize a rule from a dictionary."""
        return cls(
            name=d.get("name", ""),
            pattern=d.get("pattern", ""),
            handler=d.get("handler", ""),
            msg_type=d.get("msg_type", ""),
            priority=d.get("priority", 0),
            enabled=d.get("enabled", True),
        )


@dataclass
class Handler:
    """A local handler that can process plumb messages.

    Handlers are shell scripts or applications that are executed
    when a matching rule fires.
    """
    name: str = ""
    command: str = ""
    action: HandlerAction = HandlerAction.EXEC
    description: str = ""
    working_dir: str = ""
    timeout: float = 30.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = HandlerAction(self.action)

    def to_dict(self) -> dict[str, Any]:
        """Serialize handler to a dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "action": self.action.value,
            "description": self.description,
            "working_dir": self.working_dir,
            "timeout": self.timeout,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Handler:
        """Deserialize a handler from a dictionary."""
        return cls(
            name=d.get("name", ""),
            command=d.get("command", ""),
            action=d.get("action", "exec"),
            description=d.get("description", ""),
            working_dir=d.get("working_dir", ""),
            timeout=d.get("timeout", 30.0),
            enabled=d.get("enabled", True),
        )


@dataclass
class DispatchResult:
    """Result of dispatching a message to a handler."""
    handler_name: str = ""
    rule_name: str = ""
    success: bool = False
    output: str = ""
    error: str = ""
    timestamp: str = ""
    message_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize dispatch result to a dictionary."""
        return {
            "handler_name": self.handler_name,
            "rule_name": self.rule_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
        }
