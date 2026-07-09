"""Calibrate the flagship (domain + ESM-2) score to ACMG/AMP evidence strength
(PP3/BP4), following the local-likelihood-ratio framework of Tavtigian et al.
(2018) and Pejaver et al. (2022), which the ClinGen SVI recommends for
computational predictors.

Method (honest, out-of-sample):
  1. Score every internal-cohort variant with position-blocked cross-validation
     (StratifiedGroupKFold) so the calibration never sees a variant's own fold.
  2. For a grid of score cut-offs, compute the *local* likelihood ratio of the
     "score >= t" (pathogenic) and "score <= t" (benign) evidence and find the
     least-stringent cut-off that reaches each ACMG strength
     (supporting/moderate/strong).
  3. Validate that the internally-derived thresholds transfer to the independent
     external cohort (evidence direction and yield).

Outputs: primevarclass_manuscript_analysis/acmg_calibration.json + .csv and
docs/manuscrito/figuras/fig_acmg_calibration.png

Run: python scratch/acmg_calibration.py
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
from sklearn.model_selection import StratifiedGroupKFold

from primevarclass.core import (
    ACMG_BENIGN_LR_THRESHOLDS,
    ACMG_PATHOGENIC_LR_THRESHOLDS,
    _build_pipeline,
    compute_local_lr,
    get_feature_subsets,
)
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

RNG = 42
OUT = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_acmg_calibration.png"
os.makedirs(OUT, exist_ok=True)
esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
    return df, y.loc[keep].astype(int).to_numpy()


tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])

cols = [c for c in get_feature_subsets(tr_df)["domain_aware_plus_esm"]
        if c in tr_df.columns and c in ext_df.columns and not tr_df[c].isna().all()]
groups = (tr_df["gene"].astype(str) + ":" + tr_df["position"].astype(str)).to_numpy()

# position-blocked out-of-sample scores on the internal cohort
oof = np.zeros(len(ytr))
for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=RNG).split(tr_df[cols], ytr, groups):
    p = _build_pipeline(tr_df[cols].iloc[a], random_state=RNG)
    p.fit(tr_df[cols].iloc[a], ytr[a])
    oof[b] = p.predict_proba(tr_df[cols].iloc[b])[:, 1]

# external scores from a model trained on the full internal cohort
full = _build_pipeline(tr_df[cols], random_state=RNG)
full.fit(tr_df[cols], ytr)
ext_score = full.predict_proba(ext_df[cols])[:, 1]

P, N = int(ytr.sum()), int((1 - ytr).sum())


def path_lr(t):
    tp = int(((oof >= t) & (ytr == 1)).sum())
    fp = int(((oof >= t) & (ytr == 0)).sum())
    return compute_local_lr(tp, fp, P - tp, N - fp), tp, fp


def benign_lr(t):
    # benign evidence: treat "score <= t" with benign as the positive class
    tp = int(((oof <= t) & (ytr == 0)).sum())
    fp = int(((oof <= t) & (ytr == 1)).sum())
    return compute_local_lr(tp, fp, N - tp, P - fp), tp, fp


grid = np.round(np.linspace(0.01, 0.99, 197), 4)
path_thr, ben_thr = {}, {}
for level, lr_min in ACMG_PATHOGENIC_LR_THRESHOLDS.items():
    hits = [t for t in grid if (path_lr(t)[0] or 0) >= lr_min and path_lr(t)[1] >= 3]
    path_thr[level] = float(min(hits)) if hits else None   # least-stringent score reaching this strength
for level, lr_max in ACMG_BENIGN_LR_THRESHOLDS.items():
    inv = 1.0 / lr_max  # benign LR expressed on the same (>=1) scale
    hits = [t for t in grid if (benign_lr(t)[0] or 0) >= inv and benign_lr(t)[1] >= 3]
    ben_thr[level] = float(max(hits)) if hits else None


def assign(score):
    for lvl in ("strong", "moderate", "supporting"):
        t = path_thr.get(lvl)
        if t is not None and score >= t:
            return f"PP3_{lvl}"
    for lvl in ("strong", "moderate", "supporting"):
        t = ben_thr.get(lvl)
        if t is not None and score <= t:
            return f"BP4_{lvl}"
    return "uninformative"


ext_assign = np.array([assign(s) for s in ext_score])
Pe, Ne = int(yext.sum()), int((1 - yext).sum())
summary = {}
for lvl in ["PP3_strong", "PP3_moderate", "PP3_supporting", "uninformative",
            "BP4_supporting", "BP4_moderate", "BP4_strong"]:
    m = ext_assign == lvl
    if not m.sum():
        continue
    tp = int(yext[m].sum()); fp = int((1 - yext[m]).sum())
    # prevalence-independent local LR of this band on the EXTERNAL cohort
    p_band_path = tp / Pe if Pe else np.nan
    p_band_ben = fp / Ne if Ne else np.nan
    ext_lr = (p_band_path / p_band_ben) if p_band_ben else np.inf
    summary[lvl] = {"n_external": int(m.sum()),
                    "path_fraction": round(float(yext[m].mean()), 3),
                    "external_local_lr": round(float(ext_lr), 2)}

result = {
    "prior": 0.10,
    "lr_thresholds": {"pathogenic": ACMG_PATHOGENIC_LR_THRESHOLDS,
                      "benign": ACMG_BENIGN_LR_THRESHOLDS},
    "score_thresholds": {"pathogenic": path_thr, "benign": ben_thr},
    "external_validation": summary,
    "n_internal": int(len(ytr)), "n_external": int(len(yext)),
}
json.dump(result, open(os.path.join(OUT, "acmg_calibration.json"), "w"), indent=2, ensure_ascii=False)

# audit table: LR curve across the grid
tbl = pd.DataFrame({"score_cutoff": grid,
                    "path_local_lr": [path_lr(t)[0] for t in grid],
                    "benign_local_lr": [benign_lr(t)[0] for t in grid]})
tbl.to_csv(os.path.join(OUT, "acmg_calibration.csv"), index=False)

# figure: score -> pathogenic local LR with ACMG evidence bands
fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=200)
ax.plot(grid, [path_lr(t)[0] for t in grid], color="#c0392b", lw=2.2, label="LR+ (patogênico) para escore ≥ t")
for lvl, lr in ACMG_PATHOGENIC_LR_THRESHOLDS.items():
    ax.axhline(lr, ls="--", color="#888", lw=1)
    ax.text(0.012, lr * 1.03, f"PP3 {lvl} (LR≥{lr})", fontsize=8, color="#555")
    t = path_thr.get(lvl)
    if t is not None:
        ax.axvline(t, ls=":", color="#c0392b", lw=1)
ax.set_yscale("log")
ax.set_xlabel("Escore do modelo-carro-chefe (probabilidade)", fontsize=11)
ax.set_ylabel("Razão de verossimilhança local (LR+)", fontsize=11)
ax.set_title("Calibração ACMG/AMP do escore para força de evidência (PP3)", fontsize=12, fontweight="bold")
ax.legend(loc="upper left", fontsize=9)
ax.grid(alpha=0.25, which="both")
fig.tight_layout()
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")

print(">> ACMG score thresholds (pathogenic):", {k: round(v, 3) if v else None for k, v in path_thr.items()})
print(">> ACMG score thresholds (benign)    :", {k: round(v, 3) if v else None for k, v in ben_thr.items()})
print(">> external validation by evidence level (LR = prevalence-independent):")
for k, v in summary.items():
    print(f"     {k:16s} n={v['n_external']:3d}  fração patogênica={v['path_fraction']}  LR_externo={v['external_local_lr']}")
print(f">> wrote {OUT}/acmg_calibration.json, .csv and {FIG}")
