"""Temporal (quasi-prospective) validation: using only variants CLASSIFIED up to
a cut-off year, how well does the model classify variants that were only resolved
AFTER that year? This is the strongest evidence short of a wet-lab study — it
mimics deploying the tool in the past and checking it against the future.

Uses the live ClinVar BRCA1/2 set (with last_evaluated dates) + the full-coverage
panel ESM-2 scores. The flagship Random Forest is retrained on the pre-cut-off
variants only; the label-free ESM-2 + domain features carry most of the signal.

Run: python scratch/temporal_validation.py
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

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")
clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")


def truth(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


clin["label"] = clin.clinsig.map(truth)
clin["year"] = pd.to_datetime(clin.last_evaluated, errors="coerce").dt.year
d = clin.dropna(subset=["label", "year"]).copy()
d["label"] = d.label.astype(int)
d["hgvs_p2"] = d.hgvs_p

built, _ = build_dataset_from_dataframe(
    d[["gene", "hgvs_p", "label", "position", "aa_ref", "aa_alt"]].assign(hgvs_p=d.hgvs_p),
    mode="hybrid", keep_metadata=True)
built = attach_esm_scores(built, panel)
built["year"] = d["year"].to_numpy()
built["label"] = d["label"].to_numpy()
cols = [c for c in get_feature_subsets(built)["domain_aware_plus_esm"]
        if c in built.columns and not built[c].isna().all()]

print(f">> classified BRCA1/2 with dates: {len(built)} "
      f"(pathogenic={int(built.label.sum())}, benign={int((1-built.label).sum())})")
print("   by year (cumulative):")
res = {}
for T in [2016, 2018, 2019, 2020, 2021]:
    tr = built[built.year <= T]
    te = built[built.year > T]
    if len(set(tr.label)) < 2 or len(set(te.label)) < 2 or len(te) < 20:
        continue
    pipe = _build_pipeline(tr[cols], random_state=42)
    pipe.fit(tr[cols], tr.label.to_numpy())
    auc = roc_auc_score(te.label.to_numpy(), pipe.predict_proba(te[cols])[:, 1])
    res[str(T)] = {"n_train": int(len(tr)), "n_test_future": int(len(te)),
                   "test_pathogenic": int(te.label.sum()), "future_auc": round(float(auc), 3)}
    print(f"   corte {T}: treino={len(tr):4d}  futuro={len(te):4d} "
          f"(pat={int(te.label.sum())})  AUC_futuro={auc:.3f}")

json.dump(res, open(os.path.join(ANL, "temporal_validation.json"), "w"), indent=2, ensure_ascii=False)
print(f">> wrote {ANL}/temporal_validation.json")
