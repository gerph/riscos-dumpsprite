# riscos-dumpsprites

`riscos-dumpsprites` is a Python command line tool for inspecting RISC OS Sprite files.

It supports two output modes:

- A column summary of all sprites in a sprite file.
- A field-by-field report for a single named sprite.
- Machine-readable JSON output for either form.
- Validation reporting for malformed or suspicious sprite structures.

## Usage

Summarise the contents of a sprite file:

```bash
./riscos-dumpsprites sprites/wavytile,ff9
```

Describe a single sprite:

```bash
./riscos-dumpsprites sprites/basi3p02,ff9 basi3p02
```

Emit JSON:

```bash
./riscos-dumpsprites --json sprites/manysprites,ff9
./riscos-dumpsprites --json sprites/basi3p02,ff9 basi3p02
```

Validate a file:

```bash
./riscos-dumpsprites --check sprites/wavytile,ff9
```

The parser understands both old-format sprite mode words and the newer sprite mode word format, including alpha-channel and CMYK-related sprite type handling.
Detailed reports and JSON output include decoded palette entries. Text output previews the first 16 palette entries for large palettes.
For documented old-format mode numbers, the tool also reports standard mode metadata such as text resolution, graphics resolution, OS units, and logical colour count.
Summary output distinguishes sprites with no mask, classic 1bpp masks, and 8bpp alpha masks.

## Development

Run the test suite with:

```bash
python3 -m unittest discover -s tests
```

Sample sprite files used for testing live in [`sprites/`](sprites/).

## References

- <https://www.riscos.com/support/developers/prm/sprites.html>
- <https://www.riscos.com/support/developers/prm/video.html>
- <https://www.riscos.com/support/developers/riscos6/graphics/sprites/cmyk.html>
- <https://www.riscos.com/support/developers/riscos6/graphics/sprites/alphachannel.html>
