# imgtxt

[![CI](https://github.com/wtnb75/imgtxt/actions/workflows/ci.yml/badge.svg)](https://github.com/wtnb75/imgtxt/actions/workflows/ci.yml)

Turn any image into terminal text art. Pick your character set, tweak the width, pipe it wherever.

```
@@@@%%%%####****++++====----::::....
@@@@%%%%####****++++====----::::....
@@@@%%%%####****++++====----::::....
```

## Install

Requires Python 3 (latest stable release) and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/wtnb75/imgtxt
cd imgtxt
uv sync
```

## Usage

```sh
imgtxt convert photo.jpg
```

That's the basics — auto-detects terminal width and maps brightness to ASCII density.

### Options

```
imgtxt convert IMAGE_PATH
  --charset   ascii (default) / unicode / braille / block / sextant / emoji
  --color     mono (default) / ansi
  --bg        dark (default) / light   — terminal background hint for ANSI
  --dither    none (default) / floyd-steinberg / ordered
  --width     columns (default: terminal width)
  --height    rows (default: auto from aspect ratio)
  --invert    flip light/dark
  --output    write to file instead of stdout
```

## Examples

**Classic ASCII** — density-mapped, dark-to-light left-to-right:

```sh
imgtxt convert gradient.png --width 40
```
```
@@@@%%%%####****++++====----::::....    
@@@@%%%%####****++++====----::::....    
```

**Braille** — tight 2×4 dot grid, great for fine detail:

```sh
imgtxt convert photo.jpg --charset braille --width 80
```
```
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```

**Block elements** — crisp half-block shapes with smooth 2×2 cell sampling:

```sh
imgtxt convert photo.jpg --charset block --width 60
```
```
██  ██  ██  ██  ██  
  ██  ██  ██  ██  ██
```

**Sextant** — 2×3 sub-cell Unicode blocks (U+1FB00) for extra vertical resolution:

```sh
imgtxt convert photo.jpg --charset sextant --width 60
```

**Emoji** — nearest-color match from a curated emoji set:

```sh
imgtxt convert photo.jpg --charset emoji --width 40
```

**ANSI color** on a dark terminal:

```sh
imgtxt convert photo.jpg --charset block --color ansi --bg dark --width 80
```

**Ordered dithering** for a halftone look:

```sh
imgtxt convert photo.jpg --charset braille --dither ordered --width 80
```

**Save to file:**

```sh
imgtxt convert photo.jpg --charset unicode --width 120 --output art.txt
```

## Charsets at a glance

| Charset  | Cell size | Characters used                          | Good for              |
|----------|-----------|------------------------------------------|-----------------------|
| ascii    | 1×1       | ` .:-=+*#%@` density ramp                | Classic look          |
| unicode  | 1×1       | Extended block + math symbols            | Richer tonal range    |
| braille  | 2×4       | U+2800–U+28FF dot patterns               | Fine detail / photos  |
| block    | 2×2       | `█ ▀ ▄ ▌ ▐ ▖ ▗ ▘ ▝ ▙ ▛ ▜ ▟`            | Clean edges           |
| sextant  | 2×3       | U+1FB00–U+1FB3B sextant blocks           | Best vertical res     |
| emoji    | 1×1       | 🔴🟠🟡🟢🔵🟣⬛⬜ nearest-color match    | Colorful / fun        |

## Development

```sh
uv sync --all-extras

# run tests
uv run pytest tests/unit/           # unit tests + coverage
uv run pytest tests/functional/     # snapshot tests

# update snapshots after intentional output changes
uv run pytest tests/functional/ --update-snapshots

# lint / format
uv run ruff check .
uv run ruff format .
```

Coverage target: 80% (currently ~96%).

## License

[MIT](LICENSE)
