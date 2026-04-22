"""Deprecated legacy module — should be flagged as dead wood."""

# DEPRECATED: This module is no longer maintained.
# Use src/utils.py instead.


def old_format(data: dict) -> str:
    """Old formatting function. Do not use."""
    return str(data)


def legacy_parse(input_str: str) -> dict:
    """Legacy parser. Do not use."""
    result = {}
    for pair in input_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key.strip()] = value.strip()
    return result
