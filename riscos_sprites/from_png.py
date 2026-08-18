"""
Build a RISC OS sprite file from one or more PNG images.

Always builds new-format sprites: paletted PNGs (and grayscale PNGs,
promoted to an indexed sprite with a synthesized grey-ramp palette)
become indexed sprites at the PNG's own bit depth; RGB/RGBA PNGs become
32bpp true-colour sprites. CMYK and 16-bit-per-channel sprites are not
produced -- there is no ordinary PNG representation for CMYK, and
true-colour output is always 32bpp regardless of the source depth.

Masking: for indexed sources, a `tRNS`/alpha channel that is purely
binary (every value 0 or 255) becomes a classic 1bpp mask; anything with
intermediate values becomes a genuine 8bpp alpha mask. True-colour
sources always become an 8bpp alpha mask when they carry any
transparency at all (an RGB colour-key or an RGBA alpha channel) --
reconstructing ConvertPNG's colour-key promotion chain in reverse isn't
needed for a valid, correct sprite, just a smaller one.
"""

from __future__ import annotations

import struct
from pathlib import Path

from .errors import SpriteFormatError
from .png_reader import (
    COLOUR_TYPE_GRAY,
    COLOUR_TYPE_GRAY_ALPHA,
    COLOUR_TYPE_PALETTE,
    COLOUR_TYPE_RGB,
    COLOUR_TYPE_RGBA,
    PngImage,
    decode_png,
    read_phys_dpi,
)

MAX_SPRITE_NAME_LENGTH = 12
SPRITE_HEADER_SIZE = 44

# New-format sprite types, see riscos_sprites.modes.NEW_SPRITE_TYPES.
_INDEXED_SPRITE_TYPE_FOR_BPP = {1: 1, 2: 2, 4: 3, 8: 4}
_TRUE_COLOUR_SPRITE_TYPE = 6

_DEFAULT_DPI = 90


def _grey_palette(bit_depth: int) -> list[tuple[int, int, int]]:
    size = 1 << bit_depth
    if size == 1:
        return [(0, 0, 0)]
    return [(((index * 255) // (size - 1)),) * 3 for index in range(size)]


def _is_binary_alpha(values) -> bool:
    return all(value in (0, 255) for value in values)


def _sprite_name(path: Path, override: str | None) -> str:
    name = override if override is not None else path.stem
    if len(name.encode("latin-1", errors="replace")) > MAX_SPRITE_NAME_LENGTH:
        raise SpriteFormatError(
            "sprite name '{0}' is longer than {1} characters; "
            "use --name to give an explicit shorter name".format(name, MAX_SPRITE_NAME_LENGTH)
        )
    return name


def _indexed_from_png(png: PngImage):
    """
    Returns (bpp, palette_rgb, index_rows, mask_rows_or_none, has_alpha).
    """
    if png.colour_type == COLOUR_TYPE_PALETTE:
        bpp = png.bit_depth
        palette = list(png.palette or [])
        index_rows = png.rows
        alpha_rows = None
        if png.trns_palette is not None:
            trns = png.trns_palette
            alpha_rows = [
                [trns[index] if index < len(trns) else 255 for index in row] for row in index_rows
            ]
    elif png.colour_type == COLOUR_TYPE_GRAY:
        bpp = png.bit_depth
        palette = _grey_palette(bpp)
        index_rows = png.rows
        alpha_rows = None
    elif png.colour_type == COLOUR_TYPE_GRAY_ALPHA:
        bpp = png.bit_depth
        palette = _grey_palette(bpp)
        index_rows = [[pixel[0] for pixel in row] for row in png.rows]
        alpha_rows = [[pixel[1] for pixel in row] for row in png.rows]
    else:
        raise SpriteFormatError(
            "unsupported PNG colour type for indexed conversion: {0}".format(png.colour_type)
        )

    mask_rows = None
    has_alpha = False
    if alpha_rows is not None:
        if all(_is_binary_alpha(row) for row in alpha_rows):
            mask_rows = [[255 if value else 0 for value in row] for row in alpha_rows]
        else:
            has_alpha = True
            mask_rows = alpha_rows

    return bpp, palette, index_rows, mask_rows, has_alpha


def _true_colour_from_png(png: PngImage):
    """
    Returns (pixel_word_rows, mask_rows_or_none, has_alpha).
    """
    if png.colour_type == COLOUR_TYPE_RGBA:
        pixel_rows = [[red | (green << 8) | (blue << 16) for red, green, blue, _alpha in row] for row in png.rows]
        alpha_rows = [[alpha for _red, _green, _blue, alpha in row] for row in png.rows]
        if any(alpha != 255 for row in alpha_rows for alpha in row):
            return pixel_rows, alpha_rows, True
        return pixel_rows, None, False

    pixel_rows = [[red | (green << 8) | (blue << 16) for red, green, blue in row] for row in png.rows]
    if png.trns_colour is not None:
        mask_rows = [[0 if pixel == png.trns_colour else 255 for pixel in row] for row in png.rows]
        return pixel_rows, mask_rows, True
    return pixel_rows, None, False


def _new_format_mode_word(sprite_type: int, has_alpha: bool, x_dpi: int, y_dpi: int) -> int:
    word = (sprite_type << 27) | ((y_dpi & 0x1FFF) << 14) | ((x_dpi & 0x1FFF) << 1) | 1
    if has_alpha:
        word |= 1 << 31
    return word


def _pack_row_values(values, row_words: int, bpp: int) -> bytes:
    per_word = 32 // bpp
    value_mask = (1 << bpp) - 1
    words = []
    index = 0
    for _ in range(row_words):
        word = 0
        for position in range(per_word):
            if index < len(values):
                word |= (values[index] & value_mask) << (position * bpp)
            index += 1
        words.append(word)
    return struct.pack("<{0}I".format(row_words), *words)


def _build_sprite_record(
    name: str,
    bpp: int,
    sprite_type: int,
    has_alpha: bool,
    width_pixels: int,
    height: int,
    palette_rgb,
    pixel_rows,
    mask_rows,
    x_dpi: int,
    y_dpi: int,
) -> bytes:
    row_words = (width_pixels * bpp + 31) // 32
    extra_bits = row_words * 32 - width_pixels * bpp
    last_bit_used = 31 - extra_bits

    image_data = b"".join(_pack_row_values(row, row_words, bpp) for row in pixel_rows)

    mask_data = b""
    if mask_rows is not None:
        if has_alpha:
            mask_row_words = (width_pixels * 8 + 31) // 32
            mask_data = b"".join(_pack_row_values(row, mask_row_words, 8) for row in mask_rows)
        else:
            mask_row_words = (width_pixels + 31) // 32
            mask_data = b"".join(
                _pack_row_values([1 if value else 0 for value in row], mask_row_words, 1) for row in mask_rows
            )

    palette_bytes = bytearray()
    if palette_rgb is not None:
        for red, green, blue in palette_rgb:
            word = (blue << 24) | (green << 16) | (red << 8)
            palette_bytes.extend(struct.pack("<II", word, word))

    mode_word = _new_format_mode_word(sprite_type, has_alpha, x_dpi, y_dpi)

    image_offset = SPRITE_HEADER_SIZE + len(palette_bytes)
    mask_offset = image_offset + len(image_data) if mask_rows is not None else image_offset
    next_offset = image_offset + len(image_data) + len(mask_data)

    name_bytes = name.encode("latin-1", errors="replace")[:12].ljust(12, b"\0")
    header = struct.pack(
        "<I12sIIIIIII",
        next_offset,
        name_bytes,
        row_words - 1,
        height - 1,
        0,
        last_bit_used,
        image_offset,
        mask_offset,
        mode_word,
    )
    return header + bytes(palette_bytes) + image_data + mask_data


def sprite_bytes_from_png(png_path: Path, *, name: str | None = None) -> bytes:
    data = png_path.read_bytes()
    png = decode_png(data)
    sprite_name = _sprite_name(png_path, name)
    dpi = read_phys_dpi(data) or (_DEFAULT_DPI, _DEFAULT_DPI)

    if png.colour_type in (COLOUR_TYPE_PALETTE, COLOUR_TYPE_GRAY, COLOUR_TYPE_GRAY_ALPHA):
        bpp, palette_rgb, pixel_rows, mask_rows, has_alpha = _indexed_from_png(png)
        sprite_type = _INDEXED_SPRITE_TYPE_FOR_BPP[bpp]
        return _build_sprite_record(
            sprite_name, bpp, sprite_type, has_alpha, png.width, png.height, palette_rgb, pixel_rows, mask_rows, *dpi
        )

    if png.colour_type in (COLOUR_TYPE_RGB, COLOUR_TYPE_RGBA):
        pixel_rows, mask_rows, has_alpha = _true_colour_from_png(png)
        return _build_sprite_record(
            sprite_name, 32, _TRUE_COLOUR_SPRITE_TYPE, has_alpha, png.width, png.height, None, pixel_rows, mask_rows, *dpi
        )

    raise SpriteFormatError("unsupported PNG colour type: {0}".format(png.colour_type))


def build_sprite_file_bytes(png_paths, *, name: str | None = None) -> bytes:
    if not png_paths:
        raise SpriteFormatError("from-png requires at least one PNG file")
    if name is not None and len(png_paths) > 1:
        raise SpriteFormatError("--name can only be used when converting a single PNG file")

    records = [sprite_bytes_from_png(path, name=name) for path in png_paths]

    body = b"".join(records)
    first_sprite_offset = 16  # 12-byte file header, plus the 4-byte area-pointer convention
    free_offset = first_sprite_offset + len(body)
    header = struct.pack("<III", len(records), first_sprite_offset, free_offset)
    return header + body


def write_sprite_file_from_png(png_paths, output_path: Path, *, name: str | None = None) -> None:
    output_path.write_bytes(build_sprite_file_bytes(png_paths, name=name))
