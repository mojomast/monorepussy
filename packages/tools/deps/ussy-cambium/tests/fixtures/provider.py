"""Sample provider module for testing."""


class AuthClient:
    """Client for authentication services - extended version."""

    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def authenticate(self, username: str, password: str, mfa_code: str = "") -> dict:
        """Authenticate a user with optional MFA."""
        assert username
        assert password
        return {"token": "abc123", "expires": 3600}

    def refresh_token(self, token: str) -> dict:
        """Refresh an authentication token."""
        assert token
        return {"token": "def456", "expires": 3600}

    def validate_token(self, token: str) -> bool:
        """Validate a token."""
        assert token
        return True


class RoleManager:
    """Manage role-based access control."""

    def assign_role(self, user_id: int, role: str) -> dict:
        """Assign a role to a user."""
        assert user_id
        assert role
        return {"user_id": user_id, "role": role}


def get_server_info() -> dict:
    """Get server information."""
    return {"version": "2.0"}
