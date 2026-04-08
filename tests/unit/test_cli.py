"""Unit tests for the CLI (imgtxt.cli)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from imgtxt.cli import app

runner = CliRunner()

FIXTURE_IMAGES = Path(__file__).parent.parent / "functional" / "fixtures" / "images"


class TestCliHelp:
    def test_root_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "convert" in result.output.lower()

    def test_convert_help(self):
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--charset" in result.output
        assert "--color" in result.output
        assert "--dither" in result.output
        assert "--width" in result.output


class TestConvertCommand:
    IMG = str(FIXTURE_IMAGES / "gradient.png")

    def test_basic_ascii(self):
        result = runner.invoke(app, ["convert", self.IMG, "--charset", "ascii", "--width", "10"])
        assert result.exit_code == 0
        assert len(result.output.strip()) > 0

    def test_unicode_charset(self):
        result = runner.invoke(app, ["convert", self.IMG, "--charset", "unicode", "--width", "10"])
        assert result.exit_code == 0

    def test_block_charset(self):
        result = runner.invoke(
            app,
            [
                "convert",
                str(FIXTURE_IMAGES / "checkerboard.png"),
                "--charset",
                "block",
                "--width",
                "10",
            ],
        )
        assert result.exit_code == 0

    def test_braille_charset(self):
        result = runner.invoke(app, ["convert", self.IMG, "--charset", "braille", "--width", "10"])
        assert result.exit_code == 0

    def test_sextant_charset(self):
        result = runner.invoke(app, ["convert", self.IMG, "--charset", "sextant", "--width", "10"])
        assert result.exit_code == 0

    def test_emoji_charset(self):
        result = runner.invoke(app, ["convert", self.IMG, "--charset", "emoji", "--width", "10"])
        assert result.exit_code == 0

    def test_invert_flag(self):
        result = runner.invoke(app, ["convert", self.IMG, "--width", "10", "--invert"])
        assert result.exit_code == 0

    def test_dither_option(self):
        result = runner.invoke(
            app, ["convert", self.IMG, "--charset", "block", "--dither", "ordered", "--width", "10"]
        )
        assert result.exit_code == 0

    def test_output_to_file(self, tmp_path):
        out = tmp_path / "out.txt"
        result = runner.invoke(app, ["convert", self.IMG, "--width", "10", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert len(out.read_text()) > 0

    def test_height_option(self):
        result = runner.invoke(app, ["convert", self.IMG, "--width", "10", "--height", "3"])
        assert result.exit_code == 0
        lines = [line for line in result.output.split("\n") if line]
        assert len(lines) == 3

    def test_bg_option_light(self):
        result = runner.invoke(app, ["convert", self.IMG, "--width", "10", "--bg", "light"])
        assert result.exit_code == 0

    def test_ansi_color_non_tty_fallback(self):
        # CliRunner uses non-TTY; ansi should fall back to mono (no crash)
        result = runner.invoke(app, ["convert", self.IMG, "--color", "ansi", "--width", "10"])
        assert result.exit_code == 0

    def test_missing_image_exits_nonzero(self):
        result = runner.invoke(app, ["convert", "/nonexistent/image.png", "--width", "10"])
        assert result.exit_code != 0

    def test_auto_width_uses_terminal_default(self):
        with patch("shutil.get_terminal_size") as mock_ts:
            import os

            mock_ts.return_value = os.terminal_size((40, 24))
            result = runner.invoke(app, ["convert", self.IMG])
            assert result.exit_code == 0
