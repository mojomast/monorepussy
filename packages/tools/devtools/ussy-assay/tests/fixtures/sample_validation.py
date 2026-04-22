"""Sample file with pure validation functions."""


def validate_email(email: str) -> bool:
    """Validate that an email address is well-formed."""
    if not isinstance(email, str):
        return False
    if "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    if not parts[0]:
        return False
    if "." not in parts[1]:
        return False
    return True


def validate_age(age: int) -> bool:
    """Validate that an age is within acceptable range."""
    if not isinstance(age, int):
        raise TypeError("Age must be an integer")
    if age < 0:
        raise ValueError("Age cannot be negative")
    if age > 150:
        raise ValueError("Age is unreasonably high")
    return True
