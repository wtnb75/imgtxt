# AGENTS.md

## Project Overview

A Python CLI tool that converts images into ASCII art-style text representations.

## Tech Stack

- **Language**: Python 3.11+
- **Package manager**: [uv](https://docs.astral.sh/uv/)
- **Linter / Formatter**: [ruff](https://docs.astral.sh/ruff/)

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
├── pyproject.toml          # includes uv / ruff config
├── imgtxt/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point (typer)
│   ├── converter.py    # per-method conversion logic
│   └── utils.py        # shared utilities
└── tests/
    ├── test_converter.py
    └── test_cli.py
```

## Development Setup

```bash
# Install dependencies
uv sync

# Install in editable mode
uv pip install -e .

# Run the CLI
uv run imgtxt --help
```

## Code Quality

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check .

# Lint with auto-fix
uv run ruff check --fix .

# Run tests
uv run pytest
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
```

## Implementation Guidelines

- Implement each conversion method as an independent function or class in `converter.py`
- Use a dispatch dict (e.g. `METHOD_MAP`) to make adding new methods easy
- Use `Pillow` to load, convert to grayscale, and resize the image before passing it to each method
- Account for character aspect ratio (height:width ≈ 2:1) when auto-calculating output height
- Fall back gracefully when ANSI color output (`color` method) is used in a non-TTY context
