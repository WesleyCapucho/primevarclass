"""Central schematic: BRCA1/BRCA2 in homologous-recombination DNA repair and
hereditary breast/ovarian cancer (HBOC). Conceptual diagram (no data)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = "primevarclass_manuscript_analysis/fig_disease_mechanism.png"
GN, RD = "#1b7837", "#c1121f"
fig, ax = plt.subplots(figsize=(13.2, 8.3), dpi=200)
# o eixo y se estende abaixo de zero para a nota de rodape ter faixa propria,
# sem invadir a caixa inferior da coluna direita
ax.set_xlim(0, 10); ax.set_ylim(-1.3, 10); ax.axis("off")

# Fonte e quebras de linha calibradas para o texto caber dentro das caixas:
# linhas curtas (ate ~34 caracteres) em caixas de 4,6 unidades de largura.
FS_CAIXA = 13.0


def box(x, y, w, h, text, ec, fc):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.06,rounding_size=0.12", fc=fc, ec=ec, lw=1.9))
    ax.text(x, y, text, ha="center", va="center", fontsize=FS_CAIXA, linespacing=1.35)


def arrow(x, y1, y2, color):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", lw=2.2, color=color))


ax.text(5, 9.72, "BRCA1/BRCA2 no reparo do DNA por recombinação homóloga\ne o câncer hereditário de mama e ovário (HBOC)",
        ha="center", va="center", fontsize=15.5, fontweight="bold", linespacing=1.3)

lx, rx, w, h = 2.42, 7.58, 4.6, 1.32
ax.text(lx, 9.15, "Célula com BRCA1/BRCA2 funcionais", ha="center", fontsize=13.5, color=GN, fontweight="bold")
ax.text(rx, 9.15, "Portador(a) de variante patogênica", ha="center", fontsize=13.5, color=RD, fontweight="bold")

L = [
    (8.30, "Quebra de dupla fita no DNA\n(dano frequente e\npotencialmente letal)"),
    (6.60, "BRCA1 e BRCA2 funcionais recrutam\nRAD51 e a maquinaria de\nrecombinação homóloga (RH)"),
    (4.90, "Reparo fiel e de\nalta precisão do DNA"),
    (3.20, "Estabilidade genômica\n(proteção contra o câncer)"),
]
R = [
    (8.30, "Variante patogênica em BRCA1/BRCA2\n(ex.: Cys61Gly no RING;\nMet1775Arg no BRCT)"),
    (6.60, "Domínio funcional crítico\ncomprometido: recombinação\nhomóloga deficiente"),
    (4.90, "Reparo por vias alternativas\npropensas a erro"),
    (3.20, "Instabilidade genômica e\nacúmulo de mutações"),
    (1.50, "Tumorigênese: câncer de\nmama e de ovário"),
]
for (y, t) in L:
    box(lx, y, w, h, t, GN, "#eef7ee")
for (y, t) in R:
    box(rx, y, w, h, t, RD, "#fdeeee")
for i in range(len(L) - 1):
    arrow(lx, L[i][0] - h / 2 - 0.03, L[i + 1][0] + h / 2 + 0.03, GN)
for i in range(len(R) - 1):
    arrow(rx, R[i][0] - h / 2 - 0.03, R[i + 1][0] + h / 2 + 0.03, RD)

ax.text(5, -0.62,
        "Penetrância elevada: risco cumulativo de câncer de mama ~45–72% e de ovário ~11–44%\n"
        "ao longo da vida em portadoras de BRCA1/BRCA2. A deficiência de recombinação homóloga\n"
        "também confere sensibilidade a inibidores de PARP (letalidade sintética), base de terapias-alvo.",
        ha="center", va="center", fontsize=12.5, style="italic", color="#333333", linespacing=1.35)

import os
plt.tight_layout()
for _fp in (OUT, "docs/manuscrito/figuras/fig_disease_mechanism.png"):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    plt.savefig(_fp, bbox_inches="tight", facecolor="white")
plt.close()
print("wrote", OUT, "+ docs/manuscrito/figuras/")
