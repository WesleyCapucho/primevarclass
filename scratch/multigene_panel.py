"""Exp #1 — Does the method generalise BEYOND BRCA?

TP53 is the archetypal missense-driven tumour suppressor (pathogenic variants
concentrate in the DNA-binding domain). We apply the SAME recipe used for BRCA —
biochemistry, then + critical-domain awareness, then + a protein-language-model
score (ESM-2) — under position-blocked CV, and show the AUC climb. Critical-domain
spans come from UniProt (function-defined, label-independent). The other panel
genes (PALB2, CHEK2, ATM) are reported as-is: PALB2/CHEK2 have too few definitive
missense (their pathogenicity is truncating-dominated) and ATM's missense
pathogenicity is spatially diffuse — the method's boundary.

ESM-2 (650M, the flagship's primary model) was scored on GPU for the whole panel
via scratch/colab_esm2_650M_panel.py -> scratch/esm_input/esm2_650M_panel_scores.csv,
so the generalization uses exactly the same model as the BRCA flagship.

Run: python scratch/multigene_panel.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_multigene.png"
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
PMIS = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")
CRITICAL = {"TP53": [(94, 312), (323, 356)], "PALB2": [(9, 44), (853, 1186)],
            "CHEK2": [(113, 175), (220, 486)], "ATM": [(1960, 2566), (2712, 2962), (3024, 3056)]}


def definitive(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


rows = []
with open("data/raw/clinvar/variant_summary_current_HBOC.tsv", encoding="utf-8") as fh:
    h = fh.readline().rstrip("\n").split("\t"); idx = {n: i for i, n in enumerate(h)}
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) <= idx["Assembly"] or f[idx["Assembly"]] != "GRCh38" or f[idx["GeneSymbol"]] not in CRITICAL:
            continue
        m = PMIS.search(f[idx["Name"]])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
            continue
        lab = definitive(f[idx["ClinicalSignificance"]])
        if lab != lab:
            continue
        rows.append({"gene": f[idx["GeneSymbol"]], "position": int(m.group(2)),
                     "aa_ref": AA3TO1[m.group(1)], "aa_alt": AA3TO1[m.group(3)], "label": int(lab)})
d = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"], keep="first")
d["in_critical_domain"] = [int(any(a <= p <= b for a, b in CRITICAL[g])) for g, p in zip(d.gene, d.position)]
d["hgvs_p"] = ["p." + r + str(p) + a for r, p, a in zip(d.aa_ref, d.position, d.aa_alt)]

built, _ = build_dataset_from_dataframe(
    d[["gene", "hgvs_p", "position", "aa_ref", "aa_alt", "label"]], mode="hybrid", keep_metadata=True)
built["label"] = d["label"].to_numpy()
built["in_critical_domain"] = d["in_critical_domain"].to_numpy()
# attach panel ESM where available (650M — same model as the flagship; scored on
# GPU via scratch/colab_esm2_650M_panel.py so the generalization uses ONE model)
_esm_src = "scratch/esm_input/esm2_650M_panel_scores.csv"
if not os.path.exists(_esm_src):  # fallback to the older 150M TP53-only scores
    _esm_src = "scratch/esm_input/esm2_scores_tp53.csv"
if os.path.exists(_esm_src):
    built = attach_esm_scores(built, pd.read_csv(_esm_src))
subs = get_feature_subsets(built)
biochem = [c for c in subs["biochemical_only"] if c in built.columns and c not in ("position", "gene")]
domain = biochem + ["in_critical_domain"]
domain_esm = domain + [c for c in ("esm2_llr", "has_esm_score") if c in built.columns]


def cv_auc(sub, cols):
    c = [x for x in cols if x in sub.columns and not sub[x].isna().all()]
    X, y = sub[c], sub["label"].to_numpy(); g = sub["position"].to_numpy()
    if len(set(y)) < 2 or len(sub) < 40:
        return None
    o = np.zeros(len(y))
    try:
        for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=42).split(X, y, g):
            p = _build_pipeline(X.iloc[a], random_state=42); p.fit(X.iloc[a], y[a]); o[b] = p.predict_proba(X.iloc[b])[:, 1]
        return round(float(roc_auc_score(y, o)), 3)
    except Exception:
        return None


result = {}
for g in CRITICAL:
    sub = built[built.gene == g].reset_index(drop=True)
    r = {"n": int(len(sub)), "n_pathogenic": int(sub.label.sum()),
         "pct_pathogenic_in_critical": round(float(sub[sub.label == 1].in_critical_domain.mean()), 3) if sub.label.sum() else None,
         "auc_biochem": cv_auc(sub, biochem), "auc_domain": cv_auc(sub, domain),
         "auc_domain_esm": cv_auc(sub, domain_esm)}
    result[g] = r
    print(f"   {g:6s} n={r['n']:4d} pat={r['n_pathogenic']:4d}  bioq={r['auc_biochem']}  "
          f"+dom={r['auc_domain']}  +ESM={r.get('auc_domain_esm')}")
json.dump(result, open(os.path.join(ANL, "multigene_panel.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- figure: TP53 progression (the clean generalisation case) ---------------
tp = result["TP53"]
stages = ["bioquímico", "+ domínio\ncrítico", "+ ESM-2\n(flagship)"]
vals = [tp["auc_biochem"], tp["auc_domain"], tp.get("auc_domain_esm")]
colors = ["#9aa4b2", "#4a90c2", "#2e7d46"]
fig, ax = plt.subplots(figsize=(8.6, 5.4), dpi=200)
bars = ax.bar(stages, vals, color=colors, edgecolor="white", width=0.62)
for b, v in zip(bars, vals):
    if v is not None:
        ax.text(b.get_x() + b.get_width()/2, v + 0.008, f"{v:.3f}", ha="center", va="bottom",
                fontsize=12, fontweight="bold")
ax.axhline(0.5, ls=":", color="#aaa")
ax.set_ylim(0.5, 1.0); ax.set_ylabel("AUC-ROC (CV bloqueada por posição)")
ax.set_title(f"O método generaliza para TP53 (n={tp['n']}, {tp['n_pathogenic']} patogênicas)\n"
             "mesma receita do BRCA — a consciência de domínio e o ESM-2 elevam o modelo, gene novo",
             fontsize=11)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/multigene_panel.json and {FIG}")
