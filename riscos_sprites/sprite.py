"""A single decoded RISC OS sprite."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from .errors import SpriteFormatError
from .modes import NEW_SPRITE_TYPES, SpriteMode
from .palette import PaletteEntry, default_palette_entries
from .pixels import DecodedMask, DecodedPixels
from .pixels import decode_mask as _decode_mask
from .pixels import decode_pixels as _decode_pixels

SPRITE_HEADER_SIZE = 44


def _read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _compute_width_pixels(
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


def _unknown_or(value: str, present: object | None) -> str:
    return value if present is not None else "unknown"


def _format_pair(first: int | None, second: int | None) -> str:
    if first is None or second is None:
        return "unknown"
    return f"{first} x {second}"


def _format_memory_kb(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value}K"


def _format_hz(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value} Hz"


def _format_monitors(monitors: tuple[int, ...]) -> str:
    if not monitors:
        return "unknown"
    return ", ".join(str(monitor) for monitor in monitors)


@dataclass(frozen=True)
class Sprite:
    """A single sprite decoded from a RISC OS sprite file."""

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
    image_data: bytes
    mask_data: bytes
    palette_bytes: int
    palette_entries: int
    palette: tuple[PaletteEntry, ...]
    has_mask: bool
    mode: SpriteMode
    width_pixels: int | None
    warnings: tuple[str, ...]

    @classmethod
    def parse(cls, data: bytes, path: Path, sprite_offset: int) -> "Sprite":
        if sprite_offset + SPRITE_HEADER_SIZE > len(data):
            raise SpriteFormatError(f"{path} has a truncated sprite header at 0x{sprite_offset:x}")

        next_offset = _read_u32(data, sprite_offset)
        if next_offset < SPRITE_HEADER_SIZE:
            raise SpriteFormatError(f"{path} has a sprite with invalid size at 0x{sprite_offset:x}")

        sprite_end = sprite_offset + next_offset
        if sprite_end > len(data):
            raise SpriteFormatError(f"{path} has a sprite that runs past end of file")

        name = data[sprite_offset + 4 : sprite_offset + 16].split(b"\0", 1)[0].decode("latin-1")
        width_words = _read_u32(data, sprite_offset + 16) + 1
        height = _read_u32(data, sprite_offset + 20) + 1
        first_bit_used = _read_u32(data, sprite_offset + 24)
        last_bit_used = _read_u32(data, sprite_offset + 28)
        image_offset = _read_u32(data, sprite_offset + 32)
        mask_offset = _read_u32(data, sprite_offset + 36)
        raw_mode = _read_u32(data, sprite_offset + 40)
        mode = SpriteMode.decode(raw_mode)

        if image_offset < SPRITE_HEADER_SIZE or image_offset > next_offset:
            raise SpriteFormatError(f"{path} has a sprite with invalid image offset: {name}")
        if mask_offset < image_offset or mask_offset > next_offset:
            raise SpriteFormatError(f"{path} has a sprite with invalid mask offset: {name}")

        palette_bytes = image_offset - SPRITE_HEADER_SIZE
        if palette_bytes % 8 != 0:
            raise SpriteFormatError(f"{path} has a sprite with a malformed palette: {name}")

        palette = PaletteEntry.decode_all(data, sprite_offset + SPRITE_HEADER_SIZE, palette_bytes)
        has_mask = mask_offset != image_offset
        image_bytes = (mask_offset if has_mask else next_offset) - image_offset
        mask_bytes = next_offset - mask_offset if has_mask else 0
        image_data = data[sprite_offset + image_offset : sprite_offset + image_offset + image_bytes]
        mask_data = (
            data[sprite_offset + mask_offset : sprite_offset + mask_offset + mask_bytes]
            if has_mask
            else b""
        )
        width_pixels = _compute_width_pixels(width_words, first_bit_used, last_bit_used, mode.bpp)
        warnings = _validate(
            name=name,
            first_bit_used=first_bit_used,
            last_bit_used=last_bit_used,
            width_words=width_words,
            height=height,
            image_bytes=image_bytes,
            mask_bytes=mask_bytes,
            palette=palette,
            palette_entries=palette_bytes // 8,
            has_mask=has_mask,
            mode=mode,
            width_pixels=width_pixels,
        )

        return cls(
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
            image_data=image_data,
            mask_data=mask_data,
            palette_bytes=palette_bytes,
            palette_entries=palette_bytes // 8,
            palette=palette,
            has_mask=has_mask,
            mode=mode,
            width_pixels=width_pixels,
            warnings=tuple(warnings),
        )

    def effective_palette(self) -> tuple[PaletteEntry, ...]:
        """The sprite's own palette, or the standard default palette for
        its bits-per-pixel if it has none of its own."""
        if self.palette:
            return self.palette
        if self.mode.data_format in {"monochrome", "indexed"} and self.mode.bpp is not None:
            return default_palette_entries(self.mode.bpp)
        return ()

    def decode_pixels(self) -> DecodedPixels:
        if self.width_pixels is None:
            raise SpriteFormatError(f"{self.name}: cannot decode pixels without a known pixel width")
        if self.mode.bpp is None:
            raise SpriteFormatError(f"{self.name}: cannot decode pixels without a known bits-per-pixel")
        if self.mode.data_format is None:
            raise SpriteFormatError(f"{self.name}: cannot decode pixels without a known data format")
        return _decode_pixels(
            image_bytes=self.image_data,
            width_words=self.width_words,
            height=self.height,
            first_bit_used=self.first_bit_used,
            width_pixels=self.width_pixels,
            bpp=self.mode.bpp,
            data_format=self.mode.data_format,
        )

    def decode_mask(self) -> DecodedMask | None:
        if not self.has_mask:
            return None
        if self.width_pixels is None:
            raise SpriteFormatError(f"{self.name}: cannot decode mask without a known pixel width")
        if self.mode.mask_kind is None:
            raise SpriteFormatError(f"{self.name}: cannot decode mask without a known mask kind")
        if self.mode.bpp is None:
            raise SpriteFormatError(f"{self.name}: cannot decode mask without a known bits-per-pixel")
        return _decode_mask(
            mask_bytes=self.mask_data,
            height=self.height,
            width_pixels=self.width_pixels,
            first_bit_used=self.first_bit_used,
            mask_kind=self.mode.mask_kind,
            format_name=self.mode.format_name,
            image_bpp=self.mode.bpp,
            image_width_words=self.width_words,
        )

    def summary_mask(self) -> str:
        if not self.has_mask:
            return "none"
        return self.mode.mask_kind or "yes"

    def summary_row(self, verbose: bool = False) -> list[str]:
        row = [
            self.name,
            _unknown_or(f"{self.width_pixels}x{self.height}", self.width_pixels),
            self.mode.summary_type(),
            _unknown_or(str(self.mode.bpp), self.mode.bpp),
            self.summary_mask(),
            str(self.palette_entries),
        ]
        if verbose:
            row.extend(
                [
                    str(self.image_bytes),
                    str(self.mask_bytes),
                    _unknown_or(self.mode.colour_model, self.mode.colour_model),
                    self.mode.summary_dpi(),
                    self.mode.summary_mode(),
                ]
            )
            return row
        row.extend([self.mode.summary_dpi(), self.mode.summary_mode()])
        return row

    def palette_lines(self, verbose: bool = False) -> list[str]:
        lines = [
            f"Palette entries decoded: {len(self.palette)}",
        ]
        if not self.palette:
            return lines

        lines.append("Palette preview:")
        preview_count = len(self.palette) if verbose else min(len(self.palette), 16)
        for entry in self.palette[:preview_count]:
            lines.append(
                "  "
                f"{entry.index:3d}: "
                f"rgb=({entry.red:3d},{entry.green:3d},{entry.blue:3d}) "
                f"word1=0x{entry.word1:08x} "
                f"word2=0x{entry.word2:08x}"
            )
        if len(self.palette) > preview_count:
            lines.append(f"  ... {len(self.palette) - preview_count} more entries omitted")
        return lines

    def warning_lines(self) -> list[str]:
        lines = [f"Warnings: {len(self.warnings)}"]
        for warning in self.warnings:
            lines.append(f"  {warning}")
        return lines

    def details_lines(self, verbose: bool = False) -> list[str]:
        lines = [
            f"Sprite: {self.name}",
            f"File offset: 0x{self.file_offset:x}",
            f"Sprite size: {self.size_bytes} bytes",
            f"Dimensions: {_unknown_or(str(self.width_pixels), self.width_pixels)} x {self.height} pixels",
            f"Width in words: {self.width_words}",
            f"First bit used: {self.first_bit_used}",
            f"Last bit used: {self.last_bit_used}",
            f"Image offset: 0x{self.image_offset:x}",
            f"Mask offset: 0x{self.mask_offset:x}",
            f"Image bytes: {self.image_bytes}",
            f"Mask bytes: {self.mask_bytes}",
            f"Has mask: {'yes' if self.has_mask else 'no'}",
            f"Palette bytes: {self.palette_bytes}",
            f"Palette entries: {self.palette_entries}",
            f"Mode format: {self.mode.format_name}",
            f"Mode description: {self.mode.description}",
            f"Mode raw value: 0x{self.mode.raw_value:08x}",
            f"Mode number: {_unknown_or(str(self.mode.mode_number), self.mode.mode_number)}",
            f"Base mode number: {_unknown_or(str(self.mode.base_mode_number), self.mode.base_mode_number)}",
            f"Shadow mode: {'yes' if self.mode.shadow_mode else 'no'}",
            f"Sprite type: {self.mode.sprite_type}",
            f"Alpha channel: {'yes' if self.mode.has_alpha else 'no'}",
            f"Mode kind: {_unknown_or(self.mode.kind, self.mode.kind)}",
            f"Bits per pixel: {_unknown_or(str(self.mode.bpp), self.mode.bpp)}",
            f"Mask kind: {_unknown_or(self.mode.mask_kind, self.mode.mask_kind)}",
            f"Logical colours: {_unknown_or(str(self.mode.logical_colours), self.mode.logical_colours)}",
            f"Text resolution: {_format_pair(self.mode.text_columns, self.mode.text_rows)}",
            f"Mode pixel resolution: {_format_pair(self.mode.pixel_width, self.mode.pixel_height)}",
            f"Mode OS units: {_format_pair(self.mode.os_unit_width, self.mode.os_unit_height)}",
            f"Mode memory: {_format_memory_kb(self.mode.memory_kb)}",
            f"Mode refresh: {_format_hz(self.mode.refresh_hz)}",
            f"Supported monitors: {_format_monitors(self.mode.monitor_types)}",
            f"Mask bits per pixel: {_unknown_or(str(self.mode.mask_bpp), self.mode.mask_bpp)}",
            f"Horizontal dpi: {_unknown_or(str(self.mode.x_dpi), self.mode.x_dpi)}",
            f"Vertical dpi: {_unknown_or(str(self.mode.y_dpi), self.mode.y_dpi)}",
            f"Data format: {_unknown_or(self.mode.data_format, self.mode.data_format)}",
            f"Colour model: {_unknown_or(self.mode.colour_model, self.mode.colour_model)}",
        ]
        if self.mode.data_format == "CMYK":
            lines.extend(
                [
                    "CMYK channels: 8 bits each",
                    "CMYK byte order: cyan, magenta, yellow, black",
                ]
            )
        lines.extend(self.palette_lines(verbose=verbose))
        return lines

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "file_offset": self.file_offset,
            "size_bytes": self.size_bytes,
            "width_words": self.width_words,
            "width_pixels": self.width_pixels,
            "height": self.height,
            "first_bit_used": self.first_bit_used,
            "last_bit_used": self.last_bit_used,
            "image_offset": self.image_offset,
            "mask_offset": self.mask_offset,
            "image_bytes": self.image_bytes,
            "mask_bytes": self.mask_bytes,
            "has_mask": self.has_mask,
            "palette_bytes": self.palette_bytes,
            "palette_entries": self.palette_entries,
            "palette": [entry.to_dict() for entry in self.palette],
            "mode": self.mode.to_dict(),
            "warnings": list(self.warnings),
        }


def _validate(
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

    expected_mask_bytes = 0
    if has_mask:
        if mode.format_name == "old":
            # Old-format masks are stored at the image's own bpp (a whole
            # pixel-sized slot per pixel), reusing its row width exactly.
            expected_mask_bytes = expected_image_bytes
        elif width_pixels is not None and mode.mask_bpp is not None:
            # New-format masks (1bpp classic, or 8bpp alpha) are packed
            # into their own word-aligned rows, independent of the
            # image's row width.
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

    expected_palette_sizes = mode.expected_palette_entry_counts()
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
