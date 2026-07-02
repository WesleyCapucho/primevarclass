"""Compose the protein 3D figure from official RCSB PDB cartoon renders
(real experimental structures). Replaces the Cα-trace version.

Images: RCSB Protein Data Bank (rcsb.org). Structures 1JM7, 1JNX, 1MJE.
Run: python scratch/build_structure_composite.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageChops

OUT = "primevarclass_manuscript_analysis/fig_protein_structures.png"
PANELS = [
    ("scratch/rcsb/1JM7.jpeg", "BRCA1 — domínio RING\n(PDB 1JM7: BRCA1 + BARD1; íons de zinco)"),
    ("scratch/rcsb/1JNX.jpeg", "BRCA1 — repetições BRCT\n(PDB 1JNX: domínio crítico C-terminal)"),
    ("scratch/rcsb/1MJE.jpeg", "BRCA2 — domínio de ligação ao DNA\n(PDB 1MJE: BRCA2 + DSS1 + ssDNA)"),
]


def trim(im):
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        pad = 8
        l, t, r, b = bbox
        im = im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))
    return im


fig, axes = plt.subplots(1, 3, figsize=(13, 4.9), dpi=200)
for ax, (path, title) in zip(axes, PANELS):
    ax.imshow(trim(Image.open(path)))
    ax.set_title(title, fontsize=8.5)
    ax.axis("off")
fig.text(0.5, 0.02, "Representação em cartoon de estruturas experimentais reais. Imagens: RCSB Protein Data Bank.",
         ha="center", fontsize=7.5, style="italic", color="#444444")
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig(OUT, bbox_inches="tight", facecolor="white")
plt.close()
print("wrote", OUT)
