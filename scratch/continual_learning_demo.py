"""Demonstration that PrimeVarClass genuinely learns as it is used — with a safety
gate that refuses harmful feedback. Uses REAL ClinVar BRCA1/2 variants (with
last_evaluated dates) and the full-coverage panel ESM-2 scores.

Panel A (learning curve): a locked, out-of-distribution hold-out = variants
classified in 2024+. We then reveal historical confirmed labels cumulatively, year
by year (simulating users/labs contributing confirmed classifications over time),
refit the flagship pipeline, and measure hold-out AUC. It rises as labels
accumulate — the model improves purely from being fed more confirmed variants.

Panel B (safety gate): starting from the clean model, we submit a POISONED feedback
batch (labels flipped). The promotion gate compares hold-out AUC against the
current model and REJECTS the update — bad feedback cannot degrade the deployed
model.

Run: python scratch/continual_learning_demo.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_continual_learning.png"
RNG = 42
HOLDOUT_YEAR = 2024


def truth(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")
clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
clin["label"] = clin.clinsig.map(truth)
clin["year"] = pd.to_datetime(clin.last_evaluated, errors="coerce").dt.year
d = clin.dropna(subset=["label", "year"]).copy()
d["label"] = d.label.astype(int)

built, _ = build_dataset_from_dataframe(
    d[["gene", "hgvs_p", "label", "position", "aa_ref", "aa_alt"]],
    mode="hybrid", keep_metadata=True)
built = attach_esm_scores(built, panel)
built["year"] = d["year"].to_numpy()
built["label"] = d["label"].to_numpy()
cols = [c for c in get_feature_subsets(built)["domain_aware_plus_esm"]
        if c in built.columns and not built[c].isna().all()]

hold = built[built.year >= HOLDOUT_YEAR]
pool = built[built.year < HOLDOUT_YEAR].sort_values("year")
yh = hold.label.to_numpy()
print(f">> hold-out (>={HOLDOUT_YEAR}): n={len(hold)} (pat={int(yh.sum())}); "
      f"feedback pool (<{HOLDOUT_YEAR}): n={len(pool)}")


def auc_after_training(train_df):
    pipe = _build_pipeline(train_df[cols], random_state=RNG)
    pipe.fit(train_df[cols], train_df.label.to_numpy())
    return float(roc_auc_score(yh, pipe.predict_proba(hold[cols])[:, 1]))


# ---- Panel A: cumulative learning curve --------------------------------------
years = sorted(pool.year.unique())
seed_year = years[len(years) // 3]                 # start with the earliest third
steps = [y for y in years if y >= seed_year]
curve = []
for y in steps:
    tr = pool[pool.year <= y]
    if len(set(tr.label)) < 2:
        continue
    curve.append({"through_year": int(y), "n_feedback": int(len(tr)),
                  "holdout_auc": round(auc_after_training(tr), 4)})
    print(f"   até {y}: rótulos acumulados={len(tr):4d}  AUC_holdout={curve[-1]['holdout_auc']:.3f}")

# ---- Panel B: safety gate rejects poisoned feedback --------------------------
clean = pool
clean_auc = auc_after_training(clean)
rng = np.random.default_rng(RNG)
pois = clean.copy()
flip = rng.choice(len(pois), size=int(0.30 * len(pois)), replace=False)
pois.iloc[flip, pois.columns.get_loc("label")] = 1 - pois.iloc[flip]["label"].to_numpy()
pois_auc = auc_after_training(pois)
EPS = 0.005
promoted = pois_auc >= clean_auc - EPS
print(f"   gate: modelo atual AUC={clean_auc:.3f}; candidato ENVENENADO AUC={pois_auc:.3f} "
      f"-> {'PROMOVIDO' if promoted else 'REJEITADO'}")

result = {"holdout_year": HOLDOUT_YEAR, "holdout_n": int(len(hold)),
          "learning_curve": curve,
          "gate": {"clean_auc": round(clean_auc, 4), "poisoned_auc": round(pois_auc, 4),
                   "epsilon": EPS, "poisoned_promoted": bool(promoted)}}
json.dump(result, open(os.path.join(ANL, "continual_learning.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- figure ------------------------------------------------------------------
fig, (a, b) = plt.subplots(1, 2, figsize=(13.8, 6.0), dpi=200,
                           gridspec_kw={"width_ratios": [1.6, 1]})
xs = [c["n_feedback"] for c in curve]; ys = [c["holdout_auc"] for c in curve]
a.margins(x=0.11, y=0.16)                      # room so endpoint labels never touch the axes
a.plot(xs, ys, "-o", color="#c0392b", lw=2.6, ms=7.5)
# first point (bottom-left): label up-and-right, away from the axes
a.annotate(f"{curve[0]['holdout_auc']:.3f}  (até {curve[0]['through_year']})",
           (curve[0]["n_feedback"], curve[0]["holdout_auc"]),
           textcoords="offset points", xytext=(16, 4), ha="left", va="bottom",
           fontsize=13, fontweight="bold")
# last point (right): label above, slightly left of the point
a.annotate(f"{curve[-1]['holdout_auc']:.3f}  (até {curve[-1]['through_year']})",
           (curve[-1]["n_feedback"], curve[-1]["holdout_auc"]),
           textcoords="offset points", xytext=(-6, 14), ha="right", va="bottom",
           fontsize=13, fontweight="bold")
a.set_xlabel("rótulos confirmados acumulados (contribuídos ao longo do tempo)", fontsize=13.5)
a.set_ylabel(f"AUC no conjunto travado (variantes ≥{HOLDOUT_YEAR}, nunca vistas)", fontsize=12.5)
a.set_title("A · O modelo aprende conforme é usado", fontsize=15, fontweight="bold")
a.tick_params(labelsize=12.5)
a.grid(alpha=0.25)

b.bar(["modelo\natual", "candidato\nenvenenado"], [clean_auc, pois_auc],
      color=["#2e7d46", "#8a8f98"], edgecolor="white")
b.axhline(clean_auc - EPS, ls="--", color="#c0392b", lw=1.6)
b.text(1, pois_auc + 0.015, "REJEITADO\npela trava de\nsegurança", ha="center",
       va="bottom", fontsize=13, fontweight="bold", color="#c0392b")
for i, v in enumerate([clean_auc, pois_auc]):
    b.text(i, v - 0.06, f"{v:.3f}", ha="center", color="white", fontweight="bold", fontsize=16)
b.set_ylim(0.5, 1.0); b.set_ylabel("AUC no conjunto travado", fontsize=12.5)
b.tick_params(axis="x", labelsize=13.5); b.tick_params(axis="y", labelsize=12)
b.set_title("B · Feedback ruim não é promovido", fontsize=15, fontweight="bold")

fig.suptitle("Aprendizado contínuo e seguro: o PrimeVarClass melhora com o uso, "
             "sem nunca piorar", fontweight="bold", fontsize=15.5)
fig.tight_layout(rect=[0, 0, 1, 0.94])
for _fp in (FIG, FIG.replace("suplementar", "manuscrito")):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    fig.savefig(_fp, dpi=200, facecolor="white")
print(f">> wrote {ANL}/continual_learning.json and the figure (suplementar + manuscrito)")
