"""Random-effects meta-analysis of the domain-aware model across the four
independent external subcohorts (BRCA1/BRCA2 x expert-panel/external).

For each subcohort we compute AUC and a bootstrap 95% CI, then pool on the
logit-AUC scale with the DerSimonian-Laird random-effects estimator, reporting
the pooled AUC, its CI, Cochran's Q, and I^2 heterogeneity. A forest plot is
saved. This is a legitimate meta-analysis of our own multi-cohort validation --
no numbers are taken from third-party abstracts.

Run: python scratch/meta_analysis.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config

OUT = "primevarclass_manuscript_analysis"
os.makedirs(OUT, exist_ok=True)
RNG = 42
rng = np.random.default_rng(RNG)
B = 2000

COHORTS = {
    "BRCA1 — painel especialista": "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "BRCA2 — painel especialista": "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "BRCA1 — coorte externa": "configs/public_brca_external_real_brca1.toml",
    "BRCA2 — coorte externa": "configs/public_brca_external_real_brca2.toml",
}


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    return df.loc[keep].reset_index(drop=True), y.loc[keep].astype(int).to_numpy()


print(">> training domain-aware model on internal cohort...")
tr_df, ytr = load("configs/public_brca_real.toml")
cols = [c for c in get_feature_subsets(tr_df)["domain_aware"] if c in tr_df.columns and not tr_df[c].isna().all()]
pipe = _build_pipeline(tr_df[cols], random_state=RNG); pipe.fit(tr_df[cols], ytr)


def boot_ci(y, p):
    n = len(y); vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if y[idx].min() == y[idx].max():
            continue
        vals.append(roc_auc_score(y[idx], p[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), float(np.std(vals))


rows = []
for name, cfg in COHORTS.items():
    df, y = load(cfg)
    use = [c for c in cols if c in df.columns]
    p = pipe.predict_proba(df[use])[:, 1] if set(use) == set(cols) else _build_pipeline(tr_df[use], RNG).fit(tr_df[use], ytr).predict_proba(df[use])[:, 1]
    auc = roc_auc_score(y, p)
    lo, hi, se = boot_ci(y, p)
    rows.append({"cohort": name, "n": int(len(y)), "pathogenic": float(y.mean()),
                 "auc": float(auc), "ci_lo": lo, "ci_hi": hi, "se": se})
    print(f"   {name:30s} n={len(y):4d}  AUC={auc:.3f} [{lo:.3f}, {hi:.3f}]")

# ---- DerSimonian-Laird random-effects pooling on logit(AUC) ----
def logit(x): return np.log(x / (1 - x))
def inv_logit(x): return 1 / (1 + np.exp(-x))

theta = np.array([logit(r["auc"]) for r in rows])
# SE on logit scale via delta method: se_logit = se_auc / (auc*(1-auc))
se_logit = np.array([r["se"] / (r["auc"] * (1 - r["auc"])) for r in rows])
w = 1.0 / se_logit**2
theta_fixed = np.sum(w * theta) / np.sum(w)
Q = float(np.sum(w * (theta - theta_fixed) ** 2))
k = len(rows)
C = np.sum(w) - np.sum(w**2) / np.sum(w)
tau2 = max(0.0, (Q - (k - 1)) / C)
w_re = 1.0 / (se_logit**2 + tau2)
theta_re = np.sum(w_re * theta) / np.sum(w_re)
se_re = np.sqrt(1.0 / np.sum(w_re))
pooled = inv_logit(theta_re)
pooled_lo = inv_logit(theta_re - 1.96 * se_re)
pooled_hi = inv_logit(theta_re + 1.96 * se_re)
I2 = float(max(0.0, (Q - (k - 1)) / Q) * 100) if Q > 0 else 0.0
p_Q = float(chi2.sf(Q, k - 1))

meta = {"cohorts": rows, "pooled_auc": float(pooled), "pooled_ci": [float(pooled_lo), float(pooled_hi)],
        "Q": Q, "p_heterogeneity": p_Q, "I2_percent": I2, "tau2": float(tau2), "k": k}
json.dump(meta, open(os.path.join(OUT, "meta_analysis.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n   POOLED (random-effects) AUC = {pooled:.3f} [{pooled_lo:.3f}, {pooled_hi:.3f}]")
print(f"   Heterogeneity: I2={I2:.1f}%  Q={Q:.2f}  p={p_Q:.3f}  tau2={tau2:.4f}")

# ---- forest plot ----
plt.rcParams.update({"figure.dpi": 150, "font.size": 10})
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ys = np.arange(len(rows))[::-1]
for yi, r in zip(ys, rows):
    ax.plot([r["ci_lo"], r["ci_hi"]], [yi, yi], "-", color="#333333", lw=1.5)
    ax.plot(r["auc"], yi, "s", color="#1b7837", ms=7)
    ax.text(1.005, yi, f"{r['auc']:.3f} [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]  (n={r['n']})",
            va="center", fontsize=8)
# pooled diamond
yd = -1.2
ax.add_patch(plt.Polygon([[pooled_lo, yd], [pooled, yd + 0.25], [pooled_hi, yd], [pooled, yd - 0.25]],
                         closed=True, color="#d55e00"))
ax.text(1.005, yd, f"{pooled:.3f} [{pooled_lo:.3f}, {pooled_hi:.3f}]  (agrupado)", va="center", fontsize=8, fontweight="bold")
ax.axvline(pooled, color="#d55e00", ls=":", lw=1, alpha=0.6)
ax.axvline(0.5, color="gray", ls="--", lw=1, alpha=0.5)
ax.set_yticks(list(ys) + [yd]); ax.set_yticklabels([r["cohort"] for r in rows] + ["Agrupado (efeitos aleatórios)"], fontsize=8)
ax.set_xlim(0.45, 1.35); ax.set_xlabel("AUC-ROC (IC 95%)")
ax.set_title(f"Meta-análise de generalização externa — modelo domínio-consciente\nAUC agrupada {pooled:.3f} (IC95% {pooled_lo:.3f}–{pooled_hi:.3f}); I²={I2:.0f}%")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_meta_forest.png")); plt.close()
print(">> wrote meta_analysis.json and fig_meta_forest.png")
