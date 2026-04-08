"""Unit tests for imgtxt.converter (charset and color logic)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from imgtxt.converter import (
    _BLOCK_TABLE,
    _BRAILLE_BITS,
    ASCII_DENSITY,
    CHARSET_MAP,
    DITHER_MAP,
    VALID_BG,
    VALID_CHARSETS,
    VALID_COLORS,
    VALID_DITHER,
    _avg_rgb,
    _build_sextant_map,
    _dither_floyd_steinberg,
    _dither_none,
    _dither_ordered,
    _get_emoji_table,
    _get_sextant_map,
    _get_unicode_brightness,
    _gray_grid,
    _render_ascii,
    _render_block,
    _render_braille,
    _render_emoji,
    _render_sextant,
    _render_unicode,
    _rgb_grid,
    _sextant_fallback,
    convert,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gray_img(pixels_2d: list[list[int]]) -> Image.Image:
    """Create a grayscale PIL Image from a 2D pixel list."""
    h = len(pixels_2d)
    w = len(pixels_2d[0])
    img = Image.new("L", (w, h))
    for y, row in enumerate(pixels_2d):
        for x, v in enumerate(row):
            img.putpixel((x, y), v)
    return img


def _rgb_img(pixels_2d: list[list[tuple[int, int, int]]]) -> Image.Image:
    """Create an RGB PIL Image from a 2D pixel list."""
    h = len(pixels_2d)
    w = len(pixels_2d[0])
    img = Image.new("RGB", (w, h))
    for y, row in enumerate(pixels_2d):
        for x, v in enumerate(row):
            img.putpixel((x, y), v)
    return img


def _gradient_gray(w: int = 40, h: int = 8) -> Image.Image:
    """Create a horizontal gradient grayscale image."""
    img = Image.new("L", (w, h))
    for x in range(w):
        v = int(x * 255 / max(w - 1, 1))
        for y in range(h):
            img.putpixel((x, y), v)
    return img


def _gradient_rgb(w: int = 40, h: int = 8) -> Image.Image:
    """Create a horizontal gradient RGB image."""
    img = Image.new("RGB", (w, h))
    for x in range(w):
        v = int(x * 255 / max(w - 1, 1))
        for y in range(h):
            img.putpixel((x, y), (v, v, v))
    return img


FIXTURE_IMAGES = Path(__file__).parent.parent / "functional" / "fixtures" / "images"


# ---------------------------------------------------------------------------
# Validation / constant tests
# ---------------------------------------------------------------------------


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

    def test_charset_map_keys(self):
        assert set(CHARSET_MAP.keys()) == VALID_CHARSETS

    def test_dither_map_keys(self):
        assert set(DITHER_MAP.keys()) == VALID_DITHER

    def test_block_table_has_16_entries(self):
        assert len(_BLOCK_TABLE) == 16

    def test_block_table_full_block(self):
        assert _BLOCK_TABLE[0b1111] == "\u2588"  # full block

    def test_block_table_space(self):
        assert _BLOCK_TABLE[0b0000] == " "


# ---------------------------------------------------------------------------
# Convert validation errors
# ---------------------------------------------------------------------------


class TestConvertValidation:
    IMG = FIXTURE_IMAGES / "gradient.png"

    def test_invalid_charset_raises(self):
        with pytest.raises(ValueError, match="charset"):
            convert(self.IMG, charset="bad")

    def test_invalid_color_raises(self):
        with pytest.raises(ValueError, match="color"):
            convert(self.IMG, color="bad")

    def test_invalid_bg_raises(self):
        with pytest.raises(ValueError, match="bg"):
            convert(self.IMG, bg="bad")

    def test_invalid_dither_raises(self):
        with pytest.raises(ValueError, match="dither"):
            convert(self.IMG, dither="bad")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_gray_grid_shape(self):
        img = _gray_img([[10, 20, 30], [40, 50, 60]])
        g = _gray_grid(img)
        assert len(g) == 2
        assert len(g[0]) == 3
        assert g[0][0] == 10
        assert g[1][2] == 60

    def test_rgb_grid_shape(self):
        img = _rgb_img([[(1, 2, 3), (4, 5, 6)]])
        g = _rgb_grid(img)
        assert len(g) == 1
        assert len(g[0]) == 2
        assert g[0][0] == (1, 2, 3)

    def test_avg_rgb_basic(self):
        assert _avg_rgb([(100, 100, 100), (200, 200, 200)]) == (150, 150, 150)

    def test_avg_rgb_empty(self):
        assert _avg_rgb([]) == (0, 0, 0)


# ---------------------------------------------------------------------------
# Dithering
# ---------------------------------------------------------------------------


class TestDithering:
    def test_none_bright(self):
        pixels = [[200, 200], [200, 200]]
        result = _dither_none(pixels)
        assert result == [[1, 1], [1, 1]]

    def test_none_dark(self):
        pixels = [[0, 0], [50, 50]]
        result = _dither_none(pixels)
        assert result == [[0, 0], [0, 0]]

    def test_none_threshold_127(self):
        pixels = [[127, 128]]
        result = _dither_none(pixels)
        assert result[0][0] == 0
        assert result[0][1] == 1

    def test_floyd_steinberg_uniform_bright(self):
        pixels = [[255] * 4 for _ in range(4)]
        result = _dither_floyd_steinberg(pixels)
        assert all(result[y][x] == 1 for y in range(4) for x in range(4))

    def test_floyd_steinberg_uniform_dark(self):
        pixels = [[0] * 4 for _ in range(4)]
        result = _dither_floyd_steinberg(pixels)
        assert all(result[y][x] == 0 for y in range(4) for x in range(4))

    def test_floyd_steinberg_returns_binary(self):
        pixels = [[i * 20 for i in range(10)] for _ in range(5)]
        result = _dither_floyd_steinberg(pixels)
        assert all(v in (0, 1) for row in result for v in row)

    def test_ordered_returns_binary(self):
        pixels = [[i * 10 for i in range(16)] for _ in range(4)]
        result = _dither_ordered(pixels)
        assert all(v in (0, 1) for row in result for v in row)

    def test_ordered_uniform_bright(self):
        pixels = [[255] * 8 for _ in range(4)]
        result = _dither_ordered(pixels)
        assert all(result[y][x] == 1 for y in range(4) for x in range(8))

    def test_ordered_uniform_dark(self):
        pixels = [[0] * 8 for _ in range(4)]
        result = _dither_ordered(pixels)
        assert all(result[y][x] == 0 for y in range(4) for x in range(8))

    def test_dither_map_callable(self):
        for name, fn in DITHER_MAP.items():
            pixels = [[128]]
            result = fn(pixels)
            assert isinstance(result, list), f"dither {name!r} should return list"


# ---------------------------------------------------------------------------
# ASCII charset
# ---------------------------------------------------------------------------


class TestRenderAscii:
    def test_mono_dark_pixel_is_densest_char(self):
        img = _gray_img([[0]])
        result = _render_ascii(img, invert=False, color="mono", bg="dark", dither="none")
        assert result[0] == ASCII_DENSITY[0]

    def test_mono_bright_pixel_is_lightest_char(self):
        img = _gray_img([[255]])
        result = _render_ascii(img, invert=False, color="mono", bg="dark", dither="none")
        assert result[-1] == ASCII_DENSITY[-1]

    def test_mono_invert_reverses(self):
        img = _gray_img([[0]])
        normal = _render_ascii(img, invert=False, color="mono", bg="dark", dither="none")
        inverted = _render_ascii(img, invert=True, color="mono", bg="dark", dither="none")
        assert normal[0] == ASCII_DENSITY[0]
        assert inverted[0] == ASCII_DENSITY[-1]

    def test_mono_multirow(self):
        img = _gray_img([[0, 255], [128, 64]])
        result = _render_ascii(img, invert=False, color="mono", bg="dark", dither="none")
        lines = result.split("\n")
        assert len(lines) == 2
        assert len(lines[0]) == 2

    def test_gradient_produces_increasing_sparsity(self):
        img = _gradient_gray(20, 1)
        result = _render_ascii(img, invert=False, color="mono", bg="dark", dither="none")
        # left should be denser chars, right should be sparser
        # first char index in density string should be lower than last
        left_idx = ASCII_DENSITY.index(result[0])
        right_idx = ASCII_DENSITY.index(result[-1])
        assert left_idx <= right_idx

    def test_ansi_produces_escape_codes(self):
        img = _gradient_rgb(4, 1)
        result = _render_ascii(img, invert=False, color="ansi", bg="dark", dither="none")
        assert "\x1b[" in result
        assert "\x1b[0m" in result

    def test_ansi_light_bg(self):
        img = _gradient_rgb(4, 1)
        result = _render_ascii(img, invert=False, color="ansi", bg="light", dither="none")
        assert "\x1b[" in result


# ---------------------------------------------------------------------------
# Unicode charset
# ---------------------------------------------------------------------------


class TestRenderUnicode:
    def test_returns_string(self):
        img = _gray_img([[0, 128, 255]])
        result = _render_unicode(img, invert=False, color="mono", bg="dark", dither="none")
        assert isinstance(result, str)
        assert len(result) == 3

    def test_table_loaded(self):
        table = _get_unicode_brightness()
        assert len(table) > 10

    def test_invert(self):
        img = _gray_img([[0]])
        normal = _render_unicode(img, invert=False, color="mono", bg="dark", dither="none")
        inverted = _render_unicode(img, invert=True, color="mono", bg="dark", dither="none")
        assert normal != inverted

    def test_ansi_produces_escape_codes(self):
        img = _gradient_rgb(4, 1)
        result = _render_unicode(img, invert=False, color="ansi", bg="dark", dither="none")
        assert "\x1b[" in result


# ---------------------------------------------------------------------------
# Block charset
# ---------------------------------------------------------------------------


class TestRenderBlock:
    def _make_2x2(self, ul: int, ur: int, ll: int, lr: int) -> Image.Image:
        """Create a 2×2 grayscale image with given pixel values (0=dark, 255=bright)."""
        return _gray_img([[ul, ur], [ll, lr]])

    def test_all_bright_is_full_block(self):
        img = self._make_2x2(255, 255, 255, 255)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2588"

    def test_all_dark_is_space(self):
        img = self._make_2x2(0, 0, 0, 0)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == " "

    def test_upper_left_only(self):
        # UL=bright, rest dark → pattern 1000 → ▘
        img = self._make_2x2(255, 0, 0, 0)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2598"

    def test_upper_right_only(self):
        # UR=bright, rest dark → pattern 0100 → ▝
        img = self._make_2x2(0, 255, 0, 0)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u259d"

    def test_lower_left_only(self):
        # LL=bright, rest dark → pattern 0010 → ▖
        img = self._make_2x2(0, 0, 255, 0)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2596"

    def test_lower_right_only(self):
        # LR=bright, rest dark → pattern 0001 → ▗
        img = self._make_2x2(0, 0, 0, 255)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2597"

    def test_upper_half(self):
        # UL+UR=bright, lower=dark → pattern 1100 → ▀
        img = self._make_2x2(255, 255, 0, 0)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2580"

    def test_lower_half(self):
        # UL+UR=dark, lower=bright → pattern 0011 → ▄
        img = self._make_2x2(0, 0, 255, 255)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
        assert result == "\u2584"

    def test_invert_inverts_pattern(self):
        # all bright normally → full block; with invert → space
        img = self._make_2x2(255, 255, 255, 255)
        result = _render_block(img, invert=True, color="mono", bg="dark", dither="none")
        assert result == " "

    def test_all_16_patterns(self):
        """Exercise all 16 block patterns."""
        results = set()
        for pattern in range(16):
            ul = 255 if (pattern >> 3) & 1 else 0
            ur = 255 if (pattern >> 2) & 1 else 0
            ll = 255 if (pattern >> 1) & 1 else 0
            lr = 255 if pattern & 1 else 0
            img = self._make_2x2(ul, ur, ll, lr)
            result = _render_block(img, invert=False, color="mono", bg="dark", dither="none")
            results.add(result)
        assert len(results) == 16

    def test_ansi_produces_block_with_escape(self):
        img = _rgb_img([[(255, 0, 0), (0, 255, 0)], [(0, 0, 255), (128, 128, 128)]])
        result = _render_block(img, invert=False, color="ansi", bg="dark", dither="none")
        assert "\x1b[" in result

    def test_dithering_floyd_steinberg(self):
        img = _gradient_gray(8, 8)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="floyd-steinberg")
        assert isinstance(result, str)
        assert len(result.split("\n")) == 4

    def test_dithering_ordered(self):
        img = _gradient_gray(8, 8)
        result = _render_block(img, invert=False, color="mono", bg="dark", dither="ordered")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Braille charset
# ---------------------------------------------------------------------------


class TestRenderBraille:
    def test_all_dark_returns_full_braille(self):
        """All dark (0) pixels → all dots → ⣿"""
        img = _gray_img([[0] * 2 for _ in range(4)])
        result = _render_braille(img, invert=False, dither="none", color="mono", bg="dark")
        assert result == "\u28ff"  # ⣿ all 8 dots

    def test_all_bright_returns_empty_braille(self):
        """All bright (255) pixels → no dots → ⠀"""
        img = _gray_img([[255] * 2 for _ in range(4)])
        result = _render_braille(img, invert=False, dither="none", color="mono", bg="dark")
        assert result == "\u2800"  # ⠀ empty braille

    def test_braille_codepoint_range(self):
        img = _gradient_gray(4, 8)
        result = _render_braille(img, invert=False, dither="none", color="mono", bg="dark")
        for char in result:
            if char != "\n":
                assert 0x2800 <= ord(char) <= 0x28FF

    def test_invert_reverses(self):
        img = _gray_img([[0] * 2 for _ in range(4)])
        normal = _render_braille(img, invert=False, dither="none", color="mono", bg="dark")
        inverted = _render_braille(img, invert=True, dither="none", color="mono", bg="dark")
        assert normal != inverted

    def test_braille_bit_assignments(self):
        """Verify bit assignments: (col=0,row=0) → bit 0 (dot 1)."""
        assert _BRAILLE_BITS[0][0] == 0  # col 0, row 0 → bit 0
        assert _BRAILLE_BITS[0][3] == 6  # col 0, row 3 → bit 6
        assert _BRAILLE_BITS[1][0] == 3  # col 1, row 0 → bit 3
        assert _BRAILLE_BITS[1][3] == 7  # col 1, row 3 → bit 7

    def test_multirow_output(self):
        img = _gray_img([[0] * 2 for _ in range(8)])
        result = _render_braille(img, invert=False, dither="none", color="mono", bg="dark")
        lines = result.split("\n")
        assert len(lines) == 2

    def test_dither_ordered(self):
        img = _gradient_gray(4, 8)
        result = _render_braille(img, invert=False, dither="ordered", color="mono", bg="dark")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Sextant charset
# ---------------------------------------------------------------------------


class TestRenderSextant:
    def test_sextant_map_nonempty(self):
        smap = _get_sextant_map()
        assert len(smap) >= 50  # expect at least ~60 entries

    def test_sextant_map_bit_range(self):
        smap = _get_sextant_map()
        for bits in smap:
            assert 0 <= bits <= 0b111111

    def test_sextant_all_dark_returns_full_block(self):
        img = _gray_img([[0] * 2 for _ in range(3)])
        result = _render_sextant(img, invert=False, dither="none", color="mono", bg="dark")
        assert result == "\u2588"  # █

    def test_sextant_all_bright_returns_space(self):
        img = _gray_img([[255] * 2 for _ in range(3)])
        result = _render_sextant(img, invert=False, dither="none", color="mono", bg="dark")
        assert result == " "

    def test_sextant_fallback_returns_string(self):
        smap = _get_sextant_map()
        # 0b101010 might be missing; fallback should still return something
        result = _sextant_fallback(0b101010, smap)
        assert isinstance(result, str)
        assert len(result) == 1

    def test_sextant_invert(self):
        img = _gray_img([[0] * 2 for _ in range(3)])
        normal = _render_sextant(img, invert=False, dither="none", color="mono", bg="dark")
        inverted = _render_sextant(img, invert=True, dither="none", color="mono", bg="dark")
        assert normal != inverted

    def test_sextant_multirow(self):
        img = _gray_img([[128] * 2 for _ in range(6)])
        result = _render_sextant(img, invert=False, dither="none", color="mono", bg="dark")
        lines = result.split("\n")
        assert len(lines) == 2

    def test_sextant_build_map(self):
        smap = _build_sextant_map()
        # Verify a known character: BLOCK SEXTANT-1 = U+1FB00 (only top-left filled)
        assert 0b000001 in smap


# ---------------------------------------------------------------------------
# Emoji charset
# ---------------------------------------------------------------------------


class TestRenderEmoji:
    def test_returns_string(self):
        img = _rgb_img([[(255, 0, 0)]])
        result = _render_emoji(
            img, out_width=2, color="mono", bg="dark", dither="none", invert=False
        )
        assert isinstance(result, str)

    def test_emoji_table_nonempty(self):
        table = _get_emoji_table()
        assert len(table) > 5

    def test_dark_pixel_returns_dark_emoji(self):
        img = _rgb_img([[(10, 10, 10)]])
        result = _render_emoji(
            img, out_width=2, color="mono", bg="dark", dither="none", invert=False
        )
        # Should be a dark emoji (e.g. ⬛ or 🖤)
        assert any(ord(c) > 127 for c in result)

    def test_multirow(self):
        img = _rgb_img([[(255, 0, 0)], [(0, 0, 255)]])
        result = _render_emoji(
            img, out_width=2, color="mono", bg="dark", dither="none", invert=False
        )
        assert "\n" in result


# ---------------------------------------------------------------------------
# End-to-end convert() function
# ---------------------------------------------------------------------------


class TestConvert:
    IMG = FIXTURE_IMAGES / "gradient.png"
    CHECK = FIXTURE_IMAGES / "checkerboard.png"

    def test_ascii_mono(self):
        result = convert(self.IMG, charset="ascii", color="mono", width=20)
        lines = result.split("\n")
        assert all(len(line) == 20 for line in lines)

    def test_unicode_mono(self):
        result = convert(self.IMG, charset="unicode", color="mono", width=20)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_block_mono(self):
        result = convert(self.CHECK, charset="block", color="mono", width=20)
        assert isinstance(result, str)

    def test_braille_mono(self):
        result = convert(self.IMG, charset="braille", color="mono", width=20)
        assert isinstance(result, str)

    def test_sextant_mono(self):
        result = convert(self.IMG, charset="sextant", color="mono", width=20)
        assert isinstance(result, str)

    def test_emoji(self):
        result = convert(self.IMG, charset="emoji", width=20)
        assert isinstance(result, str)

    def test_width_respected_ascii(self):
        result = convert(self.IMG, charset="ascii", color="mono", width=30)
        for line in result.split("\n"):
            assert len(line) == 30

    def test_height_respected(self):
        result = convert(self.IMG, charset="ascii", color="mono", width=20, height=3)
        lines = result.split("\n")
        assert len(lines) == 3

    def test_dither_none(self):
        result = convert(self.CHECK, charset="block", dither="none", color="mono", width=20)
        assert isinstance(result, str)

    def test_dither_floyd_steinberg(self):
        result = convert(
            self.CHECK, charset="block", dither="floyd-steinberg", color="mono", width=20
        )
        assert isinstance(result, str)

    def test_dither_ordered(self):
        result = convert(self.CHECK, charset="block", dither="ordered", color="mono", width=20)
        assert isinstance(result, str)

    def test_invert_differs_from_normal(self):
        r1 = convert(self.IMG, charset="ascii", color="mono", width=20)
        r2 = convert(self.IMG, charset="ascii", color="mono", width=20, invert=True)
        assert r1 != r2

    def test_emoji_ignores_color_mode(self):
        # emoji should work regardless of color setting
        r1 = convert(self.IMG, charset="emoji", color="mono", width=20)
        r2 = convert(self.IMG, charset="emoji", color="ansi", width=20)
        assert r1 == r2  # both go through same emoji path (ansi ignored for emoji)
