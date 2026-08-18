# Plan: `riscos_sprites` package — PNG/PNM conversion for RISC OS sprites

## Context

`riscos-dumpsprites` is currently a single 1008-line module, `riscos_dumpsprites/cli.py`, that
parses RISC OS Sprite files into frozen dataclasses and reports on them (summary table,
per-sprite detail, JSON, `--check` validation, `--extract`). It has no external dependencies and
does not decode actual pixel data — it is a metadata/structure inspector only.

We want to grow this into real image conversion: Sprite → PNG, Sprite → PNM, and (eventually)
PNG → Sprite. The RISC OS `ConvertPNG` module in the parent source tree (`c/reverse` for
Sprite→PNG, `c/convert` for PNG→Sprite, `c/palette` for default palettes, `h/common` for the
`sprite_header` layout) already solves this problem via libpng and is the reference algorithm to
port — mask/alpha handling, old vs new mode-word decoding, 16bpp 5:5:5→8:8:8 bit replication,
CMYK byte order, and the `packswap` bit ordering RISC OS uses for <8bpp pixel data.

The work restructures the existing single-file tool into a proper `riscos_sprites` library
package (class-based: `Sprite`/`SpriteFile` gain methods for parsing, selecting and rendering,
replacing the current flat function-per-operation style), keeps `riscos-dumpsprites` working
unchanged as a thin compatibility CLI on top of it, and adds a new `riscos-sprites` command with
subcommands: `list`, `extract` (both reproducing today's `riscos-dumpsprites` behaviour),
`to-png`, `to-pnm`, and (final stage) `from-png`.

**Confirmed design decisions:**
- PNG/PNM encoding is hand-rolled against the stdlib (`zlib` for DEFLATE/CRC), no new
  dependency — matches the project's current zero-dependency stance.
- PNG mask handling replicates the full C module strategy: colour-key search for a free
  palette/colour-cube slot before falling back to promoting the image to true-colour or a full
  alpha channel (`c/reverse`'s `NO_MASK`/`PROMOTE_PALETTE`/`PROMOTE_TRUE`/`PROMOTE_ALPHA` chain).
- PNM is its own `to-pnm` subcommand (not a flag on `to-png`). Default output is a plain PPM
  (P6) with the palette expanded to raw RGB, no gamma correction. An extended mode (flag) for
  paletted sprites instead writes a PGM (P5) whose pixel data is the raw palette *index* per
  pixel, preceded by `#` comment lines recording the palette (index → RGB), sprite mode, and DPI
  — still a spec-valid PNM, but round-trippable/inspectable by a human or by our own tooling.
- `riscos-sprites list` = today's default/`--json`/`--check`/`--verbose`/`--name`/`--mode`/
  `--type`/`--has-mask` inspection (including per-sprite detail view). `riscos-sprites extract`
  = today's `--extract`, as its own subcommand with an explicit output-path argument.

## Package layout (target state)

```
riscos-dumpsprites/
├── riscos_sprites/                # new library + its own CLI
│   ├── __init__.py                 # public API re-exports
│   ├── errors.py                   # SpriteFormatError
│   ├── modes.py                    # SpriteMode dataclass, OLD_MODE_INFO, NEW_SPRITE_TYPES,
│   │                                #   SpriteMode.decode(raw_mode) classmethod
│   ├── palette.py                  # PaletteEntry dataclass, decode_palette(), default
│   │                                #   palettes ported from c/palette (2/4/16/256-entry)
│   ├── sprite.py                   # Sprite class: parse(), pixel/mask decoding, to_dict(),
│   │                                #   summary_row(), details_text(), warnings
│   ├── spritefile.py               # SpriteFile class: parse(path), select(...) filtering,
│   │                                #   iteration, extract_sprite(name, path)
│   ├── reporting.py                # text/JSON report builders operating on SpriteFile/Sprite
│   │                                #   (build_summary/build_details/build_check_report/build_json,
│   │                                #   ported near-verbatim from current cli.py)
│   ├── png.py                      # PNGWriter: Sprite -> PNG bytes (stage 4)
│   ├── pnm.py                      # PNMWriter: Sprite -> PPM/PGM bytes (stage 5)
│   ├── png_reader.py               # minimal PNG reader used by from-png (stage 6)
│   ├── from_png.py                 # PNG(s) -> SpriteFile builder (stage 6)
│   └── cli.py                      # `riscos-sprites` argparse subparsers: list/extract/
│                                    #   to-png/to-pnm/from-png
├── riscos_dumpsprites/             # kept for backward compatibility
│   ├── __init__.py
│   ├── __main__.py
│   └── cli.py                      # thin shim: argparse flags unchanged, output unchanged,
│                                    #   implementation delegates to riscos_sprites.*
├── riscos-dumpsprites               # unchanged launcher script
├── riscos-sprites                   # new launcher script (mirrors riscos-dumpsprites)
├── tests/
│   ├── test_cli.py                 # existing tests — must keep passing unmodified
│   ├── test_sprites_cli.py         # list/extract subcommand tests (stage 2)
│   ├── test_pixels.py              # pixel/mask decoding + default palettes (stage 3)
│   ├── test_png.py                 # to-png tests, incl. mask promotion cases (stage 4)
│   ├── test_pnm.py                 # to-pnm tests, incl. extended indexed format (stage 5)
│   └── test_from_png.py            # from-png round-trip tests (stage 6)
├── pyproject.toml                  # gains full [project] table, both console_scripts
└── README.md
```

`Sprite`/`SpriteFile` become real classes with methods (parsing, selecting, rendering) instead
of the current dataclass-plus-free-functions style; `SpriteMode`/`PaletteEntry` stay as small
frozen dataclasses since they are decoded value records, not things with behaviour.

## Stages (one commit per functional boundary)

- [x] **Stage 0 — branch & plan**
  Create `sprites-png-conversion` branch in the `riscos-dumpsprites` repo; add `PLAN.md`
  (this plan) at the repo root; commit.

- [x] **Stage 1 — extract `riscos_sprites` package, zero behaviour change**
  Move parsing/validation/reporting logic out of `riscos_dumpsprites/cli.py` into the
  `riscos_sprites` submodules above, converting `Sprite`/`SpriteFile` into classes with methods.
  `riscos_dumpsprites/cli.py` becomes a thin shim producing byte-identical output to today.
  Update `pyproject.toml` to a full `[project]` table covering both packages, single
  `riscos-dumpsprites` console script (as today).
  **Verification:** existing `tests/test_cli.py` passes unmodified with no edits to its
  expectations. Done: report-building logic became methods on `Sprite`/`SpriteSelection`
  rather than a separate `reporting.py` module of free functions, to keep with "methods for
  the operations we perform on them". 13/14 tests pass; the 14th failure is a pre-existing
  mismatch on unmodified master (`test_summary_for_wavytile` expects `"27 640x480"` but
  `summary_mode()` has always produced `"27 (640x480)"`), unrelated to this refactor and left
  as-is (out of scope for this plan). `setup.py` removed; metadata now lives in
  `pyproject.toml`'s `[project]` table.

- [x] **Stage 2 — `riscos-sprites` CLI with `list` and `extract`**
  Add `riscos_sprites/cli.py` with argparse subparsers `list` (mirrors all current
  inspection flags) and `extract SPRITE_FILE SPRITE_NAME OUTPUT`. Add `riscos-sprites` console
  script + root launcher script. Add `tests/test_sprites_cli.py` covering both subcommands
  end-to-end (subprocess invocation, matching the style of the existing extract/filter tests).
  Done: 10 new tests added, all passing.

- [x] **Stage 3 — pixel-level decoding and default palettes**
  Port `default_palette2/4/16/256` from `c/palette` into `riscos_sprites/palette.py`
  (used when a sprite has no embedded palette). Add pixel/mask decoding to `Sprite`: handles
  `packswap` bit order for <8bpp, old-format vs new-format bpp, 16bpp 5:5:5 truecolour with
  bit-replication to 8:8:8, 32bpp RGB, CMYK inverted-byte-order (K,Y,M,C) via `CMYK_TO_RGB`,
  and 1bpp/8bpp-alpha mask decoding aligned to word-padded rows. Add `tests/test_pixels.py`
  with hand-verified pixel values from the existing sample sprites in `sprites/`.
  Done: implemented as `riscos_sprites/pixels.py` (decode_pixels/decode_mask/cmyk_to_rgb),
  with `Sprite.decode_pixels()`/`decode_mask()`/`effective_palette()` as the class-level
  entry points, `Sprite` extended with `image_data`/`mask_data` fields. Verified against real
  sample sprites: `basi3p02` decodes to the exact PngSuite colour-bar pattern its name
  implies, and `basi4a08`'s alpha mask decodes to the exact 0..255 gradient PngSuite is known
  for. No CMYK or reserved/24bpp sample sprites exist in `sprites/`, so those paths are
  covered only by direct unit tests of `cmyk_to_rgb()`, not a real-sprite round trip.

- [x] **Stage 4 — `to-png`** (done: implemented in `riscos_sprites/png.py`; the promotion chain
  works on already-decoded pixel/mask grids rather than transliterating the C bit-twiddling.
  Not replicated: the C code's debug placeholder colour for masked-out promoted pixels — ours
  uses the pixel's own (invisible, alpha=0) colour instead, a harmless simplification. 15 new
  tests, plus manual visual inspection via `host-open`.)
  `riscos_sprites/png.py`: hand-rolled PNG writer (IHDR/PLTE/tRNS/pHYs/tEXt/sBIT/IDAT via
  `zlib`/IEND, CRC32 via `zlib.crc32`). Ports the full C mask/promotion chain from `c/reverse`:
  colour-key search for a free palette/colour-cube slot (`NO_MASK`/`PROMOTE_PALETTE`/
  `PROMOTE_TRUE`/`PROMOTE_ALPHA`), per-format row conversion (indexed 1/2/4/8bpp, 16bpp,
  32bpp RGB, CMYK), `pHYs` from mode DPI, `tEXt` Creator comment, `sBIT` for 15bpp-marked
  16bpp sprites. CLI: `riscos-sprites to-png SPRITE_FILE SPRITE_NAME OUTPUT.png` or
  `riscos-sprites to-png SPRITE_FILE --all OUTPUT_DIR` (one PNG per sprite, named after the
  sprite, filtered by the same `--name`/`--mode`/`--type`/`--has-mask` options as `list`).
  **Verification:** `tests/test_png.py` decodes the written PNGs with a small test-local
  chunk/`zlib.decompress` reader (no external PNG library available) and checks pixel data,
  palette, and transparency handling for at least one sprite from each mask-strategy branch.

- [x] **Stage 5 — `to-pnm`** (done as planned: `riscos_sprites/pnm.py`, `--indexed` flag,
  `to-pnm` subcommand mirroring `to-png`'s shape. Masks ignored entirely, as PNM has no way
  to represent them. 12 new tests (6 module-level + 6 CLI). README note on mask-dropping still
  pending until Stage 7.)

- [x] **Stage 6 — `from-png`** (done substantially as planned. Deviations: true-colour masks
  always promote straight to an 8bpp alpha mask on the way in — rather than reconstructing
  ConvertPNG's colour-key search in reverse — since that's not needed for a valid, correct
  sprite, just a smaller one; indexed sources choose bpp/mask-kind (classic 1bpp vs 8bpp alpha)
  from the PNG's own bit depth and whether its transparency is purely binary. Along the way,
  found and fixed a real bug in the pre-existing `_validate()` mask-size check: it didn't
  distinguish old-format from new-format classic masks, wrongly flagging new-format
  non-alpha-masked sprites (which `from-png` is the first thing to actually produce) with a
  bogus size warning. `tests/test_png_reader.py` added alongside to cover the four PNG filter
  types our own writer never exercises (it always emits type 0), since `test_from_png.py`'s
  round trips alone wouldn't have tested that code at all. All round trips against the real
  sample sprites produce zero warnings.

- [ ] **Stage 7 — docs and version**
  Update `README.md` to document `riscos-sprites` and all its subcommands, keep the
  `riscos-dumpsprites` section, and fix the existing stale "update the version in
  pyproject.toml" instruction (version now genuinely lives in `pyproject.toml`'s `[project]`
  table after Stage 1). Bump the package version (new features, per project convention). Final
  full test run (`python3 -m unittest discover -s tests`).

## Verification

- After every stage: `python3 -m unittest discover -s tests` inside `riscos-dumpsprites/`.
- Stage 1 must not change any existing test's expected output — this is the regression gate
  for the refactor.
- PNG/PNM correctness is verified by decoding our own output back (via the Stage 6 PNG reader,
  brought forward for use in Stage 4/5 tests) and comparing against the source sprite's known
  pixel/palette data, plus manual spot-checks with `host-open` on a couple of converted files.
- `from-png` is verified by a full round trip (sprite → PNG → sprite) against the existing
  sample sprites in `sprites/`, in addition to fresh hand-made test PNGs.
