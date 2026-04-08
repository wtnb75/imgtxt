"""Functional test infrastructure: load cases.toml and parametrize."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_cases() -> list[dict]:
    """Load test case definitions from cases.toml."""
    with open(Path(__file__).parent / "cases.toml", "rb") as f:
        data = tomllib.load(f)
    return data["cases"]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Overwrite expected output files instead of asserting equality.",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "case" in metafunc.fixturenames:
        cases = load_cases()
        metafunc.parametrize("case", cases, ids=[c["id"] for c in cases])


@pytest.fixture
def update_snapshots(request: pytest.FixtureRequest) -> bool:
    """Return True if --update-snapshots flag was passed."""
    return bool(request.config.getoption("--update-snapshots"))
