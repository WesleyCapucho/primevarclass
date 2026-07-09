"""Assemble the six confirmed-pathogenic PyMOL panels into one marketing-quality
figure: 'O algoritmo capturou mutações patogênicas reais'. Each tile carries a
large variant name, its domain, and two badges — the real ClinVar verdict and the
PrimeVarClass call — so a judge sees, at a glance, that every hit is real.

Run: python scratch/compose_detected_panel.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = "scratch/pymol"
OUTS = ["docs/galeria_resultados/figuras", "docs/suplementar/figuras",
        "docs/manuscrito/figuras"]
RAMP = [(0.10, 0.13, 0.38), (0.74, 0.15, 0.42), (1.00, 0.80, 0.22)]

TILES = [
    dict(name="C39G", title="BRCA1  p.Cys39Gly", dom="RING — sítio de zinco",
         clin="Patogênica / Provavelmente patogênica", prob="99,7%"),
    dict(name="C64G", title="BRCA1  p.Cys64Gly", dom="RING — sítio de zinco",
         clin="Patogênica", prob="99,7%"),
    dict(name="C61Y", title="BRCA1  p.Cys61Tyr", dom="RING — sítio de zinco",
         clin="Patogênica", prob="99,7%"),
    dict(name="M1689R", title="BRCA1  p.Met1689Arg", dom="BRCT — leitura de dano ao DNA",
         clin="Patogênica / Provavelmente patogênica", prob="97,9%"),
    dict(name="L1705P", title="BRCA1  p.Leu1705Pro", dom="BRCT — leitura de dano ao DNA",
         clin="Patogênica / Provavelmente patogênica", prob="96,7%"),
    dict(name="W1837C", title="BRCA1  p.Trp1837Cys", dom="BRCT — leitura de dano ao DNA",
         clin="Patogênica / Provavelmente patogênica", prob="96,3%"),
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


def pill(draw, x, y, text, fnt, fg, bg, dot=None):
    pad_x, pad_y = int(fnt.size * 0.7), int(fnt.size * 0.42)
    tw = draw.textlength(text, font=fnt)
    dw = int(fnt.size * 1.35) if dot else 0
    w = int(tw) + dw + pad_x * 2
    h = fnt.size + pad_y * 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    tx = x + pad_x
    if dot:
        cy = y + h // 2
        r = int(fnt.size * 0.32)
        draw.ellipse([tx, cy - r, tx + 2 * r, cy + r], fill=dot)
        tx += dw
    draw.text((tx, y + pad_y), text, font=fnt, fill=fg)
    return w, h


def make_tile(t, tw, strip):
    """One tile: render over gradient + a label strip with name, domain, badges.

    Strip layout is budgeted in explicit pixels so no badge is ever clipped, and
    the badge font is sized so even the longest verdict fits inside the tile.
    """
    fg = Image.open(os.path.join(SRC, f"detect_{t['name']}.png")).convert("RGBA")
    fg = fg.resize((tw, tw), Image.LANCZOS)
    tile = radial_bg(tw, tw + strip)
    tile.alpha_composite(fg)
    d = ImageDraw.Draw(tile)
    x = int(tw * 0.05)

    # variant name (top-left of the render, on the dark sky)
    d.text((x, int(tw * 0.045)), t["title"], font=font(int(tw * 0.062)),
           fill=(248, 249, 252))
    d.text((x + 2, int(tw * 0.045) + int(tw * 0.072)), t["dom"],
           font=font(int(tw * 0.036), bold=False), fill=(150, 200, 255))

    # label strip (two stacked badges) — explicit pixel budget
    fb = font(int(tw * 0.039), bold=True)          # ~46px: longest verdict still fits
    fs = font(int(tw * 0.030), bold=False)
    y = tw + int(strip * 0.05)
    d.text((x, y), "Verdade (ClinVar)", font=fs, fill=(150, 158, 176))
    _, h1 = pill(d, x, y + int(fs.size * 1.15), t["clin"], fb,
                 (10, 28, 15), (86, 200, 120), dot=(16, 38, 20))
    y = y + int(fs.size * 1.15) + h1 + int(strip * 0.055)
    d.text((x, y), "PrimeVarClass detectou", font=fs, fill=(150, 158, 176))
    pill(d, x, y + int(fs.size * 1.15), f"{t['prob']} patogênica", fb,
         (34, 22, 3), (240, 196, 74), dot=(58, 38, 5))
    return tile.convert("RGB")


def legend(draw, x, y, w, h):
    for i in range(w):
        draw.line([(x + i, y), (x + i, y + h)], fill=ramp_rgb(i / w))
    draw.rectangle([x, y, x + w, y + h], outline=(230, 232, 238), width=2)
    fs = font(int(h * 0.78), bold=False)
    draw.text((x, y - int(h * 1.5)), "Intensidade de detecção por resíduo",
              font=font(int(h * 0.78)), fill=(235, 237, 242))
    draw.text((x, y + h + int(h * 0.3)), "tolerante", font=fs, fill=(150, 160, 190))
    r = draw.textlength("patogênica", font=fs)
    draw.text((x + w - r, y + h + int(h * 0.3)), "patogênica", font=fs, fill=(240, 205, 110))


def build():
    tw, strip, gap = 1180, 400, 28
    cols, rows = 3, 2
    band = 380                                   # top title band
    W = cols * tw + (cols + 1) * gap
    H = band + rows * (tw + strip) + (rows + 1) * gap

    canvas = radial_bg(W, H, cy=0.30).convert("RGB")
    d = ImageDraw.Draw(canvas)
    d.text((gap + int(W * 0.008), int(band * 0.17)),
           "O algoritmo capturou mutações patogênicas reais",
           font=font(int(W * 0.030)), fill=(248, 249, 252))
    d.text((gap + int(W * 0.009), int(band * 0.17) + int(W * 0.036)),
           "Seis variantes de BRCA1 confirmadas no ClinVar — todas detectadas pelo "
           "PrimeVarClass com alta confiança",
           font=font(int(W * 0.0175), bold=False), fill=(214, 182, 96))
    lw, lh = int(W * 0.24), int(band * 0.052)
    legend(d, W - lw - gap - int(W * 0.012), int(band * 0.52), lw, lh)

    for i, t in enumerate(TILES):
        r, c = divmod(i, cols)
        x = gap + c * (tw + gap)
        y = band + gap + r * (tw + strip + gap)
        canvas.paste(make_tile(t, tw, strip), (x, y))

    for out in OUTS:
        os.makedirs(out, exist_ok=True)
        canvas.save(os.path.join(out, "fig_detected_panel.png"), quality=95)
    print("saved fig_detected_panel.png", canvas.size)


if __name__ == "__main__":
    build()
