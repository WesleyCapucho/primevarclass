"""Central schematic: BRCA1/BRCA2 in homologous-recombination DNA repair and
hereditary breast/ovarian cancer (HBOC). Conceptual diagram (no data)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = "primevarclass_manuscript_analysis/fig_disease_mechanism.png"
GN, RD = "#1b7837", "#c1121f"
fig, ax = plt.subplots(figsize=(11.5, 6.6), dpi=200)
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")


def box(x, y, w, h, text, ec, fc):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.06,rounding_size=0.12", fc=fc, ec=ec, lw=1.9))
    ax.text(x, y, text, ha="center", va="center", fontsize=11.5)


def arrow(x, y1, y2, color):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", lw=2.2, color=color))


ax.text(5, 9.65, "BRCA1/BRCA2 no reparo do DNA por recombinação homóloga e o câncer\nhereditário de mama e ovário (HBOC)",
        ha="center", va="center", fontsize=14.5, fontweight="bold")

lx, rx, w = 2.55, 7.45, 4.3
ax.text(lx, 8.95, "Célula com BRCA1/BRCA2 funcionais", ha="center", fontsize=12.5, color=GN, fontweight="bold")
ax.text(rx, 8.95, "Portador(a) de variante patogênica", ha="center", fontsize=12.5, color=RD, fontweight="bold")

L = [
    (8.15, "Quebra de dupla fita no DNA\n(dano frequente e potencialmente letal)"),
    (6.45, "BRCA1 e BRCA2 funcionais recrutam RAD51 e\na maquinaria de recombinação homóloga (RH)"),
    (4.75, "Reparo fiel e de alta precisão do DNA"),
    (3.05, "Estabilidade genômica\n(proteção contra o câncer)"),
]
R = [
    (8.15, "Variante patogênica em BRCA1/BRCA2\n(ex.: Cys61Gly no RING; Met1775Arg no BRCT)"),
    (6.45, "Domínio funcional crítico comprometido\n→ recombinação homóloga deficiente"),
    (4.75, "Reparo por vias alternativas\npropensas a erro"),
    (3.05, "Instabilidade genômica e\nacúmulo de mutações"),
    (1.45, "Tumorigênese: câncer de\nmama e de ovário"),
]
for (y, t) in L:
    box(lx, y, w, 1.15, t, GN, "#eef7ee")
for (y, t) in R:
    box(rx, y, w, 1.15, t, RD, "#fdeeee")
for i in range(len(L) - 1):
    arrow(lx, L[i][0] - 0.6, L[i + 1][0] + 0.6, GN)
for i in range(len(R) - 1):
    arrow(rx, R[i][0] - 0.6, R[i + 1][0] + 0.6, RD)

ax.text(5, 0.35,
        "Penetrância elevada: risco cumulativo de câncer de mama ~45–72% e de ovário ~11–44% ao longo da vida em portadoras de BRCA1/BRCA2.\n"
        "A deficiência de recombinação homóloga também confere sensibilidade a inibidores de PARP (letalidade sintética), base de terapias-alvo.",
        ha="center", va="center", fontsize=9.8, style="italic", color="#333333")

import os
plt.tight_layout()
for _fp in (OUT, "docs/manuscrito/figuras/fig_disease_mechanism.png"):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    plt.savefig(_fp, bbox_inches="tight", facecolor="white")
plt.close()
print("wrote", OUT, "+ docs/manuscrito/figuras/")
