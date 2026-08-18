"""
Convert a decoded RISC OS sprite to a PNM (PPM/PGM) file.

Two forms are supported:

- Plain PPM (P6): 8-bit-per-channel RGB. Indexed sprites are expanded
  through their palette, true-colour/CMYK sprites are used as decoded.
  No gamma or other colour correction is applied anywhere.
- Extended indexed PGM (P5), for indexed sprites only: the pixel data is
  the raw palette *index* per pixel rather than a colour, preceded by
  `#` comment lines recording the palette, sprite mode, and DPI. A
  plain PGM viewer only shows a rough grayscale-by-index image, but the
  comments let a human (or another tool) recover the true colours --
  useful for checking sprite content by eye. Requested with --indexed.

Sprite masks/alpha are not representable in PNM and are ignored: every
pixel's underlying colour or index is written regardless of whether it
would be masked out when the sprite is actually plotted.
"""

from __future__ import annotations

from pathlib import Path

from .errors import SpriteFormatError
from .sprite import Sprite


def _format_dpi(sprite: Sprite) -> str:
    if sprite.mode.x_dpi is None or sprite.mode.y_dpi is None:
        return "unknown"
    return "{0}x{1}".format(sprite.mode.x_dpi, sprite.mode.y_dpi)


def sprite_to_ppm_bytes(sprite: Sprite) -> bytes:
    pixels = sprite.decode_pixels()
    body = bytearray()

    if pixels.kind == "indexed":
        palette = sprite.effective_palette()
        colours = [(entry.red, entry.green, entry.blue) for entry in palette]
        for row in pixels.rows:
            for index in row:
                colour = colours[index] if index < len(colours) else (0, 0, 0)
                body.extend(colour)
    else:
        for row in pixels.rows:
            for colour in row:
                body.extend(colour)

    header = "P6\n{0} {1}\n255\n".format(pixels.width, pixels.height).encode("ascii")
    return header + bytes(body)


def sprite_to_indexed_pgm_bytes(sprite: Sprite) -> bytes:
    pixels = sprite.decode_pixels()
    if pixels.kind != "indexed":
        raise SpriteFormatError("{0}: --indexed PNM output requires an indexed sprite".format(sprite.name))

    palette = sprite.effective_palette()
    maxval = (1 << sprite.mode.bpp) - 1

    comment_lines = [
        "# sprite: {0}".format(sprite.name),
        "# mode: {0}".format(sprite.mode.description),
        "# dpi: {0}".format(_format_dpi(sprite)),
        "# palette: index red green blue",
    ]
    comment_lines.extend(
        "# {0} {1} {2} {3}".format(entry.index, entry.red, entry.green, entry.blue) for entry in palette
    )

    header = "P5\n" + "\n".join(comment_lines) + "\n{0} {1}\n{2}\n".format(pixels.width, pixels.height, maxval)
    body = bytearray()
    for row in pixels.rows:
        body.extend(row)

    return header.encode("ascii") + bytes(body)


def sprite_to_pnm_bytes(sprite: Sprite, *, indexed: bool = False) -> bytes:
    if indexed:
        return sprite_to_indexed_pgm_bytes(sprite)
    return sprite_to_ppm_bytes(sprite)


def sprite_to_pnm_file(sprite: Sprite, path: Path, *, indexed: bool = False) -> None:
    path.write_bytes(sprite_to_pnm_bytes(sprite, indexed=indexed))
