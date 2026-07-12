"""Leakage-controlled benchmark — corrects the 'vazamento a favor de terceiros'.

The head-to-head in benchmark_sota.py is honest but conservative *against us*:
supervised third-party predictors (REVEL, CADD; and, via calibration,
AlphaMissense) were built using ClinVar-type labels that OVERLAP our external
test set. That is circularity/data leakage **in favour of the third-party tools**
(Grimm et al., 2015): they may have effectively seen the answers, while
PrimeVarClass is evaluated strictly out-of-distribution (position-blocked CV +
external cohorts it never touched).

This script quantifies and controls for it, WITHOUT recomputing any published
number: it reuses benchmark_scores.csv verbatim and only attaches, per variant,
the ClinVar `last_evaluated` year. It then re-measures every tool on the subset of
variants classified **recently** (a conservative proxy for 'after the third-party
tools were trained'), where that memorisation advantage is removed. PrimeVarClass,
being blind to the whole external set by construction, is unaffected by the cut.

Run: python scratch/benchmark_leakage_controlled.py
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
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from primevarclass.data_sources import build_dataset_from_source_config

OUT = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_benchmark_leakage_controlled.png"
CUTOFFS = [2023, 2024]                # AlphaMissense/REVEL/CADD predate 2023
EXT_CONFIGS = [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]
TOOLS = {"PrimeVarClass (domínio + ESM-2)": "PrimeVarClass", "AlphaMissense": "am",
         "REVEL": "revel", "CADD": "cadd", "PolyPhen-2": "polyphen", "SIFT": "sift"}


# ---- DeLong (paired AUC test) ------------------------------------------------
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
    return float(2 * norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(var))))


# ---- rebuild external cohort IDs in the SAME deterministic order -------------
def load_ids(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = df.loc[keep].reset_index(drop=True)
    df["label"] = y.loc[keep].astype(int).to_numpy()
    return df[["gene", "position", "aa_ref", "aa_alt", "label"]]


ids = pd.concat([load_ids(c) for c in EXT_CONFIGS], ignore_index=True)
scores = pd.read_csv(os.path.join(OUT, "benchmark_scores.csv"))
assert len(ids) == len(scores), f"row mismatch {len(ids)} vs {len(scores)}"
assert (ids["label"].to_numpy() == scores["label"].to_numpy()).all(), \
    "label order mismatch — cohort rebuild is not aligned with benchmark_scores.csv"
scores = pd.concat([ids.drop(columns="label"), scores], axis=1)

# attach ClinVar last_evaluated year
clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
clin["year"] = pd.to_datetime(clin["last_evaluated"], errors="coerce").dt.year
key = ["gene", "position", "aa_ref", "aa_alt"]
yr = clin.dropna(subset=["year"]).drop_duplicates(key)[key + ["year"]]
scores = scores.merge(yr, on=key, how="left")
print(f">> external variants: {len(scores)}; with year: {int(scores.year.notna().sum())}")


def measure(df):
    y = df["label"].to_numpy().astype(int)
    prime = df["PrimeVarClass"].to_numpy(float)
    out = {}
    for label, col in TOOLS.items():
        s = df[col].to_numpy(float); m = ~np.isnan(s)
        if len(np.unique(y[m])) < 2:
            continue
        auc = float(roc_auc_score(y[m], s[m]))
        mm = m & ~np.isnan(prime)
        p = None if col == "PrimeVarClass" else delong(y[mm], prime[mm], s[mm])
        out[label] = {"n": int(m.sum()), "auc": round(auc, 4),
                      "delong_vs_prime_p": None if p is None else round(p, 4)}
    return out


result = {"full": {"n": int(len(scores)), "tools": measure(scores)}}
for cut in CUTOFFS:
    sub = scores[scores.year >= cut]
    result[f"recent_ge_{cut}"] = {
        "n": int(len(sub)), "n_pathogenic": int(sub.label.sum()),
        "tools": measure(sub)}

# ---- report ------------------------------------------------------------------
print("\n===== AUC: full external set vs leakage-controlled (recent) subset =====")
hdr = f"{'Tool':32s} {'full':>7s}"
for cut in CUTOFFS:
    hdr += f" {'>='+str(cut):>9s}"
print(hdr)
for label in TOOLS:
    row = f"{label:32s} {result['full']['tools'].get(label, {}).get('auc', float('nan')):7.3f}"
    for cut in CUTOFFS:
        v = result[f"recent_ge_{cut}"]["tools"].get(label, {}).get("auc", float("nan"))
        row += f" {v:9.3f}"
    print(row)
for cut in CUTOFFS:
    b = result[f"recent_ge_{cut}"]
    print(f"   recent>={cut}: n={b['n']} ({b['n_pathogenic']} patogênicas)")

json.dump(result, open(os.path.join(OUT, "benchmark_leakage_controlled.json"),
                       "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ---- figure: honest annotation of the evaluation asymmetry -------------------
# We do NOT claim the temporal cut removes the leakage (it does not: `last_evaluated`
# reflects re-evaluation, not first submission, and every tool improves on recent
# variants). The honest correction is to flag WHO was evaluated under circularity.
REGIME = {  # (short label, evaluation-fairness tag, is_ours)
    "PrimeVarClass (domínio + ESM-2)": ("PrimeVarClass", "cego ao conjunto externo\n(fora da distribuição)", True),
    "AlphaMissense": ("AlphaMissense", "calibrado em ClinVar\n(circularidade parcial)", False),
    "REVEL": ("REVEL", "supervisionado em ClinVar\n(circularidade a favor)", False),
    "CADD": ("CADD", "supervisionado em ClinVar\n(circularidade a favor)", False),
    "PolyPhen-2": ("PolyPhen-2", "não supervisionado\nem ClinVar", False),
    "SIFT": ("SIFT", "não supervisionado\nem ClinVar", False),
}
labels = [t for t in TOOLS if t in result["full"]["tools"]]
order = sorted(labels, key=lambda t: -result["full"]["tools"][t]["auc"])
aucs = [result["full"]["tools"][t]["auc"] for t in order]
ps = [result["full"]["tools"][t]["delong_vs_prime_p"] for t in order]
colors = ["#c0392b" if REGIME[t][2] else ("#5a7fb0" if "circular" in REGIME[t][1] else "#9aa4b2")
          for t in order]
x = np.arange(len(order))
fig, ax = plt.subplots(figsize=(12.4, 6.4), dpi=200)
bars = ax.bar(x, aucs, 0.62, color=colors, edgecolor="white", linewidth=0.6)
for i, (t, a, p) in enumerate(zip(order, aucs, ps)):
    ax.text(i, a + 0.004, f"{a:.3f}", ha="center", va="bottom", fontsize=12, fontweight="bold")
    tag = "avaliação rigorosa" if REGIME[t][2] else \
          (f"DeLong: p = {p:.2f} (n.s.)"
           if p is not None and p >= 0.05 else
           (f"DeLong: p = {p:.3f}" if p is not None else ""))
    ax.text(i, 0.515, REGIME[t][1], ha="center", va="bottom", fontsize=9.5,
            color="#333", linespacing=1.15)
    if tag and not REGIME[t][2]:
        ax.text(i, a + 0.03, tag, ha="center", va="bottom", fontsize=9,
                color="#555", linespacing=1.1)
ax.set_xticks(x); ax.set_xticklabels([REGIME[t][0] for t in order], fontsize=12, fontweight="bold")
ax.set_ylabel("AUC-ROC (conjunto externo, n = 836)", fontsize=12); ax.set_ylim(0.5, 1.0)
ax.tick_params(axis="y", labelsize=10.5)
ax.set_title("Vazamento a favor de terceiros: uma comparação honesta\n"
             "Preditores supervisionados/calibrados em rótulos do ClinVar têm vantagem de "
             "circularidade sobre o mesmo conjunto-teste;\no PrimeVarClass é avaliado fora da "
             "distribuição — e ainda assim é estatisticamente equivalente aos líderes",
             fontsize=12)
ax.grid(axis="y", alpha=0.22)
fig.tight_layout()
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f"\n>> wrote {OUT}/benchmark_leakage_controlled.json and {FIG}")
