# SPEC.md — Design Specification

## Design Axes

Rendering is controlled by two independent axes: **charset** and **color**.
They can be combined freely (e.g. braille + ansi, block + mono).

---

## Charset (`--charset`)

The charset determines which characters are used and how many pixels each character cell represents.

| Value | Characters used | Cell resolution | Notes |
|-------|----------------|-----------------|-------|
| `ascii` | ` .:-=+*#%@` (printable ASCII) | 1×1 | Default; widest terminal compatibility |
| `unicode` | All Unicode (excl. surrogate pairs U+D800–U+DFFF) | 1×1 | Broader density range |
| `braille` | U+2800–U+28FF (⠀–⣿) | 2×4 per cell | Highest resolution among text methods |
| `block` | U+2580–U+259F (▀▄▌▐█ etc.) | 2×2 per cell | Clean pixel-art look |
| `box` | U+2500–U+257F (─│┌┐└┘┼ etc.) | 1×1 | Traces edges with line-drawing chars |
| `sextant` | U+1FB00–U+1FB3B (🬀–🬻) | 2×3 per cell | Higher resolution than block |
| `ansi-graphics` | ANSI/VT100 line-drawing set | 1×1 | Terminal-native; limited char variety |
| `emoji` | Representative emoji per region | 1×1 | Color-expressive; wide char width (2 columns) |

### Cell Resolution and Image Sampling

Because each character cell can encode multiple pixels, the image is downsampled
differently per charset before mapping. For a target output width `W`:

| Charset | Sample width | Sample height |
|---------|-------------|---------------|
| `ascii`, `unicode`, `box`, `ansi-graphics`, `emoji` | W | W × aspect |
| `block` | W × 2 | W × 2 × aspect |
| `sextant` | W × 2 | W × 3 × aspect |
| `braille` | W × 2 | W × 4 × aspect |

---

## Color (`--color`)

| Value | Description |
|-------|-------------|
| `mono` | No color codes; character choice alone conveys brightness (default) |
| `ansi` | 4-bit ANSI foreground colors (16 colors); maps dominant hue per cell |

- In `mono` mode, the image is converted to grayscale before sampling.
- In `ansi` mode, the original RGB image is used; hue is mapped to the nearest ANSI color,
  brightness controls character choice.
- When stdout is not a TTY, `ansi` mode falls back to `mono` automatically.

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
| `--charset` | Character set: `ascii` / `unicode` / `braille` / `block` / `box` / `sextant` / `ansi-graphics` / `emoji` (default: `ascii`) |
| `--color` | Color mode: `mono` / `ansi` (default: `mono`) |
| `--width` | Output width in characters (default: 80) |
| `--height` | Output height in characters (auto-calculated from aspect ratio if omitted) |
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
│   └── utils.py                # shared utilities
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
- Use `Pillow` to load and resize the image; convert to grayscale for `mono`, keep RGB for `ansi`
- Account for character aspect ratio (height:width ≈ 2:1) when auto-calculating output height,
  combined with the per-charset cell resolution (see Cell Resolution table above)
- Fall back to `mono` when stdout is not a TTY and `--color ansi` is requested
- Each module's responsibility:
  - `cli.py` — argument parsing and subcommand routing only; no conversion logic
  - `converter.py` — all conversion logic; exposes a `convert()` function and `CHARSET_MAP` / `COLOR_MAP` dicts
  - `utils.py` — image loading, resizing, aspect ratio calculation, and ANSI escape helpers
