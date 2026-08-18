"""Errors raised while decoding RISC OS sprite files."""

from __future__ import annotations


class SpriteFormatError(ValueError):
    """The sprite file could not be parsed."""
