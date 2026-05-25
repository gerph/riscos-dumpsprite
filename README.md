# riscos-dumpsprites

`riscos-dumpsprites` is a Python command line tool for inspecting RISC OS Sprite files.

It supports two output modes:

- A column summary of all sprites in a sprite file.
- A field-by-field report for a single named sprite.

## Usage

Summarise the contents of a sprite file:

```bash
./riscos-dumpsprites sprites/wavytile,ff9
```

Describe a single sprite:

```bash
./riscos-dumpsprites sprites/basi3p02,ff9 basi3p02
```

The parser understands both old-format sprite mode words and the newer sprite mode word format, including alpha-channel and CMYK-related sprite type handling.

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

