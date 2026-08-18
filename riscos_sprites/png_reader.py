"""
A minimal PNG reader, just enough for `from-png`.

Supports what's needed to round-trip riscos_sprites' own PNG output plus
ordinary PNGs: IHDR/PLTE/tRNS/pHYs/IDAT, all five filter types, colour
types 0 (grayscale), 2 (RGB), 3 (palette), 4 (grayscale+alpha) and 6
(RGBA), and bit depths 1/2/4/8 for grayscale/palette or 8 for the rest.
Interlaced images and 16-bit-per-channel images are not supported.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from .errors import SpriteFormatError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

COLOUR_TYPE_GRAY = 0
COLOUR_TYPE_RGB = 2
COLOUR_TYPE_PALETTE = 3
COLOUR_TYPE_GRAY_ALPHA = 4
COLOUR_TYPE_RGBA = 6

_CHANNELS_FOR_COLOUR_TYPE = {
    COLOUR_TYPE_GRAY: 1,
    COLOUR_TYPE_RGB: 3,
    COLOUR_TYPE_PALETTE: 1,
    COLOUR_TYPE_GRAY_ALPHA: 2,
    COLOUR_TYPE_RGBA: 4,
}

# Same dpi <-> pixels-per-metre scale ConvertPNG (and riscos_sprites.png)
# uses: (1<<12) / 0.0254, as a 12-bit fixed point integer.
_DPI_TO_PIXELS_PER_METRE_SCALE = 0x275EB


@dataclass(frozen=True)
class PngImage:
    width: int
    height: int
    bit_depth: int
    colour_type: int
    palette: tuple[tuple[int, int, int], ...] | None
    trns_palette: tuple[int, ...] | None
    trns_colour: tuple[int, ...] | None
    rows: list


def _read_chunks(data: bytes) -> dict[bytes, list[bytes]]:
    if data[:8] != PNG_SIGNATURE:
        raise SpriteFormatError("not a PNG file")
    chunks: dict[bytes, list[bytes]] = {}
    offset = 8
    while offset < len(data):
        if offset + 8 > len(data):
            raise SpriteFormatError("truncated PNG file")
        (length,) = struct.unpack_from(">I", data, offset)
        tag = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        chunks.setdefault(tag, []).append(payload)
        if tag == b"IEND":
            break
    return chunks


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter(raw: bytes, height: int, bytes_per_pixel: int, row_bytes: int) -> bytearray:
    out = bytearray(row_bytes * height)
    prev_row = bytearray(row_bytes)
    offset = 0
    for row_index in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + row_bytes])
        offset += row_bytes
        for i in range(row_bytes):
            a = row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            b = prev_row[i]
            c = prev_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            if filter_type == 0:
                pass
            elif filter_type == 1:
                row[i] = (row[i] + a) & 0xFF
            elif filter_type == 2:
                row[i] = (row[i] + b) & 0xFF
            elif filter_type == 3:
                row[i] = (row[i] + (a + b) // 2) & 0xFF
            elif filter_type == 4:
                row[i] = (row[i] + _paeth(a, b, c)) & 0xFF
            else:
                raise SpriteFormatError("unsupported PNG filter type: {0}".format(filter_type))
        out[row_index * row_bytes : (row_index + 1) * row_bytes] = row
        prev_row = row
    return out


def _unpack_row(row_bytes: bytes, width: int, colour_type: int, bit_depth: int, channels: int):
    if bit_depth < 8:
        per_byte = 8 // bit_depth
        value_mask = (1 << bit_depth) - 1
        values = []
        for byte in row_bytes:
            for position in range(per_byte):
                shift = 8 - bit_depth * (position + 1)
                values.append((byte >> shift) & value_mask)
        return values[:width]
    if channels == 1:
        return list(row_bytes[:width])
    pixels = []
    for i in range(0, width * channels, channels):
        pixels.append(tuple(row_bytes[i : i + channels]))
    return pixels


def decode_png(data: bytes) -> PngImage:
    chunks = _read_chunks(data)
    if b"IHDR" not in chunks:
        raise SpriteFormatError("PNG file has no IHDR chunk")

    width, height, bit_depth, colour_type, compression, filter_method, interlace = struct.unpack(
        ">IIBBBBB", chunks[b"IHDR"][0]
    )
    if compression != 0 or filter_method != 0:
        raise SpriteFormatError("unsupported PNG compression or filter method")
    if interlace != 0:
        raise SpriteFormatError("interlaced PNG files are not supported")
    if colour_type not in _CHANNELS_FOR_COLOUR_TYPE:
        raise SpriteFormatError("unsupported PNG colour type: {0}".format(colour_type))
    channels = _CHANNELS_FOR_COLOUR_TYPE[colour_type]
    if colour_type in (COLOUR_TYPE_RGB, COLOUR_TYPE_GRAY_ALPHA, COLOUR_TYPE_RGBA) and bit_depth != 8:
        raise SpriteFormatError(
            "unsupported PNG bit depth {0} for colour type {1}".format(bit_depth, colour_type)
        )
    if bit_depth not in (1, 2, 4, 8):
        raise SpriteFormatError("unsupported PNG bit depth: {0}".format(bit_depth))

    palette = None
    if b"PLTE" in chunks:
        plte = chunks[b"PLTE"][0]
        palette = tuple((plte[i], plte[i + 1], plte[i + 2]) for i in range(0, len(plte), 3))

    trns_palette = None
    trns_colour = None
    if b"tRNS" in chunks:
        trns = chunks[b"tRNS"][0]
        if colour_type == COLOUR_TYPE_PALETTE:
            palette_size = len(palette) if palette else 0
            trns_palette = tuple(trns) + (255,) * (palette_size - len(trns))
        elif colour_type == COLOUR_TYPE_GRAY:
            (value,) = struct.unpack(">H", trns)
            trns_colour = (value & 0xFF,)
        elif colour_type == COLOUR_TYPE_RGB:
            red, green, blue = struct.unpack(">HHH", trns)
            trns_colour = (red & 0xFF, green & 0xFF, blue & 0xFF)

    bits_per_pixel = channels * bit_depth
    row_bytes = (width * bits_per_pixel + 7) // 8
    bytes_per_pixel = max(1, bits_per_pixel // 8)

    raw = zlib.decompress(b"".join(chunks.get(b"IDAT", [])))
    unfiltered = _unfilter(raw, height, bytes_per_pixel, row_bytes)

    rows = [
        _unpack_row(unfiltered[row_index * row_bytes : (row_index + 1) * row_bytes], width, colour_type, bit_depth, channels)
        for row_index in range(height)
    ]

    return PngImage(
        width=width,
        height=height,
        bit_depth=bit_depth,
        colour_type=colour_type,
        palette=palette,
        trns_palette=trns_palette,
        trns_colour=trns_colour,
        rows=rows,
    )


def read_phys_dpi(data: bytes) -> tuple[int, int] | None:
    chunks = _read_chunks(data)
    if b"pHYs" not in chunks:
        return None
    x_per_metre, y_per_metre, unit = struct.unpack(">IIB", chunks[b"pHYs"][0])
    if unit != 1:
        return None
    x_dpi = round(((x_per_metre - 1) << 12) / _DPI_TO_PIXELS_PER_METRE_SCALE)
    y_dpi = round(((y_per_metre - 1) << 12) / _DPI_TO_PIXELS_PER_METRE_SCALE)
    return x_dpi, y_dpi
