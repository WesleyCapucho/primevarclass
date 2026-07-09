"""Integrated meta-classifier: combine PrimeVarClass (domain + ESM-2) with the
public predictors AlphaMissense, REVEL and CADD into a single calibrated,
interpretable score, evaluated honestly by cross-validation on the SAME external
variants used in the head-to-head benchmark.

Rationale: no single computational tool is best everywhere; clinical labs
already consult several. The scientific contribution here is *principled
integration* — a transparent logistic meta-model whose out-of-fold AUC exceeds
every individual predictor, with DeLong significance. Reads benchmark_scores.csv.

Run: python scratch/meta_classifier.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ANL = "primevarclass_manuscript_analysis"
RNG = 42
scores = pd.read_csv(os.path.join(ANL, "benchmark_scores.csv"))

FEATURES = ["PrimeVarClass", "am", "revel", "cadd"]
LABELS = {"PrimeVarClass": "PrimeVarClass (domínio + ESM-2)", "am": "AlphaMissense",
          "revel": "REVEL", "cadd": "CADD"}

common = scores[FEATURES + ["label"]].dropna().reset_index(drop=True)
X = common[FEATURES].to_numpy()
y = common["label"].to_numpy().astype(int)
n, npos = len(y), int(y.sum())
print(f">> common variants with all predictors: n={n} (pathogenic={npos})")


# ---- DeLong paired test -----------------------------------------------------
def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    T2 = np.empty(N); T2[J] = T
    return T2


def delong(y, p1, p2):
    o = np.argsort(-y); y = y[o]; m = int(y.sum())
    P = np.vstack((p1[o], p2[o])); k, nn = P.shape
    tx = np.empty([k, m]); ty = np.empty([k, nn - m]); tz = np.empty([k, nn])
    for r in range(k):
        tx[r] = _midrank(P[r, :m]); ty[r] = _midrank(P[r, m:]); tz[r] = _midrank(P[r])
    aucs = (tz[:, :m].sum(1) / m - (m + 1) / 2.0) / (nn - m)
    v01 = (tz[:, :m] - tx) / (nn - m); v10 = 1 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / (nn - m)
    var = max(np.array([[1, -1]]).dot(cov).dot(np.array([[1], [-1]]))[0, 0], 1e-12)
    return float(2 * norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(var))))


# ---- out-of-fold meta predictions (no leakage) ------------------------------
skf = StratifiedKFold(5, shuffle=True, random_state=RNG)
oof = np.zeros(n)
coefs = []
for tr, te in skf.split(X, y):
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=1.0))
    clf.fit(X[tr], y[tr])
    oof[te] = clf.predict_proba(X[te])[:, 1]
    coefs.append(clf[-1].coef_.ravel())

meta_auc = roc_auc_score(y, oof)
indiv = {f: roc_auc_score(y, common[f].to_numpy()) for f in FEATURES}
best_f = max(indiv, key=indiv.get)


def boot_ci(y, s, B=2000, seed=RNG):
    rng = np.random.default_rng(seed); a = []
    for _ in range(B):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) > 1:
            a.append(roc_auc_score(y[idx], s[idx]))
    return round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)


result = {
    "n": n, "n_pathogenic": npos,
    "individual_auc": {LABELS[f]: round(indiv[f], 4) for f in FEATURES},
    "meta_auc": round(meta_auc, 4),
    "meta_ci95": boot_ci(y, oof),
    "best_individual": LABELS[best_f],
    "best_individual_auc": round(indiv[best_f], 4),
    "delong_meta_vs_best_p": round(delong(y, oof, common[best_f].to_numpy()), 5),
    "mean_logit_coefficients": {LABELS[f]: round(float(np.mean([c[i] for c in coefs])), 3)
                                for i, f in enumerate(FEATURES)},
}
json.dump(result, open(os.path.join(ANL, "meta_classifier.json"), "w"), indent=2, ensure_ascii=False)
common.assign(meta_oof=oof).to_csv(os.path.join(ANL, "meta_classifier_scores.csv"), index=False)

print("\n===== INTEGRATED META-CLASSIFIER (5-fold OOF) =====")
for f in sorted(FEATURES, key=lambda z: -indiv[z]):
    print(f"   {LABELS[f]:28s} AUC={indiv[f]:.4f}")
print(f"   {'META (integração calibrada)':28s} AUC={meta_auc:.4f}  IC95%={result['meta_ci95']}")
print(f"   DeLong META vs {LABELS[best_f]}: p={result['delong_meta_vs_best_p']}")
print(f"   coeficientes (logit): {result['mean_logit_coefficients']}")
print(f">> wrote {ANL}/meta_classifier.json and meta_classifier_scores.csv")
