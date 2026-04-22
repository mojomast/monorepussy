"""Stenography — Steganographic Code Review Tool.

Detects invisible steganographic attacks in source code including:
- Zero-width Unicode characters
- Homoglyph substitutions (Cyrillic, Greek, Latin)
- RTL override exploits (Trojan Source)
- Whitespace steganography
- Comment steganography via Unicode tricks
"""

__version__ = "1.0.0"
