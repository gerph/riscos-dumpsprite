from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from riscos_dumpsprites.cli import build_details, build_summary, parse_sprite_file


ROOT = Path(__file__).resolve().parents[1]


class SpriteParserTests(unittest.TestCase):
    def test_summary_for_wavytile(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "wavytile,ff9")
        self.assertEqual(sprite_file.sprite_count, 3)

        first = sprite_file.sprites[0]
        self.assertEqual(first.name, "tile_1r")
        self.assertEqual(first.width_pixels, 32)
        self.assertEqual(first.height, 16)
        self.assertTrue(first.has_mask)
        self.assertEqual(first.mode.mode_number, 27)
        self.assertEqual(first.mode.bpp, 4)

        summary = build_summary(sprite_file)
        self.assertIn("tile_1r", summary)
        self.assertIn("32x16", summary)
        self.assertIn("old", summary)
        self.assertIn("27", summary)

    def test_details_for_new_format_sprite(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "basi3p02,ff9")
        details = build_details(sprite_file, "basi3p02")
        self.assertIn("Mode format: new", details)
        self.assertIn("Sprite type: 2", details)
        self.assertIn("Bits per pixel: 2", details)
        self.assertIn("Horizontal dpi: 90", details)
        self.assertIn("Vertical dpi: 90", details)

    def test_alpha_sprites_are_decoded(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "manysprites,ff9")
        alpha_sprite = next(sprite for sprite in sprite_file.sprites if sprite.name == "basi4a08")
        self.assertEqual(alpha_sprite.mode.sprite_type, 4)
        self.assertTrue(alpha_sprite.mode.has_alpha)
        self.assertEqual(alpha_sprite.mode.bpp, 8)
        self.assertEqual(alpha_sprite.mode.mask_bpp, 8)
        self.assertEqual(alpha_sprite.width_pixels, 32)

    def test_cli_missing_sprite_reports_available_names(self) -> None:
        result = subprocess.run(
            [sys.executable, "riscos-dumpsprites", "sprites/wavytile,ff9", "missing"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("available sprites", result.stderr)
        self.assertIn("tile_1r-8", result.stderr)


if __name__ == "__main__":
    unittest.main()
