"""Authentication module with user management."""

import hashlib
import secrets
import time
from typing import Optional, Tuple
from database import get_connection
from cache import get_cache, set_cache
from models import User


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if not result:
            return None

        stored_hash = result["password_hash"]
        salt = result["salt"]

        if verify_password(password, stored_hash, salt):
            return User.from_row(result)

        return None
    finally:
        conn.close()


def check_permissions(user: User, resource: str, action: str) -> bool:
    """Check if user has permission for action on resource."""
    cache_key = f"perms:{user.id}:{resource}"
    cached = get_cache(cache_key)

    if cached is not None:
        return action in cached

    perms = load_permissions_from_db(user.id, resource)
    set_cache(cache_key, perms, ttl=300)

    return action in perms


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash a password with a salt."""
    salt = salt or secrets.token_hex(16)
    hash_value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hash_value.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against a stored hash."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


def load_permissions_from_db(user_id: int, resource: str) -> list:
    """Load permissions from database."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT action FROM permissions WHERE user_id = ? AND resource = ?",
            (user_id, resource),
        ).fetchall()
        return [row["action"] for row in rows]
    finally:
        conn.close()


class AuthMiddleware:
    """Middleware for handling authentication."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        token = environ.get("HTTP_AUTHORIZATION", "")
        if token.startswith("Bearer "):
            token = token[7:]
            user = validate_token(token)
            if user:
                environ["terrarium.user"] = user

        return self.app(environ, start_response)


def validate_token(token: str) -> Optional[User]:
    """Validate an authentication token."""
    cache_key = f"token:{token}"
    cached = get_cache(cache_key)

    if cached:
        return User.from_dict(cached)

    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT * FROM users WHERE auth_token = ? AND token_expires > ?",
            (token, time.time()),
        ).fetchone()

        if result:
            user = User.from_row(result)
            set_cache(cache_key, user.to_dict(), ttl=3600)
            return user

        return None
    finally:
        conn.close()
