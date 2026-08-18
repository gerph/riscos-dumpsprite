"""Decoding of RISC OS sprite mode words, old-format and new-format alike."""

from __future__ import annotations

from dataclasses import dataclass


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


def _infer_bpp_from_logical_colours(logical_colours: int | None) -> int | None:
    colour_to_bpp = {
        2: 1,
        4: 2,
        16: 4,
        256: 8,
    }
    return colour_to_bpp.get(logical_colours)


def _tuple_or_none(value: tuple[int, int] | None, index: int) -> int | None:
    if value is None:
        return None
    return value[index]


@dataclass(frozen=True)
class SpriteMode:
    """A decoded sprite mode word, old-format or new-format."""

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

    @classmethod
    def decode(cls, raw_mode: int) -> "SpriteMode":
        sprite_type = raw_mode >> 27
        if sprite_type == 0:
            shadow_mode = bool(raw_mode & 0x80)
            base_mode = raw_mode & 0x7F
            mode_info = OLD_MODE_INFO.get(base_mode, {})
            bpp = _infer_bpp_from_logical_colours(mode_info.get("logical_colours"))
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
            return cls(
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
                text_columns=_tuple_or_none(mode_info.get("text"), 0),
                text_rows=_tuple_or_none(mode_info.get("text"), 1),
                pixel_width=_tuple_or_none(pixel, 0),
                pixel_height=_tuple_or_none(pixel, 1),
                os_unit_width=_tuple_or_none(mode_info.get("os_units"), 0),
                os_unit_height=_tuple_or_none(mode_info.get("os_units"), 1),
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
        return cls(
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

    def expected_palette_entry_counts(self) -> set[int]:
        if self.data_format != "indexed" or self.bpp is None:
            return {0}
        if self.bpp == 1:
            return {0, 2}
        if self.bpp == 2:
            return {0, 4}
        if self.bpp == 4:
            return {0, 16}
        if self.bpp == 8:
            return {0, 16, 64, 256}
        return {0}

    def summary_mode(self) -> str:
        if self.format_name == "old":
            if self.pixel_width is not None and self.pixel_height is not None:
                return f"{self.mode_number} ({self.pixel_width}x{self.pixel_height})"
            return str(self.mode_number)
        alpha_suffix = "+a" if self.has_alpha else ""
        return f"type {self.sprite_type}{alpha_suffix}"

    def summary_dpi(self) -> str:
        if self.x_dpi is None or self.y_dpi is None:
            return ""
        return f"{self.x_dpi}x{self.y_dpi}"

    def summary_type(self) -> str:
        if self.format_name == "old":
            return "old"
        label = NEW_SPRITE_TYPES.get(self.sprite_type, {}).get("name", f"type {self.sprite_type}")
        if self.has_alpha:
            return f"{label}+a"
        return label

    def matches_mode_filter(self, mode_filter: str) -> bool:
        if self.mode_number is not None:
            return mode_filter in {
                str(self.mode_number),
                str(self.base_mode_number),
            }
        return mode_filter in {
            str(self.raw_value),
            self.summary_mode(),
            f"type {self.sprite_type}",
        }

    def matches_type_filter(self, type_filter: str) -> bool:
        candidates = {
            self.summary_type().lower(),
            (self.colour_model if self.colour_model is not None else "unknown").lower(),
        }
        if self.format_name == "old":
            candidates.add("old")
        else:
            candidates.add(f"type {self.sprite_type}")
        return type_filter.lower() in candidates

    def to_dict(self) -> dict[str, object]:
        return {
            "format": self.format_name,
            "raw_value": self.raw_value,
            "mode_number": self.mode_number,
            "base_mode_number": self.base_mode_number,
            "shadow_mode": self.shadow_mode,
            "sprite_type": self.sprite_type,
            "has_alpha": self.has_alpha,
            "kind": self.kind,
            "bits_per_pixel": self.bpp,
            "mask_bits_per_pixel": self.mask_bpp,
            "mask_kind": self.mask_kind,
            "logical_colours": self.logical_colours,
            "text_resolution": {
                "columns": self.text_columns,
                "rows": self.text_rows,
            },
            "pixel_resolution": {
                "width": self.pixel_width,
                "height": self.pixel_height,
            },
            "os_unit_resolution": {
                "width": self.os_unit_width,
                "height": self.os_unit_height,
            },
            "memory_kb": self.memory_kb,
            "refresh_hz": self.refresh_hz,
            "monitor_types": list(self.monitor_types),
            "horizontal_dpi": self.x_dpi,
            "vertical_dpi": self.y_dpi,
            "data_format": self.data_format,
            "colour_model": self.colour_model,
            "description": self.description,
        }
