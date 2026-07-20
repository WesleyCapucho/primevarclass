"""Compose the two PyMOL renders (real experimental structures) into one
publication-quality 2-panel figure with panel titles, the model's ESM-2 score
for each variant, and a colour legend. Writes into the manuscript figure folder.

Run: python scratch/compose_variants_figure.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SRC = "scratch/pymol"
OUT = "docs/manuscrito/figuras/fig_variants_3d.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

imgA = mpimg.imread(os.path.join(SRC, "var_ring_c61.png"))
imgB = mpimg.imread(os.path.join(SRC, "var_brct_m1775.png"))

fig, axes = plt.subplots(1, 2, figsize=(12.2, 6.2), dpi=200)
fig.patch.set_facecolor("white")

panels = [
    (axes[0], imgA,
     "A   BRCA1 p.Cys61Gly — domínio RING",
     "Sítio de zinco estrutural (PDB 1JM7)   •   ESM-2 LLR = −10,9 (patogênico)"),
    (axes[1], imgB,
     "B   BRCA1 p.Met1775Arg — domínio BRCT",
     "Nativo (1JNX) sobreposto ao mutante (1N5O)   •   ESM-2 LLR = −12,0 (patogênico)"),
]
for ax, img, title, sub in panels:
    ax.imshow(img)
    ax.set_axis_off()
    ax.set_title(title, fontsize=12.5, fontweight="bold", color="#1a1a1a", pad=6, loc="left")
    ax.text(0.0, -0.035, sub, transform=ax.transAxes, fontsize=12,
            color="#333333", ha="left", va="top")

# shared colour legend along the bottom
legend_handles = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor="#6b7fd7",
           markersize=11, label="Íon Zn²⁺ estrutural"),
    Patch(facecolor="#2e8b2e", edgecolor="none", label="Resíduo nativo (Cys61 / Met1775)"),
    Patch(facecolor="#e23b28", edgecolor="none", label="Resíduo mutante / patogênico"),
    Patch(facecolor="#f0a020", edgecolor="none", label="Cisteínas coordenadoras vizinhas"),
    Line2D([0], [0], color="#888888", lw=1.6, ls=(0, (2, 2)),
           label="Coordenação tiol–Zn²⁺"),
]
fig.legend(handles=legend_handles, loc="lower center", ncol=5, frameon=False,
           fontsize=12, bbox_to_anchor=(0.5, -0.005), handletextpad=0.5,
           columnspacing=1.4)

fig.subplots_adjust(left=0.008, right=0.992, top=0.93, bottom=0.11, wspace=0.02)
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT)
