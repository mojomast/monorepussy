"""Authentication module — intentionally complex for testing."""


class AuthError(Exception):
    """Authentication error."""
    pass


def authenticate(username: str, password: str, token: str = "") -> bool:
    """Authenticate a user with username/password or token.

    This function has high cyclomatic complexity for testing.
    """
    if not username:
        raise AuthError("Username required")

    if not password and not token:
        raise AuthError("Password or token required")

    if token:
        if len(token) < 10:
            raise AuthError("Token too short")
        if token.startswith("test_"):
            return True
        if token.startswith("admin_"):
            return True
        return False

    if len(password) < 8:
        raise AuthError("Password too short")

    if username == "admin" and password == "admin123":
        return True

    if username.startswith("user_"):
        if password.isdigit():
            return True
        elif password.isalpha():
            return False
        else:
            return True

    return False


def check_permission(user: str, resource: str, action: str) -> bool:
    """Check if a user has permission for an action on a resource."""
    if action == "read":
        return True
    elif action == "write":
        if user == "admin":
            return True
        elif user.startswith("user_"):
            return resource.startswith("user_")
        else:
            return False
    elif action == "delete":
        if user == "admin":
            return True
        return False
    else:
        return False


# DEPRECATED: Use check_permission instead
def is_admin(user: str) -> bool:
    """Check if user is admin. Deprecated."""
    return user == "admin"
