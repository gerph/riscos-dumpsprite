from __future__ import annotations

import struct
import unittest
import zlib

from riscos_sprites.png_reader import (
    COLOUR_TYPE_GRAY,
    COLOUR_TYPE_PALETTE,
    COLOUR_TYPE_RGB,
    decode_png,
    read_phys_dpi,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _build_png(
    width: int,
    height: int,
    bit_depth: int,
    colour_type: int,
    scanlines: list[bytes],
    *,
    palette: bytes | None = None,
    extra_chunks: list[bytes] | None = None,
) -> bytes:
    parts = [PNG_SIGNATURE]
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, colour_type, 0, 0, 0)
    parts.append(_chunk(b"IHDR", ihdr))
    if palette is not None:
        parts.append(_chunk(b"PLTE", palette))
    for extra in extra_chunks or []:
        parts.append(extra)
    parts.append(_chunk(b"IDAT", zlib.compress(b"".join(scanlines), 9)))
    parts.append(_chunk(b"IEND", b""))
    return b"".join(parts)


def _filter_sub(row: bytes, bpp: int) -> bytes:
    out = bytearray(len(row))
    for i in range(len(row)):
        left = row[i - bpp] if i >= bpp else 0
        out[i] = (row[i] - left) & 0xFF
    return bytes(out)


def _filter_up(row: bytes, prev: bytes) -> bytes:
    return bytes((row[i] - prev[i]) & 0xFF for i in range(len(row)))


def _filter_average(row: bytes, prev: bytes, bpp: int) -> bytes:
    out = bytearray(len(row))
    for i in range(len(row)):
        left = row[i - bpp] if i >= bpp else 0
        out[i] = (row[i] - (left + prev[i]) // 2) & 0xFF
    return bytes(out)


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _filter_paeth(row: bytes, prev: bytes, bpp: int) -> bytes:
    out = bytearray(len(row))
    for i in range(len(row)):
        a = row[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        out[i] = (row[i] - _paeth_predictor(a, b, c)) & 0xFF
    return bytes(out)


class FilterTypeDecodingTests(unittest.TestCase):
    """Our own PNG writer always uses filter type 0 (None), so a
    round-trip test through it never exercises the other four decoder
    branches. These build minimal PNGs by hand, encoding known raw
    pixel data with each filter type in turn, to check the decoder
    reconstructs the original bytes regardless of which filter was used."""

    def _check_gray_rows(self, raw_rows: list[bytes], filter_type: int, filter_fn) -> None:
        width = len(raw_rows[0])
        height = len(raw_rows)
        bpp = 1
        prev = bytes(width)
        scanlines = []
        for row in raw_rows:
            if filter_type == 0:
                filtered = row
            elif filter_type == 1:
                filtered = _filter_sub(row, bpp)
            elif filter_type == 2:
                filtered = _filter_up(row, prev)
            elif filter_type == 3:
                filtered = _filter_average(row, prev, bpp)
            elif filter_type == 4:
                filtered = _filter_paeth(row, prev, bpp)
            else:
                raise AssertionError(filter_type)
            scanlines.append(bytes([filter_type]) + filtered)
            prev = row

        png_bytes = _build_png(width, height, 8, COLOUR_TYPE_GRAY, scanlines)
        image = decode_png(png_bytes)
        self.assertEqual(image.rows, [list(row) for row in raw_rows])

    def test_filter_none(self) -> None:
        self._check_gray_rows([bytes([10, 20, 30, 40]), bytes([50, 60, 70, 80])], 0, None)

    def test_filter_sub(self) -> None:
        self._check_gray_rows([bytes([10, 20, 30, 40]), bytes([1, 2, 3, 4])], 1, None)

    def test_filter_up(self) -> None:
        self._check_gray_rows([bytes([10, 20, 30, 40]), bytes([15, 25, 35, 45])], 2, None)

    def test_filter_average(self) -> None:
        self._check_gray_rows([bytes([10, 20, 30, 40]), bytes([100, 110, 120, 130])], 3, None)

    def test_filter_paeth(self) -> None:
        self._check_gray_rows([bytes([0, 5, 250, 128]), bytes([200, 150, 100, 50])], 4, None)

    def test_mixed_filters_across_rows(self) -> None:
        raw_rows = [bytes([10, 20, 30]), bytes([40, 50, 60]), bytes([70, 80, 90]), bytes([15, 95, 3])]
        filters = [0, 1, 2, 4]
        width = 3
        bpp = 1
        prev = bytes(width)
        scanlines = []
        for row, filter_type in zip(raw_rows, filters):
            if filter_type == 0:
                filtered = row
            elif filter_type == 1:
                filtered = _filter_sub(row, bpp)
            elif filter_type == 2:
                filtered = _filter_up(row, prev)
            elif filter_type == 4:
                filtered = _filter_paeth(row, prev, bpp)
            scanlines.append(bytes([filter_type]) + filtered)
            prev = row
        png_bytes = _build_png(width, len(raw_rows), 8, COLOUR_TYPE_GRAY, scanlines)
        image = decode_png(png_bytes)
        self.assertEqual(image.rows, [list(row) for row in raw_rows])


class ChunkParsingTests(unittest.TestCase):
    def test_palette_and_trns_are_decoded(self) -> None:
        palette = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255])  # red, green, blue
        trns = _chunk(b"tRNS", bytes([0, 255, 128]))
        scanline = bytes([0]) + bytes([0, 1, 2])  # filter None, one row of 3 indices
        png_bytes = _build_png(3, 1, 8, COLOUR_TYPE_PALETTE, [scanline], palette=palette, extra_chunks=[trns])

        image = decode_png(png_bytes)
        self.assertEqual(image.palette, ((255, 0, 0), (0, 255, 0), (0, 0, 255)))
        self.assertEqual(image.trns_palette, (0, 255, 128))
        self.assertEqual(image.rows, [[0, 1, 2]])

    def test_sub_byte_palette_depth_unpacks_msb_first(self) -> None:
        # PNG packs sub-byte samples MSB-first (the opposite of RISC OS's
        # own LSB-first sprite packing) -- a byte 0b01_10_11_00 at 2 bits
        # per sample should read as [1, 2, 3, 0].
        palette = bytes([0, 0, 0] * 4)
        scanline = bytes([0]) + bytes([0b01_10_11_00])
        png_bytes = _build_png(4, 1, 2, COLOUR_TYPE_PALETTE, [scanline], palette=palette)
        image = decode_png(png_bytes)
        self.assertEqual(image.rows, [[1, 2, 3, 0]])

    def test_rgb_pixels_decode_as_triples(self) -> None:
        scanline = bytes([0]) + bytes([10, 20, 30, 40, 50, 60])
        png_bytes = _build_png(2, 1, 8, COLOUR_TYPE_RGB, [scanline])
        image = decode_png(png_bytes)
        self.assertEqual(image.rows, [[(10, 20, 30), (40, 50, 60)]])


class PhysChunkTests(unittest.TestCase):
    def test_round_trips_common_dpi_values(self) -> None:
        from riscos_sprites.png import _dpi_to_pixels_per_metre

        for dpi in (45, 90, 180):
            x_per_metre = _dpi_to_pixels_per_metre(dpi)
            phys = _chunk(b"pHYs", struct.pack(">IIB", x_per_metre, x_per_metre, 1))
            png_bytes = _build_png(1, 1, 8, COLOUR_TYPE_GRAY, [bytes([0, 0])], extra_chunks=[phys])
            self.assertEqual(read_phys_dpi(png_bytes), (dpi, dpi))

    def test_returns_none_when_absent(self) -> None:
        png_bytes = _build_png(1, 1, 8, COLOUR_TYPE_GRAY, [bytes([0, 0])])
        self.assertIsNone(read_phys_dpi(png_bytes))


if __name__ == "__main__":
    unittest.main()
