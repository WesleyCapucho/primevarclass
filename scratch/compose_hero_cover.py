"""Compose the transparent PyMOL hero renders over a dramatic radial-gradient
background, with a LARGE, legible title and an explicit colour-ramp legend.

Run: python scratch/compose_hero_cover.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = "scratch/pymol"
OUT = "docs/suplementar/figuras"
os.makedirs(OUT, exist_ok=True)
RAMP = [(0.10, 0.13, 0.38), (0.74, 0.15, 0.42), (1.00, 0.80, 0.22)]  # indigo->magenta->gold


def font(sz, bold=True):
    for c in (("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
              "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(c):
            return ImageFont.truetype(c, sz)
    return ImageFont.load_default()


def radial_bg(w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.clip(np.sqrt(((xx - w * .5) / (w * .62)) ** 2 + ((yy - h * .42) / (h * .62)) ** 2), 0, 1)
    t = (r ** 1.35)[..., None]
    col = (np.array([20, 26, 54]) * (1 - t) + np.array([3, 4, 10]) * t).astype(np.uint8)
    return Image.fromarray(col, "RGB").convert("RGBA")


def ramp_rgb(x):  # x in [0,1] -> RGB tuple
    if x < 0.5:
        a, b, f = RAMP[0], RAMP[1], x / 0.5
    else:
        a, b, f = RAMP[1], RAMP[2], (x - 0.5) / 0.5
    return tuple(int(255 * (a[i] * (1 - f) + b[i] * f)) for i in range(3))


def legend(draw, x, y, w, h, title):
    for i in range(w):                       # gradient bar
        draw.line([(x + i, y), (x + i, y + h)], fill=ramp_rgb(i / w))
    draw.rectangle([x, y, x + w, y + h], outline=(230, 232, 238), width=2)
    fs = font(int(h * 0.82), bold=False)
    ft = font(int(h * 0.82))
    draw.text((x, y - int(h * 1.55)), title, font=ft, fill=(235, 237, 242))
    draw.text((x, y + h + int(h * 0.35)), "tolerante", font=fs, fill=(150, 160, 190))
    r = draw.textlength("detectada (patogênica)", font=fs)
    draw.text((x + w - r, y + h + int(h * 0.35)), "detectada (patogênica)", font=fs, fill=(240, 205, 110))


def compose(name, title, subtitle, out_name):
    fg = Image.open(os.path.join(SRC, name)).convert("RGBA")
    w, h = fg.size
    img = radial_bg(w, h)
    img.alpha_composite(fg)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # bottom vignette band so text is always legible
    band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for yy in range(int(h * 0.72), h):
        a = int(210 * (yy - h * 0.72) / (h * 0.28))
        bd.line([(0, yy), (w, yy)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), band).convert("RGB")
    draw = ImageDraw.Draw(img)

    # title + subtitle (large, bottom-left) — full width, no legend to collide with
    draw.text((int(w * 0.045), int(h * 0.845)), title, font=font(int(w * 0.036)), fill=(248, 249, 252))
    draw.text((int(w * 0.045), int(h * 0.912)), subtitle, font=font(int(w * 0.019), bold=False),
              fill=(214, 182, 96))
    # colour-ramp legend (top-right, in the empty sky) — never overlaps the title band
    lw, lh = int(w * 0.30), int(h * 0.026)
    legend(draw, w - lw - int(w * 0.045), int(h * 0.115), lw, lh,
           "Intensidade de detecção por resíduo")
    img.save(os.path.join(OUT, out_name), quality=95)
    print("saved", out_name, img.size)


compose("hero_ring.png", "PrimeVarClass",
        "Mutações patogênicas detectadas no sítio de zinco do domínio RING de BRCA1",
        "fig_hero_ring.png")
if os.path.exists(os.path.join(SRC, "hero_brct.png")):
    compose("hero_brct.png", "PrimeVarClass",
            "Mapa de vulnerabilidade das repetições BRCT de BRCA1",
            "fig_hero_brct.png")
