"""Generate the application icon assets from ``assets/logo.png``.

The logo is a wide canvas with the actual mark centered on a transparent
background, so the mark is cropped to its alpha bounding box, padded a little
and resized to a square canvas.  Both the PNG used for ``iconphoto()`` and the
multi-resolution ``.ico`` used by Windows are written here.

Run after changing the logo::

    python scripts/generate_icons.py
"""

from __future__ import annotations

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "assets", "logo.png")
ICON_PNG = os.path.join(ROOT, "assets", "icon.png")
ICON_ICO = os.path.join(ROOT, "assets", "icon.ico")

CANVAS = 256
MARGIN = 0.04
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def build_icon(size: int = CANVAS, margin: float = MARGIN) -> Image.Image:
    """Return a square icon built from the logo mark."""
    with Image.open(SOURCE) as raw:
        image = raw.convert("RGBA")
    bbox = image.getchannel("A").getbbox() or (0, 0, image.width, image.height)
    image = image.crop(bbox)
    side = max(image.size)
    side += 2 * int(round(side * margin))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    icon = build_icon()
    icon.save(ICON_PNG)
    icon.save(ICON_ICO, format="ICO", sizes=[(size, size) for size in ICO_SIZES])
    print(f"wrote {ICON_PNG}")
    print(f"wrote {ICON_ICO}")


if __name__ == "__main__":
    main()
