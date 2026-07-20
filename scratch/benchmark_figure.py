"""Benchmark figure: ROC overlay of PrimeVarClass, the established predictors
(AlphaMissense, REVEL, CADD) and the integrated META-classifier on the SAME
external variants (common intersection), plus an AUC bar chart with 95% bootstrap
CIs. Reads benchmark_scores.csv and meta_classifier_scores.csv.

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
OUT = "docs/suplementar/figuras/fig_benchmark_roc.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

scores = pd.read_csv(os.path.join(ANL, "benchmark_scores.csv"))
meta = pd.read_csv(os.path.join(ANL, "meta_classifier_scores.csv"))

# common set where every individual predictor has a score (matches the meta set)
base = ["PrimeVarClass", "am", "revel", "cadd"]
common = scores[base + ["label"]].dropna().reset_index(drop=True)
common["meta"] = meta["meta_oof"].to_numpy()
y = common["label"].to_numpy().astype(int)
n = len(y)

SERIES = [("META (integração calibrada)", "meta", "#1a1a1a", 2.8),
          ("PrimeVarClass (domínio + ESM-2)", "PrimeVarClass", "#c0392b", 2.2),
          ("AlphaMissense", "am", "#2e6fb0", 1.7),
          ("REVEL", "revel", "#2e8b57", 1.7),
          ("CADD", "cadd", "#e08a1e", 1.7)]

fig, (ax, axb) = plt.subplots(1, 2, figsize=(12.6, 6.0), dpi=200,
                              gridspec_kw={"width_ratios": [1.3, 1]})
rng = np.random.default_rng(42)
stats = {}
for lab, c, col, lw in SERIES:
    s = common[c].to_numpy(float)
    fpr, tpr, _ = roc_curve(y, s)
    a = roc_auc_score(y, s)
    bs = [roc_auc_score(y[i], s[i]) for i in (rng.integers(0, n, n) for _ in range(2000))
          if len(np.unique(y[i])) > 1]
    stats[lab] = (a, np.percentile(bs, 2.5), np.percentile(bs, 97.5), col)
    ax.plot(fpr, tpr, color=col, lw=lw, label=f"{lab}: AUC {a:.3f}",
            zorder=6 if c in ("meta", "PrimeVarClass") else 3)
ax.plot([0, 1], [0, 1], ls="--", color="#bbb", lw=1)
ax.set_xlabel("1 − especificidade (FPR)", fontsize=14.3)
ax.set_ylabel("Sensibilidade (TPR)", fontsize=14.3)
ax.set_title(f"A   ROC nas coortes externas independentes (n = {n})", fontsize=12, fontweight="bold", loc="left")
ax.legend(loc="lower right", fontsize=12)
ax.set_xlim(-0.01, 1.01); ax.set_ylim(-0.01, 1.01); ax.grid(alpha=0.25)

order = sorted(stats.items(), key=lambda kv: kv[1][0])
ypos = np.arange(len(order))
axb.barh(ypos, [v[0] for _, v in order],
         xerr=[[v[0] - v[1] for _, v in order], [v[2] - v[0] for _, v in order]],
         color=[v[3] for _, v in order], alpha=0.9, height=0.6,
         error_kw={"elinewidth": 1.2, "capsize": 3})
axb.set_yticks(ypos); axb.set_yticklabels([k.split(" (")[0] for k, _ in order], fontsize=12.3)
axb.set_xlim(0.5, 1.0); axb.set_xlabel("AUC-ROC (IC95% bootstrap)", fontsize=14.3)
axb.set_title("B   AUC no conjunto comum", fontsize=12, fontweight="bold", loc="left")
for i, (_, v) in enumerate(order):
    axb.text(v[2] + 0.006, i, f"{v[0]:.3f}", va="center", fontsize=12)
axb.grid(axis="x", alpha=0.25)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "| n =", n)
for k, v in sorted(stats.items(), key=lambda kv: -kv[1][0]):
    print(f"   {k:34s} AUC={v[0]:.4f} [{v[1]:.3f}, {v[2]:.3f}]")
