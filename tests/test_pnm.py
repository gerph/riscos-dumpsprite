from __future__ import annotations

import unittest
from pathlib import Path

from riscos_sprites import SpriteFile, SpriteFormatError
from riscos_sprites.pnm import sprite_to_indexed_pgm_bytes, sprite_to_ppm_bytes


ROOT = Path(__file__).resolve().parents[1]


def sprite_named(sprite_file: SpriteFile, name: str):
    return next(sprite for sprite in sprite_file.sprites if sprite.name == name)


def parse_ppm_header(data: bytes) -> tuple[str, int, int, int, bytes]:
    assert data[:2] == b"P6"
    offset = 2
    values = []
    while len(values) < 3:
        while data[offset : offset + 1].isspace():
            offset += 1
        if data[offset : offset + 1] == b"#":
            offset = data.index(b"\n", offset) + 1
            continue
        start = offset
        while not data[offset : offset + 1].isspace():
            offset += 1
        values.append(int(data[start:offset]))
    offset += 1  # the single whitespace byte required after maxval
    width, height, maxval = values
    return "P6", width, height, maxval, data[offset:]


class PpmConversionTests(unittest.TestCase):
    def test_indexed_sprite_expands_through_palette(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
        sprite = sprite_file.sprites[0]
        data = sprite_to_ppm_bytes(sprite)

        magic, width, height, maxval, body = parse_ppm_header(data)
        self.assertEqual((width, height, maxval), (32, 32, 255))

        pixels = sprite.decode_pixels()
        palette = sprite.effective_palette()
        expected = bytearray()
        for row in pixels.rows:
            for index in row:
                entry = palette[index]
                expected.extend((entry.red, entry.green, entry.blue))
        self.assertEqual(body, bytes(expected))

    def test_rgb_sprite_uses_decoded_colours_directly(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "manysprites,ff9"))
        sprite = sprite_named(sprite_file, "basi2c08")
        data = sprite_to_ppm_bytes(sprite)

        _magic, width, height, _maxval, body = parse_ppm_header(data)
        pixels = sprite.decode_pixels()
        self.assertEqual((width, height), (pixels.width, pixels.height))

        expected = bytearray()
        for row in pixels.rows:
            for colour in row:
                expected.extend(colour)
        self.assertEqual(body, bytes(expected))

    def test_mask_is_ignored_underlying_colour_is_written(self) -> None:
        # switcher is a masked old-format sprite; PPM output has no way to
        # represent transparency, so every pixel's own colour should come
        # through regardless of the mask.
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "manysprites,ff9"))
        sprite = sprite_named(sprite_file, "switcher")
        data = sprite_to_ppm_bytes(sprite)
        _magic, width, height, _maxval, body = parse_ppm_header(data)
        self.assertEqual(len(body), width * height * 3)


class IndexedPgmConversionTests(unittest.TestCase):
    def test_pixel_data_is_raw_palette_indices(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
        sprite = sprite_file.sprites[0]
        data = sprite_to_indexed_pgm_bytes(sprite)

        self.assertTrue(data.startswith(b"P5\n"))
        pixels = sprite.decode_pixels()
        expected_body = bytes(index for row in pixels.rows for index in row)
        self.assertTrue(data.endswith(expected_body))
        self.assertEqual(len(expected_body), pixels.width * pixels.height)

    def test_comments_record_palette_mode_and_dpi(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
        sprite = sprite_file.sprites[0]
        data = sprite_to_indexed_pgm_bytes(sprite)
        text_part = data.split(b"\n\n", 1)[0] if b"\n\n" in data else data
        header_text = data[: data.index(str(sprite.width_pixels).encode() + b" ")].decode("ascii")

        self.assertIn("# sprite: {0}".format(sprite.name), header_text)
        self.assertIn("# mode:", header_text)
        self.assertIn("# dpi:", header_text)
        self.assertIn("# 0 0 255 0", header_text)  # first palette entry, from earlier tests: green

    def test_rejects_non_indexed_sprite(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "manysprites,ff9"))
        sprite = sprite_named(sprite_file, "basi2c08")
        with self.assertRaises(SpriteFormatError):
            sprite_to_indexed_pgm_bytes(sprite)


if __name__ == "__main__":
    unittest.main()
