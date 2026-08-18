# riscos-sprites / riscos-dumpsprites

Python command line tools for inspecting RISC OS Sprite files and converting them to and
from PNG and PNM. The sprite-decoding and conversion logic lives in the `riscos_sprites`
library package; both command line tools are built on top of it.

- **`riscos-sprites`** is the main tool, with subcommands: `list`, `extract`, `to-png`,
  `to-pnm`, and `from-png`.
- **`riscos-dumpsprites`** is kept for backward compatibility. It behaves exactly as it
  always has (summary/detail/JSON/`--check`/`--extract`) and is equivalent to
  `riscos-sprites list` plus `riscos-sprites extract`.

## `riscos-sprites list`

Summarise the contents of a sprite file:

```bash
./riscos-sprites list sprites/wavytile,ff9
```

Describe a single sprite:

```bash
./riscos-sprites list sprites/basi3p02,ff9 basi3p02
```

Emit JSON:

```bash
./riscos-sprites list --json sprites/manysprites,ff9
./riscos-sprites list --json sprites/basi3p02,ff9 basi3p02
```

Validate a file:

```bash
./riscos-sprites list --check sprites/wavytile,ff9
```

Show richer text output:

```bash
./riscos-sprites list --verbose sprites/manysprites,ff9
```

Filter the sprite list:

```bash
./riscos-sprites list --name 'basi4*' sprites/manysprites,ff9
./riscos-sprites list --type 32bpp+a --has-mask sprites/manysprites,ff9
./riscos-sprites list --mode 27 sprites/wavytile,ff9
```

The parser understands both old-format sprite mode words and the newer sprite mode word
format, including alpha-channel and CMYK-related sprite type handling.
Detailed reports and JSON output include decoded palette entries. Text output previews the
first 16 palette entries for large palettes.
For documented old-format mode numbers, the tool also reports standard mode metadata such as
text resolution, graphics resolution, OS units, and logical colour count.
Summary output distinguishes sprites with no mask, classic 1bpp masks, and 8bpp alpha masks.

## `riscos-sprites extract`

Write a single sprite out to its own sprite file:

```bash
./riscos-sprites extract sprites/wavytile,ff9 tile_1r tile_1r,ff9
```

## `riscos-sprites to-png`

Convert a single sprite to a PNG file:

```bash
./riscos-sprites to-png sprites/basi3p02,ff9 basi3p02 basi3p02.png
```

Convert every sprite in a file (optionally filtered, using the same `--name`/`--mode`/
`--type`/`--has-mask` options as `list`) into a directory, one PNG per sprite named after
the sprite:

```bash
./riscos-sprites to-png sprites/manysprites,ff9 --all out/
./riscos-sprites to-png sprites/manysprites,ff9 --all out/ --name 'basi4*'
```

Masked sprites are converted following the same strategy as the RISC OS `ConvertPNG`
module: a masked sprite first tries to find an unused palette index (indexed sprites) or an
unused RGB colour, using it as a colour-key, and only promotes to a larger palette, plain
true-colour, or a full alpha channel if no such colour-key is available. CMYK sprites always
promote straight to an alpha channel. Sprites with a genuine alpha channel already (new-format
alpha-masked sprites) use that alpha data directly.

## `riscos-sprites to-pnm`

Convert a sprite to a plain PPM (P6), with any palette expanded to 8-bit-per-channel RGB and
no gamma or other colour correction applied:

```bash
./riscos-sprites to-pnm sprites/basi3p02,ff9 basi3p02 basi3p02.ppm
```

For indexed sprites, `--indexed` instead writes a PGM (P5) whose pixel data is the raw
palette *index* per pixel, preceded by `#` comment lines recording the palette, sprite mode,
and DPI. A plain PGM viewer only shows a rough grayscale-by-index image, but the comments let
you (or another tool) recover the true colours -- useful for a quick manual check of sprite
content:

```bash
./riscos-sprites to-pnm --indexed sprites/basi3p02,ff9 basi3p02 basi3p02.pnm
```

`--all` works the same way as `to-png`, writing one `.pnm` per selected sprite into a
directory. Sprite masks/alpha are not representable in PNM and are ignored by both forms:
every pixel's underlying colour or index is written regardless of whether it would be masked
out when the sprite is actually plotted.

## `riscos-sprites from-png`

Build a sprite file from one or more PNG images, each becoming one sprite:

```bash
./riscos-sprites from-png icon.png icon,ff9
./riscos-sprites from-png tile1.png tile2.png tile3.png tiles,ff9
```

By default each sprite is named after its PNG's filename stem (RISC OS sprite names are
limited to 12 characters). Use `--name` to give an explicit name, which only works when
converting a single PNG:

```bash
./riscos-sprites from-png --name myicon a-very-long-filename.png icon,ff9
```

Paletted and grayscale PNGs become indexed sprites at the PNG's own bit depth (grayscale is
promoted to a synthesized grey-ramp palette); RGB/RGBA PNGs become 32bpp true-colour sprites.
Always produces new-format sprites; there is no CMYK or 16-bit-per-channel output. A purely
binary (every value 0 or 255) `tRNS`/alpha channel on an indexed source becomes a classic
1bpp mask; anything with intermediate values becomes a genuine 8bpp alpha mask. True-colour
sources always become an 8bpp alpha mask when they carry any transparency at all.

## `riscos-dumpsprites`

Equivalent to `riscos-sprites list`/`extract`, using flags instead of subcommands (kept
for backward compatibility with existing scripts):

```bash
./riscos-dumpsprites sprites/wavytile,ff9
./riscos-dumpsprites sprites/basi3p02,ff9 basi3p02
./riscos-dumpsprites --json sprites/manysprites,ff9
./riscos-dumpsprites --check sprites/wavytile,ff9
./riscos-dumpsprites --verbose sprites/manysprites,ff9
./riscos-dumpsprites --name 'basi4*' sprites/manysprites,ff9
./riscos-dumpsprites sprites/wavytile,ff9 tile_1r --extract tile_1r,ff9
```

## Development

Run the test suite with:

```bash
python3 -m unittest discover -s tests
```

Sample sprite files used for testing live in [`sprites/`](sprites/).

## Publishing

To publish a new version to PyPI:

1. Update the version in `pyproject.toml`.
2. Build and publish using `make`:
   ```bash
   make publish
   ```
   *Note: This requires `twine` to be configured with your PyPI credentials.*

## References

- <https://www.riscos.com/support/developers/prm/sprites.html>
- <https://www.riscos.com/support/developers/prm/video.html>
- <https://www.riscos.com/support/developers/riscos6/graphics/sprites/cmyk.html>
- <https://www.riscos.com/support/developers/riscos6/graphics/sprites/alphachannel.html>
