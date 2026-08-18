from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from riscos_sprites import SpriteFile


ROOT = Path(__file__).resolve().parents[1]


def run_riscos_sprites(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "riscos-sprites", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ListSubcommandTests(unittest.TestCase):
    def test_summary_for_wavytile(self) -> None:
        result = run_riscos_sprites("list", "sprites/wavytile,ff9")
        self.assertEqual(result.returncode, 0)
        self.assertIn("tile_1r", result.stdout)
        self.assertIn("32x16", result.stdout)
        self.assertIn("old", result.stdout)
        self.assertIn("1bpp", result.stdout)
        self.assertIn("27 (640x480)", result.stdout)

    def test_details_for_named_sprite(self) -> None:
        result = run_riscos_sprites("list", "sprites/basi3p02,ff9", "basi3p02")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Mode format: new", result.stdout)
        self.assertIn("Sprite type: 2", result.stdout)
        self.assertIn("Bits per pixel: 2", result.stdout)
        self.assertIn("Palette entries decoded: 4", result.stdout)

    def test_json_output_for_named_sprite(self) -> None:
        result = run_riscos_sprites("list", "--json", "sprites/basi3p02,ff9", "basi3p02")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["name"], "basi3p02")
        self.assertEqual(payload["mode"]["sprite_type"], 2)
        self.assertEqual(payload["palette_entries"], 4)

    def test_verbose_name_filter(self) -> None:
        result = run_riscos_sprites(
            "list", "--verbose", "--name", "basi4*", "sprites/manysprites,ff9"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Sprites shown: 2 of 43", result.stdout)
        self.assertIn("basi4a08", result.stdout)
        self.assertNotIn("basi0g01", result.stdout)

    def test_check_ok_for_valid_sample(self) -> None:
        result = run_riscos_sprites("list", "--check", "sprites/wavytile,ff9")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK", result.stdout)

    def test_check_returns_non_zero_when_warnings_present(self) -> None:
        bad_path = ROOT / "tests" / "bad-palette-sprites-cli.sprite"
        data = bytearray((ROOT / "sprites" / "basi3p02,ff9").read_bytes())
        data[0x38:0x3C] = (0x00FFFF00).to_bytes(4, "little")
        bad_path.write_bytes(data)
        self.addCleanup(bad_path.unlink)

        result = run_riscos_sprites("list", "--check", str(bad_path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("warning", result.stdout)
        self.assertIn("palette entry words differ", result.stdout)

    def test_missing_sprite_reports_available_names(self) -> None:
        result = run_riscos_sprites("list", "sprites/wavytile,ff9", "missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("available sprites", result.stderr)
        self.assertIn("tile_1r-8", result.stderr)


class ExtractSubcommandTests(unittest.TestCase):
    def test_extract_writes_single_sprite_file(self) -> None:
        extracted_path = ROOT / "tests" / "tile_1r-sprites-cli.sprite"
        self.addCleanup(lambda: extracted_path.unlink(missing_ok=True))

        result = run_riscos_sprites(
            "extract", "sprites/wavytile,ff9", "tile_1r", str(extracted_path)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Extracted tile_1r", result.stdout)
        self.assertTrue(extracted_path.exists())

        sprite_file = SpriteFile.parse(extracted_path)
        self.assertEqual(sprite_file.sprite_count, 1)
        self.assertEqual(sprite_file.sprites[0].name, "tile_1r")
        self.assertEqual(sprite_file.sprites[0].size_bytes, 684)

    def test_extract_requires_sprite_name_and_output(self) -> None:
        result = run_riscos_sprites("extract", "sprites/wavytile,ff9")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage", result.stderr)


if __name__ == "__main__":
    unittest.main()
