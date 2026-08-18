"""Command line interface for riscos-sprites.

Provides subcommands built on top of the riscos_sprites library:

- ``list``    -- inspect a sprite file (summary/detail/JSON/check), the
                 same behaviour riscos-dumpsprites has always provided.
- ``extract`` -- write a single named sprite out to its own sprite file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import SpriteFormatError
from .spritefile import SpriteFile


def _add_list_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "list",
        help="Display information about a RISC OS sprite file",
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
    parser.set_defaults(func=_run_list)


def _add_extract_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "extract",
        help="Write a single sprite to its own sprite file",
    )
    parser.add_argument("sprite_file", type=Path, help="Path to the sprite file")
    parser.add_argument("sprite_name", help="Name of the sprite to extract")
    parser.add_argument("output", type=Path, help="Path to write the extracted sprite file to")
    parser.set_defaults(func=_run_extract)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="riscos-sprites",
        description="Inspect and convert RISC OS sprite files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_list_subcommand(subparsers)
    _add_extract_subcommand(subparsers)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _run_list(args: argparse.Namespace) -> int:
    sprite_file = SpriteFile.parse(args.sprite_file)
    selection = sprite_file.select(
        name_pattern=args.name_pattern,
        mode_filter=args.mode_filter,
        type_filter=args.type_filter,
        has_mask=args.has_mask,
    )
    if args.check and args.json:
        output = selection.check_json_text()
    elif args.check:
        output = selection.check_text(verbose=args.verbose)
    elif args.json:
        output = selection.json_text(args.sprite_name)
    elif args.sprite_name:
        output = selection.details_text(args.sprite_name, verbose=args.verbose)
    else:
        output = selection.summary_text(verbose=args.verbose)

    print(output)
    if args.check and selection.warnings():
        return 1
    return 0


def _run_extract(args: argparse.Namespace) -> int:
    sprite_file = SpriteFile.parse(args.sprite_file)
    selection = sprite_file.select()
    selection.extract(args.sprite_name, args.output)
    print(f"Extracted {args.sprite_name} to {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return args.func(args)
    except (OSError, SpriteFormatError) as exc:
        print(f"riscos-sprites: {exc}", file=sys.stderr)
        return 1
