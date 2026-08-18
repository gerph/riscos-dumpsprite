from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from riscos_sprites import SpriteFile, SpriteFormatError
from riscos_sprites.from_png import build_sprite_file_bytes, write_sprite_file_from_png
from riscos_sprites.png import sprite_to_png_file


ROOT = Path(__file__).resolve().parents[1]


def sprite_named(sprite_file: SpriteFile, name: str):
    return next(sprite for sprite in sprite_file.sprites if sprite.name == name)


def assert_visible_pixels_match(test: unittest.TestCase, original, round_tripped) -> None:
    """
    Compares two sprites pixel-for-pixel by *colour*, not by raw index
    (from-png may legitimately choose different palette ordering), and by
    mask visibility. Underlying colour of masked-out pixels is ignored,
    since it's never displayed and to-png/from-png have no reason to
    preserve it.
    """
    original_pixels = original.decode_pixels()
    round_tripped_pixels = round_tripped.decode_pixels()
    test.assertEqual(
        (original_pixels.width, original_pixels.height),
        (round_tripped_pixels.width, round_tripped_pixels.height),
    )

    def colour_at(sprite, pixels_kind, value):
        if pixels_kind == "indexed":
            entry = sprite.effective_palette()[value]
            return (entry.red, entry.green, entry.blue)
        return value

    original_mask = original.decode_mask()
    round_tripped_mask = round_tripped.decode_mask()

    for row_index, (orig_row, new_row) in enumerate(zip(original_pixels.rows, round_tripped_pixels.rows)):
        orig_mask_row = original_mask.rows[row_index] if original_mask else [255] * len(orig_row)
        new_mask_row = round_tripped_mask.rows[row_index] if round_tripped_mask else [255] * len(new_row)
        for col_index, (orig_value, new_value, orig_alpha, new_alpha) in enumerate(
            zip(orig_row, new_row, orig_mask_row, new_mask_row)
        ):
            test.assertEqual(
                bool(orig_alpha), bool(new_alpha),
                "visibility differs at ({0}, {1})".format(row_index, col_index),
            )
            if orig_alpha and new_alpha:
                orig_colour = colour_at(original, original_pixels.kind, orig_value)
                new_colour = colour_at(round_tripped, round_tripped_pixels.kind, new_value)
                test.assertEqual(
                    orig_colour, new_colour, "colour differs at ({0}, {1})".format(row_index, col_index)
                )
            if original_mask is not None and round_tripped_mask is not None:
                if original_mask.kind == "alpha" and round_tripped_mask.kind == "alpha":
                    test.assertEqual(
                        orig_alpha, new_alpha, "alpha differs at ({0}, {1})".format(row_index, col_index)
                    )


class RoundTripTests(unittest.TestCase):
    def _round_trip(self, sprite_file_name: str, sprite_name: str):
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", sprite_file_name))
        sprite = sprite_named(sprite_file, sprite_name)
        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            png_path = tmp.joinpath("{0}.png".format(sprite_name))
            sprite_to_png_file(sprite, png_path)
            sprite_path = tmp.joinpath("{0}.sprite".format(sprite_name))
            write_sprite_file_from_png([png_path], sprite_path)
            round_tripped_file = SpriteFile.parse(sprite_path)
        self.assertEqual(round_tripped_file.warnings, ())
        round_tripped = round_tripped_file.sprites[0]
        self.assertEqual(round_tripped.warnings, ())
        return sprite, round_tripped

    def test_indexed_no_mask(self) -> None:
        original, round_tripped = self._round_trip("basi3p02,ff9", "basi3p02")
        self.assertEqual(round_tripped.mode.data_format, "indexed")
        self.assertIsNone(round_tripped.decode_mask())
        assert_visible_pixels_match(self, original, round_tripped)

    def test_indexed_classic_mask(self) -> None:
        # switcher is old-format; the round trip becomes a new-format
        # sprite with a genuinely 1bpp mask, but the visible shape and
        # colours must be preserved exactly.
        original, round_tripped = self._round_trip("manysprites,ff9", "switcher")
        self.assertEqual(round_tripped.mode.format_name, "new")
        self.assertEqual(round_tripped.mode.mask_kind, "1bpp")
        self.assertFalse(round_tripped.mode.has_alpha)
        assert_visible_pixels_match(self, original, round_tripped)

    def test_indexed_alpha_mask_promotes_through_rgba_png(self) -> None:
        # to-png already promotes indexed+alpha sprites to an RGBA PNG,
        # so the round trip inherently becomes a 32bpp true-colour sprite
        # rather than staying indexed -- that's expected, not a bug.
        original, round_tripped = self._round_trip("manysprites,ff9", "basi4a08")
        self.assertEqual(round_tripped.mode.data_format, "RGB")
        self.assertEqual(round_tripped.mode.mask_kind, "alpha")
        assert_visible_pixels_match(self, original, round_tripped)

    def test_rgb_no_mask(self) -> None:
        original, round_tripped = self._round_trip("manysprites,ff9", "basi2c08")
        self.assertEqual(round_tripped.mode.data_format, "RGB")
        self.assertIsNone(round_tripped.decode_mask())
        assert_visible_pixels_match(self, original, round_tripped)

    def test_rgb_alpha_mask(self) -> None:
        original, round_tripped = self._round_trip("manysprites,ff9", "basi6a08")
        self.assertEqual(round_tripped.mode.mask_kind, "alpha")
        assert_visible_pixels_match(self, original, round_tripped)

    def test_rgb_colour_key_mask_becomes_alpha(self) -> None:
        # No sample sprite exercises a plain-RGB-with-colour-key PNG (only
        # RGBA-alpha ones appear in sprites/), so this checks the
        # conversion directly: from-png always promotes a true-colour
        # colour-key to a genuine alpha channel rather than reconstructing
        # ConvertPNG's colour-key mechanism in reverse.
        from riscos_sprites.from_png import _true_colour_from_png
        from riscos_sprites.png_reader import COLOUR_TYPE_RGB, PngImage

        png = PngImage(
            width=2,
            height=1,
            bit_depth=8,
            colour_type=COLOUR_TYPE_RGB,
            palette=None,
            trns_palette=None,
            trns_colour=(0, 0, 0),
            rows=[[(0, 0, 0), (10, 20, 30)]],
        )
        pixel_rows, mask_rows, has_alpha = _true_colour_from_png(png)
        self.assertTrue(has_alpha)
        self.assertEqual(mask_rows[0], [0, 255])
        self.assertEqual(pixel_rows[0][1], 10 | (20 << 8) | (30 << 16))


class MultiPngTests(unittest.TestCase):
    def test_builds_a_multi_sprite_file(self) -> None:
        sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "manysprites,ff9"))
        names = ["basi3p02", "basi0g08", "32k"]
        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            paths = []
            for name in names:
                sprite = sprite_named(sprite_file, name)
                path = tmp.joinpath("{0}.png".format(name))
                sprite_to_png_file(sprite, path)
                paths.append(path)

            output_path = tmp.joinpath("multi.sprite")
            write_sprite_file_from_png(paths, output_path)
            result = SpriteFile.parse(output_path)

        self.assertEqual(result.sprite_count, 3)
        self.assertEqual(result.warnings, ())
        self.assertEqual([sprite.name for sprite in result.sprites], names)
        for sprite in result.sprites:
            self.assertEqual(sprite.warnings, ())

    def test_name_override_requires_single_png(self) -> None:
        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
            path_a = tmp.joinpath("a.png")
            path_b = tmp.joinpath("b.png")
            sprite_to_png_file(sprite_file.sprites[0], path_a)
            sprite_to_png_file(sprite_file.sprites[0], path_b)
            with self.assertRaises(SpriteFormatError):
                build_sprite_file_bytes([path_a, path_b], name="override")

    def test_name_too_long_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
            long_path = tmp.joinpath("this-name-is-way-too-long-for-a-sprite.png")
            sprite_to_png_file(sprite_file.sprites[0], long_path)
            with self.assertRaises(SpriteFormatError):
                build_sprite_file_bytes([long_path])

    def test_explicit_name_overrides_filename_stem(self) -> None:
        with TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            sprite_file = SpriteFile.parse(ROOT.joinpath("sprites", "basi3p02,ff9"))
            path = tmp.joinpath("irrelevant.png")
            sprite_to_png_file(sprite_file.sprites[0], path)
            output_path = tmp.joinpath("out.sprite")
            write_sprite_file_from_png([path], output_path, name="shortname")
            result = SpriteFile.parse(output_path)

        self.assertEqual(result.sprites[0].name, "shortname")


if __name__ == "__main__":
    unittest.main()
