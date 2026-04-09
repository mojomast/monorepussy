"""Color utilities for TimeLoom."""

from __future__ import annotations

import hashlib


COMMIT_TYPE_SCHEMES = {
    "warm": {
        "feature": "#E85D3A",
        "fix": "#3A8DE8",
        "refactor": "#8D8D8D",
        "delete": "#1A1A1A",
        "other": "#C4A882",
    },
    "cool": {
        "feature": "#4AA3DF",
        "fix": "#1E5AA8",
        "refactor": "#6B7C93",
        "delete": "#111827",
        "other": "#A3B8D1",
    },
    "neon": {
        "feature": "#FF4D8D",
        "fix": "#00D1FF",
        "refactor": "#B000FF",
        "delete": "#111111",
        "other": "#FFD166",
    },
    "monochrome": {
        "feature": "#666666",
        "fix": "#4A4A4A",
        "refactor": "#808080",
        "delete": "#1A1A1A",
        "other": "#B0B0B0",
    },
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert a hex color to an RGB tuple."""

    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert an RGB tuple to a hex color."""

    return "#%02x%02x%02x" % rgb


def darken(hex_color: str, factor: float = 0.8) -> str:
    """Darken a hex color by a factor."""

    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(
        (max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor)))
    )


def lighten(hex_color: str, factor: float = 1.15) -> str:
    """Lighten a hex color by a factor."""

    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex(
        (
            min(255, int(r * factor)),
            min(255, int(g * factor)),
            min(255, int(b * factor)),
        )
    )


def directory_color(path: str, scheme: str = "warm") -> str:
    """Derive a stable directory color from a path."""

    palette = [
        "#E76F51",
        "#2A9D8F",
        "#264653",
        "#F4A261",
        "#8AB17D",
        "#7D5BA6",
        "#3D5A80",
        "#D62828",
    ]
    digest = hashlib.sha1(f"{scheme}:{path}".encode("utf-8")).digest()
    return palette[digest[0] % len(palette)]


def commit_type_color(change_type: str, scheme: str = "warm") -> str:
    """Return the configured color for a commit type."""

    return COMMIT_TYPE_SCHEMES.get(scheme, COMMIT_TYPE_SCHEMES["warm"]).get(
        change_type,
        COMMIT_TYPE_SCHEMES[scheme]["other"]
        if scheme in COMMIT_TYPE_SCHEMES
        else COMMIT_TYPE_SCHEMES["warm"]["other"],
    )
