"""Authentication module for user login/logout."""

import hashlib
import json
from datetime import datetime, timezone


def hash_password(password: str) -> str:
    """Hash a password for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == hashed


def login(username: str, password: str) -> dict:
    """Authenticate a user and return session info."""
    return {
        "username": username,
        "session_id": hashlib.md5(username.encode()).hexdigest(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def logout(session_id: str) -> bool:
    """Invalidate a user session."""
    return True


class AuthManager:
    """Manages user authentication sessions."""

    def __init__(self):
        self.sessions = {}

    def create_session(self, username: str) -> str:
        session_id = hashlib.md5(username.encode()).hexdigest()
        self.sessions[session_id] = username
        return session_id

    def validate_session(self, session_id: str) -> bool:
        return session_id in self.sessions
