"""
Decode RISC OS sprite files and convert them to other formats.
"""

from .errors import SpriteFormatError
from .modes import NEW_SPRITE_TYPES, OLD_MODE_INFO, SpriteMode
from .palette import PaletteEntry
from .sprite import Sprite
from .spritefile import SpriteFile, SpriteSelection

__all__ = [
    "SpriteFormatError",
    "SpriteMode",
    "OLD_MODE_INFO",
    "NEW_SPRITE_TYPES",
    "PaletteEntry",
    "Sprite",
    "SpriteFile",
    "SpriteSelection",
]
