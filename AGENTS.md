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
        │   ├── images/         # sample input images (committed to repo)
        │   │   ├── gradient.png
        │   │   ├── checkerboard.png
        │   │   └── ...
        │   └── expected/       # expected text output files
        │       ├── gradient_brightness_w20.txt
        │       ├── gradient_edge_w20.txt
        │       ├── checkerboard_block_w20.txt
        │       └── ...         # named as {image}_{method}_{options}.txt
        ├── cases.toml          # test case definitions
        ├── conftest.py         # loads cases.toml and provides fixtures
        └── test_convert.py     # parametrized functional tests
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

# Run unit tests with coverage
uv run pytest tests/unit --cov=imgtxt --cov-report=term-missing

# Run functional tests
uv run pytest tests/functional

# Run all tests
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

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["imgtxt"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

## Implementation Guidelines

- Implement each conversion method as an independent function or class in `converter.py`
- Use a dispatch dict (e.g. `METHOD_MAP`) to make adding new methods easy
- Use `Pillow` to load, convert to grayscale, and resize the image before passing it to each method
- Account for character aspect ratio (height:width ≈ 2:1) when auto-calculating output height
- Fall back gracefully when ANSI color output (`color` method) is used in a non-TTY context

## Functional Test Design

Tests are split into two categories:

| Category | Location | Approach | Coverage |
|----------|----------|----------|----------|
| Unit tests | `tests/unit/` | Whitebox — test internal functions/classes directly | **Target: 80%** |
| Functional tests | `tests/functional/` | Blackbox — compare CLI/converter output against expected text files | N/A |

Run unit tests with coverage enforcement:

```bash
uv run pytest tests/unit --cov=imgtxt --cov-report=term-missing
# fails if coverage drops below 80% (configured via fail_under in pyproject.toml)
```

### Test Case Definitions (`tests/functional/cases.toml`)

Each test case declares an input image, conversion options, and the expected output file.
To add a new test (e.g. for a new method), add an entry to `cases.toml` and place the
expected output file in `tests/functional/fixtures/expected/`.

```toml
[[cases]]
id = "gradient-brightness"
image = "gradient.png"
method = "brightness"
width = 20
expected = "gradient_brightness_w20.txt"

[[cases]]
id = "gradient-edge"
image = "gradient.png"
method = "edge"
width = 20
expected = "gradient_edge_w20.txt"

[[cases]]
id = "checkerboard-block"
image = "checkerboard.png"
method = "block"
width = 20
expected = "checkerboard_block_w20.txt"

# Add new methods here — no changes to test code required
```

### `tests/functional/conftest.py`

Loads `cases.toml` and exposes each case as a pytest parameter:

```python
import tomllib
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

def load_cases():
    with open(Path(__file__).parent / "cases.toml", "rb") as f:
        data = tomllib.load(f)
    return data["cases"]

def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        cases = load_cases()
        metafunc.parametrize("case", cases, ids=[c["id"] for c in cases])
```

### `tests/functional/test_convert.py`

```python
from imgtxt.converter import convert
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

def test_convert_output(case):
    image_path = FIXTURES / "images" / case["image"]
    expected_path = FIXTURES / "expected" / case["expected"]
    result = convert(image_path, method=case["method"], width=case["width"])
    assert result == expected_path.read_text()
```

### Updating Expected Outputs

When the conversion logic is intentionally changed, regenerate expected outputs with:

```bash
uv run pytest tests/functional --update-snapshots
```

Implement `--update-snapshots` in `conftest.py` to overwrite files in `tests/functional/fixtures/expected/`
instead of asserting equality.
