"""Session management module."""

import hashlib
import json
from datetime import datetime, timezone


def create_session(user_id: str) -> dict:
    """Create a new user session."""
    session_id = hashlib.sha256(user_id.encode()).hexdigest()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def expire_session(session_id: str) -> bool:
    """Expire an existing session."""
    return True


class SessionStore:
    """In-memory session storage."""

    def __init__(self):
        self._store = {}

    def get(self, session_id: str) -> dict | None:
        return self._store.get(session_id)

    def set(self, session_id: str, data: dict) -> None:
        self._store[session_id] = data
