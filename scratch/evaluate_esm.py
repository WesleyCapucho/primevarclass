"""Evaluate whether adding real ESM-2 scores to the domain-aware model improves
generalization, under the SAME anti-leakage protocol used throughout the paper
(position-blocked CV + external cohorts; DeLong test).

Requires scratch/esm_input/esm2_scores.csv (produced by esm2_score.py).
Run: python scratch/evaluate_esm.py
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import roc_auc_score
from scipy.stats import norm
from primevarclass.core import get_feature_subsets, _build_pipeline
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores
RNG = 42
OUT = "primevarclass_manuscript_analysis"
os.makedirs(OUT, exist_ok=True)

ESM = "scratch/esm_input/esm2_scores.csv"
esm_df = pd.read_csv(ESM)
print(f">> ESM-2 scores: {len(esm_df)} variants, coverage LLR mean {esm_df.esm2_llr.mean():.2f}")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    df = df.loc[keep].reset_index(drop=True)
    df = attach_esm_scores(df, esm_df)  # overwrite esm2_llr / has_esm_score with real values
    return df, y.loc[keep].astype(int).to_numpy()


tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])
cov_tr = tr_df["has_esm_score"].mean(); cov_ext = ext_df["has_esm_score"].mean()
print(f"   train n={len(tr_df)} (ESM cov {cov_tr:.0%}) | external n={len(ext_df)} (ESM cov {cov_ext:.0%})")


def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]: j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    T2 = np.empty(N); T2[J] = T; return T2


def delong(y, p1, p2):
    o = np.argsort(-y); y = y[o]; m = int(y.sum()); P = np.vstack((p1[o], p2[o])); k, n = P.shape
    tx = np.empty([k, m]); ty = np.empty([k, n - m]); tz = np.empty([k, n])
    for r in range(k):
        tx[r] = _midrank(P[r, :m]); ty[r] = _midrank(P[r, m:]); tz[r] = _midrank(P[r])
    aucs = (tz[:, :m].sum(1) / m - (m + 1) / 2.0) / (n - m)
    v01 = (tz[:, :m] - tx) / (n - m); v10 = 1 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / (n - m)
    var = max(np.array([[1, -1]]).dot(cov).dot(np.array([[1], [-1]]))[0, 0], 1e-12)
    return float(aucs[0]), float(aucs[1]), float(2 * norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(var))))


sub = get_feature_subsets(tr_df)
MODELS = {
    "ESM-2 sozinho": ["esm2_llr"],
    "Domínio-consciente": sub["domain_aware"],
    "Domínio + ESM-2": sub["domain_aware_plus_esm"],
}
def ok(cols, df): return [c for c in cols if c in df.columns and not df[c].isna().all()]

groups = (tr_df["gene"].astype(str) + ":" + tr_df["position"].astype(str)).to_numpy()
res = {}
print("\n===== A) CV BLOQUEADA POR POSIÇÃO =====")
oof = {}
for name, cols in MODELS.items():
    c = ok(cols, tr_df); X = tr_df[c].copy(); o = np.zeros(len(ytr))
    for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=RNG).split(X, ytr, groups):
        p = _build_pipeline(X.iloc[a], random_state=RNG); p.fit(X.iloc[a], ytr[a])
        o[b] = p.predict_proba(X.iloc[b])[:, 1]
    oof[name] = o
    print(f"   {name:22s} AUC={roc_auc_score(ytr, o):.4f}")

print("\n===== B) GENERALIZAÇÃO EXTERNA =====")
extP = {}
for name, cols in MODELS.items():
    c = [x for x in ok(cols, tr_df) if x in ext_df.columns]
    p = _build_pipeline(tr_df[c], random_state=RNG); p.fit(tr_df[c], ytr)
    extP[name] = p.predict_proba(ext_df[c])[:, 1]
    print(f"   {name:22s} AUC={roc_auc_score(yext, extP[name]):.4f}")

d_cv = delong(ytr, oof["Domínio + ESM-2"], oof["Domínio-consciente"])
d_ext = delong(yext, extP["Domínio + ESM-2"], extP["Domínio-consciente"])
print(f"\nDeLong (Domínio+ESM vs Domínio):  interno {d_cv[0]:.4f} vs {d_cv[1]:.4f} p={d_cv[2]:.4g}"
      f"  |  externo {d_ext[0]:.4f} vs {d_ext[1]:.4f} p={d_ext[2]:.4g}")

res = {
    "esm_coverage_train": float(cov_tr), "esm_coverage_external": float(cov_ext),
    "cv": {k: float(roc_auc_score(ytr, oof[k])) for k in MODELS},
    "external": {k: float(roc_auc_score(yext, extP[k])) for k in MODELS},
    "delong_domesm_vs_dom_cv_p": d_cv[2], "delong_domesm_vs_dom_ext_p": d_ext[2],
}
json.dump(res, open(os.path.join(OUT, "esm_evaluation.json"), "w"), indent=2, ensure_ascii=False)
print(f"\n>> wrote {OUT}/esm_evaluation.json")
