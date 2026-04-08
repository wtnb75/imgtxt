"""Image-to-text conversion logic."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from PIL import Image

from imgtxt import utils

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

VALID_CHARSETS = {"ascii", "unicode", "braille", "block", "sextant", "emoji"}
VALID_COLORS = {"mono", "ansi"}
VALID_BG = {"dark", "light"}
VALID_DITHER = {"none", "floyd-steinberg", "ordered"}

# Charsets that support dithering (thresholded charsets)
DITHERED_CHARSETS = {"block", "braille", "sextant"}


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

    # emoji always ignores color mode; others fall back to mono when not a TTY
    effective_color = color
    if charset == "emoji":
        effective_color = "mono"  # color layer irrelevant; emoji charset handles color itself
    elif color == "ansi" and not utils.is_tty():
        effective_color = "mono"

    out_width = utils.get_output_width(width)
    img = utils.load_image(image_path)
    sample_w, sample_h = utils.compute_sample_size(out_width, height, charset, img.size)

    # For emoji: always RGB; for ansi: RGB; for mono: grayscale
    if charset == "emoji" or effective_color == "ansi":
        img_resized = img.resize((sample_w, sample_h), Image.LANCZOS)
        if img_resized.mode != "RGB":
            img_resized = img_resized.convert("RGB")
    else:
        img_resized = img.resize((sample_w, sample_h), Image.LANCZOS).convert("L")

    render_fn = CHARSET_MAP[charset]
    return render_fn(
        img_resized,
        color=effective_color,
        bg=bg,
        dither=dither,
        invert=invert,
        out_width=out_width,
    )


# ---------------------------------------------------------------------------
# Dithering
# ---------------------------------------------------------------------------

# 4×4 Bayer matrix (range 1–254 to ensure pixel=0 → all dark, pixel=255 → all bright)
_BAYER_4x4 = [
    [1, 136, 34, 170],
    [204, 68, 238, 102],
    [51, 187, 17, 153],
    [254, 119, 221, 85],
]


def _dither_none(pixels: list[list[int]]) -> list[list[int]]:
    """Threshold: no dithering. Returns binary 0/1 array."""
    return [[1 if v > 127 else 0 for v in row] for row in pixels]


def _dither_floyd_steinberg(pixels: list[list[int]]) -> list[list[int]]:
    """Floyd-Steinberg error diffusion. Returns binary 0/1 array."""
    rows = len(pixels)
    cols = len(pixels[0]) if rows > 0 else 0
    buf = [list(row) for row in pixels]  # mutable copy
    result = [[0] * cols for _ in range(rows)]
    for y in range(rows):
        for x in range(cols):
            old = buf[y][x]
            new = 255 if old > 127 else 0
            result[y][x] = 1 if new == 255 else 0
            err = old - new
            if x + 1 < cols:
                buf[y][x + 1] = max(0, min(255, buf[y][x + 1] + err * 7 // 16))
            if y + 1 < rows:
                if x - 1 >= 0:
                    buf[y + 1][x - 1] = max(0, min(255, buf[y + 1][x - 1] + err * 3 // 16))
                buf[y + 1][x] = max(0, min(255, buf[y + 1][x] + err * 5 // 16))
                if x + 1 < cols:
                    buf[y + 1][x + 1] = max(0, min(255, buf[y + 1][x + 1] + err * 1 // 16))
    return result


def _dither_ordered(pixels: list[list[int]]) -> list[list[int]]:
    """Ordered (Bayer 4×4) dithering. Returns binary 0/1 array."""
    rows = len(pixels)
    cols = len(pixels[0]) if rows > 0 else 0
    result = [[0] * cols for _ in range(rows)]
    for y in range(rows):
        for x in range(cols):
            threshold = _BAYER_4x4[y % 4][x % 4]
            result[y][x] = 1 if pixels[y][x] > threshold else 0
    return result


DITHER_MAP = {
    "none": _dither_none,
    "floyd-steinberg": _dither_floyd_steinberg,
    "ordered": _dither_ordered,
}


# ---------------------------------------------------------------------------
# Helper: extract grayscale or RGB pixel grid from PIL image
# ---------------------------------------------------------------------------


def _gray_grid(img: Image.Image) -> list[list[int]]:
    """Return a 2D list of grayscale values (0–255) from a grayscale image."""
    w, h = img.size
    pix = img.load()
    return [[pix[x, y] for x in range(w)] for y in range(h)]  # type: ignore[index]


def _rgb_grid(img: Image.Image) -> list[list[tuple[int, int, int]]]:
    """Return a 2D list of (R, G, B) tuples from an RGB image."""
    w, h = img.size
    pix = img.load()
    return [[pix[x, y] for x in range(w)] for y in range(h)]  # type: ignore[index]


def _avg_rgb(cells: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not cells:
        return (0, 0, 0)
    r = sum(c[0] for c in cells) // len(cells)
    g = sum(c[1] for c in cells) // len(cells)
    b = sum(c[2] for c in cells) // len(cells)
    return (r, g, b)


# ---------------------------------------------------------------------------
# ASCII charset
# ---------------------------------------------------------------------------

# Density string: darkest (densest) → brightest (most sparse)
ASCII_DENSITY = "@%#*+=-:. "


def _render_ascii(img: Image.Image, *, invert: bool, color: str, bg: str, **_kw: object) -> str:
    """Render using printable ASCII chars mapped by brightness."""
    density = ASCII_DENSITY[::-1] if invert else ASCII_DENSITY
    n = len(density)

    if color == "ansi":
        palettes = utils.load_ansi_palettes()
        palette = palettes[bg]["colors"]
        exclude = palettes[bg]["exclude"]
        rgb_grid = _rgb_grid(img)
        lines = []
        for row in rgb_grid:
            line = []
            for r, g, b in row:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                idx = min(n - 1, gray * n // 256)
                char = density[idx]
                code = utils.nearest_ansi_color((r, g, b), palette, exclude)
                line.append(utils.ansi_fg(code) + char)
            lines.append("".join(line) + utils.ANSI_RESET)
        return "\n".join(lines)
    else:
        gray_grid = _gray_grid(img)
        lines = []
        for row in gray_grid:
            line = []
            for v in row:
                idx = min(n - 1, v * n // 256)
                line.append(density[idx])
            lines.append("".join(line))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Unicode charset
# ---------------------------------------------------------------------------

_unicode_brightness_cache: list[str] | None = None


def _get_unicode_brightness() -> list[str]:
    global _unicode_brightness_cache
    if _unicode_brightness_cache is None:
        _unicode_brightness_cache = utils.load_unicode_brightness()
    return _unicode_brightness_cache


def _render_unicode(img: Image.Image, *, invert: bool, color: str, bg: str, **_kw: object) -> str:
    """Render using the pre-computed Unicode brightness table."""
    table = _get_unicode_brightness()
    n = len(table)
    # table[0] = darkest, table[-1] = lightest
    if invert:
        table = list(reversed(table))

    if color == "ansi":
        palettes = utils.load_ansi_palettes()
        palette = palettes[bg]["colors"]
        exclude = palettes[bg]["exclude"]
        rgb_grid = _rgb_grid(img)
        lines = []
        for row in rgb_grid:
            line = []
            for r, g, b in row:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                idx = min(n - 1, gray * n // 256)
                char = table[idx]
                code = utils.nearest_ansi_color((r, g, b), palette, exclude)
                line.append(utils.ansi_fg(code) + char)
            lines.append("".join(line) + utils.ANSI_RESET)
        return "\n".join(lines)
    else:
        gray_grid = _gray_grid(img)
        lines = []
        for row in gray_grid:
            line = []
            for v in row:
                idx = min(n - 1, v * n // 256)
                line.append(table[idx])
            lines.append("".join(line))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Block charset (2×2 per cell)
# ---------------------------------------------------------------------------

# Pattern (UL, UR, LL, LR) -> Unicode character
# bit 3 = upper-left, bit 2 = upper-right, bit 1 = lower-left, bit 0 = lower-right
_BLOCK_TABLE = [
    " ",  # 0000
    "\u2597",  # 0001 ▗ lower-right
    "\u2596",  # 0010 ▖ lower-left
    "\u2584",  # 0011 ▄ lower half
    "\u259d",  # 0100 ▝ upper-right
    "\u2590",  # 0101 ▐ right half
    "\u259e",  # 0110 ▞ checker (upper-right + lower-left)
    "\u259f",  # 0111 ▟ three-quarters (missing upper-left)
    "\u2598",  # 1000 ▘ upper-left
    "\u259a",  # 1001 ▚ checker (upper-left + lower-right)
    "\u258c",  # 1010 ▌ left half
    "\u2599",  # 1011 ▙ three-quarters (missing upper-right)
    "\u2580",  # 1100 ▀ upper half
    "\u259c",  # 1101 ▜ three-quarters (missing lower-left)
    "\u259b",  # 1110 ▛ three-quarters (missing lower-right)
    "\u2588",  # 1111 █ full block
]


def _render_block(
    img: Image.Image, *, invert: bool, color: str, bg: str, dither: str, **_kw: object
) -> str:
    """Render using 2×2 block characters."""
    w, h = img.size
    char_cols = w // 2
    char_rows = h // 2

    if color == "ansi":
        palettes = utils.load_ansi_palettes()
        palette = palettes[bg]["colors"]
        exclude = palettes[bg]["exclude"]
        rgb_g = _rgb_grid(img)
        lines = []
        for cr in range(char_rows):
            line = []
            for cc in range(char_cols):
                px = cr * 2
                py = cc * 2
                # upper half = row px, lower half = row px+1
                upper = [rgb_g[px][py], rgb_g[px][py + 1]]
                lower = [rgb_g[px + 1][py], rgb_g[px + 1][py + 1]]
                upper_rgb = _avg_rgb(upper)
                lower_rgb = _avg_rgb(lower)
                fg_code = utils.nearest_ansi_color(upper_rgb, palette, exclude)
                bg_code = utils.nearest_ansi_color(lower_rgb, palette, exclude)
                if fg_code == bg_code:
                    line.append(utils.ansi_fg(fg_code) + "\u2588")
                else:
                    line.append(utils.ansi_fg(fg_code) + utils.ansi_bg(bg_code) + "\u2580")
            lines.append("".join(line) + utils.ANSI_RESET)
        return "\n".join(lines)
    else:
        gray_g = _gray_grid(img)
        dither_fn = DITHER_MAP[dither]
        binary = dither_fn(gray_g)
        # Invert: 1=bright, 0=dark. Normally 1=lit char.
        # With invert=True, swap 0 and 1 when building pattern.
        lines = []
        for cr in range(char_rows):
            line = []
            for cc in range(char_cols):
                px, py = cr * 2, cc * 2
                ul = binary[px][py]
                ur = binary[px][py + 1]
                ll = binary[px + 1][py]
                lr = binary[px + 1][py + 1]
                if invert:
                    ul, ur, ll, lr = 1 - ul, 1 - ur, 1 - ll, 1 - lr
                pattern = (ul << 3) | (ur << 2) | (ll << 1) | lr
                line.append(_BLOCK_TABLE[pattern])
            lines.append("".join(line))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Braille charset (2×4 per cell)
# ---------------------------------------------------------------------------

# Braille bit assignments per (col, row):
# col 0: row 0→bit0, row 1→bit1, row 2→bit2, row 3→bit6
# col 1: row 0→bit3, row 1→bit4, row 2→bit5, row 3→bit7
_BRAILLE_BITS = [
    [0, 1, 2, 6],  # col 0, rows 0-3
    [3, 4, 5, 7],  # col 1, rows 0-3
]


def _render_braille(img: Image.Image, *, invert: bool, dither: str, **_kw: object) -> str:
    """Render using 2×4 braille dot encoding."""
    w, h = img.size
    char_cols = w // 2
    char_rows = h // 4

    gray_g = _gray_grid(img)
    dither_fn = DITHER_MAP[dither]
    binary = dither_fn(gray_g)

    lines = []
    for cr in range(char_rows):
        line = []
        for cc in range(char_cols):
            bits = 0
            for col in range(2):
                for row in range(4):
                    py, px = cr * 4 + row, cc * 2 + col
                    val = binary[py][px]
                    # Default: dark pixel (val=0) = dot present; --invert reverses this.
                    if not invert:
                        val = 1 - val
                    if val:
                        bits |= 1 << _BRAILLE_BITS[col][row]
            line.append(chr(0x2800 + bits))
        lines.append("".join(line))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sextant charset (2×3 per cell) — Block Sextant U+1FB00–U+1FB3B
# ---------------------------------------------------------------------------


def _build_sextant_map() -> dict[int, str]:
    """Build mapping from 6-bit pattern to sextant character.

    Sextant characters are at U+1FB00–U+1FB3B. Unicode names follow the pattern
    "BLOCK SEXTANT-{digits}" where digits are the filled position numbers (1-6),
    e.g. "BLOCK SEXTANT-12" means positions 1 and 2 are filled.

    Bit encoding (matches SPEC position numbering):
      bit 0 = pos 1 (top-left)
      bit 1 = pos 2 (top-right)
      bit 2 = pos 3 (mid-left)
      bit 3 = pos 4 (mid-right)
      bit 4 = pos 5 (bot-left)
      bit 5 = pos 6 (bot-right)
    """
    smap: dict[int, str] = {}
    for cp in range(0x1FB00, 0x1FB3C):
        try:
            c = chr(cp)
            name = unicodedata.name(c, "")
        except (ValueError, TypeError):
            continue
        if not name.startswith("BLOCK SEXTANT-"):
            continue
        # Suffix is the concatenated position digits, e.g. "12" → positions {1, 2}
        suffix = name[len("BLOCK SEXTANT-") :]
        try:
            positions = {int(ch) for ch in suffix if ch.isdigit()}
        except ValueError:
            continue
        if not positions or not all(1 <= p <= 6 for p in positions):
            continue
        bits = 0
        for pos in positions:
            bits |= 1 << (pos - 1)
        smap[bits] = c
    return smap


_SEXTANT_MAP: dict[int, str] | None = None


def _get_sextant_map() -> dict[int, str]:
    global _SEXTANT_MAP
    if _SEXTANT_MAP is None:
        _SEXTANT_MAP = _build_sextant_map()
    return _SEXTANT_MAP


def _sextant_fallback(bits: int, smap: dict[int, str]) -> str:
    """Find the nearest sextant character for a missing pattern.

    Strategy: find the pattern with the same popcount first; if not found,
    try the closest Hamming distance.
    """
    best = " "
    best_dist = 999
    for pattern, char in smap.items():
        dist = bin(bits ^ pattern).count("1")
        if dist < best_dist:
            best_dist = dist
            best = char
    return best


def _render_sextant(img: Image.Image, *, invert: bool, dither: str, **_kw: object) -> str:
    """Render using 2×3 block sextant characters."""
    smap = _get_sextant_map()
    w, h = img.size
    char_cols = w // 2
    char_rows = h // 3

    gray_g = _gray_grid(img)
    dither_fn = DITHER_MAP[dither]
    binary = dither_fn(gray_g)

    lines = []
    for cr in range(char_rows):
        line = []
        for cc in range(char_cols):
            bits = 0
            # Positions: row 0 → bits 0,1; row 1 → bits 2,3; row 2 → bits 4,5
            for row in range(3):
                for col in range(2):
                    py, px = cr * 3 + row, cc * 2 + col
                    val = binary[py][px]
                    # Default: dark pixel (val=0) = dot present; --invert reverses this.
                    if not invert:
                        val = 1 - val
                    bit_idx = row * 2 + col
                    if val:
                        bits |= 1 << bit_idx
            if bits == 0:
                char = " "
            elif bits == 0b111111:
                char = "\u2588"  # full block
            elif bits in smap:
                char = smap[bits]
            else:
                char = _sextant_fallback(bits, smap)
            line.append(char)
        lines.append("".join(line))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Emoji charset (1×1, double-width, RGB matching)
# ---------------------------------------------------------------------------

_emoji_table_cache: list[tuple[str, tuple[int, int, int]]] | None = None


def _get_emoji_table() -> list[tuple[str, tuple[int, int, int]]]:
    global _emoji_table_cache
    if _emoji_table_cache is None:
        _emoji_table_cache = utils.load_emoji_colors()
    return _emoji_table_cache


def _render_emoji(img: Image.Image, *, out_width: int, **_kw: object) -> str:
    """Render using emoji characters matched by average RGB."""
    emoji_table = _get_emoji_table()
    rgb_g = _rgb_grid(img)
    lines = []
    for row in rgb_g:
        line = []
        for pixel in row:
            char = utils.nearest_emoji(pixel, emoji_table)
            line.append(char)
        lines.append("".join(line))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Charset dispatch map
# ---------------------------------------------------------------------------


def _dispatch_ascii(img: Image.Image, **kw: object) -> str:
    return _render_ascii(img, **kw)


def _dispatch_unicode(img: Image.Image, **kw: object) -> str:
    return _render_unicode(img, **kw)


def _dispatch_block(img: Image.Image, **kw: object) -> str:
    return _render_block(img, **kw)


def _dispatch_braille(img: Image.Image, **kw: object) -> str:
    return _render_braille(img, **kw)


def _dispatch_sextant(img: Image.Image, **kw: object) -> str:
    return _render_sextant(img, **kw)


def _dispatch_emoji(img: Image.Image, **kw: object) -> str:
    return _render_emoji(img, **kw)


CHARSET_MAP: dict = {
    "ascii": _dispatch_ascii,
    "unicode": _dispatch_unicode,
    "block": _dispatch_block,
    "braille": _dispatch_braille,
    "sextant": _dispatch_sextant,
    "emoji": _dispatch_emoji,
}
