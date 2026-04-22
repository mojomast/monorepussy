"""Sample consumer module for testing."""


class AuthClient:
    """Client for authentication services."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def authenticate(self, username: str, password: str) -> dict:
        """Authenticate a user."""
        assert username
        assert password
        return {"token": "abc123"}

    def refresh_token(self, token: str) -> dict:
        """Refresh an authentication token."""
        assert token
        return {"token": "def456"}

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        assert token
        return True


class UserManager:
    """Manage user accounts."""

    def create_user(self, username: str, email: str) -> dict:
        """Create a new user."""
        assert username
        assert email
        return {"id": 1, "username": username}

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        assert user_id
        return True


def get_auth_status() -> str:
    """Get current authentication status."""
    return "authenticated"
