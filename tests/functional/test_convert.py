"""Functional tests: compare converter output against expected text files."""

from __future__ import annotations

from pathlib import Path

from imgtxt.converter import convert

FIXTURES = Path(__file__).parent / "fixtures"


def test_convert_output(case: dict, update_snapshots: bool) -> None:
    """Run convert() and compare against the expected output file."""
    image_path = FIXTURES / "images" / case["image"]
    expected_path = FIXTURES / "expected" / case["expected"]

    result = convert(
        image_path,
        charset=case["charset"],
        color=case["color"],
        width=case["width"],
    )

    if update_snapshots:
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(result, encoding="utf-8")
        return

    assert result == expected_path.read_text(encoding="utf-8")
