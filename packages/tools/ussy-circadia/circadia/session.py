"""Session tracking for Circadia — tracks coding session start/end times."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SESSION_FILE = ".circadia_session.json"


@dataclass
class Session:
    """Represents a coding session."""

    start_time: str = ""  # ISO format UTC datetime
    end_time: str = ""    # ISO format UTC datetime, empty if active

    @property
    def start_dt(self) -> Optional[datetime]:
        """Parse start_time string to datetime."""
        if not self.start_time:
            return None
        return datetime.fromisoformat(self.start_time)

    @property
    def end_dt(self) -> Optional[datetime]:
        """Parse end_time string to datetime."""
        if not self.end_time:
            return None
        return datetime.fromisoformat(self.end_time)

    @property
    def is_active(self) -> bool:
        """Whether the session is currently active."""
        return bool(self.start_time) and not self.end_time

    def duration_hours(self, now: Optional[datetime] = None) -> float:
        """Calculate session duration in hours.

        Args:
            now: Current UTC datetime. If None, uses current time.

        Returns:
            Duration in hours (0 if session not active).
        """
        if not self.start_time:
            return 0.0
        start = self.start_dt
        if start is None:
            return 0.0
        end = self.end_dt or (now or datetime.now(timezone.utc))
        delta = end - start
        return max(0.0, delta.total_seconds() / 3600.0)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dictionary."""
        return cls(
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
        )


class SessionTracker:
    """Tracks coding sessions with start/end times.

    Session data is stored in a JSON file in the project root or home directory.
    """

    def __init__(self, session_file: Optional[str] = None) -> None:
        """Initialize session tracker.

        Args:
            session_file: Path to session file. Defaults to .circadia_session.json
                          in current directory.
        """
        if session_file:
            self._session_file = Path(session_file)
        else:
            self._session_file = Path.cwd() / SESSION_FILE

    @property
    def session_file(self) -> Path:
        """Path to session file."""
        return self._session_file

    def _load_sessions(self) -> list[Session]:
        """Load sessions from file."""
        if not self._session_file.exists():
            return []
        try:
            with open(self._session_file, "r") as f:
                data = json.load(f)
            return [Session.from_dict(s) for s in data.get("sessions", [])]
        except (json.JSONDecodeError, OSError):
            return []

    def _save_sessions(self, sessions: list[Session]) -> None:
        """Save sessions to file."""
        self._session_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"sessions": [s.to_dict() for s in sessions]}
        with open(self._session_file, "w") as f:
            json.dump(data, f, indent=2)

    def start_session(self, dt: Optional[datetime] = None) -> Session:
        """Start a new coding session.

        Args:
            dt: Start time in UTC. If None, uses current time.

        Returns:
            The new Session.

        Raises:
            RuntimeError: If a session is already active.
        """
        sessions = self._load_sessions()
        active = [s for s in sessions if s.is_active]
        if active:
            raise RuntimeError(
                f"Session already active since {active[0].start_time}. "
                "End it before starting a new one."
            )

        start = dt or datetime.now(timezone.utc)
        session = Session(start_time=start.isoformat())
        sessions.append("")
        sessions[-1] = session
        self._save_sessions(sessions)
        return session

    def end_session(self, dt: Optional[datetime] = None) -> Session:
        """End the current active session.

        Args:
            dt: End time in UTC. If None, uses current time.

        Returns:
            The ended Session.

        Raises:
            RuntimeError: If no active session exists.
        """
        sessions = self._load_sessions()
        active = [s for s in sessions if s.is_active]
        if not active:
            raise RuntimeError("No active session to end.")

        end = dt or datetime.now(timezone.utc)
        session = active[0]
        session.end_time = end.isoformat()
        self._save_sessions(sessions)
        return session

    def get_active_session(self) -> Optional[Session]:
        """Get the current active session, if any."""
        sessions = self._load_sessions()
        active = [s for s in sessions if s.is_active]
        return active[0] if active else None

    def get_current_duration_hours(self) -> float:
        """Get the duration of the current active session in hours.

        Returns 0.0 if no session is active.
        """
        session = self.get_active_session()
        if session is None:
            return 0.0
        return session.duration_hours()

    def clear_sessions(self) -> None:
        """Clear all session data."""
        if self._session_file.exists():
            self._session_file.unlink()
