# SPEC.md — Design Specification

## Design Axes

Rendering is controlled by two independent axes: **charset** and **color**.
They can be combined freely (e.g. braille + ansi, block + mono).

---

## Charset (`--charset`)

The charset determines which characters are used and how many pixels each character cell represents.

| Value | Characters used | Cell resolution | Status |
|-------|----------------|-----------------|--------|
| `ascii` | ` .:-=+*#%@` (printable ASCII) | 1×1 | Implemented |
| `unicode` | Monospace-renderable Unicode (pre-computed table) | 1×1 | Implemented |
| `braille` | U+2800–U+28FF (⠀–⣿) | 2×4 per cell | Implemented |
| `block` | U+2580–U+259F quarter/half blocks | 2×2 per cell | Implemented |
| `sextant` | U+1FB00–U+1FB3B (🬀–🬻) | 2×3 per cell | Implemented |
| `emoji` | Representative emoji (pre-computed table) | 1×1 (2-col wide) | Implemented |
| `box` | U+2500–U+257F box-drawing chars | 1×1 | **Deferred** |
| `ansi-graphics` | ANSI/VT100 line-drawing set | 1×1 | **Deferred** |

`box` and `ansi-graphics` require edge-direction detection (a fundamentally different algorithm)
and are deferred to a future release. The `CHARSET_MAP` dispatch structure must accommodate
adding them without modifying existing code.

---

### `ascii` and `unicode` — Brightness-to-character mapping

`ascii` uses a fixed hand-curated string ordered by visual density.

`unicode` uses a pre-computed brightness table generated offline:
- Render candidate characters using commonly used monospace fonts
  (DejaVu Sans Mono, Noto Sans Mono, Fira Code, Source Code Pro)
- Compute pixel density (fraction of dark pixels) per glyph at a standard size
- Average across fonts; sort by density; deduplicate visually similar entries
- Store the result as a data file (`imgtxt/data/unicode_brightness.txt`) committed to the repo
- At runtime, load the table once and use it for brightness lookup

For `unicode`, characters whose `wcwidth()` ≠ 1 (double-width, combining, etc.) are excluded
from the table. This keeps the grid calculation identical to `ascii`.

---

### `emoji` — Color-based character mapping

Each emoji is mapped to an (R, G, B) representative color pre-computed offline:
- Render emoji using a standard emoji font (Noto Emoji or Twemoji)
- Compute the average RGB of non-transparent pixels per glyph
- Store as `imgtxt/data/emoji_colors.json` committed to the repo

At runtime, given a cell's average RGB, find the nearest emoji by Euclidean distance in RGB space.

#### Double-width character handling (emoji and CJK)

Emoji and CJK characters occupy **2 terminal columns**. The output grid must account for this:

- Use `wcwidth(char)` (via the `wcwidth` Python package) to get the display width of each character
- When a charset produces double-width characters, the effective output width in characters
  is `W // 2` — sample `W // 2` pixel columns and emit one character per 2-column slot
- The same logic applies to `unicode` if CJK characters appear in the brightness table
  (they are excluded from the `unicode` table; `emoji` always produces double-width output)

Cell resolution and image sampling for target output width `W` (in terminal columns):

| Charset | Terminal cols per char | Pixel columns sampled | Pixel rows sampled |
|---------|------------------------|----------------------|--------------------|
| `ascii`, `unicode` | 1 | W | W × aspect / 2 |
| `emoji` | 2 | W / 2 | W / 2 × aspect / 2 |
| `block` | 1 | W × 2 | W × aspect |
| `sextant` | 1 | W × 2 | W × 3/2 × aspect |
| `braille` | 1 | W × 2 | W × 2 × aspect |

(The `/2` in row counts accounts for the terminal character aspect ratio of ~2:1.)

---

### `block` — Precise 2×2 bit-pattern mapping

Each output character cell covers a 2×2 pixel region. Each pixel is thresholded to 0 (dark)
or 1 (bright). The 4-bit pattern is encoded as:

```
bit 3 | bit 2        upper-left  | upper-right
------+------   →   ------------+-------------
bit 1 | bit 0        lower-left  | lower-right
```

All 16 patterns map to a specific Unicode character:

| Pattern (UL UR LL LR) | Char | Codepoint |
|-----------------------|------|-----------|
| 0000 | ` ` | U+0020 |
| 0001 | `▗` | U+2597 |
| 0010 | `▖` | U+2596 |
| 0011 | `▄` | U+2584 |
| 0100 | `▝` | U+259D |
| 0101 | `▐` | U+2590 |
| 0110 | `▞` | U+259E |
| 0111 | `▟` | U+259F |
| 1000 | `▘` | U+2598 |
| 1001 | `▚` | U+259A |
| 1010 | `▌` | U+258C |
| 1011 | `▙` | U+2599 |
| 1100 | `▀` | U+2580 |
| 1101 | `▜` | U+259C |
| 1110 | `▛` | U+259B |
| 1111 | `█` | U+2588 |

The threshold for each pixel: `1` if brightness > 128 (adjustable with `--invert`).

---

### `braille` — 2×4 dot encoding

Each braille cell covers a 2×4 pixel region. Pixels are thresholded (dark pixel = dot present).
The Unicode braille codepoint is `U+2800 + bits`, where bits are assigned as:

```
col 0, row 0 → bit 0 (dot 1)    col 1, row 0 → bit 3 (dot 4)
col 0, row 1 → bit 1 (dot 2)    col 1, row 1 → bit 4 (dot 5)
col 0, row 2 → bit 2 (dot 3)    col 1, row 2 → bit 5 (dot 6)
col 0, row 3 → bit 6 (dot 7)    col 1, row 3 → bit 7 (dot 8)
```

---

### `sextant` — 2×3 dot encoding

Each sextant cell covers a 2×3 pixel region (6 bits → 63 non-space characters + space).
U+1FB00 encodes pattern `000001`, U+1FB3B encodes `111110`; `U+0020` (space) = `000000`,
`U+2588` (█) = `111111`.

---

## Color (`--color`)

| Value | Description |
|-------|-------------|
| `mono` | No color codes; character choice alone conveys brightness (default) |
| `ansi` | ANSI foreground + background colors; requires `--bg` to match terminal |

### `ansi` mode design

ANSI 16-color palettes vary by terminal, so we use two canonical palettes
(common defaults for dark and light terminals) selectable via `--bg`:

| `--bg` | Description |
|--------|-------------|
| `dark` | Optimized for dark/black terminal backgrounds (default) |
| `light` | Optimized for light/white terminal backgrounds |

Each palette defines representative RGB values for the 8 standard + 8 bright ANSI colors.
The palette data is stored in `imgtxt/data/ansi_palettes.toml`.

**Mapping algorithm (per cell):**
1. Compute average RGB of the cell's pixels
2. Find the nearest color in the active palette by Euclidean distance in RGB space
3. Emit the corresponding ANSI foreground escape code + character

**Rules:**
- Black (color 0) and white (color 7/15) are excluded from the foreground palette
  when `--bg dark` / `--bg light` respectively, to avoid invisible text
- In `mono` mode: convert to grayscale before sampling; no escape codes emitted
- In `ansi` mode: keep RGB; brightness still controls character choice within the cell
- When stdout is not a TTY, `ansi` falls back to `mono` automatically

---

---

## CLI Interface

The CLI uses subcommands to allow future extensibility. The primary subcommand is `convert`.

```
imgtxt [OPTIONS] COMMAND [ARGS]...
```

#### `imgtxt convert` — Convert an image to text

```
imgtxt convert [OPTIONS] IMAGE_PATH
```

| Option | Description |
|--------|-------------|
| `--charset` | Character set: `ascii` / `unicode` / `braille` / `block` / `sextant` / `emoji` (default: `ascii`) |
| `--color` | Color mode: `mono` / `ansi` (default: `mono`) |
| `--bg` | Terminal background for ANSI palette: `dark` / `light` (default: `dark`; ignored in `mono` mode) |
| `--width` | Output width in terminal columns (default: 80) |
| `--height` | Output height in terminal rows (auto-calculated from aspect ratio if omitted) |
| `--output` | Output file path (defaults to stdout) |
| `--invert` | Invert light/dark |


## Directory Structure

```
imgtxt/
├── AGENTS.md
├── SPEC.md
├── SPEC_TEST.md
├── pyproject.toml              # includes uv / ruff config
├── imgtxt/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point (typer)
│   ├── converter.py            # per-method conversion logic
│   ├── utils.py                # shared utilities
│   └── data/
│       ├── unicode_brightness.txt  # pre-computed brightness table
│       ├── emoji_colors.json       # emoji → representative RGB
│       └── ansi_palettes.toml      # dark/light ANSI color palettes
└── tests/
    ├── unit/                   # whitebox unit tests (coverage target: 80%)
    │   ├── test_converter.py
    │   ├── test_cli.py
    │   └── test_utils.py
    └── functional/             # blackbox functional tests
        ├── fixtures/
        │   ├── images/
        │   └── expected/
        ├── cases.toml
        ├── conftest.py
        └── test_convert.py
```

## Expected pyproject.toml

```toml
[project]
name = "imgtxt"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "Pillow",       # image loading and resizing
    "typer",        # CLI framework
    "numpy",        # numerical operations (e.g. edge detection)
]

[project.scripts]
imgtxt = "imgtxt.cli:app"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["imgtxt"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

## Implementation Guidelines

- `--charset` and `--color` are orthogonal; implement them as separate pipeline stages
- Use `Pillow` to load and resize; convert to grayscale for `mono`, keep RGB for `ansi`
- Account for character aspect ratio (~2:1) and per-charset cell resolution when computing sample size
- Use `wcwidth()` from the `wcwidth` package for all display-width calculations;
  never assume a character is 1 column wide without checking
- Fall back to `mono` when stdout is not a TTY and `--color ansi` is requested
- Pre-computed data files live in `imgtxt/data/` and are committed to the repo:
  - `unicode_brightness.txt` — characters sorted by visual density
  - `emoji_colors.json` — emoji to representative RGB mapping
  - `ansi_palettes.toml` — dark/light canonical ANSI color palettes
- Each module's responsibility:
  - `cli.py` — argument parsing and subcommand routing only; no conversion logic
  - `converter.py` — all conversion logic; exposes `convert()` and `CHARSET_MAP` / `COLOR_MAP` dicts
  - `utils.py` — image loading, resizing, aspect ratio calculation, ANSI escape helpers, wcwidth utilities
