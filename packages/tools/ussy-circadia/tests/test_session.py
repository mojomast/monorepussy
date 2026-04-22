"""Tests for session module."""
import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from ussy_circadia.session import Session, SessionTracker


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSession:
    def test_is_active_when_active(self):
        now = datetime.now(timezone.utc)
        session = Session(start_time=now.isoformat())
        assert session.is_active is True

    def test_is_active_when_ended(self):
        now = datetime.now(timezone.utc)
        session = Session(
            start_time=now.isoformat(),
            end_time=now.isoformat(),
        )
        assert session.is_active is False

    def test_is_active_no_start(self):
        session = Session()
        assert session.is_active is False

    def test_duration_hours(self):
        now = datetime.now(timezone.utc)
        session = Session(start_time=now.isoformat())
        duration = session.duration_hours(now=now)
        assert duration >= 0

    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        session = Session(start_time=now.isoformat())
        d = session.to_dict()
        assert "start_time" in d

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        d = {"start_time": now.isoformat()}
        session = Session.from_dict(d)
        assert session.is_active is True

    def test_from_dict_roundtrip(self):
        now = datetime.now(timezone.utc)
        session = Session(start_time=now.isoformat())
        d = session.to_dict()
        restored = Session.from_dict(d)
        assert restored.start_time == session.start_time


class TestSessionTracker:
    def test_start_session(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        session = tracker.start_session()
        assert session is not None
        assert session.is_active is True

    def test_end_session(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        tracker.start_session()
        session = tracker.end_session()
        assert session is not None
        assert session.is_active is False

    def test_get_active_session(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        tracker.start_session()
        active = tracker.get_active_session()
        assert active is not None
        assert active.is_active is True

    def test_get_active_session_none(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        active = tracker.get_active_session()
        assert active is None

    def test_get_current_duration_hours(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        tracker.start_session()
        hours = tracker.get_current_duration_hours()
        assert hours >= 0

    def test_get_current_duration_no_session(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        hours = tracker.get_current_duration_hours()
        assert hours == 0.0

    def test_clear_sessions(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        tracker.start_session()
        tracker.clear_sessions()
        active = tracker.get_active_session()
        assert active is None

    def test_session_file_property(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        assert str(tracker.session_file) == state_file

    def test_end_session_without_start_raises(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        with pytest.raises(RuntimeError):
            tracker.end_session()

    def test_double_start_raises(self, tmp_dir):
        state_file = os.path.join(tmp_dir, "sessions.json")
        tracker = SessionTracker(session_file=state_file)
        tracker.start_session()
        with pytest.raises(RuntimeError):
            tracker.start_session()
