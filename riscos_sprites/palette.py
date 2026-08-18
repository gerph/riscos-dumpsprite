"""Decoding of RISC OS sprite palettes."""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class PaletteEntry:
    """A single decoded palette entry (two RISC OS palette words)."""

    index: int
    word1: int
    word2: int
    red: int
    green: int
    blue: int
    words_match: bool

    @classmethod
    def decode_all(cls, data: bytes, palette_offset: int, palette_bytes: int) -> tuple["PaletteEntry", ...]:
        entries: list[PaletteEntry] = []
        for index in range(palette_bytes // 8):
            word1, word2 = struct.unpack_from("<II", data, palette_offset + (index * 8))
            entries.append(
                cls(
                    index=index,
                    word1=word1,
                    word2=word2,
                    red=(word1 >> 8) & 0xFF,
                    green=(word1 >> 16) & 0xFF,
                    blue=(word1 >> 24) & 0xFF,
                    words_match=word1 == word2,
                )
            )
        return tuple(entries)

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "word1": self.word1,
            "word2": self.word2,
            "rgb": {
                "red": self.red,
                "green": self.green,
                "blue": self.blue,
            },
            "words_match": self.words_match,
        }
