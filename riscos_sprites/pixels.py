"""Decoding of raw RISC OS sprite image/mask bytes into pixel grids.

Ports the pixel-level algorithms from the RISC OS ConvertPNG module's
``c/reverse`` (Sprite -> PNG direction): the LSB-first bit packing RISC OS
uses within a word (the reason ConvertPNG calls ``png_set_packswap()`` for
<8bpp sprites), the 5:5:5 -> 8:8:8 bit-replication for 16bpp true-colour
sprites, and the CMYK -> RGB conversion.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .errors import SpriteFormatError


@dataclass(frozen=True)
class DecodedPixels:
    """A decoded grid of sprite image pixels, row by row.

    For ``kind == "indexed"`` each row is a tuple of palette indices.
    For ``kind == "rgb"`` each row is a tuple of ``(red, green, blue)``
    8-bit-per-channel tuples.
    """

    width: int
    height: int
    kind: str
    rows: tuple[tuple, ...]


@dataclass(frozen=True)
class DecodedMask:
    """A decoded grid of sprite mask/alpha values, row by row.

    Each row is a tuple of one 8-bit opacity value per pixel (0
    transparent, 255 opaque), regardless of whether the source was a
    classic 1bpp mask or a new-format 8bpp alpha mask.
    """

    width: int
    height: int
    kind: str
    rows: tuple[tuple[int, ...], ...]


def _row_values(row_bytes: bytes, row_words: int, first_bit_used: int, count: int, bpp: int) -> list[int]:
    """Unpack ``count`` values of ``bpp`` bits each from a word-aligned
    row, skipping ``first_bit_used`` bits at the start of the row.

    RISC OS packs pixels least-significant-bit first within each 32-bit
    word, so pixel 0 of a word is its lowest ``bpp`` bits.
    """
    words = struct.unpack(f"<{row_words}I", row_bytes)
    per_word = 32 // bpp
    mask = (1 << bpp) - 1
    values: list[int] = []
    for word in words:
        for n in range(per_word):
            values.append((word >> (n * bpp)) & mask)
    skip = first_bit_used // bpp
    return values[skip : skip + count]


def _expand_5bit(colour: int) -> tuple[int, int, int]:
    """Expand a 5:5:5 true-colour sprite pixel to 8 bits per channel."""
    r = (colour & (31 << 0)) << 3
    r |= r >> 5
    g = (colour & (31 << 5)) >> 2
    g |= g >> 5
    b = (colour & (31 << 10)) >> 7
    b |= b >> 5
    return r, g, b


def cmyk_to_rgb(cyan: int, magenta: int, yellow: int, black: int) -> tuple[int, int, int]:
    """Convert a CMYK sprite pixel's 8-bit ink channels to RGB.

    Sprite CMYK pixel bytes are stored in order cyan, magenta, yellow,
    black. Each RGB channel is the inverted, black-added complement of
    its corresponding ink channel (red from cyan, green from magenta,
    blue from yellow).
    """
    red = 255 - min(255, cyan + black)
    green = 255 - min(255, magenta + black)
    blue = 255 - min(255, yellow + black)
    return red, green, blue


def decode_pixels(
    *,
    image_bytes: bytes,
    width_words: int,
    height: int,
    first_bit_used: int,
    width_pixels: int,
    bpp: int,
    data_format: str,
) -> DecodedPixels:
    row_bytes_len = width_words * 4

    if data_format in {"monochrome", "indexed"}:
        rows = []
        for row in range(height):
            row_bytes = image_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
            rows.append(tuple(_row_values(row_bytes, width_words, first_bit_used, width_pixels, bpp)))
        return DecodedPixels(width=width_pixels, height=height, kind="indexed", rows=tuple(rows))

    if data_format == "RGB":
        rows = []
        for row in range(height):
            row_bytes = image_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
            raw = _row_values(row_bytes, width_words, first_bit_used, width_pixels, bpp)
            if bpp == 16:
                pixel_row = tuple(_expand_5bit(value) for value in raw)
            elif bpp == 32:
                pixel_row = tuple((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF) for value in raw)
            else:
                raise SpriteFormatError(f"unsupported RGB sprite bit depth: {bpp}")
            rows.append(pixel_row)
        return DecodedPixels(width=width_pixels, height=height, kind="rgb", rows=tuple(rows))

    if data_format == "CMYK":
        rows = []
        for row in range(height):
            row_bytes = image_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
            raw = _row_values(row_bytes, width_words, first_bit_used, width_pixels, 32)
            pixel_row = []
            for value in raw:
                cyan = value & 0xFF
                magenta = (value >> 8) & 0xFF
                yellow = (value >> 16) & 0xFF
                black = (value >> 24) & 0xFF
                pixel_row.append(cmyk_to_rgb(cyan, magenta, yellow, black))
            rows.append(tuple(pixel_row))
        return DecodedPixels(width=width_pixels, height=height, kind="rgb", rows=tuple(rows))

    raise SpriteFormatError(f"cannot decode pixel data for sprite data format: {data_format}")


def decode_mask(
    *,
    mask_bytes: bytes,
    height: int,
    width_pixels: int,
    first_bit_used: int,
    mask_kind: str,
    format_name: str,
    image_bpp: int,
    image_width_words: int,
) -> DecodedMask:
    if mask_kind == "alpha":
        mask_width_words = (width_pixels * 8 + 31) // 32
        row_bytes_len = mask_width_words * 4
        rows = []
        for row in range(height):
            row_bytes = mask_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
            rows.append(tuple(_row_values(row_bytes, mask_width_words, 0, width_pixels, 8)))
        return DecodedMask(width=width_pixels, height=height, kind="alpha", rows=tuple(rows))

    if mask_kind == "1bpp":
        if format_name == "old":
            # Old-format masks are stored at the *same* bits-per-pixel as
            # the image itself (a whole pixel-sized slot per pixel, zero
            # meaning transparent), not literally 1 bit per pixel -- they
            # reuse the image's own row layout entirely.
            row_bytes_len = image_width_words * 4
            rows = []
            for row in range(height):
                row_bytes = mask_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
                values = _row_values(row_bytes, image_width_words, first_bit_used, width_pixels, image_bpp)
                rows.append(tuple(255 if value else 0 for value in values))
            return DecodedMask(width=width_pixels, height=height, kind="1bpp", rows=tuple(rows))

        # New-format classic masks really are 1 bit per pixel, packed
        # into their own word-aligned rows independent of the image's
        # own row width.
        mask_width_words = (width_pixels + 31) // 32
        row_bytes_len = mask_width_words * 4
        rows = []
        for row in range(height):
            row_bytes = mask_bytes[row * row_bytes_len : (row + 1) * row_bytes_len]
            values = _row_values(row_bytes, mask_width_words, 0, width_pixels, 1)
            rows.append(tuple(255 if value else 0 for value in values))
        return DecodedMask(width=width_pixels, height=height, kind="1bpp", rows=tuple(rows))

    raise SpriteFormatError(f"cannot decode mask data of kind: {mask_kind}")
