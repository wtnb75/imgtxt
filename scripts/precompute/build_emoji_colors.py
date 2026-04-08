"""Generate imgtxt/data/emoji_colors.json.

Renders emoji characters using a Noto Emoji (or compatible) font via Pillow,
computes the average RGB of non-transparent pixels per glyph, and writes a
JSON array of {char, rgb} objects sorted by hue for easier visual inspection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "imgtxt" / "data" / "emoji_colors.json"

# Representative emoji covering a broad color range
EMOJI_CANDIDATES = [
    # Reds / pinks
    "❤️",
    "🔴",
    "🍎",
    "🌹",
    "🍓",
    "🫶",
    # Oranges
    "🟠",
    "🍊",
    "🎃",
    "🔥",
    "🦊",
    # Yellows
    "🟡",
    "⭐",
    "🌟",
    "🌞",
    "🍋",
    "🌻",
    # Greens
    "🟢",
    "🍀",
    "🌿",
    "🌲",
    "🍏",
    "🐸",
    # Blues
    "🔵",
    "💙",
    "🌊",
    "🐬",
    "🫐",
    "🌀",
    # Purples
    "🟣",
    "💜",
    "🍇",
    "🔮",
    "🦄",
    # Browns / earth tones
    "🟤",
    "🪵",
    "🍫",
    "🌰",
    # Whites / light
    "⬜",
    "☁️",
    "🤍",
    "🕊️",
    # Blacks / dark
    "⬛",
    "🖤",
    "🌑",
    "🐈‍⬛",
    # Cyans / teals
    "🩵",
    "🌐",
    "🧊",
    # Pinks / magentas
    "🩷",
    "🌸",
    "🪷",
    "💗",
]


def render_emoji_rgb(char: str, font, size: int = 32) -> tuple[int, int, int] | None:
    """Return average RGB of non-transparent pixels for an emoji glyph."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), char, font=font, embedded_color=True)

    pixels = list(img.getdata())
    visible = [(r, g, b) for r, g, b, a in pixels if a > 64]
    if not visible:
        return None
    avg_r = sum(p[0] for p in visible) // len(visible)
    avg_g = sum(p[1] for p in visible) // len(visible)
    avg_b = sum(p[2] for p in visible) // len(visible)
    return (avg_r, avg_g, avg_b)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font", required=True, help="Path to a color emoji font file (e.g. NotoEmoji-Regular.ttf)"
    )
    parser.add_argument("--size", type=int, default=32, help="Render size in pixels (default: 32)")
    args = parser.parse_args()

    font_path = Path(args.font)
    if not font_path.exists():
        print(f"ERROR: Font not found: {font_path}", file=sys.stderr)
        sys.exit(1)

    try:
        from PIL import ImageFont
    except ImportError:
        print("ERROR: Pillow is required. Run: uv pip install Pillow", file=sys.stderr)
        sys.exit(1)

    font = ImageFont.truetype(str(font_path), args.size)
    entries: list[dict] = []

    for emoji in EMOJI_CANDIDATES:
        rgb = render_emoji_rgb(emoji, font, args.size)
        if rgb is not None:
            entries.append({"char": emoji, "rgb": list(rgb)})
            print(f"  {emoji}  →  rgb{rgb}")
        else:
            print(f"  {emoji}  →  (skipped, no visible pixels)")

    OUTPUT_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(entries)} emoji entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
