from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


FILE_HEADER_SIZE = 12
SPRITE_HEADER_SIZE = 44

OLD_MODE_INFO = {
    0: {"bpp": 1, "x_dpi": 90, "y_dpi": 45},
    1: {"bpp": 2, "x_dpi": 45, "y_dpi": 45},
    4: {"bpp": 1, "x_dpi": 45, "y_dpi": 45},
    8: {"bpp": 2, "x_dpi": 90, "y_dpi": 45},
    9: {"bpp": 4, "x_dpi": 45, "y_dpi": 45},
    12: {"bpp": 4, "x_dpi": 90, "y_dpi": 45},
    13: {"bpp": 8, "x_dpi": 45, "y_dpi": 45},
    15: {"bpp": 8, "x_dpi": 90, "y_dpi": 45},
    18: {"bpp": 1},
    19: {"bpp": 2},
    20: {"bpp": 4},
    21: {"bpp": 8},
    25: {"bpp": 1, "x_dpi": 90, "y_dpi": 90},
    26: {"bpp": 2, "x_dpi": 90, "y_dpi": 90},
    27: {"bpp": 4, "x_dpi": 90, "y_dpi": 90},
    28: {"bpp": 8, "x_dpi": 90, "y_dpi": 90},
}

NEW_SPRITE_TYPES = {
    1: {"name": "1bpp", "bpp": 1, "mask_bpp": 1, "data_format": "monochrome"},
    2: {"name": "2bpp", "bpp": 2, "mask_bpp": 1, "data_format": "indexed"},
    3: {"name": "4bpp", "bpp": 4, "mask_bpp": 1, "data_format": "indexed"},
    4: {"name": "8bpp", "bpp": 8, "mask_bpp": 1, "data_format": "indexed"},
    5: {"name": "16bpp", "bpp": 16, "mask_bpp": 1, "data_format": "RGB"},
    6: {"name": "32bpp", "bpp": 32, "mask_bpp": 1, "data_format": "RGB"},
    7: {"name": "CMYK", "bpp": 32, "mask_bpp": 1, "data_format": "CMYK"},
    8: {"name": "24bpp", "bpp": 24, "mask_bpp": 1, "data_format": "reserved"},
}


class SpriteFormatError(ValueError):
    """The sprite file could not be parsed."""


@dataclass(frozen=True)
class SpriteMode:
    format_name: str
    raw_value: int
    mode_number: int | None
    sprite_type: int
    has_alpha: bool
    bpp: int | None
    mask_bpp: int | None
    x_dpi: int | None
    y_dpi: int | None
    data_format: str | None
    description: str


@dataclass(frozen=True)
class Sprite:
    name: str
    file_offset: int
    size_bytes: int
    width_words: int
    height: int
    first_bit_used: int
    last_bit_used: int
    image_offset: int
    mask_offset: int
    image_bytes: int
    mask_bytes: int
    palette_bytes: int
    palette_entries: int
    has_mask: bool
    mode: SpriteMode
    width_pixels: int | None


@dataclass(frozen=True)
class SpriteFile:
    path: Path
    sprite_count: int
    first_sprite_offset: int
    free_offset: int
    extension_words: tuple[int, ...]
    sprites: tuple[Sprite, ...]


def parse_sprite_mode(raw_mode: int) -> SpriteMode:
    sprite_type = raw_mode >> 27
    if sprite_type == 0:
        mode_info = OLD_MODE_INFO.get(raw_mode, {})
        bpp = mode_info.get("bpp")
        x_dpi = mode_info.get("x_dpi")
        y_dpi = mode_info.get("y_dpi")
        description = f"old format, mode {raw_mode}"
        return SpriteMode(
            format_name="old",
            raw_value=raw_mode,
            mode_number=raw_mode,
            sprite_type=0,
            has_alpha=False,
            bpp=bpp,
            mask_bpp=bpp,
            x_dpi=x_dpi,
            y_dpi=y_dpi,
            data_format="indexed",
            description=description,
        )

    has_alpha = bool(raw_mode & 0x80000000)
    sprite_type = (raw_mode >> 27) & 0x0F
    type_info = NEW_SPRITE_TYPES.get(sprite_type, {})
    x_dpi = (raw_mode >> 1) & 0x1FFF
    y_dpi = (raw_mode >> 14) & 0x1FFF
    label = type_info.get("name", f"type {sprite_type}")
    if has_alpha:
        description = f"new format, {label} with alpha channel, {x_dpi}x{y_dpi} dpi"
    else:
        description = f"new format, {label}, {x_dpi}x{y_dpi} dpi"
    return SpriteMode(
        format_name="new",
        raw_value=raw_mode,
        mode_number=None,
        sprite_type=sprite_type,
        has_alpha=has_alpha,
        bpp=type_info.get("bpp"),
        mask_bpp=8 if has_alpha else type_info.get("mask_bpp"),
        x_dpi=x_dpi,
        y_dpi=y_dpi,
        data_format=type_info.get("data_format"),
        description=description,
    )


def parse_sprite_file(path: Path) -> SpriteFile:
    data = path.read_bytes()
    if len(data) < FILE_HEADER_SIZE:
        raise SpriteFormatError(f"{path} is too small to be a sprite file")

    sprite_count, first_sprite_offset, free_offset = struct.unpack_from("<III", data, 0)
    first_sprite_file_offset = area_to_file_offset(first_sprite_offset)
    free_file_offset = area_to_file_offset(free_offset)

    if first_sprite_file_offset < FILE_HEADER_SIZE:
        raise SpriteFormatError(f"{path} has an invalid first sprite offset")
    if free_file_offset > len(data):
        raise SpriteFormatError(f"{path} has an invalid free offset")

    extension_bytes = first_sprite_file_offset - FILE_HEADER_SIZE
    if extension_bytes % 4 != 0:
        raise SpriteFormatError(f"{path} has a misaligned file header")
    extension_words = tuple(
        struct.unpack_from("<I", data, FILE_HEADER_SIZE + index)[0]
        for index in range(0, extension_bytes, 4)
    )

    sprites: list[Sprite] = []
    sprite_offset = first_sprite_file_offset
    for sprite_index in range(sprite_count):
        sprite = parse_sprite(data, path, sprite_offset)
        sprites.append(sprite)
        sprite_offset += sprite.size_bytes

    if sprite_offset != free_file_offset:
        raise SpriteFormatError(
            f"{path} ended sprite parsing at 0x{sprite_offset:x}, expected 0x{free_file_offset:x}"
        )

    return SpriteFile(
        path=path,
        sprite_count=sprite_count,
        first_sprite_offset=first_sprite_offset,
        free_offset=free_offset,
        extension_words=extension_words,
        sprites=tuple(sprites),
    )


def parse_sprite(data: bytes, path: Path, sprite_offset: int) -> Sprite:
    if sprite_offset + SPRITE_HEADER_SIZE > len(data):
        raise SpriteFormatError(f"{path} has a truncated sprite header at 0x{sprite_offset:x}")

    next_offset = read_u32(data, sprite_offset)
    if next_offset < SPRITE_HEADER_SIZE:
        raise SpriteFormatError(f"{path} has a sprite with invalid size at 0x{sprite_offset:x}")

    sprite_end = sprite_offset + next_offset
    if sprite_end > len(data):
        raise SpriteFormatError(f"{path} has a sprite that runs past end of file")

    name = data[sprite_offset + 4 : sprite_offset + 16].split(b"\0", 1)[0].decode("latin-1")
    width_words = read_u32(data, sprite_offset + 16) + 1
    height = read_u32(data, sprite_offset + 20) + 1
    first_bit_used = read_u32(data, sprite_offset + 24)
    last_bit_used = read_u32(data, sprite_offset + 28)
    image_offset = read_u32(data, sprite_offset + 32)
    mask_offset = read_u32(data, sprite_offset + 36)
    raw_mode = read_u32(data, sprite_offset + 40)
    mode = parse_sprite_mode(raw_mode)

    if image_offset < SPRITE_HEADER_SIZE or image_offset > next_offset:
        raise SpriteFormatError(f"{path} has a sprite with invalid image offset: {name}")
    if mask_offset < image_offset or mask_offset > next_offset:
        raise SpriteFormatError(f"{path} has a sprite with invalid mask offset: {name}")

    palette_bytes = image_offset - SPRITE_HEADER_SIZE
    if palette_bytes % 8 != 0:
        raise SpriteFormatError(f"{path} has a sprite with a malformed palette: {name}")

    has_mask = mask_offset != image_offset
    image_bytes = (mask_offset if has_mask else next_offset) - image_offset
    mask_bytes = next_offset - mask_offset if has_mask else 0
    width_pixels = compute_width_pixels(width_words, first_bit_used, last_bit_used, mode.bpp)

    return Sprite(
        name=name,
        file_offset=sprite_offset,
        size_bytes=next_offset,
        width_words=width_words,
        height=height,
        first_bit_used=first_bit_used,
        last_bit_used=last_bit_used,
        image_offset=image_offset,
        mask_offset=mask_offset,
        image_bytes=image_bytes,
        mask_bytes=mask_bytes,
        palette_bytes=palette_bytes,
        palette_entries=palette_bytes // 8,
        has_mask=has_mask,
        mode=mode,
        width_pixels=width_pixels,
    )


def area_to_file_offset(area_offset: int) -> int:
    if area_offset < 4:
        raise SpriteFormatError(f"invalid area offset 0x{area_offset:x}")
    return area_offset - 4


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def compute_width_pixels(
    width_words: int,
    first_bit_used: int,
    last_bit_used: int,
    bits_per_pixel: int | None,
) -> int | None:
    if bits_per_pixel is None or bits_per_pixel <= 0:
        return None

    total_bits = width_words * 32
    used_bits = total_bits - first_bit_used - (31 - last_bit_used)
    if used_bits <= 0 or used_bits % bits_per_pixel != 0:
        return None
    return used_bits // bits_per_pixel


def build_summary(sprite_file: SpriteFile) -> str:
    rows = [
        [
            "Name",
            "Size",
            "Type",
            "BPP",
            "Mask",
            "Palette",
            "Mode",
        ]
    ]
    for sprite in sprite_file.sprites:
        size = unknown_or(f"{sprite.width_pixels}x{sprite.height}", sprite.width_pixels)
        sprite_type = summary_type(sprite.mode)
        bpp = unknown_or(str(sprite.mode.bpp), sprite.mode.bpp)
        mask = "yes" if sprite.has_mask else "no"
        palette = str(sprite.palette_entries)
        mode = summary_mode(sprite.mode)
        rows.append([sprite.name, size, sprite_type, bpp, mask, palette, mode])

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    return "\n".join(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows
    )


def build_details(sprite_file: SpriteFile, sprite_name: str) -> str:
    sprite = find_sprite(sprite_file, sprite_name)
    lines = [
        f"File: {sprite_file.path}",
        f"Sprite: {sprite.name}",
        f"File offset: 0x{sprite.file_offset:x}",
        f"Sprite size: {sprite.size_bytes} bytes",
        f"Dimensions: {unknown_or(str(sprite.width_pixels), sprite.width_pixels)} x {sprite.height} pixels",
        f"Width in words: {sprite.width_words}",
        f"First bit used: {sprite.first_bit_used}",
        f"Last bit used: {sprite.last_bit_used}",
        f"Image offset: 0x{sprite.image_offset:x}",
        f"Mask offset: 0x{sprite.mask_offset:x}",
        f"Image bytes: {sprite.image_bytes}",
        f"Mask bytes: {sprite.mask_bytes}",
        f"Has mask: {'yes' if sprite.has_mask else 'no'}",
        f"Palette bytes: {sprite.palette_bytes}",
        f"Palette entries: {sprite.palette_entries}",
        f"Mode format: {sprite.mode.format_name}",
        f"Mode description: {sprite.mode.description}",
        f"Mode raw value: 0x{sprite.mode.raw_value:08x}",
        f"Mode number: {unknown_or(str(sprite.mode.mode_number), sprite.mode.mode_number)}",
        f"Sprite type: {sprite.mode.sprite_type}",
        f"Alpha channel: {'yes' if sprite.mode.has_alpha else 'no'}",
        f"Bits per pixel: {unknown_or(str(sprite.mode.bpp), sprite.mode.bpp)}",
        f"Mask bits per pixel: {unknown_or(str(sprite.mode.mask_bpp), sprite.mode.mask_bpp)}",
        f"Horizontal dpi: {unknown_or(str(sprite.mode.x_dpi), sprite.mode.x_dpi)}",
        f"Vertical dpi: {unknown_or(str(sprite.mode.y_dpi), sprite.mode.y_dpi)}",
        f"Data format: {unknown_or(sprite.mode.data_format, sprite.mode.data_format)}",
    ]
    return "\n".join(lines)


def find_sprite(sprite_file: SpriteFile, sprite_name: str) -> Sprite:
    for sprite in sprite_file.sprites:
        if sprite.name == sprite_name:
            return sprite
    available = ", ".join(sprite.name for sprite in sprite_file.sprites)
    raise SpriteFormatError(f"sprite '{sprite_name}' not found; available sprites: {available}")


def summary_mode(mode: SpriteMode) -> str:
    if mode.format_name == "old":
        return str(mode.mode_number)
    alpha_suffix = "+a" if mode.has_alpha else ""
    return f"type {mode.sprite_type}{alpha_suffix} {mode.x_dpi}x{mode.y_dpi}"


def summary_type(mode: SpriteMode) -> str:
    if mode.format_name == "old":
        return "old"
    label = NEW_SPRITE_TYPES.get(mode.sprite_type, {}).get("name", f"type {mode.sprite_type}")
    if mode.has_alpha:
        return f"{label}+a"
    return label


def unknown_or(value: str, present: object | None) -> str:
    return value if present is not None else "unknown"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="riscos-dumpsprites",
        description="Display information about a RISC OS sprite file.",
    )
    parser.add_argument("sprite_file", type=Path, help="Path to the sprite file")
    parser.add_argument(
        "sprite_name",
        nargs="?",
        help="Optional sprite name for a field-by-field description",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        sprite_file = parse_sprite_file(args.sprite_file)
        if args.sprite_name:
            output = build_details(sprite_file, args.sprite_name)
        else:
            output = build_summary(sprite_file)
    except (OSError, SpriteFormatError) as exc:
        print(f"riscos-dumpsprites: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0
