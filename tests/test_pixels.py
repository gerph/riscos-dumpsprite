from __future__ import annotations

import unittest
from pathlib import Path

from riscos_sprites import SpriteFile
from riscos_sprites.palette import default_palette_entries
from riscos_sprites.pixels import _expand_5bit, cmyk_to_rgb


ROOT = Path(__file__).resolve().parents[1]


def sprite_named(sprite_file: SpriteFile, name: str):
    return next(sprite for sprite in sprite_file.sprites if sprite.name == name)


class IndexedPixelDecodingTests(unittest.TestCase):
    def test_basi3p02_decodes_to_known_colour_bar_pattern(self) -> None:
        # basi3p02 is the standard PngSuite "basic, 2-bit palette" test
        # image: four vertical colour bars, 4 pixels wide each, repeated
        # across the 32-pixel width.
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "basi3p02,ff9")
        sprite = sprite_file.sprites[0]
        pixels = sprite.decode_pixels()

        self.assertEqual(pixels.kind, "indexed")
        self.assertEqual(pixels.width, 32)
        self.assertEqual(pixels.height, 32)
        expected_row = (3, 3, 3, 3, 1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0) * 2
        self.assertEqual(pixels.rows[0], expected_row)
        # The last row is the same repeating 4-wide colour-bar pattern,
        # just phase-shifted by one block.
        expected_last_row = (1, 1, 1, 1, 2, 2, 2, 2, 0, 0, 0, 0, 3, 3, 3, 3) * 2
        self.assertEqual(pixels.rows[-1], expected_last_row)

        palette = sprite.effective_palette()
        self.assertEqual(len(palette), 4)
        self.assertEqual((palette[0].red, palette[0].green, palette[0].blue), (0, 255, 0))


class DefaultPaletteTests(unittest.TestCase):
    def test_default_palette_sizes(self) -> None:
        self.assertEqual(len(default_palette_entries(1)), 2)
        self.assertEqual(len(default_palette_entries(2)), 4)
        self.assertEqual(len(default_palette_entries(4)), 16)
        self.assertEqual(len(default_palette_entries(8)), 256)
        self.assertEqual(default_palette_entries(16), ())

    def test_default_palette_entries_are_grey_ramp_for_2bpp(self) -> None:
        entries = default_palette_entries(2)
        self.assertEqual((entries[0].red, entries[0].green, entries[0].blue), (255, 255, 255))
        self.assertEqual((entries[-1].red, entries[-1].green, entries[-1].blue), (0, 0, 0))

    def test_effective_palette_falls_back_to_default_when_sprite_has_none(self) -> None:
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "manysprites,ff9")
        sprite = sprite_named(sprite_file, "!draw")
        self.assertEqual(sprite.palette_entries, 0)
        palette = sprite.effective_palette()
        self.assertEqual(len(palette), 256)


class MaskDecodingTests(unittest.TestCase):
    def test_classic_1bpp_mask_decodes_to_0_or_255(self) -> None:
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "wavytile,ff9")
        sprite = sprite_file.sprites[0]
        mask = sprite.decode_mask()
        self.assertEqual(mask.kind, "1bpp")
        self.assertEqual((mask.width, mask.height), (32, 16))
        values = {value for row in mask.rows for value in row}
        self.assertTrue(values <= {0, 255})

    def test_alpha_mask_decodes_to_known_gradient(self) -> None:
        # basi4a08 is the standard PngSuite grey+alpha test image: a
        # smooth 0..255 alpha ramp across the width of the image.
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "manysprites,ff9")
        sprite = sprite_named(sprite_file, "basi4a08")
        mask = sprite.decode_mask()
        self.assertEqual(mask.kind, "alpha")
        self.assertEqual(mask.rows[0][0], 0)
        self.assertEqual(mask.rows[0][-1], 255)
        self.assertEqual(list(mask.rows[0]), sorted(mask.rows[0]))

    def test_no_mask_returns_none(self) -> None:
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "basi3p02,ff9")
        self.assertIsNone(sprite_file.sprites[0].decode_mask())


class TrueColourPixelDecodingTests(unittest.TestCase):
    def test_32bpp_rgb_decodes_to_rgb_tuples(self) -> None:
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "manysprites,ff9")
        sprite = sprite_named(sprite_file, "basi2c08")
        pixels = sprite.decode_pixels()
        self.assertEqual(pixels.kind, "rgb")
        self.assertEqual(pixels.rows[0][0], (255, 255, 255))

    def test_16bpp_rgb_decodes_without_error(self) -> None:
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "manysprites,ff9")
        sprite = sprite_named(sprite_file, "32k")
        pixels = sprite.decode_pixels()
        self.assertEqual(pixels.kind, "rgb")
        self.assertEqual(len(pixels.rows), sprite.height)
        self.assertEqual(len(pixels.rows[0]), sprite.width_pixels)
        for channel in pixels.rows[0][0]:
            self.assertGreaterEqual(channel, 0)
            self.assertLessEqual(channel, 255)


class Expand5BitTests(unittest.TestCase):
    def test_pure_channels_expand_to_full_scale(self) -> None:
        self.assertEqual(_expand_5bit(0), (0, 0, 0))
        self.assertEqual(_expand_5bit(31 << 0), (255, 0, 0))
        self.assertEqual(_expand_5bit(31 << 5), (0, 255, 0))
        self.assertEqual(_expand_5bit(31 << 10), (0, 0, 255))


class CmykToRgbTests(unittest.TestCase):
    def test_pure_ink_channels_produce_expected_complementary_colours(self) -> None:
        self.assertEqual(cmyk_to_rgb(0, 0, 0, 0), (255, 255, 255))
        self.assertEqual(cmyk_to_rgb(0, 0, 0, 255), (0, 0, 0))
        self.assertEqual(cmyk_to_rgb(255, 0, 0, 0), (0, 255, 255))
        self.assertEqual(cmyk_to_rgb(0, 255, 0, 0), (255, 0, 255))
        self.assertEqual(cmyk_to_rgb(0, 0, 255, 0), (255, 255, 0))

    def test_channels_saturate_and_do_not_wrap(self) -> None:
        self.assertEqual(cmyk_to_rgb(200, 200, 200, 200), (0, 0, 0))
        self.assertEqual(cmyk_to_rgb(200, 0, 0, 200), (0, 55, 55))


if __name__ == "__main__":
    unittest.main()
