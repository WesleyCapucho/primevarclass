"""Protein/domain figures for the manuscript, from real annotated data:
  - fig_domain_architecture.png: BRCA1 (P38398) and BRCA2 (P51587) linear
    domain maps with the observed variants overlaid (pathogenic vs benign).
  - fig_pathogenicity_by_domain.png: pathogenic fraction by functional region.

Run: python scratch/figures_domains.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.domain_annotation import BRCA1_DOMAINS, BRCA2_DOMAINS

OUT = "primevarclass_manuscript_analysis"
os.makedirs(OUT, exist_ok=True)
LEN = {"BRCA1": 1863, "BRCA2": 3418}
DOMS = {"BRCA1": BRCA1_DOMAINS, "BRCA2": BRCA2_DOMAINS}


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = df.loc[keep].reset_index(drop=True); df["label"] = y.loc[keep].astype(int).values
    return df


df = load("configs/public_brca_real.toml")
plt.rcParams.update({"figure.dpi": 150, "font.size": 10})

# ---------- Fig 1: domain architecture ----------
fig, axes = plt.subplots(2, 1, figsize=(9, 5.2))
for ax, gene in zip(axes, ["BRCA1", "BRCA2"]):
    L = LEN[gene]
    ax.add_patch(Rectangle((0, 0.35), L, 0.30, facecolor="#e8e8e8", edgecolor="#999", lw=0.8))
    for sp in DOMS[gene]:
        col = "#d55e00" if sp.critical else "#4c72b0"
        ax.add_patch(Rectangle((sp.start, 0.30), sp.end - sp.start, 0.40, facecolor=col,
                               edgecolor="black", lw=0.6, alpha=0.9))
        ax.text((sp.start + sp.end) / 2, 0.83, sp.name, ha="center", va="bottom", fontsize=6.5, rotation=0)
    g = df[df["gene"] == gene]
    for _, r in g.iterrows():
        x = int(r["position"]); patho = int(r["label"]) == 1
        ax.plot([x, x], (0.05, 0.22) if patho else (0.78, 0.95),
                color=("#c1121f" if patho else "#2a9d8f"), lw=0.35, alpha=0.5)
    ax.set_xlim(-20, L + 20); ax.set_ylim(0, 1.05)
    ax.set_yticks([]); ax.set_title(f"{gene} ({'P38398' if gene=='BRCA1' else 'P51587'}, {L} aa) — "
                                    f"vermelho=região crítica, azul=demais domínios; "
                                    f"riscos: patogênicas (baixo) vs benignas (topo)", fontsize=8)
    ax.set_xlabel("Posição do resíduo (aa)")
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_domain_architecture.png")); plt.close()

# ---------- Fig 2: pathogenicity by region ----------
def region(gene, pos):
    for sp in DOMS[gene]:
        if sp.start <= pos <= sp.end:
            return "Domínio crítico" if sp.critical else "Domínio não crítico"
    return "Ligante (linker)"

df["region"] = [region(g, int(p)) for g, p in zip(df["gene"], df["position"])]
order = ["Domínio crítico", "Domínio não crítico", "Ligante (linker)"]
rates = df.groupby("region")["label"].agg(["mean", "count"]).reindex(order)
fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(order, rates["mean"] * 100, color=["#d55e00", "#4c72b0", "#999999"], alpha=0.9)
for b, (_, row) in zip(bars, rates.iterrows()):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1,
            f"{b.get_height():.0f}%\n(n={int(row['count'])})", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("Fração de variantes patogênicas (%)")
ax.set_title("Patogenicidade por região funcional (coorte interna)")
ax.set_ylim(0, max(rates["mean"] * 100) + 12)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_pathogenicity_by_domain.png")); plt.close()
print("wrote fig_domain_architecture.png and fig_pathogenicity_by_domain.png")
print(rates)
