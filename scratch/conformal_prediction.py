"""Exp #5 — Per-variant uncertainty via split-conformal prediction (Mondrian /
class-conditional, to respect the class imbalance). Turns the flagship model into
a clinically safer tool: for a chosen error budget ε, each variant gets a
prediction SET — a confident singleton call {patogênica} or {benigna}, or an
'abstenção' {ambas} when the evidence is insufficient — with a guaranteed
per-class error rate of ~ε.

Split-conformal (Vovk): fit on a proper-train split, calibrate nonconformity on a
held-out calibration split, then form prediction sets on the untouched external
cohorts. Coverage is validated empirically.

Run: python scratch/conformal_prediction.py
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
from sklearn.model_selection import train_test_split

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

RNG = 42
ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_conformal.png"
esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
    df["label"] = y.loc[keep].astype(int).to_numpy()
    return df


tr = load("configs/public_brca_real.toml")
ext = pd.concat([load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]], ignore_index=True)
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all() and c in ext.columns]

# proper-train / calibration split (stratified)
Xtr, Xcal, ytr, ycal = train_test_split(
    tr[cols], tr["label"].to_numpy(), test_size=0.35, random_state=RNG,
    stratify=tr["label"].to_numpy())
pipe = _build_pipeline(Xtr, random_state=RNG); pipe.fit(Xtr, ytr)

p_cal = pipe.predict_proba(Xcal)              # [:,0]=benign, [:,1]=pathogenic
p_ext = pipe.predict_proba(ext[cols])
yext = ext["label"].to_numpy()


def mondrian_thresholds(eps):
    """Per-class nonconformity quantile q_c = 1 - p_hat(true class)."""
    q = {}
    for c in (0, 1):
        s = 1.0 - p_cal[ycal == c, c]         # nonconformity of calibration pts of class c
        n = len(s)
        k = int(np.ceil((n + 1) * (1 - eps)))
        k = min(max(k, 1), n)
        q[c] = np.sort(s)[k - 1]
    return q


def evaluate(eps):
    q = mondrian_thresholds(eps)
    # prediction set: include class c if 1 - p_hat(c) <= q_c
    inc0 = (1.0 - p_ext[:, 0]) <= q[0]
    inc1 = (1.0 - p_ext[:, 1]) <= q[1]
    setsize = inc0.astype(int) + inc1.astype(int)
    covered = ((yext == 0) & inc0) | ((yext == 1) & inc1)
    singleton = setsize == 1
    # confident singleton correctness
    pred_single = np.where(inc1 & ~inc0, 1, np.where(inc0 & ~inc1, 0, -1))
    single_mask = pred_single != -1
    single_acc = float((pred_single[single_mask] == yext[single_mask]).mean()) if single_mask.any() else float("nan")
    return {
        "epsilon": eps, "target_coverage": round(1 - eps, 3),
        "empirical_coverage": round(float(covered.mean()), 3),
        "confident_singleton_rate": round(float(singleton.mean()), 3),
        "abstention_rate": round(float((setsize == 2).mean()), 3),
        "empty_rate": round(float((setsize == 0).mean()), 3),
        "singleton_accuracy": round(single_acc, 3),
    }


rows = [evaluate(e) for e in (0.20, 0.15, 0.10, 0.05)]
print(f"{'ε':>5} {'alvo':>6} {'cobertura':>10} {'call único':>11} {'abstenção':>10} {'acurácia único':>15}")
for r in rows:
    print(f"{r['epsilon']:5.2f} {r['target_coverage']:6.2f} {r['empirical_coverage']:10.3f} "
          f"{r['confident_singleton_rate']:11.3f} {r['abstention_rate']:10.3f} {r['singleton_accuracy']:15.3f}")
json.dump({"n_external": int(len(yext)), "results": rows},
          open(os.path.join(ANL, "conformal.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- figure: coverage guarantee + call/abstain trade-off --------------------
eps = [r["epsilon"] for r in rows]
cov = [r["empirical_coverage"] for r in rows]
tgt = [r["target_coverage"] for r in rows]
call = [r["confident_singleton_rate"] for r in rows]
abst = [r["abstention_rate"] for r in rows]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 5.0), dpi=200)
a1.plot(tgt, cov, "-o", color="#2e7d46", lw=2.4, ms=7, label="cobertura empírica")
a1.plot([0.75, 0.96], [0.75, 0.96], "--", color="#888", label="cobertura-alvo (ideal)")
a1.set_xlabel("cobertura-alvo (1 − ε)"); a1.set_ylabel("cobertura empírica no conjunto externo")
a1.set_title("A · A garantia de cobertura se cumpre", fontweight="bold", fontsize=14.3)
a1.legend(fontsize=12); a1.grid(alpha=0.25)
x = np.arange(len(eps)); w = 0.38
a2.bar(x - w/2, call, w, color="#2e6fb0", label="chamada confiante (call único)")
a2.bar(x + w/2, abst, w, color="#c8ccd0", label="abstenção (zona incerta)")
a2.set_xticks(x); a2.set_xticklabels([f"{1-e:.0%}" for e in eps])
a2.set_xlabel("confiança exigida (1 − ε)"); a2.set_ylabel("fração das variantes externas")
a2.set_title("B · Quanto mais confiança, mais o modelo se abstém", fontweight="bold", fontsize=14.3)
a2.legend(fontsize=12); a2.grid(axis="y", alpha=0.25)
fig.suptitle("Predição conformal: incerteza calibrada e abstenção segura por variante",
             fontweight="bold", fontsize=12.5)
fig.tight_layout(rect=[0, 0, 1, 0.95])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/conformal.json and {FIG}")
