# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==11.1.0", "fonttools[woff]==4.55.3"]
# ///
r"""Render static/og.png: background from og.svg (via rsvg-convert), text with the site's fonts.

    sed -E '/<text|<\/text>/d' site/og.svg > /tmp/og-bg.svg   # og.svg minus its text
    rsvg-convert -w 1200 -h 630 /tmp/og-bg.svg -o /tmp/og-bg.png
    uv run site/og.py /tmp/og-bg.png

rsvg-convert on macOS ignores fontconfig, so the text is drawn here with the
site's own woff2 fonts instead of whatever the system substitutes.
"""

import io
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "static" / "fonts"


def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    ttf = TTFont(FONTS / name)
    ttf.flavor = None
    buffer = io.BytesIO()
    ttf.save(buffer)
    buffer.seek(0)
    loaded = ImageFont.truetype(buffer, size)
    if weight is not None:
        axes = loaded.get_variation_axes()
        values = [
            weight if axis["name"] in {b"Weight", "Weight"} else axis["default"] for axis in axes
        ]
        loaded.set_variation_by_axes(values)
    return loaded


image = Image.open(sys.argv[1]).convert("RGBA")
draw = ImageDraw.Draw(image)
paper, sage_light = (245, 243, 239), (184, 212, 204)
faint = (245, 243, 239, 158)

draw.text(
    (146, 82), "Circumstances", font=font("space-grotesk-normal-latin.woff2", 34, 600), fill=paper
)
draw.text(
    (76, 212), "Test agents", font=font("space-grotesk-normal-latin.woff2", 108, 600), fill=paper
)
draw.text(
    (78, 322),
    "under the circumstances.",
    font=font("playfair-display-italic-latin.woff2", 96),
    fill=sage_light,
)
overlay = Image.new("RGBA", image.size)
od = ImageDraw.Draw(overlay)
od.text(
    (144, 466),
    "pass^3 1.00 · sealed · verifiable",
    font=font("dm-sans-normal-latin.woff2", 19, 400),
    fill=(245, 243, 239, 140),
)
od.text(
    (80, 522),
    "Open-source situational testing for whole agent systems · by Ænima Labs",
    font=font("dm-sans-normal-latin.woff2", 24, 400),
    fill=faint,
)
image = Image.alpha_composite(image, overlay)
image.convert("RGB").save(HERE / "static" / "og.png", optimize=True)
print("wrote", HERE / "static" / "og.png")
