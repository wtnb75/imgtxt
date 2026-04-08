"""Unit tests for imgtxt.converter (charset and color logic)."""

from __future__ import annotations

from imgtxt.converter import VALID_BG, VALID_CHARSETS, VALID_COLORS, VALID_DITHER


class TestValidation:
    def test_valid_charsets_set(self):
        assert "ascii" in VALID_CHARSETS
        assert "unicode" in VALID_CHARSETS
        assert "block" in VALID_CHARSETS
        assert "braille" in VALID_CHARSETS
        assert "sextant" in VALID_CHARSETS
        assert "emoji" in VALID_CHARSETS

    def test_valid_colors_set(self):
        assert VALID_COLORS == {"mono", "ansi"}

    def test_valid_dither_set(self):
        assert "none" in VALID_DITHER
        assert "floyd-steinberg" in VALID_DITHER
        assert "ordered" in VALID_DITHER

    def test_valid_bg_set(self):
        assert VALID_BG == {"dark", "light"}
