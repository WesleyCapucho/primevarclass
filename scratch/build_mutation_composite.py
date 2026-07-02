"""Compose the structural-consequence-of-mutation figure (2 panels)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageChops

OUT = "primevarclass_manuscript_analysis/fig_mutation_consequence.png"
PANELS = [
    ("scratch/pymol/ring_zinc.png",
     "(A) Sítio de zinco do domínio RING do BRCA1 (PDB 1JM7)\nCys61 e Cys64 (vermelho) coordenam o Zn²⁺ (roxo)"),
    ("scratch/pymol/brct_mut.png",
     "(B) Domínio BRCT com a variante patogênica\nBRCA1 p.Met1775Arg (resíduo 1775; PDB 1N5O)"),
]


def trim(im):
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        p = 10
        l, t, r, b = bbox
        im = im.crop((max(l - p, 0), max(t - p, 0), min(r + p, im.width), min(b + p, im.height)))
    return im


fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), dpi=200)
for ax, (path, title) in zip(axes, PANELS):
    ax.imshow(trim(Image.open(path)))
    ax.set_title(title, fontsize=9)
    ax.axis("off")
plt.tight_layout()
plt.savefig(OUT, bbox_inches="tight", facecolor="white")
plt.close()
print("wrote", OUT)
