# AGENTS.md

## Project Overview

A Python CLI tool that converts images into ASCII art-style text representations.

See [SPEC.md](SPEC.md) for design details and [SPEC_TEST.md](SPEC_TEST.md) for test strategy.

## Tech Stack

- **Language**: Python 3 (latest stable release)
- **Package manager**: [uv](https://docs.astral.sh/uv/)
- **Linter / Formatter**: [ruff](https://docs.astral.sh/ruff/)

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

## Coding Rules

- All source code and comments must be written in English
- Each conversion method must be implemented as an independent function or class
- Use a dispatch dict (e.g. `METHOD_MAP`) so new methods can be added without modifying callers
- Do not use mutable default arguments
- Prefer `pathlib.Path` over `os.path` for file operations
- Public functions must have type annotations and docstrings

