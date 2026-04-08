"""Unit tests for the CLI (imgtxt.cli)."""

from __future__ import annotations

from typer.testing import CliRunner

from imgtxt.cli import app

runner = CliRunner()


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
