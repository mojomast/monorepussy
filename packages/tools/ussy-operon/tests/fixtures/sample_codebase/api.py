"""API routes module."""

from auth import login, logout
from session import create_session, SessionStore


def handle_login(request: dict) -> dict:
    """Handle login API request."""
    username = request.get("username")
    password = request.get("password")
    result = login(username, password)
    session = create_session(result["session_id"])
    return {"status": "ok", "session": session}


def handle_logout(session_id: str) -> dict:
    """Handle logout API request."""
    logout(session_id)
    return {"status": "ok"}
