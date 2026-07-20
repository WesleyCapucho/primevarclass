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

# ---- figura (antes era um PNG orfao, sem script que o gerasse) ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

anos = sorted(res, key=int)
aucs = [res[a]["future_auc"] for a in anos]
ns = [res[a]["n_test_future"] for a in anos]
fig, ax = plt.subplots(figsize=(10.6, 6.0), dpi=200)
ax.plot([int(a) for a in anos], aucs, "-o", color="#c0392b", lw=2.6, ms=9)
for a, v, n in zip(anos, aucs, ns):
    ax.annotate(f"{v:.3f}".replace(".", ","), (int(a), v), textcoords="offset points",
                xytext=(0, 12), ha="center", fontsize=14, fontweight="bold")
    ax.annotate(f"n={n}", (int(a), v), textcoords="offset points",
                xytext=(0, -20), ha="center", fontsize=15, color="#555555")
ax.set_xlabel("ano de corte (treino usa apenas o que era definitivo até ali)", fontsize=13.5)
ax.set_ylabel("AUC nas variantes classificadas depois do corte", fontsize=13.5)
ax.set_title("Validação temporal: treinado só com o passado, testado no futuro",
             fontsize=15.5, fontweight="bold")
ax.set_xticks([int(a) for a in anos])
ax.tick_params(labelsize=12.5)
ax.margins(x=0.10, y=0.20)
ax.grid(alpha=0.25)
fig.tight_layout()
for _fp in ("docs/suplementar/figuras/fig_temporal_validation.png",
            "docs/manuscrito/figuras/fig_temporal_validation.png",
            "docs/galeria_resultados/figuras/fig_temporal_validation.png"):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    fig.savefig(_fp, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/temporal_validation.json and fig_temporal_validation.png (3 pastas)")
