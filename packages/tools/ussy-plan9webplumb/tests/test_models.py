"""Tests for Plan9-WebPlumb data models."""

import re
from datetime import datetime, timezone

import pytest

from ussy_plan9webplumb.models import (
    DispatchResult,
    Handler,
    HandlerAction,
    HandlerRule,
    MessageType,
    PlumbMessage,
)


# ---- PlumbMessage ----

class TestPlumbMessage:
    """Tests for PlumbMessage dataclass."""

    def test_default_creation(self):
        msg = PlumbMessage()
        assert msg.src == "browser"
        assert msg.dst == ""
        assert msg.msg_type == MessageType.TEXT
        assert msg.data == ""
        assert msg.url == ""
        assert msg.id != ""
        assert msg.timestamp != ""

    def test_creation_with_data(self):
        msg = PlumbMessage(data="hello world", url="https://example.com")
        assert msg.data == "hello world"
        assert msg.url == "https://example.com"

    def test_auto_generated_id(self):
        msg1 = PlumbMessage()
        msg2 = PlumbMessage()
        assert msg1.id != msg2.id

    def test_auto_generated_timestamp(self):
        before = datetime.now(timezone.utc).isoformat()
        msg = PlumbMessage()
        after = datetime.now(timezone.utc).isoformat()
        assert before <= msg.timestamp <= after

    def test_preserves_provided_id(self):
        msg = PlumbMessage(id="custom-id-123")
        assert msg.id == "custom-id-123"

    def test_preserves_provided_timestamp(self):
        ts = "2025-01-01T00:00:00+00:00"
        msg = PlumbMessage(timestamp=ts)
        assert msg.timestamp == ts

    def test_matches_pattern_on_data(self):
        msg = PlumbMessage(data="https://github.com/org/repo/issues/42")
        assert msg.matches(r"github\.com/.+/issues/\d+")

    def test_matches_pattern_on_url(self):
        msg = PlumbMessage(url="https://github.com/org/repo/issues/42")
        assert msg.matches(r"github\.com/.+/issues/\d+")

    def test_no_match(self):
        msg = PlumbMessage(data="hello world")
        assert not msg.matches(r"github\.com")

    def test_matches_invalid_regex(self):
        msg = PlumbMessage(data="test")
        assert not msg.matches(r"[invalid")

    def test_to_dict(self):
        msg = PlumbMessage(data="test data", url="https://example.com", msg_type=MessageType.URL)
        d = msg.to_dict()
        assert d["data"] == "test data"
        assert d["url"] == "https://example.com"
        assert d["msg_type"] == "url"
        assert "id" in d
        assert "timestamp" in d

    def test_from_dict(self):
        d = {
            "id": "test-id",
            "src": "browser",
            "dst": "",
            "msg_type": "url",
            "data": "test",
            "url": "https://example.com",
            "title": "Example",
            "tab_id": 5,
            "timestamp": "2025-01-01T00:00:00+00:00",
        }
        msg = PlumbMessage.from_dict(d)
        assert msg.id == "test-id"
        assert msg.msg_type == MessageType.URL
        assert msg.data == "test"
        assert msg.tab_id == 5

    def test_from_dict_defaults(self):
        msg = PlumbMessage.from_dict({})
        assert msg.src == "browser"
        assert msg.msg_type == MessageType.TEXT

    def test_roundtrip_dict(self):
        msg = PlumbMessage(data="roundtrip", url="https://rt.com", title="RT")
        d = msg.to_dict()
        msg2 = PlumbMessage.from_dict(d)
        assert msg2.data == msg.data
        assert msg2.url == msg.url
        assert msg2.title == msg.title
        assert msg2.id == msg.id

    def test_message_type_enum(self):
        assert MessageType.TEXT.value == "text"
        assert MessageType.URL.value == "url"
        assert MessageType.DOM_ELEMENT.value == "dom_element"
        assert MessageType.CLIPBOARD.value == "clipboard"


# ---- HandlerRule ----

class TestHandlerRule:
    """Tests for HandlerRule dataclass."""

    def test_default_creation(self):
        rule = HandlerRule()
        assert rule.name == ""
        assert rule.pattern == ""
        assert rule.handler == ""
        assert rule.priority == 0
        assert rule.enabled is True

    def test_matches_text_message(self):
        rule = HandlerRule(pattern=r"github\.com", handler="todo")
        msg = PlumbMessage(data="Check https://github.com/org/repo/issues/1")
        assert rule.matches(msg)

    def test_matches_url_message(self):
        rule = HandlerRule(pattern=r"github\.com/.+/issues/\d+", handler="todo")
        msg = PlumbMessage(url="https://github.com/org/repo/issues/42")
        assert rule.matches(msg)

    def test_no_match(self):
        rule = HandlerRule(pattern=r"github\.com", handler="todo")
        msg = PlumbMessage(data="hello world")
        assert not rule.matches(msg)

    def test_disabled_rule(self):
        rule = HandlerRule(pattern=r".*", handler="todo", enabled=False)
        msg = PlumbMessage(data="anything")
        assert not rule.matches(msg)

    def test_msg_type_filter(self):
        rule = HandlerRule(pattern=r".*", handler="todo", msg_type="url")
        text_msg = PlumbMessage(data="test", msg_type=MessageType.TEXT)
        url_msg = PlumbMessage(url="https://example.com", msg_type=MessageType.URL)
        assert not rule.matches(text_msg)
        assert rule.matches(url_msg)

    def test_empty_pattern_matches_all(self):
        rule = HandlerRule(pattern="", handler="catchall")
        msg = PlumbMessage(data="anything at all")
        assert rule.matches(msg)

    def test_to_dict(self):
        rule = HandlerRule(name="test_rule", pattern=r"test", handler="handler1", priority=5)
        d = rule.to_dict()
        assert d["name"] == "test_rule"
        assert d["pattern"] == r"test"
        assert d["handler"] == "handler1"
        assert d["priority"] == 5

    def test_from_dict(self):
        d = {"name": "rule1", "pattern": r"test", "handler": "h1", "priority": 3}
        rule = HandlerRule.from_dict(d)
        assert rule.name == "rule1"
        assert rule.priority == 3

    def test_from_dict_defaults(self):
        rule = HandlerRule.from_dict({})
        assert rule.name == ""
        assert rule.enabled is True


# ---- Handler ----

class TestHandler:
    """Tests for Handler dataclass."""

    def test_default_creation(self):
        h = Handler()
        assert h.name == ""
        assert h.command == ""
        assert h.action == HandlerAction.EXEC
        assert h.timeout == 30.0
        assert h.enabled is True

    def test_creation_with_params(self):
        h = Handler(name="todo", command="echo test", description="A handler")
        assert h.name == "todo"
        assert h.command == "echo test"

    def test_action_from_string(self):
        h = Handler(action="pipe")
        assert h.action == HandlerAction.PIPE

    def test_to_dict(self):
        h = Handler(name="todo", command="echo test", action=HandlerAction.EXEC, timeout=60.0)
        d = h.to_dict()
        assert d["name"] == "todo"
        assert d["command"] == "echo test"
        assert d["action"] == "exec"
        assert d["timeout"] == 60.0

    def test_from_dict(self):
        d = {"name": "todo", "command": "echo test", "action": "exec"}
        h = Handler.from_dict(d)
        assert h.name == "todo"
        assert h.action == HandlerAction.EXEC

    def test_from_dict_defaults(self):
        h = Handler.from_dict({})
        assert h.action == HandlerAction.EXEC
        assert h.timeout == 30.0

    def test_handler_action_enum(self):
        assert HandlerAction.EXEC.value == "exec"
        assert HandlerAction.PIPE.value == "pipe"
        assert HandlerAction.NOTIFY.value == "notify"


# ---- DispatchResult ----

class TestDispatchResult:
    """Tests for DispatchResult dataclass."""

    def test_default_creation(self):
        r = DispatchResult()
        assert r.handler_name == ""
        assert r.success is False
        assert r.timestamp != ""

    def test_auto_timestamp(self):
        before = datetime.now(timezone.utc).isoformat()
        r = DispatchResult()
        after = datetime.now(timezone.utc).isoformat()
        assert before <= r.timestamp <= after

    def test_preserves_provided_timestamp(self):
        ts = "2025-06-01T00:00:00+00:00"
        r = DispatchResult(timestamp=ts)
        assert r.timestamp == ts

    def test_to_dict(self):
        r = DispatchResult(handler_name="todo", success=True, output="OK")
        d = r.to_dict()
        assert d["handler_name"] == "todo"
        assert d["success"] is True
        assert d["output"] == "OK"
