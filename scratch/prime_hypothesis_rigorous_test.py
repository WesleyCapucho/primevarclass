"""THE definitive, reproducible test of the prime-number hypothesis, under the
SAME rigorous anti-leakage protocol used everywhere else in this project:
position-blocked StratifiedGroupKFold (grouped by gene:position) for internal
validation, PLUS held-out external cohorts never touched during training.

This supersedes scratch/decisive_prime_test.py, which used a plain (non-blocked)
StratifiedKFold — that script is a useful DIAGNOSTIC of position leakage itself
(a naive protocol inflates AUC for anything carrying raw position), but is NOT
the rigorous test the manuscript's prime-refutation claim rests on. This script
IS that rigorous test, and its output is the canonical source for the
"hipótese dos primos foi refutada" section of the manuscript.

Run: python scratch/prime_hypothesis_rigorous_test.py
"""
from __future__ import annotations

import json
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
OUT = "primevarclass_manuscript_analysis"


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    return df.loc[keep].reset_index(drop=True), y.loc[keep].astype(int).to_numpy()


def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    T2 = np.empty(N); T2[J] = T; return T2


def delong(y, p1, p2):
    o = np.argsort(-y); y = y[o]; m = int(y.sum())
    P = np.vstack((p1[o], p2[o])); k, n = P.shape
    tx = np.empty([k, m]); ty = np.empty([k, n - m]); tz = np.empty([k, n])
    for r in range(k):
        tx[r] = _midrank(P[r, :m]); ty[r] = _midrank(P[r, m:]); tz[r] = _midrank(P[r])
    aucs = (tz[:, :m].sum(1) / m - (m + 1) / 2.0) / (n - m)
    v01 = (tz[:, :m] - tx) / (n - m); v10 = 1 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / (n - m)
    var = max(np.array([[1, -1]]).dot(cov).dot(np.array([[1], [-1]]))[0, 0], 1e-12)
    return float(aucs[0]), float(aucs[1]), float(2 * norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(var))))


print(">> loading real cohorts (public_brca_real.toml + 4 external configs)...")
tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])
print(f"   train n={len(tr_df)} (pat={int(ytr.sum())})  external n={len(ext_df)} (pat={int(yext.sum())})")

subs = get_feature_subsets(tr_df)
FSETS = {
    "identidade_com_posicao": [c for c in ["gene", "aa_ref", "aa_alt", "position"] if c in tr_df.columns],
    "identidade_sem_posicao": [c for c in ["gene", "aa_ref", "aa_alt"] if c in tr_df.columns],
    "bioquimico": subs["biochemical_only"],          # includes gene + raw position
    "hibrido": subs["hybrid"],                        # bioquimico + primos
    "apenas_primos": subs["prime_only"],
}


def ok(cols, df):
    return [c for c in cols if c in df.columns and not df[c].isna().all()]


groups = (tr_df["gene"].astype(str) + ":" + tr_df["position"].astype(str)).to_numpy()

print("\n===== A) CV BLOQUEADA POR POSIÇÃO (StratifiedGroupKFold, 5 folds) =====")
oof = {}
n_features = {}
for name, cols in FSETS.items():
    c = ok(cols, tr_df); n_features[name] = len(c)
    X = tr_df[c].copy(); o = np.zeros(len(ytr))
    for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=RNG).split(X, ytr, groups):
        p = _build_pipeline(X.iloc[a], random_state=RNG); p.fit(X.iloc[a], ytr[a])
        o[b] = p.predict_proba(X.iloc[b])[:, 1]
    oof[name] = o
    print(f"   {name:26s} n_feat={len(c):3d}  AUC={roc_auc_score(ytr, o):.4f}")

print("\n===== B) GENERALIZAÇÃO EXTERNA =====")
extP = {}
for name, cols in FSETS.items():
    c = [x for x in ok(cols, tr_df) if x in ext_df.columns]
    p = _build_pipeline(tr_df[c], random_state=RNG); p.fit(tr_df[c], ytr)
    extP[name] = p.predict_proba(ext_df[c])[:, 1]
    print(f"   {name:26s} AUC={roc_auc_score(yext, extP[name]):.4f}")

print("\n===== C) DeLong (comparações que testam a hipótese dos primos) =====")
comparisons = [
    ("apenas_primos", "identidade_sem_posicao", "os primos superam a identidade simples?"),
    ("hibrido", "bioquimico", "adicionar primos a um modelo bioquímico ajuda?"),
]
result = {"n_train": int(len(tr_df)), "n_external": int(len(ext_df)),
          "n_features": n_features, "cv_blocked": {}, "external": {}, "delong": []}
for name in FSETS:
    result["cv_blocked"][name] = round(float(roc_auc_score(ytr, oof[name])), 4)
    result["external"][name] = round(float(roc_auc_score(yext, extP[name])), 4)
for a, b, q in comparisons:
    for scope, y_, d_ in [("cv_blocked", ytr, oof), ("external", yext, extP)]:
        auc_a, auc_b, p = delong(y_, d_[a], d_[b])
        print(f"   [{scope}] {q}\n      {a}={auc_a:.4f} vs {b}={auc_b:.4f}  delta={auc_a-auc_b:+.4f}  p={p:.4g}")
        result["delong"].append({"scope": scope, "a": a, "b": b, "question": q,
                                 "auc_a": round(auc_a, 4), "auc_b": round(auc_b, 4),
                                 "delta": round(auc_a - auc_b, 4), "p": round(p, 6)})

json.dump(result, open(os.path.join(OUT, "prime_hypothesis_rigorous.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print(f"\n>> wrote {OUT}/prime_hypothesis_rigorous.json")
