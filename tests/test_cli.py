from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from riscos_dumpsprites.cli import (
    build_check_report,
    build_details,
    build_json,
    build_summary,
    parse_sprite_file,
)


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
        self.assertIn("Palette entries decoded: 4", details)
        self.assertIn("rgb=(  0,255,  0)", details)

    def test_alpha_sprites_are_decoded(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "manysprites,ff9")
        alpha_sprite = next(sprite for sprite in sprite_file.sprites if sprite.name == "basi4a08")
        self.assertEqual(alpha_sprite.mode.sprite_type, 4)
        self.assertTrue(alpha_sprite.mode.has_alpha)
        self.assertEqual(alpha_sprite.mode.bpp, 8)
        self.assertEqual(alpha_sprite.mode.mask_bpp, 8)
        self.assertEqual(alpha_sprite.width_pixels, 32)
        self.assertEqual(alpha_sprite.palette_entries, 256)

    def test_json_output_contains_palette_and_mode(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "basi3p02,ff9")
        payload = json.loads(build_json(sprite_file, "basi3p02"))
        self.assertEqual(payload["name"], "basi3p02")
        self.assertEqual(payload["mode"]["sprite_type"], 2)
        self.assertEqual(payload["palette_entries"], 4)
        self.assertEqual(payload["palette"][0]["rgb"], {"red": 0, "green": 255, "blue": 0})

    def test_check_report_ok_for_valid_sample(self) -> None:
        sprite_file = parse_sprite_file(ROOT / "sprites" / "wavytile,ff9")
        self.assertEqual(build_check_report(sprite_file), f"{ROOT / 'sprites' / 'wavytile,ff9'}: OK")

    def test_check_mode_returns_non_zero_when_warnings_present(self) -> None:
        bad_path = ROOT / "tests" / "bad-palette.sprite"
        data = bytearray((ROOT / "sprites" / "basi3p02,ff9").read_bytes())
        data[0x38:0x3C] = (0x00FFFF00).to_bytes(4, "little")
        bad_path.write_bytes(data)
        self.addCleanup(bad_path.unlink)

        result = subprocess.run(
            [sys.executable, "riscos-dumpsprites", "--check", str(bad_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("warning", result.stdout)
        self.assertIn("palette entry words differ", result.stdout)

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
