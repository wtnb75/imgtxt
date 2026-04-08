"""Generate imgtxt/data/unicode_brightness.txt.

Renders printable Unicode characters using common monospace fonts via Pillow,
computes pixel density (fraction of dark pixels) per glyph, averages across
fonts, filters to wcwidth==1, deduplicates near-identical entries, and writes
characters sorted from darkest to brightest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "imgtxt" / "data" / "unicode_brightness.txt"

# Font paths to try (first found on the system will be used)
FONT_CANDIDATES = [
    # DejaVu Sans Mono
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/DejaVu Sans Mono.ttf",
    # Noto Sans Mono
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf",
    # Fira Code
    "/usr/share/fonts/truetype/firacode/FiraCode-Regular.ttf",
    "/Library/Fonts/FiraCode-Regular.ttf",
    # Source Code Pro
    "/usr/share/fonts/truetype/scp/SourceCodePro-Regular.ttf",
]

FONT_SIZE = 16
DARK_THRESHOLD = 128  # pixels darker than this count as "ink"


def find_fonts() -> list[str]:
    return [p for p in FONT_CANDIDATES if Path(p).exists()]


def render_char_density(char: str, font) -> float:  # type: ignore[type-arg]
    """Return fraction of dark pixels when rendering char at FONT_SIZE."""
    from PIL import Image, ImageDraw

    img = Image.new("L", (FONT_SIZE, FONT_SIZE), color=255)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), char, font=font, fill=0)
    pixels = list(img.getdata())
    dark = sum(1 for p in pixels if p < DARK_THRESHOLD)
    return dark / len(pixels)


def build_table(font_paths: list[str], char_range: range) -> list[tuple[str, float]]:
    from PIL import ImageFont
    from wcwidth import wcwidth

    fonts = [ImageFont.truetype(p, FONT_SIZE) for p in font_paths]
    results: list[tuple[str, float]] = []

    for codepoint in char_range:
        char = chr(codepoint)
        # Skip non-single-width, control, surrogate, and unassigned-looking chars
        if wcwidth(char) != 1:
            continue
        try:
            densities = [render_char_density(char, f) for f in fonts]
        except Exception:
            continue
        avg = sum(densities) / len(densities)
        if avg > 0:  # skip invisible/blank characters
            results.append((char, avg))

    # Sort darkest first, deduplicate chars within 0.5% density bands
    results.sort(key=lambda x: x[1], reverse=True)
    deduped: list[tuple[str, float]] = []
    prev_density = -1.0
    for char, density in results:
        if abs(density - prev_density) > 0.005:
            deduped.append((char, density))
            prev_density = density

    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--range-start",
        type=lambda x: int(x, 0),
        default=0x0021,
        help="Start of Unicode codepoint range (default: 0x0021)",
    )
    parser.add_argument(
        "--range-end",
        type=lambda x: int(x, 0),
        default=0x2FFF,
        help="End of Unicode codepoint range (default: 0x2FFF)",
    )
    args = parser.parse_args()

    font_paths = find_fonts()
    if not font_paths:
        print(
            "ERROR: No supported monospace fonts found. See scripts/precompute/README.md",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Using {len(font_paths)} font(s): {font_paths}")
    print(f"Scanning U+{args.range_start:04X}–U+{args.range_end:04X} ...")

    table = build_table(font_paths, range(args.range_start, args.range_end + 1))
    chars = "".join(c for c, _ in table)

    OUTPUT_PATH.write_text(chars, encoding="utf-8")
    print(f"Wrote {len(chars)} characters to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
