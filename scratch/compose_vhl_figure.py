"""Compose the final VHL supplement figure: the ray-traced PyMOL detection map
(scratch/pymol/vhl_detection.png, produced by scratch/pymol_vhl_detection.py) with
a title, subtitle and a blue->gold colour-bar legend. Keeps PyMOL's resolution
(PIL paste, no resampling).

Run: python scratch/compose_vhl_figure.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = "scratch/pymol/vhl_detection.png"
OUT = "docs/suplementar/figuras/fig_vhl_detection.png"
RAMP = [(0.09, 0.12, 0.36), (0.74, 0.15, 0.42), (1.00, 0.80, 0.22)]


def font(sz, bold=True):
    for c in (("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
              "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(c):
            return ImageFont.truetype(c, sz)
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(255 * (a[i] + (b[i] - a[i]) * t)) for i in range(3))


im = Image.open(SRC).convert("RGB")
arr = np.asarray(im); mask = (arr < 245).any(2); ys, xs = np.where(mask)
pad = 40
im = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad),
              min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))
W = im.width; TOP = int(W * 0.115); BOT = int(W * 0.085)
canvas = Image.new("RGB", (W, TOP + im.height + BOT), "white"); canvas.paste(im, (0, TOP))
d = ImageDraw.Draw(canvas)
d.text((int(W * 0.03), int(TOP * 0.14)), "VHL (von Hippel-Lindau) — mapa de detecção do PrimeVarClass",
       font=font(int(W * 0.0255)), fill=(18, 32, 58))
y = int(TOP * 0.14) + int(W * 0.031)
d.text((int(W * 0.03), y), "sinal ESM-2 por resíduo na estrutura cristalográfica (PDB 1LM8) — AUC 0,966 (CV bloqueada, ClinVar real).",
       font=font(int(W * 0.0150), bold=False), fill=(122, 90, 0))
d.text((int(W * 0.03), y + int(W * 0.021)), "Sticks = resíduos com variante patogênica real; concentram-se nas zonas douradas (detectadas).",
       font=font(int(W * 0.0150), bold=False), fill=(122, 90, 0))
bx0 = int(W * 0.30); bx1 = int(W * 0.70); by0 = TOP + im.height + int(BOT * 0.24); bh = int(BOT * 0.28)
for i in range(bx1 - bx0):
    t = i / (bx1 - bx0)
    d.line([(bx0 + i, by0), (bx0 + i, by0 + bh)], fill=lerp(RAMP[0], RAMP[1], t * 2) if t < 0.5 else lerp(RAMP[1], RAMP[2], (t - 0.5) * 2))
d.rectangle([bx0, by0, bx1, by0 + bh], outline=(120, 120, 120))
fs = font(int(W * 0.016), bold=False)
d.text((bx0, by0 + bh + int(BOT * 0.05)), "tolerante", font=fs, fill=(60, 60, 60))
r = d.textlength("detectado", font=fs)
d.text((bx1 - r, by0 + bh + int(BOT * 0.05)), "detectado", font=fs, fill=(150, 110, 0))
canvas.save(OUT, quality=95)
print(">> wrote", OUT, canvas.size)
