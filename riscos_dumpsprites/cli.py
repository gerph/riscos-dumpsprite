from __future__ import annotations

import argparse
import fnmatch
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


FILE_HEADER_SIZE = 12
SPRITE_HEADER_SIZE = 44

OLD_MODE_INFO = {
    0: {"text": (80, 32), "pixel": (640, 256), "os_units": (1280, 1024), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 20, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    1: {"text": (40, 32), "pixel": (320, 256), "os_units": (1280, 1024), "logical_colours": 4, "x_dpi": 45, "y_dpi": 45, "kind": "graphics", "memory_kb": 20, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    2: {"text": (20, 32), "pixel": (160, 256), "os_units": (1280, 1024), "logical_colours": 16, "x_dpi": 22, "y_dpi": 45, "kind": "graphics", "memory_kb": 40, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    3: {"text": (80, 25), "pixel": None, "os_units": None, "logical_colours": 2, "kind": "text", "memory_kb": 40, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    4: {"text": (40, 32), "pixel": (320, 256), "os_units": (1280, 1024), "logical_colours": 2, "x_dpi": 45, "y_dpi": 45, "kind": "graphics", "memory_kb": 20, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    5: {"text": (20, 32), "pixel": (160, 256), "os_units": (1280, 1024), "logical_colours": 4, "x_dpi": 22, "y_dpi": 45, "kind": "graphics", "memory_kb": 20, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    6: {"text": (40, 25), "pixel": None, "os_units": None, "logical_colours": 2, "kind": "text", "memory_kb": 20, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    7: {"text": (40, 25), "pixel": None, "os_units": None, "logical_colours": 16, "kind": "teletext", "memory_kb": 80, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    8: {"text": (80, 32), "pixel": (640, 256), "os_units": (1280, 1024), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 40, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    9: {"text": (40, 32), "pixel": (320, 256), "os_units": (1280, 1024), "logical_colours": 16, "x_dpi": 45, "y_dpi": 45, "kind": "graphics", "memory_kb": 40, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    10: {"text": (20, 32), "pixel": (160, 256), "os_units": (1280, 1024), "logical_colours": 256, "x_dpi": 22, "y_dpi": 45, "kind": "graphics", "memory_kb": 80, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    11: {"text": (80, 25), "pixel": (640, 250), "os_units": (1280, 1000), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 40, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    12: {"text": (80, 32), "pixel": (640, 256), "os_units": (1280, 1024), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 80, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    13: {"text": (40, 32), "pixel": (320, 256), "os_units": (1280, 1024), "logical_colours": 256, "x_dpi": 45, "y_dpi": 45, "kind": "graphics", "memory_kb": 80, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    14: {"text": (80, 25), "pixel": (640, 250), "os_units": (1280, 1000), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 80, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    15: {"text": (80, 32), "pixel": (640, 256), "os_units": (1280, 1024), "logical_colours": 256, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 160, "hz": 50, "monitors": (0, 1, 3, 4, 5)},
    16: {"text": (132, 32), "pixel": (1056, 256), "os_units": (2112, 1024), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 132, "hz": 50, "monitors": (0, 1)},
    17: {"text": (132, 25), "pixel": (1056, 250), "os_units": (2112, 1000), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 132, "hz": 50, "monitors": (0, 1)},
    18: {"text": (80, 64), "pixel": (640, 512), "os_units": (1280, 1024), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 40, "hz": 50, "monitors": (1,)},
    19: {"text": (80, 64), "pixel": (640, 512), "os_units": (1280, 1024), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 80, "hz": 50, "monitors": (1,)},
    20: {"text": (80, 64), "pixel": (640, 512), "os_units": (1280, 1024), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 160, "hz": 50, "monitors": (1,)},
    21: {"text": (80, 64), "pixel": (640, 512), "os_units": (1280, 1024), "logical_colours": 256, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 320, "hz": 50, "monitors": (1,)},
    22: {"text": (96, 36), "pixel": (768, 288), "os_units": (768, 576), "logical_colours": 16, "x_dpi": 180, "y_dpi": 90, "kind": "graphics", "memory_kb": 108, "hz": 50, "monitors": (0, 1)},
    23: {"text": (144, 56), "pixel": (1152, 896), "os_units": (2304, 1792), "logical_colours": 2, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 126, "hz": 64, "monitors": (2,)},
    24: {"text": (132, 32), "pixel": (1056, 256), "os_units": (2112, 1024), "logical_colours": 256, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 264, "hz": 50, "monitors": (0, 1)},
    25: {"text": (80, 60), "pixel": (640, 480), "os_units": (1280, 960), "logical_colours": 2, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 38, "hz": 60, "monitors": (1, 3, 4, 5)},
    26: {"text": (80, 60), "pixel": (640, 480), "os_units": (1280, 960), "logical_colours": 4, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 75, "hz": 60, "monitors": (1, 3, 4, 5)},
    27: {"text": (80, 60), "pixel": (640, 480), "os_units": (1280, 960), "logical_colours": 16, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 150, "hz": 60, "monitors": (1, 3, 4, 5)},
    28: {"text": (80, 60), "pixel": (640, 480), "os_units": (1280, 960), "logical_colours": 256, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 300, "hz": 60, "monitors": (1, 3, 4, 5)},
    29: {"text": (100, 75), "pixel": (800, 600), "os_units": (1600, 1200), "logical_colours": 2, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 59, "hz": 56, "monitors": (1, 4)},
    30: {"text": (100, 75), "pixel": (800, 600), "os_units": (1600, 1200), "logical_colours": 4, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 117, "hz": 56, "monitors": (1, 4)},
    31: {"text": (100, 75), "pixel": (800, 600), "os_units": (1600, 1200), "logical_colours": 16, "x_dpi": 90, "y_dpi": 90, "kind": "graphics", "memory_kb": 234, "hz": 56, "monitors": (1, 4)},
    33: {"text": (96, 36), "pixel": (768, 288), "os_units": (1536, 1152), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 27, "hz": 50, "monitors": (0, 1)},
    34: {"text": (96, 36), "pixel": (768, 288), "os_units": (1536, 1152), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 54, "hz": 50, "monitors": (0, 1)},
    35: {"text": (96, 36), "pixel": (768, 288), "os_units": (1536, 1152), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 108, "hz": 50, "monitors": (0, 1)},
    36: {"text": (96, 36), "pixel": (768, 288), "os_units": (1536, 1152), "logical_colours": 256, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 216, "hz": 50, "monitors": (0, 1)},
    37: {"text": (112, 44), "pixel": (896, 352), "os_units": (1792, 1408), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 39, "hz": 60, "monitors": (1,)},
    38: {"text": (112, 44), "pixel": (896, 352), "os_units": (1792, 1408), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 77, "hz": 60, "monitors": (1,)},
    39: {"text": (112, 44), "pixel": (896, 352), "os_units": (1792, 1408), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 154, "hz": 60, "monitors": (1,)},
    40: {"text": (112, 44), "pixel": (896, 352), "os_units": (1792, 1408), "logical_colours": 256, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 308, "hz": 60, "monitors": (1,)},
    41: {"text": (80, 44), "pixel": (640, 352), "os_units": (1280, 1408), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 28, "hz": 60, "monitors": (1, 3, 4, 5)},
    42: {"text": (80, 44), "pixel": (640, 352), "os_units": (1280, 1408), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 55, "hz": 60, "monitors": (1, 3, 4, 5)},
    43: {"text": (80, 44), "pixel": (640, 352), "os_units": (1280, 1408), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 110, "hz": 60, "monitors": (1, 3, 4, 5)},
    44: {"text": (80, 25), "pixel": (640, 200), "os_units": (1280, 800), "logical_colours": 2, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 16, "hz": 60, "monitors": (1, 3, 4, 5)},
    45: {"text": (80, 25), "pixel": (640, 200), "os_units": (1280, 800), "logical_colours": 4, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 31, "hz": 60, "monitors": (1, 3, 4, 5)},
    46: {"text": (80, 25), "pixel": (640, 200), "os_units": (1280, 800), "logical_colours": 16, "x_dpi": 90, "y_dpi": 45, "kind": "graphics", "memory_kb": 63, "hz": 60, "monitors": (1, 3, 4, 5)},
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
    base_mode_number: int | None
    shadow_mode: bool
    sprite_type: int
    has_alpha: bool
    kind: str | None
    bpp: int | None
    mask_bpp: int | None
    mask_kind: str | None
    logical_colours: int | None
    text_columns: int | None
    text_rows: int | None
    pixel_width: int | None
    pixel_height: int | None
    os_unit_width: int | None
    os_unit_height: int | None
    memory_kb: int | None
    refresh_hz: int | None
    monitor_types: tuple[int, ...]
    x_dpi: int | None
    y_dpi: int | None
    data_format: str | None
    colour_model: str | None
    description: str


@dataclass(frozen=True)
class PaletteEntry:
    index: int
    word1: int
    word2: int
    red: int
    green: int
    blue: int
    words_match: bool


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
    palette: tuple[PaletteEntry, ...]
    has_mask: bool
    mode: SpriteMode
    width_pixels: int | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SpriteFile:
    path: Path
    sprite_count: int
    first_sprite_offset: int
    free_offset: int
    extension_words: tuple[int, ...]
    sprites: tuple[Sprite, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SpriteSelection:
    sprite_file: SpriteFile
    sprites: tuple[Sprite, ...]


def parse_sprite_mode(raw_mode: int) -> SpriteMode:
    sprite_type = raw_mode >> 27
    if sprite_type == 0:
        shadow_mode = bool(raw_mode & 0x80)
        base_mode = raw_mode & 0x7F
        mode_info = OLD_MODE_INFO.get(base_mode, {})
        bpp = infer_bpp_from_logical_colours(mode_info.get("logical_colours"))
        x_dpi = mode_info.get("x_dpi")
        y_dpi = mode_info.get("y_dpi")
        pixel = mode_info.get("pixel")
        logical_colours = mode_info.get("logical_colours")
        if pixel and logical_colours:
            description = (
                f"old format, mode {base_mode}, {pixel[0]}x{pixel[1]} pixels, "
                f"{logical_colours} logical colours"
            )
        else:
            description = f"old format, mode {base_mode}"
        if shadow_mode:
            description += ", shadow screen"
        return SpriteMode(
            format_name="old",
            raw_value=raw_mode,
            mode_number=raw_mode,
            base_mode_number=base_mode,
            shadow_mode=shadow_mode,
            sprite_type=0,
            has_alpha=False,
            kind=mode_info.get("kind"),
            bpp=bpp,
            mask_bpp=1,
            mask_kind="1bpp" if bpp is not None else None,
            logical_colours=logical_colours,
            text_columns=tuple_or_none(mode_info.get("text"), 0),
            text_rows=tuple_or_none(mode_info.get("text"), 1),
            pixel_width=tuple_or_none(pixel, 0),
            pixel_height=tuple_or_none(pixel, 1),
            os_unit_width=tuple_or_none(mode_info.get("os_units"), 0),
            os_unit_height=tuple_or_none(mode_info.get("os_units"), 1),
            memory_kb=mode_info.get("memory_kb"),
            refresh_hz=mode_info.get("hz"),
            monitor_types=mode_info.get("monitors", ()),
            x_dpi=x_dpi,
            y_dpi=y_dpi,
            data_format="indexed",
            colour_model="indexed",
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
        base_mode_number=None,
        shadow_mode=False,
        sprite_type=sprite_type,
        has_alpha=has_alpha,
        kind="graphics",
        bpp=type_info.get("bpp"),
        mask_bpp=8 if has_alpha else type_info.get("mask_bpp"),
        mask_kind="alpha" if has_alpha else "1bpp",
        logical_colours=None,
        text_columns=None,
        text_rows=None,
        pixel_width=None,
        pixel_height=None,
        os_unit_width=None,
        os_unit_height=None,
        memory_kb=None,
        refresh_hz=None,
        monitor_types=(),
        x_dpi=x_dpi,
        y_dpi=y_dpi,
        data_format=type_info.get("data_format"),
        colour_model=type_info.get("data_format"),
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

    warnings: list[str] = []
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

    if free_file_offset != len(data):
        warnings.append(
            f"file free offset 0x{free_offset:x} does not match file size 0x{len(data) + 4:x}"
        )

    return SpriteFile(
        path=path,
        sprite_count=sprite_count,
        first_sprite_offset=first_sprite_offset,
        free_offset=free_offset,
        extension_words=extension_words,
        sprites=tuple(sprites),
        warnings=tuple(warnings),
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

    palette = decode_palette(data, sprite_offset + SPRITE_HEADER_SIZE, palette_bytes)
    has_mask = mask_offset != image_offset
    image_bytes = (mask_offset if has_mask else next_offset) - image_offset
    mask_bytes = next_offset - mask_offset if has_mask else 0
    width_pixels = compute_width_pixels(width_words, first_bit_used, last_bit_used, mode.bpp)
    warnings = validate_sprite(
        name=name,
        width_words=width_words,
        height=height,
        first_bit_used=first_bit_used,
        last_bit_used=last_bit_used,
        image_bytes=image_bytes,
        mask_bytes=mask_bytes,
        palette=palette,
        palette_entries=palette_bytes // 8,
        has_mask=has_mask,
        mode=mode,
        width_pixels=width_pixels,
    )

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
        palette=palette,
        has_mask=has_mask,
        mode=mode,
        width_pixels=width_pixels,
        warnings=tuple(warnings),
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


def infer_bpp_from_logical_colours(logical_colours: int | None) -> int | None:
    colour_to_bpp = {
        2: 1,
        4: 2,
        16: 4,
        256: 8,
    }
    return colour_to_bpp.get(logical_colours)


def tuple_or_none(value: tuple[int, int] | None, index: int) -> int | None:
    if value is None:
        return None
    return value[index]


def decode_palette(data: bytes, palette_offset: int, palette_bytes: int) -> tuple[PaletteEntry, ...]:
    entries: list[PaletteEntry] = []
    for index in range(palette_bytes // 8):
        word1, word2 = struct.unpack_from("<II", data, palette_offset + (index * 8))
        entries.append(
            PaletteEntry(
                index=index,
                word1=word1,
                word2=word2,
                red=(word1 >> 8) & 0xFF,
                green=(word1 >> 16) & 0xFF,
                blue=(word1 >> 24) & 0xFF,
                words_match=word1 == word2,
            )
        )
    return tuple(entries)


def validate_sprite(
    *,
    name: str,
    width_words: int,
    height: int,
    first_bit_used: int,
    last_bit_used: int,
    image_bytes: int,
    mask_bytes: int,
    palette: tuple[PaletteEntry, ...],
    palette_entries: int,
    has_mask: bool,
    mode: SpriteMode,
    width_pixels: int | None,
) -> list[str]:
    warnings: list[str] = []

    if first_bit_used > 31 or last_bit_used > 31:
        warnings.append("bit usage fields exceed the valid 0..31 range")
    if first_bit_used > last_bit_used:
        warnings.append("first bit used is greater than last bit used")
    if width_pixels is None:
        warnings.append("pixel width could not be derived from width words and mode")

    expected_row_bytes = width_words * 4
    expected_image_bytes = expected_row_bytes * height
    if image_bytes != expected_image_bytes:
        warnings.append(
            f"image data is {image_bytes} bytes, expected {expected_image_bytes} from width/height"
        )

    expected_mask_bytes = expected_image_bytes if has_mask else 0
    if has_mask and mode.has_alpha and width_pixels is not None and mode.mask_bpp is not None:
        bits_per_row = width_pixels * mode.mask_bpp
        expected_mask_bytes = (((bits_per_row + 31) // 32) * 4) * height
    if has_mask and mask_bytes != expected_mask_bytes:
        warnings.append(
            f"mask data is {mask_bytes} bytes, expected {expected_mask_bytes} for this sprite type"
        )

    if mode.format_name == "old" and mode.bpp is None:
        warnings.append(f"old-format mode {mode.raw_value} is not in the known mode table")
    if mode.format_name == "old" and mode.kind in {"text", "teletext"}:
        warnings.append(f"old-format mode {mode.raw_value} is a {mode.kind} mode, not a graphics mode")
    if mode.format_name == "new" and mode.sprite_type not in NEW_SPRITE_TYPES:
        warnings.append(f"new-format sprite type {mode.sprite_type} is not recognised")

    expected_palette_sizes = expected_palette_entry_counts(mode)
    if palette_entries and expected_palette_sizes and palette_entries not in expected_palette_sizes:
        expected_text = ", ".join(str(size) for size in sorted(expected_palette_sizes))
        warnings.append(f"palette has {palette_entries} entries; expected one of {expected_text}")

    mismatch_entries = [entry.index for entry in palette if not entry.words_match]
    if mismatch_entries:
        preview = ", ".join(str(index) for index in mismatch_entries[:8])
        if len(mismatch_entries) > 8:
            preview += ", ..."
        warnings.append(f"palette entry words differ at indexes {preview}")

    if mode.data_format == "indexed" and mode.bpp == 8 and palette_entries == 64:
        warnings.append("64-entry 8bpp palette detected; this is valid but non-standard")

    if mode.data_format in {"RGB", "CMYK"} and palette_entries:
        warnings.append("true-colour sprite contains palette entries")

    if not has_mask and mode.has_alpha:
        warnings.append("alpha-capable sprite type has no mask data")

    return [f"{name}: {warning}" for warning in warnings]


def expected_palette_entry_counts(mode: SpriteMode) -> set[int]:
    if mode.data_format != "indexed" or mode.bpp is None:
        return {0}
    if mode.bpp == 1:
        return {0, 2}
    if mode.bpp == 2:
        return {0, 4}
    if mode.bpp == 4:
        return {0, 16}
    if mode.bpp == 8:
        return {0, 16, 64, 256}
    return {0}


def build_summary(selection: SpriteSelection, verbose: bool = False) -> str:
    sprite_file = selection.sprite_file
    rows = [
        summary_headers(verbose)
    ]
    for sprite in selection.sprites:
        rows.append(summary_row(sprite, verbose))

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    table = "\n".join(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows
    )
    if verbose:
        return f"File: {sprite_file.path}\nSprites shown: {len(selection.sprites)} of {sprite_file.sprite_count}\n{table}"
    return table


def build_details(selection: SpriteSelection, sprite_name: str, verbose: bool = False) -> str:
    sprite_file = selection.sprite_file
    sprite = find_sprite(selection.sprites, sprite_name)
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
        f"Base mode number: {unknown_or(str(sprite.mode.base_mode_number), sprite.mode.base_mode_number)}",
        f"Shadow mode: {'yes' if sprite.mode.shadow_mode else 'no'}",
        f"Sprite type: {sprite.mode.sprite_type}",
        f"Alpha channel: {'yes' if sprite.mode.has_alpha else 'no'}",
        f"Mode kind: {unknown_or(sprite.mode.kind, sprite.mode.kind)}",
        f"Bits per pixel: {unknown_or(str(sprite.mode.bpp), sprite.mode.bpp)}",
        f"Mask kind: {unknown_or(sprite.mode.mask_kind, sprite.mode.mask_kind)}",
        f"Logical colours: {unknown_or(str(sprite.mode.logical_colours), sprite.mode.logical_colours)}",
        f"Text resolution: {format_pair(sprite.mode.text_columns, sprite.mode.text_rows)}",
        f"Mode pixel resolution: {format_pair(sprite.mode.pixel_width, sprite.mode.pixel_height)}",
        f"Mode OS units: {format_pair(sprite.mode.os_unit_width, sprite.mode.os_unit_height)}",
        f"Mode memory: {format_memory_kb(sprite.mode.memory_kb)}",
        f"Mode refresh: {format_hz(sprite.mode.refresh_hz)}",
        f"Supported monitors: {format_monitors(sprite.mode.monitor_types)}",
        f"Mask bits per pixel: {unknown_or(str(sprite.mode.mask_bpp), sprite.mode.mask_bpp)}",
        f"Horizontal dpi: {unknown_or(str(sprite.mode.x_dpi), sprite.mode.x_dpi)}",
        f"Vertical dpi: {unknown_or(str(sprite.mode.y_dpi), sprite.mode.y_dpi)}",
        f"Data format: {unknown_or(sprite.mode.data_format, sprite.mode.data_format)}",
        f"Colour model: {unknown_or(sprite.mode.colour_model, sprite.mode.colour_model)}",
    ]
    if sprite.mode.data_format == "CMYK":
        lines.extend(
            [
                "CMYK channels: 8 bits each",
                "CMYK byte order: cyan, magenta, yellow, black",
            ]
        )
    lines.extend(build_palette_lines(sprite, verbose=verbose))
    if verbose:
        lines.extend(
            [
                f"File sprite count: {sprite_file.sprite_count}",
                f"File first sprite offset: 0x{sprite_file.first_sprite_offset:x}",
                f"File free offset: 0x{sprite_file.free_offset:x}",
                f"File extension words: {format_extension_words(sprite_file.extension_words)}",
            ]
        )
    lines.extend(build_warning_lines(sprite.warnings))
    return "\n".join(lines)


def build_palette_lines(sprite: Sprite, verbose: bool = False) -> list[str]:
    lines = [
        f"Palette entries decoded: {len(sprite.palette)}",
    ]
    if not sprite.palette:
        return lines

    lines.append("Palette preview:")
    preview_count = len(sprite.palette) if verbose else min(len(sprite.palette), 16)
    for entry in sprite.palette[:preview_count]:
        lines.append(
            "  "
            f"{entry.index:3d}: "
            f"rgb=({entry.red:3d},{entry.green:3d},{entry.blue:3d}) "
            f"word1=0x{entry.word1:08x} "
            f"word2=0x{entry.word2:08x}"
        )
    if len(sprite.palette) > preview_count:
        lines.append(f"  ... {len(sprite.palette) - preview_count} more entries omitted")
    return lines


def build_warning_lines(warnings: tuple[str, ...]) -> list[str]:
    lines = [f"Warnings: {len(warnings)}"]
    for warning in warnings:
        lines.append(f"  {warning}")
    return lines


def build_check_report(selection: SpriteSelection, verbose: bool = False) -> str:
    sprite_file = selection.sprite_file
    warnings = collect_warnings(selection)
    if not warnings:
        suffix = f" ({len(selection.sprites)} of {sprite_file.sprite_count} sprites checked)" if verbose else ""
        return f"{sprite_file.path}: OK{suffix}"
    lines = [f"{sprite_file.path}: {len(warnings)} warning(s)"]
    if verbose:
        lines.append(f"Sprites checked: {len(selection.sprites)} of {sprite_file.sprite_count}")
    lines.extend(warnings)
    return "\n".join(lines)


def build_json(selection: SpriteSelection, sprite_name: str | None = None) -> str:
    sprite_file = selection.sprite_file
    if sprite_name:
        payload = sprite_to_dict(find_sprite(selection.sprites, sprite_name))
    else:
        payload = sprite_file_to_dict(sprite_file, selection.sprites)
    return json.dumps(payload, indent=2)


def extract_sprite(selection: SpriteSelection, sprite_name: str, output_path: Path) -> None:
    sprite = find_sprite(selection.sprites, sprite_name)
    source = selection.sprite_file.path.read_bytes()
    sprite_bytes = source[sprite.file_offset : sprite.file_offset + sprite.size_bytes]
    first_sprite_offset = 16
    free_offset = first_sprite_offset + sprite.size_bytes
    output = struct.pack("<III", 1, first_sprite_offset, free_offset) + sprite_bytes
    output_path.write_bytes(output)


def find_sprite(sprites: tuple[Sprite, ...], sprite_name: str) -> Sprite:
    for sprite in sprites:
        if sprite.name == sprite_name:
            return sprite
    available = ", ".join(sprite.name for sprite in sprites)
    raise SpriteFormatError(f"sprite '{sprite_name}' not found; available sprites: {available}")


def summary_mode(mode: SpriteMode) -> str:
    if mode.format_name == "old":
        if mode.pixel_width is not None and mode.pixel_height is not None:
            return f"{mode.mode_number} ({mode.pixel_width}x{mode.pixel_height})"
        return str(mode.mode_number)
    alpha_suffix = "+a" if mode.has_alpha else ""
    return f"type {mode.sprite_type}{alpha_suffix}"


def summary_dpi(mode: SpriteMode) -> str:
    if mode.x_dpi is None or mode.y_dpi is None:
        return ""
    return f"{mode.x_dpi}x{mode.y_dpi}"


def summary_type(mode: SpriteMode) -> str:
    if mode.format_name == "old":
        return "old"
    label = NEW_SPRITE_TYPES.get(mode.sprite_type, {}).get("name", f"type {mode.sprite_type}")
    if mode.has_alpha:
        return f"{label}+a"
    return label


def summary_mask(sprite: Sprite) -> str:
    if not sprite.has_mask:
        return "none"
    return sprite.mode.mask_kind or "yes"


def unknown_or(value: str, present: object | None) -> str:
    return value if present is not None else "unknown"


def format_pair(first: int | None, second: int | None) -> str:
    if first is None or second is None:
        return "unknown"
    return f"{first} x {second}"


def format_memory_kb(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value}K"


def format_hz(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value} Hz"


def format_monitors(monitors: tuple[int, ...]) -> str:
    if not monitors:
        return "unknown"
    return ", ".join(str(monitor) for monitor in monitors)


def collect_warnings(selection: SpriteSelection) -> list[str]:
    warnings = list(selection.sprite_file.warnings)
    for sprite in selection.sprites:
        warnings.extend(sprite.warnings)
    return warnings


def sprite_mode_to_dict(mode: SpriteMode) -> dict[str, object]:
    return {
        "format": mode.format_name,
        "raw_value": mode.raw_value,
        "mode_number": mode.mode_number,
        "base_mode_number": mode.base_mode_number,
        "shadow_mode": mode.shadow_mode,
        "sprite_type": mode.sprite_type,
        "has_alpha": mode.has_alpha,
        "kind": mode.kind,
        "bits_per_pixel": mode.bpp,
        "mask_bits_per_pixel": mode.mask_bpp,
        "mask_kind": mode.mask_kind,
        "logical_colours": mode.logical_colours,
        "text_resolution": {
            "columns": mode.text_columns,
            "rows": mode.text_rows,
        },
        "pixel_resolution": {
            "width": mode.pixel_width,
            "height": mode.pixel_height,
        },
        "os_unit_resolution": {
            "width": mode.os_unit_width,
            "height": mode.os_unit_height,
        },
        "memory_kb": mode.memory_kb,
        "refresh_hz": mode.refresh_hz,
        "monitor_types": list(mode.monitor_types),
        "horizontal_dpi": mode.x_dpi,
        "vertical_dpi": mode.y_dpi,
        "data_format": mode.data_format,
        "colour_model": mode.colour_model,
        "description": mode.description,
    }


def palette_entry_to_dict(entry: PaletteEntry) -> dict[str, object]:
    return {
        "index": entry.index,
        "word1": entry.word1,
        "word2": entry.word2,
        "rgb": {
            "red": entry.red,
            "green": entry.green,
            "blue": entry.blue,
        },
        "words_match": entry.words_match,
    }


def sprite_to_dict(sprite: Sprite) -> dict[str, object]:
    return {
        "name": sprite.name,
        "file_offset": sprite.file_offset,
        "size_bytes": sprite.size_bytes,
        "width_words": sprite.width_words,
        "width_pixels": sprite.width_pixels,
        "height": sprite.height,
        "first_bit_used": sprite.first_bit_used,
        "last_bit_used": sprite.last_bit_used,
        "image_offset": sprite.image_offset,
        "mask_offset": sprite.mask_offset,
        "image_bytes": sprite.image_bytes,
        "mask_bytes": sprite.mask_bytes,
        "has_mask": sprite.has_mask,
        "palette_bytes": sprite.palette_bytes,
        "palette_entries": sprite.palette_entries,
        "palette": [palette_entry_to_dict(entry) for entry in sprite.palette],
        "mode": sprite_mode_to_dict(sprite.mode),
        "warnings": list(sprite.warnings),
    }


def sprite_file_to_dict(sprite_file: SpriteFile, sprites: tuple[Sprite, ...]) -> dict[str, object]:
    return {
        "path": str(sprite_file.path),
        "sprite_count": sprite_file.sprite_count,
        "filtered_sprite_count": len(sprites),
        "first_sprite_offset": sprite_file.first_sprite_offset,
        "free_offset": sprite_file.free_offset,
        "extension_words": list(sprite_file.extension_words),
        "warnings": list(sprite_file.warnings),
        "sprites": [sprite_to_dict(sprite) for sprite in sprites],
    }


def summary_headers(verbose: bool) -> list[str]:
    if not verbose:
        return ["Name", "Size", "Type", "BPP", "Mask", "Palette", "DPI", "Mode"]
    return [
        "Name",
        "Size",
        "Type",
        "BPP",
        "Mask",
        "Palette",
        "Image",
        "MaskBytes",
        "Colour",
        "DPI",
        "Mode",
    ]


def summary_row(sprite: Sprite, verbose: bool) -> list[str]:
    row = [
        sprite.name,
        unknown_or(f"{sprite.width_pixels}x{sprite.height}", sprite.width_pixels),
        summary_type(sprite.mode),
        unknown_or(str(sprite.mode.bpp), sprite.mode.bpp),
        summary_mask(sprite),
        str(sprite.palette_entries),
    ]
    if verbose:
        row.extend(
            [
                str(sprite.image_bytes),
                str(sprite.mask_bytes),
                unknown_or(sprite.mode.colour_model, sprite.mode.colour_model),
                summary_dpi(sprite.mode),
                summary_mode(sprite.mode),
            ]
        )
        return row
    row.extend([summary_dpi(sprite.mode), summary_mode(sprite.mode)])
    return row


def format_extension_words(words: tuple[int, ...]) -> str:
    if not words:
        return "none"
    return ", ".join(f"0x{word:08x}" for word in words)


def select_sprites(
    sprite_file: SpriteFile,
    *,
    name_pattern: str | None = None,
    mode_filter: str | None = None,
    type_filter: str | None = None,
    has_mask: bool = False,
) -> SpriteSelection:
    sprites = list(sprite_file.sprites)
    if name_pattern:
        sprites = [sprite for sprite in sprites if fnmatch.fnmatch(sprite.name, name_pattern)]
    if mode_filter:
        sprites = [sprite for sprite in sprites if sprite_matches_mode_filter(sprite, mode_filter)]
    if type_filter:
        sprites = [sprite for sprite in sprites if sprite_matches_type_filter(sprite, type_filter)]
    if has_mask:
        sprites = [sprite for sprite in sprites if sprite.has_mask]
    return SpriteSelection(sprite_file=sprite_file, sprites=tuple(sprites))


def sprite_matches_mode_filter(sprite: Sprite, mode_filter: str) -> bool:
    if sprite.mode.mode_number is not None:
        return mode_filter in {
            str(sprite.mode.mode_number),
            str(sprite.mode.base_mode_number),
        }
    return mode_filter in {
        str(sprite.mode.raw_value),
        summary_mode(sprite.mode),
        f"type {sprite.mode.sprite_type}",
    }


def sprite_matches_type_filter(sprite: Sprite, type_filter: str) -> bool:
    candidates = {
        summary_type(sprite.mode).lower(),
        unknown_or(sprite.mode.colour_model or "", sprite.mode.colour_model).lower(),
    }
    if sprite.mode.format_name == "old":
        candidates.add("old")
    else:
        candidates.add(f"type {sprite.mode.sprite_type}")
    return type_filter.lower() in candidates


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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text output",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the sprite file structure and report warnings",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show more fields in text output",
    )
    parser.add_argument(
        "--name",
        dest="name_pattern",
        help="Filter sprites by shell-style name pattern",
    )
    parser.add_argument(
        "--mode",
        dest="mode_filter",
        help="Filter by mode number, base mode number, raw mode value, or type string",
    )
    parser.add_argument(
        "--type",
        dest="type_filter",
        help="Filter by sprite type label such as old, 8bpp, 8bpp+a, 32bpp, RGB, or CMYK",
    )
    parser.add_argument(
        "--has-mask",
        action="store_true",
        help="Show only sprites which contain mask data",
    )
    parser.add_argument(
        "--extract",
        type=Path,
        metavar="OUTPUT",
        help="Write the selected sprite to its own sprite file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.extract is not None and not args.sprite_name:
        print("riscos-dumpsprites: --extract requires a sprite name", file=sys.stderr)
        return 1
    try:
        sprite_file = parse_sprite_file(args.sprite_file)
        selection = select_sprites(
            sprite_file,
            name_pattern=args.name_pattern,
            mode_filter=args.mode_filter,
            type_filter=args.type_filter,
            has_mask=args.has_mask,
        )
        if args.extract is not None:
            extract_sprite(selection, args.sprite_name, args.extract)
            output = f"Extracted {args.sprite_name} to {args.extract}"
        elif args.check and args.json:
            payload = {
                "path": str(sprite_file.path),
                "filtered_sprite_count": len(selection.sprites),
                "warnings": collect_warnings(selection),
                "ok": not collect_warnings(selection),
            }
            output = json.dumps(payload, indent=2)
        elif args.check:
            output = build_check_report(selection, verbose=args.verbose)
        elif args.json:
            output = build_json(selection, args.sprite_name)
        elif args.sprite_name:
            output = build_details(selection, args.sprite_name, verbose=args.verbose)
        else:
            output = build_summary(selection, verbose=args.verbose)
    except (OSError, SpriteFormatError) as exc:
        print(f"riscos-dumpsprites: {exc}", file=sys.stderr)
        return 1

    print(output)
    if args.check and collect_warnings(selection):
        return 1
    return 0
