# scripts/precompute/README.md
# Pre-computation scripts for imgtxt data files

## Prerequisites

Install font packages before running these scripts:

```bash
# Debian/Ubuntu
sudo apt-get install fonts-dejavu fonts-noto-mono fonts-firacode

# macOS (with Homebrew)
brew install font-dejavu font-noto-sans-mono font-fira-code
```

Additional Python deps (run in repo root):

```bash
uv pip install Pillow wcwidth fonttools
```

For `build_emoji_colors.py`, a Noto Emoji font file is required:

```bash
# Download Noto Emoji font
wget -O /tmp/NotoEmoji.ttf \
  "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoEmoji-Regular.ttf"
```

## Usage

```bash
# Generate imgtxt/data/unicode_brightness.txt
python scripts/precompute/build_unicode_brightness.py

# Generate imgtxt/data/emoji_colors.json
python scripts/precompute/build_emoji_colors.py --font /tmp/NotoEmoji.ttf
```

Both scripts write output to `imgtxt/data/` relative to the repository root.
Commit the resulting files.
