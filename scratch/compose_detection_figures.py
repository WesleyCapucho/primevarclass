"""Compose the PyMOL detection renders into publication figures:

  docs/manuscrito/figuras/fig_detection_landscape.png   (article Fig. — RING+BRCT)
  docs/manuscrito/figuras/fig_detected_mutations.png     (article Fig. — zinc site
        closeup + table of top ClinVar-validated detections)
  docs/suplementar/figuras/fig_detected_brct.png         (supplement — BRCT closeup)

Run: python scratch/compose_detection_figures.py
"""
from __future__ import annotations

import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize

SRC = "scratch/pymol"
os.makedirs("docs/manuscrito/figuras", exist_ok=True)
os.makedirs("docs/suplementar/figuras", exist_ok=True)


def _img(ax, path, title):
    ax.imshow(mpimg.imread(path)); ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=12.5, fontweight="bold", loc="left", color="#1a1a1a")


# ---------- Article Fig 1: detection landscape (RING + BRCT) ----------------
fig = plt.figure(figsize=(12.4, 6.0), dpi=200)
gs = fig.add_gridspec(1, 2, wspace=0.02)
_img(fig.add_subplot(gs[0]), f"{SRC}/ring_detection.png", "A   BRCA1 — domínio RING (PDB 1JM7)")
_img(fig.add_subplot(gs[1]), f"{SRC}/brct_detection.png", "B   BRCA1 — repetições BRCT (PDB 1JNX)")
cax = fig.add_axes([0.30, 0.07, 0.40, 0.028])
ColorbarBase(cax, cmap=cm.get_cmap("bwr"), norm=Normalize(0, 1), orientation="horizontal")
cax.set_title("Fração das 19 substituições detectadas como patogênicas (PP3_Forte)  —  azul: baixa · vermelho: alta",
              fontsize=8.6, color="#333")
fig.subplots_adjust(left=0.005, right=0.995, top=0.94, bottom=0.14)
fig.savefig("docs/manuscrito/figuras/fig_detection_landscape.png", dpi=200,
            bbox_inches="tight", facecolor="white")
print("saved fig_detection_landscape.png")

# ---------- Article Fig 2: detected mutations at the zinc site ---------------
top = pd.read_csv("primevarclass_manuscript_analysis/detected_top_variants.csv")
ring = top[top.functional_domain == "RING"].copy()
ring = ring[ring.clinvar.astype(str).str.contains("athogenic", na=False)].head(8)

fig = plt.figure(figsize=(12.6, 6.2), dpi=200)
gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.04)
_img(fig.add_subplot(gs[0]), f"{SRC}/ring_detection_closeup.png",
     "A   Mutações detectadas no sítio de zinco do RING")
ax = fig.add_subplot(gs[1]); ax.set_axis_off()
ax.set_title("B   Principais detecções (PP3_Forte) validadas no ClinVar",
             fontsize=12.5, fontweight="bold", loc="left", color="#1a1a1a")
rows = [["Variante", "Prob.", "ClinVar"]]
for _, r in ring.iterrows():
    cv = str(r.clinvar).replace("Pathogenic/Likely pathogenic", "P/LP").replace(
        "Likely pathogenic", "LP").replace("Pathogenic", "P")
    rows.append([r.hgvs_p, f"{r.pathogenicity_prob:.3f}", cv])
tbl = ax.table(cellText=rows[1:], colLabels=rows[0], loc="center", cellLoc="left",
               colWidths=[0.42, 0.22, 0.30])
tbl.auto_set_font_size(False); tbl.set_fontsize(10.5); tbl.scale(1, 1.55)
for (rr, _), cell in tbl.get_celld().items():
    cell.set_edgecolor("#ddd")
    if rr == 0:
        cell.set_facecolor("#c0392b"); cell.set_text_props(color="white", fontweight="bold")
ax.text(0.0, 0.06,
        "As substituições nas cisteínas que coordenam o zinco (Cys24/39/61/64) —\n"
        "núcleo estrutural do RING — são detectadas com probabilidade > 0,99 e\n"
        "confirmadas como patogênicas no ClinVar.",
        transform=ax.transAxes, fontsize=9, color="#333", va="top")
fig.subplots_adjust(left=0.005, right=0.985, top=0.93, bottom=0.05)
fig.savefig("docs/manuscrito/figuras/fig_detected_mutations.png", dpi=200,
            bbox_inches="tight", facecolor="white")
print("saved fig_detected_mutations.png")

# ---------- Supplement: BRCT closeup ----------------------------------------
fig, ax = plt.subplots(figsize=(7.6, 6.4), dpi=200)
_img(ax, f"{SRC}/brct_detection_closeup.png",
     "Resíduos-alvo detectados no núcleo do domínio BRCT (1JNX)")
fig.tight_layout()
fig.savefig("docs/suplementar/figuras/fig_detected_brct.png", dpi=200,
            bbox_inches="tight", facecolor="white")
print("saved fig_detected_brct.png")
