"""Image-to-text conversion logic."""

from __future__ import annotations

from pathlib import Path

from imgtxt import utils

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

VALID_CHARSETS = {"ascii", "unicode", "braille", "block", "sextant", "emoji"}
VALID_COLORS = {"mono", "ansi"}
VALID_BG = {"dark", "light"}
VALID_DITHER = {"none", "floyd-steinberg", "ordered"}


def convert(
    image_path: Path,
    *,
    charset: str = "ascii",
    color: str = "mono",
    bg: str = "dark",
    dither: str = "none",
    width: int | None = None,
    height: int | None = None,
    invert: bool = False,
) -> str:
    """Convert an image file to an ASCII art-style text string.

    Args:
        image_path: Path to the source image.
        charset: Character set to use for rendering.
        color: Color mode ('mono' or 'ansi').
        bg: Terminal background preset for ANSI palette ('dark' or 'light').
        dither: Dithering algorithm for thresholded charsets.
        width: Output width in terminal columns. Auto-detected if None.
        height: Output height in terminal rows. Derived from aspect ratio if None.
        invert: Invert light/dark threshold.

    Returns:
        The rendered text representation of the image.
    """
    if charset not in VALID_CHARSETS:
        raise ValueError(f"Invalid charset {charset!r}. Choose from {VALID_CHARSETS}")
    if color not in VALID_COLORS:
        raise ValueError(f"Invalid color {color!r}. Choose from {VALID_COLORS}")
    if bg not in VALID_BG:
        raise ValueError(f"Invalid bg {bg!r}. Choose from {VALID_BG}")
    if dither not in VALID_DITHER:
        raise ValueError(f"Invalid dither {dither!r}. Choose from {VALID_DITHER}")

    out_width = utils.get_output_width(width)
    img = utils.load_image(image_path)
    sample_w, sample_h = utils.compute_sample_size(out_width, height, charset, img.size)
    img_resized = utils.resize_image(img, sample_w, sample_h, color)

    render_fn = CHARSET_MAP[charset]
    return render_fn(
        img_resized, color=color, bg=bg, dither=dither, invert=invert, out_width=out_width
    )


# ---------------------------------------------------------------------------
# Charset dispatch map (populated after function definitions)
# ---------------------------------------------------------------------------

CHARSET_MAP: dict = {}  # filled at module bottom
