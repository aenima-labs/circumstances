# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==11.1.0", "fonttools[woff]==4.55.3"]
# ///
# ruff: noqa: E501  (inline SVG markup reads better unwrapped)
"""Render the README banners: .github/assets/banner-{dark,light}.png.

    uv run site/banner.py

Shapes are drawn by rsvg-convert (brew install librsvg) from SVG written here;
text is drawn with the site's own woff2 fonts, because rsvg-convert on macOS
ignores fontconfig. GitHub shows the variant that matches the reader's theme.
"""

import io
import subprocess
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "static" / "fonts"
OUT = HERE.parent / ".github" / "assets"
W, H = 1600, 520

THEMES = {
    "dark": {
        "bg": "#11111F",
        "dot": "#F5F3EF",
        "dot_opacity": 0.07,
        "glow": "#6B8F8E",
        "glow_opacity": 0.38,
        "warm_opacity": 0.22,
        "ink": (245, 243, 239),
        "accent": (184, 212, 204),
        "muted": (245, 243, 239, 150),
        "card_stroke": "#F5F3EF",
        "card_stroke_opacity": 0.12,
    },
    "light": {
        "bg": "#F5F3EF",
        "dot": "#11111F",
        "dot_opacity": 0.08,
        "glow": "#B8D4CC",
        "glow_opacity": 0.75,
        "warm_opacity": 0.22,
        "ink": (17, 17, 31),
        "accent": (69, 101, 100),
        "muted": (17, 17, 31, 160),
        "card_stroke": "#11111F",
        "card_stroke_opacity": 0.0,
    },
}

PASS, FAIL = "#6CC7A0", "#E58C7A"
CARD = (1036, 70, 484, 380)  # x, y, width, height
ROWS = [  # (offset from card top, role, text, verdict)
    (84, "user", "Which party did Mira vote for?", None),
    (130, "agent", "Nothing I can see says how", None),
    (160, "", "Mira voted, so I won't guess.", None),
    (218, "smoke", "no party named", "pass"),
    (264, "semantic", "abstains when silent", "pass"),
]


def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    ttf = TTFont(FONTS / name)
    ttf.flavor = None
    buffer = io.BytesIO()
    ttf.save(buffer)
    buffer.seek(0)
    loaded = ImageFont.truetype(buffer, size)
    if weight is not None:
        axes = loaded.get_variation_axes()
        loaded.set_variation_by_axes(
            [weight if axis["name"] in {b"Weight", "Weight"} else axis["default"] for axis in axes]
        )
    return loaded


def background(t: dict) -> str:
    x, y, w, h = CARD
    mark_fill = "#F5F3EF" if t["bg"] == "#11111F" else "#11111F"
    rows = []
    for offset, _, _, verdict in ROWS:
        if verdict:
            ry = y + offset + 12
            rows.append(
                f'<rect x="{x + w - 92}" y="{ry - 15}" width="64" height="26" rx="13"'
                f' fill="{PASS}" fill-opacity=".16"/>'
            )
    squares = "".join(
        f'<rect x="{x + 28 + i * 24}" y="{y + h - 50}" width="16" height="16" rx="4"'
        f' fill="{PASS}"/>'
        for i in range(3)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
  <defs>
    <radialGradient id="g1" cx="0.82" cy="0.2" r="0.6"><stop offset="0" stop-color="{t["glow"]}"
      stop-opacity="{t["glow_opacity"]}"/><stop offset="1" stop-color="{t["glow"]}" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx="0.02" cy="1" r="0.5"><stop offset="0" stop-color="#C9956B"
      stop-opacity="{t["warm_opacity"]}"/><stop offset="1" stop-color="#C9956B" stop-opacity="0"/></radialGradient>
    <pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1.1"
      fill="{t["dot"]}" fill-opacity="{t["dot_opacity"]}"/></pattern>
  </defs>
  <rect width="{W}" height="{H}" fill="{t["bg"]}"/>
  <rect width="{W}" height="{H}" fill="url(#dots)"/>
  <rect width="{W}" height="{H}" fill="url(#g1)"/>
  <rect width="{W}" height="{H}" fill="url(#g2)"/>
  <g transform="translate(80 64) scale(1.75)">
    <path d="M26.34 19.76 A11 11 0 1 1 23.07 7.57" fill="none" stroke="{mark_fill}" stroke-width="2.4"
      stroke-linecap="round"/>
    <circle cx="17.91" cy="26.83" r="2.1" fill="{mark_fill}"/><circle cx="5" cy="16" r="2.1" fill="{mark_fill}"/>
    <circle cx="14.09" cy="5.17" r="2.1" fill="{mark_fill}"/><circle cx="26.62" cy="13.15" r="3" fill="#C9956B"/>
  </g>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="#1A1A2E" stroke="{t["card_stroke"]}"
    stroke-opacity="{t["card_stroke_opacity"]}" stroke-width="2"/>
  <line x1="{x}" y1="{y + 52}" x2="{x + w}" y2="{y + 52}" stroke="#F5F3EF" stroke-opacity=".08" stroke-width="2"/>
  <circle cx="{x + 30}" cy="{y + 26}" r="6" fill="#F5F3EF" fill-opacity=".16"/>
  <circle cx="{x + 50}" cy="{y + 26}" r="6" fill="#F5F3EF" fill-opacity=".16"/>
  <circle cx="{x + 70}" cy="{y + 26}" r="6" fill="#F5F3EF" fill-opacity=".16"/>
  {"".join(rows)}
  {squares}
</svg>"""


def render(name: str, t: dict) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "bg.svg", Path(tmp) / "bg.png"
        svg.write_text(background(t))
        subprocess.run(["rsvg-convert", str(svg), "-o", str(png)], check=True)
        image = Image.open(png).convert("RGBA")

    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    grotesk = "space-grotesk-normal-latin.woff2"
    sans = "dm-sans-normal-latin.woff2"
    mono_ish = font(sans, 21, 500)

    draw.text((150, 72), "Circumstances", font=font(grotesk, 40, 600), fill=t["ink"])
    draw.text((76, 168), "Test agents", font=font(grotesk, 116, 600), fill=t["ink"])
    draw.text(
        (80, 296),
        "under the circumstances.",
        font=font("playfair-display-italic-latin.woff2", 80),
        fill=t["accent"],
    )
    draw.text(
        (82, 436),
        "Open-source situational testing for whole agent systems",
        font=font(sans, 27, 400),
        fill=t["muted"],
    )

    x, y, w, h = CARD
    card_ink, card_muted = (245, 243, 239), (245, 243, 239, 120)
    draw.text((x + 96, y + 15), "results/7780ded3…/trials", font=font(sans, 19), fill=card_muted)
    for offset, role, text, verdict in ROWS:
        ry = y + offset
        draw.text((x + 28, ry), role, font=mono_ish, fill=(184, 212, 204))
        draw.text((x + 142, ry), text, font=font(sans, 21), fill=card_ink)
        if verdict:
            draw.text((x + w - 79, ry + 1), verdict, font=font(sans, 18, 600), fill=PASS)
    draw.text(
        (x + 110, y + h - 54),
        "pass^3 1.00 · sealed · verifiable",
        font=font(sans, 19),
        fill=card_muted,
    )

    image = Image.alpha_composite(image, overlay)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"banner-{name}.png"
    image.convert("RGB").save(target, optimize=True)
    print("wrote", target.relative_to(HERE.parent))


for theme_name, theme in THEMES.items():
    render(theme_name, theme)
