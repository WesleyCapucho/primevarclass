"""Compose the two domain-surface renders (BRCA1 BRCT + BRCA2 DBD), coloured by
detection intensity, into one figure: 'Paisagem de detecção na superfície dos
domínios'. Large title, per-panel captions and a shared colour legend.

Run: python scratch/compose_domain_surface.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = "scratch/pymol"
OUTS = ["docs/galeria_resultados/figuras", "docs/suplementar/figuras",
        "docs/manuscrito/figuras"]
RAMP = [(0.10, 0.13, 0.38), (0.74, 0.15, 0.42), (1.00, 0.80, 0.22)]

PANELS = [
    dict(img="surf_brct.png", tag="BRCA1 · domínio BRCT (1JNX)",
         sub="Superfície que 'lê' o dano ao DNA —\nzonas douradas concentram as detecções"),
    dict(img="surf_dbd.png", tag="BRCA2 · domínio DBD (1MJE)",
         sub="Superfície que liga DNA de fita simples —\nmesmas zonas de detecção mapeadas"),
]


def font(sz, bold=True):
    for c in (("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
              "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(c):
            return ImageFont.truetype(c, sz)
    return ImageFont.load_default()


def radial_bg(w, h, cx=0.5, cy=0.42):
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.clip(np.sqrt(((xx - w * cx) / (w * .62)) ** 2 + ((yy - h * cy) / (h * .62)) ** 2), 0, 1)
    t = (r ** 1.35)[..., None]
    col = (np.array([20, 26, 54]) * (1 - t) + np.array([3, 4, 10]) * t).astype(np.uint8)
    return Image.fromarray(col, "RGB").convert("RGBA")


def ramp_rgb(x):
    if x < 0.5:
        a, b, f = RAMP[0], RAMP[1], x / 0.5
    else:
        a, b, f = RAMP[1], RAMP[2], (x - 0.5) / 0.5
    return tuple(int(255 * (a[i] * (1 - f) + b[i] * f)) for i in range(3))


def legend(draw, x, y, w, h, big):
    for i in range(w):
        draw.line([(x + i, y), (x + i, y + h)], fill=ramp_rgb(i / w))
    draw.rectangle([x, y, x + w, y + h], outline=(230, 232, 238), width=3)
    ft = font(int(big * 1.05)); fl = font(int(big), bold=False)
    draw.text((x, y - int(big * 1.75)), "Intensidade de detecção por resíduo",
              font=ft, fill=(236, 238, 244))
    draw.text((x, y + h + int(big * 0.35)), "tolerante", font=fl, fill=(178, 188, 212))
    r = draw.textlength("detectada (patogênica)", font=fl)
    draw.text((x + w - r, y + h + int(big * 0.35)), "detectada (patogênica)",
              font=fl, fill=(242, 208, 120))


def make_panel(p, w):
    fg = Image.open(os.path.join(SRC, p["img"])).convert("RGBA").resize((w, w), Image.LANCZOS)
    tile = radial_bg(w, w)
    tile.alpha_composite(fg)
    d = ImageDraw.Draw(tile)
    d.text((int(w * 0.04), int(w * 0.045)), p["tag"], font=font(int(w * 0.052)),
           fill=(248, 249, 252))
    d.multiline_text((int(w * 0.041), int(w * 0.045) + int(w * 0.066)), p["sub"],
                     font=font(int(w * 0.031), bold=False), fill=(165, 205, 255),
                     spacing=int(w * 0.010))
    return tile.convert("RGB")


def build():
    pw, gap, band = 1500, 30, 340
    W = 2 * pw + 3 * gap
    H = band + pw + 2 * gap + int(band * 0.98)
    canvas = radial_bg(W, H, cy=0.32).convert("RGB")
    d = ImageDraw.Draw(canvas)
    d.text((gap + int(W * 0.006), int(band * 0.20)),
           "Paisagem de detecção na superfície dos domínios",
           font=font(int(W * 0.030)), fill=(248, 249, 252))
    d.text((gap + int(W * 0.007), int(band * 0.20) + int(W * 0.037)),
           "Onde o PrimeVarClass 'enxerga' risco na superfície das proteínas — mesma "
           "assinatura estrutural em BRCA1 e BRCA2",
           font=font(int(W * 0.017), bold=False), fill=(214, 182, 96))

    for i, p in enumerate(PANELS):
        x = gap + i * (pw + gap)
        canvas.paste(make_panel(p, pw), (x, band))

    lw, lh = int(W * 0.42), int(band * 0.085)
    legend(d, (W - lw) // 2, band + pw + gap + int(band * 0.38), lw, lh, int(W * 0.0155))
    for out in OUTS:
        os.makedirs(out, exist_ok=True)
        canvas.save(os.path.join(out, "fig_surface_landscape.png"), quality=95)
    print("saved fig_surface_landscape.png", canvas.size)


if __name__ == "__main__":
    build()
