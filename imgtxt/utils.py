"""Shared utilities: image I/O, sampling, ANSI helpers, data loaders, color matching."""

from __future__ import annotations

import json
import shutil
import sys
import tomllib
from importlib.resources import files
from pathlib import Path

from PIL import Image
from wcwidth import wcwidth

# ---------------------------------------------------------------------------
# Terminal width
# ---------------------------------------------------------------------------


def get_output_width(width: int | None) -> int:
    """Return the output width in terminal columns.

    Uses the provided value if given; otherwise auto-detects via
    shutil.get_terminal_size() with a fallback of 80 columns.
    """
    if width is not None:
        return width
    return shutil.get_terminal_size(fallback=(80, 24)).columns


# ---------------------------------------------------------------------------
# Image loading and resizing
# ---------------------------------------------------------------------------


def load_image(path: Path) -> Image.Image:
    """Open an image file and return a PIL Image in RGB mode."""
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def resize_image(img: Image.Image, sample_w: int, sample_h: int, color: str) -> Image.Image:
    """Resize image to (sample_w, sample_h) and convert color mode.

    For 'mono', converts to grayscale ('L').
    For 'ansi', keeps RGB.
    """
    resized = img.resize((sample_w, sample_h), Image.LANCZOS)
    if color == "mono":
        return resized.convert("L")
    return resized


def compute_sample_size(
    out_width: int,
    out_height: int | None,
    charset: str,
    original_size: tuple[int, int],
) -> tuple[int, int]:
    """Compute the pixel sample dimensions for the given charset and output size.

    The character aspect ratio is assumed to be 2:1 (height:width).
    Each charset multiplies the cell count by its sub-cell resolution.

    Args:
        out_width: Output width in terminal columns.
        out_height: Output height in terminal rows (None = auto from aspect ratio).
        charset: The charset identifier.
        original_size: (width, height) of the source image in pixels.

    Returns:
        (sample_w, sample_h) — the pixel dimensions to resize to.
    """
    orig_w, orig_h = original_size
    aspect = orig_h / orig_w  # height / width ratio of source image

    # Cell multipliers (pixels per character cell per axis)
    cell_w, cell_h = _cell_multipliers(charset)

    # For emoji, effective character columns = out_width // 2 (each emoji is 2 cols wide)
    if charset == "emoji":
        char_cols = max(1, out_width // 2)
    else:
        char_cols = out_width

    sample_w = char_cols * cell_w

    # emoji is a wide character (2 terminal columns), so its cell aspect ratio is ~1.0
    # (2 cols wide × ~2 rows tall ≈ square). Other charsets use 2.0 (1 col × 2 rows tall).
    char_aspect = 1.0 if charset == "emoji" else 2.0

    if out_height is not None:
        sample_h = out_height * cell_h
    else:
        # Derive row count from aspect ratio, accounting for character aspect ratio
        char_rows = max(1, round(char_cols * aspect / char_aspect))
        sample_h = char_rows * cell_h

    return (max(1, sample_w), max(1, sample_h))


def _cell_multipliers(charset: str) -> tuple[int, int]:
    """Return (cell_width_pixels, cell_height_pixels) for a charset."""
    return {
        "ascii": (1, 1),
        "unicode": (1, 1),
        "emoji": (1, 1),
        "block": (2, 2),
        "sextant": (2, 3),
        "braille": (2, 4),
    }[charset]


# ---------------------------------------------------------------------------
# Display width
# ---------------------------------------------------------------------------


def display_width(char: str) -> int:
    """Return the display width of a character in terminal columns."""
    w = wcwidth(char)
    return w if w > 0 else 1


# ---------------------------------------------------------------------------
# ANSI escape helpers
# ---------------------------------------------------------------------------


def ansi_fg(code: int) -> str:
    """Return ANSI SGR escape for foreground color (0–7: standard, 8–15: via bright)."""
    if code < 8:
        return f"\x1b[3{code}m"
    return f"\x1b[9{code - 8}m"


def ansi_bg(code: int) -> str:
    """Return ANSI SGR escape for background color (0–7: standard, 8–15: via bright)."""
    if code < 8:
        return f"\x1b[4{code}m"
    return f"\x1b[10{code - 8}m"


ANSI_RESET = "\x1b[0m"


def is_tty() -> bool:
    """Return True if stdout is connected to a terminal."""
    return sys.stdout.isatty()


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _data_path(filename: str) -> Path:
    """Return the path to a file inside imgtxt/data/."""
    return Path(str(files("imgtxt").joinpath("data") / filename))


def load_unicode_brightness() -> list[str]:
    """Load the pre-computed Unicode brightness table.

    Returns a list of characters sorted from darkest (densest) to brightest (most sparse).
    """
    path = _data_path("unicode_brightness.txt")
    return list(path.read_text(encoding="utf-8").strip())


def load_emoji_colors() -> list[tuple[str, tuple[int, int, int]]]:
    """Load the pre-computed emoji color table.

    Returns a list of (emoji_char, (R, G, B)) tuples.
    """
    path = _data_path("emoji_colors.json")
    data: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    return [(entry["char"], tuple(entry["rgb"])) for entry in data]  # type: ignore[misc]


def load_ansi_palettes() -> dict:
    """Load ANSI color palettes from ansi_palettes.toml."""
    path = _data_path("ansi_palettes.toml")
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Color matching
# ---------------------------------------------------------------------------


def nearest_ansi_color(
    rgb: tuple[int, int, int],
    palette: list[dict],
    exclude: list[int],
) -> int:
    """Return the ANSI color code nearest to the given RGB value.

    Args:
        rgb: Target (R, G, B) color.
        palette: List of {'code': int, 'rgb': [R, G, B]} dicts.
        exclude: Color codes to skip (e.g. black on dark bg).

    Returns:
        The ANSI color code (0–15) of the nearest palette entry.
    """
    r, g, b = rgb
    best_code = -1
    best_dist = float("inf")
    for entry in palette:
        code = entry["code"]
        if code in exclude:
            continue
        pr, pg, pb = entry["rgb"]
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_code = code
    return best_code


def nearest_emoji(
    rgb: tuple[int, int, int],
    emoji_table: list[tuple[str, tuple[int, int, int]]],
) -> str:
    """Return the emoji character whose representative color is nearest to rgb."""
    r, g, b = rgb
    best_char = emoji_table[0][0]
    best_dist = float("inf")
    for char, (er, eg, eb) in emoji_table:
        dist = (r - er) ** 2 + (g - eg) ** 2 + (b - eb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_char = char
    return best_char
