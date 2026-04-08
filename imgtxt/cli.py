"""CLI entry point for imgtxt."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Convert images to ASCII art-style text.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """imgtxt — Convert images to ASCII art-style text."""


@app.command()
def convert(
    image_path: Annotated[Path, typer.Argument(help="Path to the input image.")],
    charset: Annotated[
        str,
        typer.Option(help="Character set: ascii / unicode / braille / block / sextant / emoji"),
    ] = "ascii",
    color: Annotated[str, typer.Option(help="Color mode: mono / ansi")] = "mono",
    bg: Annotated[
        str, typer.Option(help="Terminal background for ANSI palette: dark / light")
    ] = "dark",
    dither: Annotated[
        str,
        typer.Option(help="Dithering for thresholded charsets: none / floyd-steinberg / ordered"),
    ] = "none",
    width: Annotated[
        int | None, typer.Option(help="Output width in terminal columns (default: auto-detect)")
    ] = None,
    height: Annotated[
        int | None,
        typer.Option(help="Output height in terminal rows (default: auto from aspect ratio)"),
    ] = None,
    output: Annotated[Path | None, typer.Option(help="Output file path (default: stdout)")] = None,
    invert: Annotated[bool, typer.Option(help="Invert light/dark")] = False,
) -> None:
    """Convert an image to ASCII art-style text."""
    from imgtxt.converter import convert as _convert

    result = _convert(
        image_path=image_path,
        charset=charset,
        color=color,
        bg=bg,
        dither=dither,
        width=width,
        height=height,
        invert=invert,
    )

    if output is None:
        typer.echo(result, nl=False)
    else:
        output.write_text(result)


if __name__ == "__main__":
    app()
