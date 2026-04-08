"""Unit tests for imgtxt.utils."""

from __future__ import annotations

import os
from unittest.mock import patch

from imgtxt import utils


class TestGetOutputWidth:
    def test_explicit_width_returned_as_is(self):
        assert utils.get_output_width(120) == 120

    def test_none_uses_terminal_size(self):
        with patch("shutil.get_terminal_size", return_value=os.terminal_size((100, 24))):
            assert utils.get_output_width(None) == 100

    def test_none_falls_back_to_80_when_not_tty(self):
        with patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 24))):
            assert utils.get_output_width(None) == 80


class TestComputeSampleSize:
    def test_ascii_1x1_cells(self):
        w, h = utils.compute_sample_size(40, None, "ascii", (100, 50))
        assert w == 40
        # aspect=0.5, char_aspect=2.0 → char_rows = round(40 * 0.5 / 2.0) = 10
        assert h == 10

    def test_block_2x2_cells(self):
        w, h = utils.compute_sample_size(20, None, "block", (100, 100))
        assert w == 40  # 20 * 2
        # aspect=1.0, char_rows=round(20*1.0/2)=10, sample_h=10*2=20
        assert h == 20

    def test_braille_2x4_cells(self):
        w, h = utils.compute_sample_size(20, None, "braille", (100, 100))
        assert w == 40  # 20 * 2
        # char_rows=10, sample_h=10*4=40
        assert h == 40

    def test_sextant_2x3_cells(self):
        w, h = utils.compute_sample_size(20, None, "sextant", (100, 100))
        assert w == 40
        assert h == 30  # char_rows=10, 10*3=30

    def test_emoji_halves_columns(self):
        w, h = utils.compute_sample_size(40, None, "emoji", (100, 100))
        assert w == 20  # 40//2 * 1
        assert h == 10  # char_rows = round(20*1.0/2)=10

    def test_explicit_height_overrides_auto(self):
        w, h = utils.compute_sample_size(40, 5, "ascii", (100, 100))
        assert w == 40
        assert h == 5


class TestDisplayWidth:
    def test_ascii_is_1(self):
        assert utils.display_width("A") == 1

    def test_cjk_is_2(self):
        assert utils.display_width("あ") == 2

    def test_emoji_is_2(self):
        assert utils.display_width("😀") == 2


class TestAnsiHelpers:
    def test_fg_standard(self):
        assert utils.ansi_fg(1) == "\x1b[31m"

    def test_fg_bright(self):
        assert utils.ansi_fg(9) == "\x1b[91m"

    def test_bg_standard(self):
        assert utils.ansi_bg(2) == "\x1b[42m"

    def test_bg_bright(self):
        assert utils.ansi_bg(10) == "\x1b[102m"

    def test_reset_constant(self):
        assert utils.ANSI_RESET == "\x1b[0m"


class TestNearestAnsiColor:
    PALETTE = [
        {"code": 1, "rgb": [128, 0, 0]},
        {"code": 2, "rgb": [0, 128, 0]},
        {"code": 4, "rgb": [0, 0, 128]},
    ]

    def test_exact_match(self):
        assert utils.nearest_ansi_color((128, 0, 0), self.PALETTE, []) == 1

    def test_nearest_by_distance(self):
        # (0, 0, 130) is closest to blue (0, 0, 128)
        assert utils.nearest_ansi_color((0, 0, 130), self.PALETTE, []) == 4

    def test_exclude_skips_code(self):
        # exclude code 4 (blue), nearest to (0, 0, 130) becomes green
        result = utils.nearest_ansi_color((0, 0, 130), self.PALETTE, [4])
        assert result in (1, 2)  # not 4


class TestNearestEmoji:
    TABLE = [("🔴", (255, 0, 0)), ("🟢", (0, 255, 0)), ("🔵", (0, 0, 255))]

    def test_red(self):
        assert utils.nearest_emoji((240, 10, 10), self.TABLE) == "🔴"

    def test_green(self):
        assert utils.nearest_emoji((10, 240, 10), self.TABLE) == "🟢"

    def test_blue(self):
        assert utils.nearest_emoji((10, 10, 240), self.TABLE) == "🔵"
