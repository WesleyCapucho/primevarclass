"""Orthogonal validation: do PrimeVarClass scores track EXPERIMENTAL molecular
function? We correlate our predictions with deep-mutational-scanning (DMS)
functional scores for BRCA1 — the saturation genome-editing assay of Findlay
et al. (2018, Nature) and the HDR assay of Starita et al. (2015) — from MaveDB.

This validation uses NO clinical labels: it asks whether the model ranks
variants by real loss of function measured in the lab, the same gold standard
used to benchmark AlphaMissense. Metrics: Spearman correlation (threshold-free)
and AUC for classifying loss-of-function (LOF vs functional), with the LOF
boundary set objectively by a 2-component Gaussian mixture on the assay scores.

Run: python scratch/functional_validation.py
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
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.mixture import GaussianMixture

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

OUT = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_functional_validation.png"
os.makedirs(OUT, exist_ok=True)
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
# full-coverage panel scores (identical LLRs to the clinical set on the overlap,
# r=1.00) — needed to cover the DMS-assayed positions
_panel = "scratch/esm_input/esm2_scores_panel.csv"
esm_df = pd.read_csv(_panel if os.path.exists(_panel) else "scratch/esm_input/esm2_scores.csv")

ASSAYS = {
    "Findlay 2018 — SGE BRCA1 (função)": ("urn:mavedb:00001222-b-2", "BRCA1"),
    "Starita 2015 — HDR BRCA1": ("urn:mavedb:00000081-a-2", "BRCA1"),
    "HDR BRCA2 (VC-8)": ("urn:mavedb:00001224-a-1", "BRCA2"),
}
# in every assay a LOWER score = loss of function (deleterious)

import re
MISS = re.compile(r"^p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$")
BRCA1_SEQ = open("scratch/esm_input/BRCA1_P38398.txt").read().strip()
BRCA2_SEQ = open("scratch/esm_input/BRCA2_P51587.txt").read().strip()
SEQS = {"BRCA1": BRCA1_SEQ, "BRCA2": BRCA2_SEQ}


def parse_hgvs(h):
    m = MISS.match(str(h))
    if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
        return None
    return AA3TO1[m.group(1)], int(m.group(2)), AA3TO1[m.group(3)]


def best_offset(aa_refs, positions, seq):
    """Find the integer offset that aligns MaveDB target-local numbering to the
    canonical BRCA1 protein (Findlay's SGE records are numbered within the assayed
    region; Starita uses canonical numbering -> offset 0). Returns the offset with
    the highest reference-AA agreement."""
    ref_at = {}
    for r, p in zip(aa_refs, positions):
        ref_at.setdefault(int(p), r)
    items = list(ref_at.items())
    best_k, best_frac = 0, 0.0
    for k in range(-3, len(seq)):
        tot = match = 0
        for p, r in items:
            j = p + k - 1
            if 0 <= j < len(seq):
                tot += 1
                match += (seq[j] == r)
        if tot >= 50 and match / tot > best_frac:
            best_frac, best_k = match / tot, k
    return best_k if best_frac > 0.9 else 0


# ---- train the flagship model on the internal cohort -----------------------
tr, _, _ = build_dataset_from_source_config("configs/public_brca_real.toml", mode="hybrid", keep_metadata=True)
ytr = pd.to_numeric(tr["label"], errors="coerce")
keep = ytr.notna()
tr = attach_esm_scores(tr.loc[keep].reset_index(drop=True), esm_df)
ytr = ytr.loc[keep].astype(int).to_numpy()
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all()]
pipe = _build_pipeline(tr[cols], random_state=42)
pipe.fit(tr[cols], ytr)


def score_variants(df, gene):
    q = df.copy()
    q["gene"] = gene
    q["label"] = 0
    qb, _ = build_dataset_from_dataframe(q[["gene", "hgvs_p", "label", "position", "aa_ref", "aa_alt"]],
                                         mode="hybrid", keep_metadata=True)
    qb = attach_esm_scores(qb, esm_df)
    for c in cols:
        if c not in qb.columns:
            qb[c] = pd.NA
    prob = pipe.predict_proba(qb[cols])[:, 1]
    return prob, qb["esm2_llr"].to_numpy()


dms = pd.read_csv("data/raw/mavedb/brca_function_scores.csv")

results = {}
fig, axes = plt.subplots(1, len(ASSAYS), figsize=(4.6 * len(ASSAYS), 4.4), dpi=200)
for ax, (name, (urn, gene)) in zip(axes, ASSAYS.items()):
    seq = SEQS[gene]
    a = dms[dms.score_set_urn == urn].copy()
    parsed = a["hgvs_p"].map(parse_hgvs)
    a = a[parsed.notna()].copy()
    a[["aa_ref", "position", "aa_alt"]] = pd.DataFrame(parsed[parsed.notna()].tolist(), index=a.index)
    a = a.dropna(subset=["score"]).drop_duplicates(["position", "aa_ref", "aa_alt"])
    # align target-local numbering to the canonical protein, then keep only
    # variants whose reference AA matches the sequence (drops residual noise)
    off = best_offset(a["aa_ref"].tolist(), a["position"].tolist(), seq)
    a["position"] = a["position"] + off
    keep_pos = [0 <= p - 1 < len(seq) and seq[p - 1] == r
                for p, r in zip(a["position"], a["aa_ref"])]
    a = a[keep_pos].copy()
    a["hgvs_p"] = ["p." + r + str(p) + al for r, p, al in zip(a.aa_ref, a.position, a.aa_alt)]
    print(f"   [{name}] gene={gene} offset={off:+d}  aligned n={len(a)}")
    prob, esm = score_variants(a, gene)
    a["prob"], a["esm"] = prob, esm

    fscore = a["score"].to_numpy()
    # Spearman: pathogenicity prob should be NEGATIVELY correlated with function
    rho_prob = spearmanr(a["prob"], fscore).correlation
    ok = ~np.isnan(a["esm"].to_numpy())
    rho_esm = spearmanr(a["esm"].to_numpy()[ok], fscore[ok]).correlation

    # objective LOF boundary via 2-component GMM on the (bimodal) function scores
    gm = GaussianMixture(2, random_state=0).fit(fscore.reshape(-1, 1))
    lof_comp = int(np.argmin(gm.means_.ravel()))
    lof = (gm.predict(fscore.reshape(-1, 1)) == lof_comp).astype(int)
    auc_prob = roc_auc_score(lof, a["prob"]) if lof.sum() and (1 - lof).sum() else np.nan
    auc_esm = roc_auc_score(lof[ok], -a["esm"].to_numpy()[ok]) if ok.sum() else np.nan

    results[name] = {"urn": urn, "n": int(len(a)), "n_esm_covered": int(ok.sum()),
                     "spearman_prob_vs_function": round(float(rho_prob), 3),
                     "spearman_esm_vs_function": round(float(rho_esm), 3),
                     "auc_prob_vs_LOF": round(float(auc_prob), 3),
                     "auc_esm_vs_LOF": round(float(auc_esm), 3),
                     "n_LOF": int(lof.sum())}
    ax.scatter(a["prob"], fscore, s=6, alpha=0.35, c="#c0392b", edgecolors="none")
    ax.set_title(f"{name}\nn={len(a)}  ρ={rho_prob:.2f}  AUC={auc_prob:.2f}", fontsize=9.5)
    ax.set_xlabel("Prob. patogenicidade (modelo)", fontsize=9)
    ax.set_ylabel("Escore funcional experimental", fontsize=9)
    ax.grid(alpha=0.2)

fig.suptitle("Validação funcional ortogonal — predições vs. função medida em laboratório (DMS de BRCA1)",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
json.dump(results, open(os.path.join(OUT, "functional_validation.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)

print(">> Orthogonal functional validation (BRCA1 DMS):")
for k, v in results.items():
    print(f"   {k:34s} n={v['n']:4d} (ESM {v['n_esm_covered']:4d})  "
          f"ρ_prob={v['spearman_prob_vs_function']:+.2f}  AUC_prob={v['auc_prob_vs_LOF']:.3f}  "
          f"ρ_esm={v['spearman_esm_vs_function']:+.2f}")
print(f">> wrote {OUT}/functional_validation.json and {FIG}")
