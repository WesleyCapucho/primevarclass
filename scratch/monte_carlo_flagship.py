"""Robust Monte Carlo cross-validation of the flagship (domain + ESM-2).

Beyond the single blocked-CV point estimate and the 12-seed repeat, this runs
N=1000 independent random position-blocked splits (GroupShuffleSplit grouped by
gene:position, 70/30), REFITTING the flagship each time, and reports the full
AUC distribution. It captures both sampling and model-fitting variance under the
anti-leakage protocol — the strongest stability statement for the headline model.

Run: python scratch/monte_carlo_flagship.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath("src")); os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

OUT = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_montecarlo.png"
N_ITER = 500
esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")

df, _, _ = build_dataset_from_source_config("configs/public_brca_real.toml", mode="hybrid", keep_metadata=True)
y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
y = y.loc[keep].astype(int).to_numpy()
cols = [c for c in get_feature_subsets(df)["domain_aware_plus_esm"]
        if c in df.columns and not df[c].isna().all()]
groups = (df["gene"].astype(str) + ":" + df["position"].astype(str)).to_numpy()
X = df[cols]
print(f">> n={len(df)} pat={int(y.sum())} feats={len(cols)} groups={len(set(groups))}", flush=True)

gss = GroupShuffleSplit(n_splits=N_ITER, test_size=0.30, random_state=42)
aucs = []
for k, (tr, te) in enumerate(gss.split(X, y, groups)):
    if len(np.unique(y[te])) < 2 or len(np.unique(y[tr])) < 2:
        continue
    p = _build_pipeline(X.iloc[tr], random_state=42)
    p.fit(X.iloc[tr], y[tr])
    aucs.append(float(roc_auc_score(y[te], p.predict_proba(X.iloc[te])[:, 1])))
    if (k + 1) % 200 == 0:
        print(f"   {k+1}/{N_ITER}  running mean={np.mean(aucs):.3f}", flush=True)
aucs = np.array(aucs)
res = {"n_iter": int(len(aucs)), "mean": round(float(aucs.mean()), 3),
       "sd": round(float(aucs.std(ddof=1)), 3),
       "median": round(float(np.median(aucs)), 3),
       "ci95": [round(float(np.percentile(aucs, 2.5)), 3), round(float(np.percentile(aucs, 97.5)), 3)],
       "min": round(float(aucs.min()), 3), "max": round(float(aucs.max()), 3),
       "frac_above_0.80": round(float((aucs > 0.80).mean()), 3)}
print(json.dumps(res, indent=2))
json.dump(res, open(os.path.join(OUT, "monte_carlo.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=200)
ax.hist(aucs, bins=40, color="#2e7d46", edgecolor="white", alpha=0.85)
ax.axvline(res["mean"], color="#c0392b", lw=2, label=f"média = {res['mean']:.3f}")
ax.axvline(res["ci95"][0], color="#c0392b", ls="--", lw=1.2, alpha=0.7)
ax.axvline(res["ci95"][1], color="#c0392b", ls="--", lw=1.2, alpha=0.7,
           label=f"IC95% [{res['ci95'][0]:.3f}, {res['ci95'][1]:.3f}]")
ax.set_xlabel("AUC-ROC (validação bloqueada por posição, teste retido)")
ax.set_ylabel(f"frequência ({res['n_iter']} divisões Monte Carlo)")
ax.set_title("Estabilidade Monte Carlo do modelo-carro-chefe (domínio + ESM-2)\n"
             f"{res['n_iter']} divisões aleatórias bloqueadas por posição, reajuste a cada iteração",
             fontsize=11)
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {OUT}/monte_carlo.json and {FIG}")
