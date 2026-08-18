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
    def test_old_format_classic_mask_uses_image_bpp_not_1bpp_packing(self) -> None:
        # Old-format masks are stored at the sprite's own bits-per-pixel
        # (a whole pixel-sized slot per pixel, zero meaning transparent),
        # not literally 1 bit per pixel densely packed -- "switcher" (an
        # 8bpp old-format icon) makes a good check because its mask traces
        # a distinctive cog/gear silhouette rather than a plain rectangle.
        sprite_file = SpriteFile.parse(ROOT / "sprites" / "manysprites,ff9")
        sprite = sprite_named(sprite_file, "switcher")
        self.assertEqual(sprite.mode.format_name, "old")
        mask = sprite.decode_mask()
        self.assertEqual(mask.kind, "1bpp")
        self.assertEqual((mask.width, mask.height), (40, 42))
        values = {value for row in mask.rows for value in row}
        self.assertTrue(values <= {0, 255})
        # Top-left corner is outside the cog outline (transparent); the
        # centre of the top row sits on the cog body (opaque).
        self.assertEqual(mask.rows[0][0], 0)
        self.assertEqual(mask.rows[8][20], 255)

    def test_new_format_classic_mask_is_densely_1bpp_packed(self) -> None:
        # No sample sprite exercises this path (only old-format classic
        # masks appear in sprites/), so this is a synthetic check that a
        # new-format 1bpp mask uses its own word-aligned row width,
        # independent of the image's own (wider, per-image-bpp) rows.
        from riscos_sprites.pixels import decode_mask

        width_pixels = 40
        height = 1
        mask_width_words = (width_pixels + 31) // 32  # 2 words, not the image's 10
        mask_bytes = bytearray(mask_width_words * 4)
        mask_bytes[0] = 0b00000001  # pixel 0 opaque
        mask_bytes[1] = 0b00000010  # pixel 9 opaque
        mask = decode_mask(
            mask_bytes=bytes(mask_bytes),
            height=height,
            width_pixels=width_pixels,
            first_bit_used=0,
            mask_kind="1bpp",
            format_name="new",
            image_bpp=8,
            image_width_words=10,
        )
        self.assertEqual(mask.rows[0][0], 255)
        self.assertEqual(mask.rows[0][9], 255)
        self.assertEqual(sum(1 for v in mask.rows[0] if v), 2)

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
