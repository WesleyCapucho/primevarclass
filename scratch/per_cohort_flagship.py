"""Per-cohort AUC of the FLAGSHIP model (domain + ESM-2), not the intermediate
domain-only model. Directly addresses the heterogeneity concern: does the flagship
lift the weak BRCA1 external cohort, and is that cohort's low estimate a
small-positive-sample artefact (wide CI)?

Run: python scratch/per_cohort_flagship.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

RNG = 42
esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")
COHORTS = {
    "BRCA1 — painel especialista": "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "BRCA2 — painel especialista": "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "BRCA1 — coorte externa": "configs/public_brca_external_real_brca1.toml",
    "BRCA2 — coorte externa": "configs/public_brca_external_real_brca2.toml",
}


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
    return df, y.loc[keep].astype(int).to_numpy()


def boot_ci(y, s, B=2000, seed=RNG):
    rng = np.random.default_rng(seed); n = len(y); a = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        a.append(roc_auc_score(y[idx], s[idx]))
    return (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))) if a else (float("nan"),) * 2


tr_df, ytr = load("configs/public_brca_real.toml")
cols = [c for c in get_feature_subsets(tr_df)["domain_aware_plus_esm"]
        if c in tr_df.columns and not tr_df[c].isna().all()]
pipe = _build_pipeline(tr_df[cols], random_state=RNG); pipe.fit(tr_df[cols], ytr)

print(f"{'Coorte':32s} {'n':>4s} {'pat':>4s} {'AUC(flagship)':>13s}  IC95%")
out = {}
for name, cfg in COHORTS.items():
    df, y = load(cfg)
    c = [x for x in cols if x in df.columns]
    p = pipe.predict_proba(df[c])[:, 1]
    auc = roc_auc_score(y, p) if len(set(y)) > 1 else float("nan")
    lo, hi = boot_ci(y, p)
    out[name] = {"n": int(len(y)), "n_pat": int(y.sum()), "auc_flagship": round(float(auc), 3),
                 "ci95": [round(lo, 3), round(hi, 3)]}
    print(f"{name:32s} {len(y):4d} {int(y.sum()):4d} {auc:13.3f}  [{lo:.3f}, {hi:.3f}]")

json.dump(out, open("primevarclass_manuscript_analysis/per_cohort_flagship.json", "w",
                    encoding="utf-8"), indent=2, ensure_ascii=False)
print(">> wrote primevarclass_manuscript_analysis/per_cohort_flagship.json")
