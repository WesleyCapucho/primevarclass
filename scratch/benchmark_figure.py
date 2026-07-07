"""Benchmark figure: ROC overlay of PrimeVarClass vs established predictors on
the SAME external variants (common intersection where every tool has a score),
plus an AUC bar chart with 95% bootstrap CIs. Reads benchmark_scores.csv.

Run: python scratch/benchmark_figure.py
"""
from __future__ import annotations

import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve

ANL = "primevarclass_manuscript_analysis"
OUT = "docs/manuscrito/figuras/fig_benchmark_roc.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

scores = pd.read_csv(os.path.join(ANL, "benchmark_scores.csv"))
COLS = [("PrimeVarClass (domínio + ESM-2)", "PrimeVarClass", "#c0392b", 2.6),
        ("AlphaMissense", "am", "#2e6fb0", 1.8),
        ("REVEL", "revel", "#2e8b57", 1.8),
        ("CADD", "cadd", "#e08a1e", 1.8),
        ("PolyPhen-2", "polyphen", "#7f5aa8", 1.4),
        ("SIFT", "sift", "#888888", 1.4)]
COLS = [(lab, c, col, lw) for lab, c, col, lw in COLS if c in scores.columns]

y = scores["label"].to_numpy(int)
present = np.ones(len(scores), bool)
for _, c, _, _ in COLS:
    present &= ~scores[c].isna().to_numpy()
yc = y[present]
n_common = int(present.sum())

fig, (ax, axb) = plt.subplots(1, 2, figsize=(12.4, 6.0), dpi=200,
                              gridspec_kw={"width_ratios": [1.32, 1]})

aucs = {}
rng = np.random.default_rng(42)
for lab, c, col, lw in COLS:
    s = scores[c].to_numpy(float)[present]
    fpr, tpr, _ = roc_curve(yc, s)
    a = roc_auc_score(yc, s)
    aucs[lab] = a
    ax.plot(fpr, tpr, color=col, lw=lw, label=f"{lab} — AUC {a:.3f}",
            zorder=5 if c == "PrimeVarClass" else 3)
ax.plot([0, 1], [0, 1], ls="--", color="#bbbbbb", lw=1)
ax.set_xlabel("1 − especificidade (FPR)", fontsize=11)
ax.set_ylabel("Sensibilidade (TPR)", fontsize=11)
ax.set_title(f"A   Curvas ROC nas coortes externas (n = {n_common} comuns)",
             fontsize=12, fontweight="bold", loc="left")
ax.legend(loc="lower right", fontsize=9, frameon=True)
ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.01)
ax.grid(alpha=0.25)

# bar chart with bootstrap CIs on the common set
labs = [l for l, _, _, _ in COLS]
colvals = [c for _, c, _, _ in COLS]
cols_hex = [c for _, _, c, _ in COLS]
means, los, his = [], [], []
for _, c, _, _ in COLS:
    s = scores[c].to_numpy(float)[present]
    a = roc_auc_score(yc, s); bs = []
    for _ in range(2000):
        idx = rng.integers(0, len(yc), len(yc))
        if len(np.unique(yc[idx])) < 2:
            continue
        bs.append(roc_auc_score(yc[idx], s[idx]))
    means.append(a); los.append(a - np.percentile(bs, 2.5)); his.append(np.percentile(bs, 97.5) - a)
order = np.argsort(means)[::-1]
ypos = np.arange(len(order))
axb.barh(ypos, [means[i] for i in order], xerr=[[los[i] for i in order], [his[i] for i in order]],
         color=[cols_hex[i] for i in order], alpha=0.9, height=0.62,
         error_kw={"elinewidth": 1.2, "capsize": 3})
axb.set_yticks(ypos); axb.set_yticklabels([labs[i] for i in order], fontsize=9.5)
axb.invert_yaxis()
axb.set_xlim(0.5, 1.0)
axb.set_xlabel("AUC-ROC (IC95% bootstrap)", fontsize=11)
axb.set_title("B   AUC no conjunto comum", fontsize=12, fontweight="bold", loc="left")
for i, oi in enumerate(order):
    axb.text(means[oi] + his[oi] + 0.006, i, f"{means[oi]:.3f}", va="center", fontsize=8.6)
axb.grid(axis="x", alpha=0.25)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "| common n =", n_common)
print("AUCs (common set):", {k: round(v, 4) for k, v in aucs.items()})
