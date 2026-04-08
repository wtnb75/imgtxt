# SPEC.md — Design Specification

## Features

### Conversion Methods (selectable)

| Method | Description |
|--------|-------------|
| `brightness` | Maps pixel brightness to ASCII character density (default) |
| `edge` | Detects edges (e.g. Sobel filter) and renders them as characters |
| `block` | Uses block elements (▀▄█ etc.) for a pixel-art look |
| `color` | Outputs colored text using ANSI escape codes |
| `braille` | Uses braille characters (⠀–⣿) for high-resolution output |

### CLI Interface

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
| `--method` | Conversion method: `brightness` / `edge` / `block` / `color` / `braille` |
| `--width` | Output width in characters (default: 80) |
| `--height` | Output height in characters (auto-calculated from aspect ratio if omitted) |
| `--output` | Output file path (defaults to stdout) |
| `--invert` | Invert light/dark |
| `--charset` | Character set used by the `brightness` method (default: ` .:-=+*#%@`) |

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

- Use `Pillow` to load, convert to grayscale, and resize the image before passing it to each method
- Account for character aspect ratio (height:width ≈ 2:1) when auto-calculating output height
- Fall back gracefully when ANSI color output (`color` method) is used in a non-TTY context
- Each module's responsibility:
  - `cli.py` — argument parsing and subcommand routing only; no conversion logic
  - `converter.py` — all conversion logic; exposes a `convert()` function and a `METHOD_MAP` dict
  - `utils.py` — image loading, resizing, and other shared helpers
