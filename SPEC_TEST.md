# SPEC_TEST.md — Test Strategy

## Overview

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

## Functional Test Design

### Test Data Layout

```
tests/functional/
├── fixtures/
│   ├── images/             # sample input images (committed to repo)
│   │   ├── gradient.png    # simple horizontal brightness gradient
│   │   ├── checkerboard.png
│   │   └── ...
│   └── expected/           # expected text output files
│       ├── gradient_brightness_w20.txt
│       ├── gradient_edge_w20.txt
│       ├── checkerboard_block_w20.txt
│       └── ...             # named as {image}_{method}_{options}.txt
├── cases.toml              # test case definitions
├── conftest.py             # loads cases.toml and provides fixtures
└── test_convert.py         # parametrized functional tests
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
