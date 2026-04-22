"""SHA-256 content hashing for drift detection."""

import hashlib


def content_hash(data: bytes) -> str:
    """Compute SHA-256 hash of byte content.

    Args:
        data: Raw bytes to hash.

    Returns:
        Hex-encoded SHA-256 digest string.
    """
    return hashlib.sha256(data).hexdigest()


def file_hash(path: str) -> str:
    """Compute SHA-256 hash of a file's contents.

    Args:
        path: Filesystem path to the file.

    Returns:
        Hex-encoded SHA-256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    with open(path, "rb") as f:
        return content_hash(f.read())


def string_hash(text: str) -> str:
    """Compute SHA-256 hash of a string (UTF-8 encoded).

    Args:
        text: String to hash.

    Returns:
        Hex-encoded SHA-256 digest string.
    """
    return content_hash(text.encode("utf-8"))
