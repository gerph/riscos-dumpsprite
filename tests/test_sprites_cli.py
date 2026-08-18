from __future__ import annotations

import json
import shutil
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


class ToPngSubcommandTests(unittest.TestCase):
    def test_converts_a_single_sprite(self) -> None:
        output_path = ROOT / "tests" / "basi3p02-cli.png"
        self.addCleanup(lambda: output_path.unlink(missing_ok=True))

        result = run_riscos_sprites(
            "to-png", "sprites/basi3p02,ff9", "basi3p02", str(output_path)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted basi3p02", result.stdout)
        self.assertTrue(output_path.exists())
        with output_path.open("rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")

    def test_all_writes_one_png_per_selected_sprite(self) -> None:
        output_dir = ROOT / "tests" / "to-png-all-cli"
        self.addCleanup(lambda: shutil.rmtree(output_dir, ignore_errors=True))

        result = run_riscos_sprites(
            "to-png",
            "sprites/manysprites,ff9",
            str(output_dir),
            "--all",
            "--name",
            "basi4*",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted 2 sprite(s)", result.stdout)
        produced = sorted(p.name for p in output_dir.glob("*.png"))
        self.assertEqual(produced, ["basi4a08.png", "basi4a16.png"])

    def test_all_rejects_a_sprite_name(self) -> None:
        result = run_riscos_sprites(
            "to-png", "sprites/wavytile,ff9", "tile_1r", "out-dir", "--all"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not take a sprite name", result.stderr)

    def test_missing_sprite_name_without_all_is_an_error(self) -> None:
        result = run_riscos_sprites("to-png", "sprites/wavytile,ff9", "out.png")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a sprite name", result.stderr)


class ToPnmSubcommandTests(unittest.TestCase):
    def test_converts_a_single_sprite_to_ppm_by_default(self) -> None:
        output_path = ROOT / "tests" / "basi3p02-cli.pnm"
        self.addCleanup(lambda: output_path.unlink(missing_ok=True))

        result = run_riscos_sprites(
            "to-pnm", "sprites/basi3p02,ff9", "basi3p02", str(output_path)
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted basi3p02", result.stdout)
        with output_path.open("rb") as handle:
            self.assertEqual(handle.read(2), b"P6")

    def test_indexed_flag_writes_pgm(self) -> None:
        output_path = ROOT / "tests" / "basi3p02-indexed-cli.pnm"
        self.addCleanup(lambda: output_path.unlink(missing_ok=True))

        result = run_riscos_sprites(
            "to-pnm", "--indexed", "sprites/basi3p02,ff9", "basi3p02", str(output_path)
        )
        self.assertEqual(result.returncode, 0)
        with output_path.open("rb") as handle:
            self.assertEqual(handle.read(2), b"P5")

    def test_all_writes_one_pnm_per_selected_sprite(self) -> None:
        output_dir = ROOT / "tests" / "to-pnm-all-cli"
        self.addCleanup(lambda: shutil.rmtree(output_dir, ignore_errors=True))

        result = run_riscos_sprites(
            "to-pnm",
            "sprites/manysprites,ff9",
            str(output_dir),
            "--all",
            "--name",
            "basi4*",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Converted 2 sprite(s)", result.stdout)
        produced = sorted(p.name for p in output_dir.glob("*.pnm"))
        self.assertEqual(produced, ["basi4a08.pnm", "basi4a16.pnm"])

    def test_all_rejects_a_sprite_name(self) -> None:
        result = run_riscos_sprites(
            "to-pnm", "sprites/wavytile,ff9", "tile_1r", "out-dir", "--all"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not take a sprite name", result.stderr)

    def test_missing_sprite_name_without_all_is_an_error(self) -> None:
        result = run_riscos_sprites("to-pnm", "sprites/wavytile,ff9", "out.pnm")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a sprite name", result.stderr)


class FromPngSubcommandTests(unittest.TestCase):
    def test_builds_a_sprite_file_from_one_png(self) -> None:
        # Sprite names are limited to 12 characters, so the source PNG's
        # filename stem must be kept short here.
        png_path = ROOT / "tests" / "cli-src.png"
        sprite_path = ROOT / "tests" / "cli-result.sprite"
        self.addCleanup(lambda: png_path.unlink(missing_ok=True))
        self.addCleanup(lambda: sprite_path.unlink(missing_ok=True))

        convert = run_riscos_sprites(
            "to-png", "sprites/basi3p02,ff9", "basi3p02", str(png_path)
        )
        self.assertEqual(convert.returncode, 0)

        result = run_riscos_sprites("from-png", str(png_path), str(sprite_path))
        self.assertEqual(result.returncode, 0)
        self.assertIn("Wrote 1 sprite(s)", result.stdout)

        sprite_file = SpriteFile.parse(sprite_path)
        self.assertEqual(sprite_file.sprite_count, 1)
        self.assertEqual(sprite_file.sprites[0].name, "cli-src")
        self.assertEqual(sprite_file.warnings, ())

    def test_multiple_pngs_become_multiple_sprites(self) -> None:
        png_a = ROOT / "tests" / "multi-a.png"
        png_b = ROOT / "tests" / "multi-b.png"
        sprite_path = ROOT / "tests" / "cli-multi.sprite"
        for path in (png_a, png_b, sprite_path):
            self.addCleanup(lambda p=path: p.unlink(missing_ok=True))

        self.assertEqual(
            run_riscos_sprites("to-png", "sprites/basi3p02,ff9", "basi3p02", str(png_a)).returncode, 0
        )
        self.assertEqual(
            run_riscos_sprites("to-png", "sprites/wavytile,ff9", "tile_1r", str(png_b)).returncode, 0
        )

        result = run_riscos_sprites("from-png", str(png_a), str(png_b), str(sprite_path))
        self.assertEqual(result.returncode, 0)
        self.assertIn("Wrote 2 sprite(s)", result.stdout)

        sprite_file = SpriteFile.parse(sprite_path)
        self.assertEqual([s.name for s in sprite_file.sprites], ["multi-a", "multi-b"])

    def test_name_flag_rejects_multiple_pngs(self) -> None:
        png_a = ROOT / "tests" / "name-a.png"
        png_b = ROOT / "tests" / "name-b.png"
        for path in (png_a, png_b):
            self.addCleanup(lambda p=path: p.unlink(missing_ok=True))
        run_riscos_sprites("to-png", "sprites/basi3p02,ff9", "basi3p02", str(png_a))
        run_riscos_sprites("to-png", "sprites/basi3p02,ff9", "basi3p02", str(png_b))

        result = run_riscos_sprites(
            "from-png", "--name", "x", str(png_a), str(png_b), "out.sprite"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single PNG file", result.stderr)


if __name__ == "__main__":
    unittest.main()
