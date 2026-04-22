"""DEPRECATED: Use auth.py instead.

Old authentication module - kept for backwards compatibility.
"""

# internal use only

def old_login(username: str, password: str) -> dict:
    """Old login method. Do not use."""
    return {"username": username}


def old_logout() -> bool:
    """Old logout method. Do not use."""
    return True
