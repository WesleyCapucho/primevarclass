"""End-to-end check: the INTEGRATED core (domain features populated inside
encode_variant_features + the `domain_aware` subset from get_feature_subsets)
reproduces the validated headline result on real ClinVar/expert cohorts.

Run: python scratch/validate_domain_integration.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config

RNG = 42


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    return df.loc[keep].reset_index(drop=True), y.loc[keep].astype(int).to_numpy()


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


print(">> loading real cohorts (domains populated INSIDE core)...")
tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])

# Confirm core actually populated real domain labels (not the "unknown" placeholder).
n_annot = (tr_df["functional_domain"].astype(str) != "linker").sum()
print(f"   train n={len(tr_df)}  external n={len(ext_df)}  residues inside a domain={int(n_annot)}")
assert set(tr_df["functional_domain"].unique()) - {"linker"}, "core did not populate domains!"

subs = get_feature_subsets(tr_df)
biochem_no_pos = [c for c in subs["biochemical_only"] if c != "position"]
FSETS = {
    "biochemical (no position)": biochem_no_pos,
    "domain_aware (core subset)": subs["domain_aware"],
    "biochemical + raw position": subs["biochemical_only"],
}


def ok(cols, df):
    return [c for c in cols if c in df.columns and not df[c].isna().all()]


groups = (tr_df["gene"].astype(str) + ":" + tr_df["position"].astype(str)).to_numpy()
print("\n===== A) POSITION-BLOCKED CV =====")
oof = {}
for name, cols in FSETS.items():
    c = ok(cols, tr_df); X = tr_df[c].copy(); o = np.zeros(len(ytr))
    for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=RNG).split(X, ytr, groups):
        p = _build_pipeline(X.iloc[a], random_state=RNG); p.fit(X.iloc[a], ytr[a])
        o[b] = p.predict_proba(X.iloc[b])[:, 1]
    oof[name] = o
    print(f"   {name:32s} AUC={roc_auc_score(ytr, o):.4f}")
d = delong(ytr, oof["domain_aware (core subset)"], oof["biochemical (no position)"])
print(f"   DeLong domain_aware vs biochemical: {d[0]:.4f} vs {d[1]:.4f}  p={d[2]:.4g}")

print("\n===== B) EXTERNAL GENERALIZATION =====")
extP = {}
for name, cols in FSETS.items():
    c = [x for x in ok(cols, tr_df) if x in ext_df.columns]
    p = _build_pipeline(tr_df[c], random_state=RNG); p.fit(tr_df[c], ytr)
    extP[name] = p.predict_proba(ext_df[c])[:, 1]
    print(f"   {name:32s} AUC={roc_auc_score(yext, extP[name]):.4f}")
d = delong(yext, extP["domain_aware (core subset)"], extP["biochemical (no position)"])
print(f"   DeLong domain_aware vs biochemical (external): {d[0]:.4f} vs {d[1]:.4f}  p={d[2]:.4g}")
