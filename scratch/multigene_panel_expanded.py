"""Expanded multigene generalization — beyond HBOC into Lynch / VHL / MEN2.

Applies the SAME recipe used for BRCA/TP53 (biochemistry -> + critical-domain
awareness -> + ESM-2 650M, the flagship's model) under position-blocked CV, to
five cancer-predisposition genes that pass the real-ClinVar label threshold
(>=40 definitive missense, both classes, minority >=8):

    VHL (von Hippel-Lindau) | MLH1, MSH2, MSH6 (Lynch / mismatch repair) | RET (MEN2)

Inputs (all real, reproducible):
  * labels : primevarclass_manuscript_analysis/panel_new_clinvar_labels.csv
             (definitive missense from ClinVar variant_summary, GRCh38, dedup)
  * domains: primevarclass_manuscript_analysis/panel_new_pfam_domains.json
             (Pfam function-defined domains from InterPro -- label-independent)
  * ESM    : scratch/esm_input/esm2_650M_expanded_scores.csv
             (masked-marginal LLR from ESM-2 650M, scored on Colab GPU)

Run (after the Colab CSV is in place):
    python scratch/multigene_panel_expanded.py
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
from sklearn.model_selection import StratifiedGroupKFold

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_multigene_expanded.png"
ESM_SRC = "scratch/esm_input/esm2_650M_expanded_scores.csv"
SYND = {"VHL": "von Hippel-Lindau", "MLH1": "Lynch", "MSH2": "Lynch",
        "MSH6": "Lynch", "RET": "MEN2"}
RNG = 42

if not os.path.exists(ESM_SRC):
    sys.exit(f"!! missing {ESM_SRC} — run scratch/colab_esm2_650M_expanded.py on Colab "
             "and drop esm2_650M_expanded_scores.csv there first.")

labels = pd.read_csv(os.path.join(ANL, "panel_new_clinvar_labels.csv"))
pfam = json.load(open(os.path.join(ANL, "panel_new_pfam_domains.json")))
CRITICAL = {g: [(s, e) for s, e, *_ in v["pfam"]] for g, v in pfam.items()}
esm_df = pd.read_csv(ESM_SRC)


def in_crit(g, p):
    return int(any(a <= p <= b for a, b in CRITICAL.get(g, [])))


labels["hgvs_p"] = ["p." + r + str(p) + a for r, p, a in
                    zip(labels.aa_ref, labels.position, labels.aa_alt)]
built, _ = build_dataset_from_dataframe(
    labels[["gene", "hgvs_p", "position", "aa_ref", "aa_alt", "label"]],
    mode="hybrid", keep_metadata=True)
built["label"] = labels["label"].to_numpy()
built["in_critical_domain"] = [in_crit(g, p) for g, p in zip(labels.gene, labels.position)]
built = attach_esm_scores(built, esm_df)

subs = get_feature_subsets(built)
biochem = [c for c in subs["biochemical_only"] if c in built.columns and c not in ("position", "gene")]
domain = biochem + ["in_critical_domain"]
domain_esm = domain + [c for c in ("esm2_llr", "has_esm_score") if c in built.columns]


def cv_oof(sub, cols):
    c = [x for x in cols if x in sub.columns and not sub[x].isna().all()]
    X, y = sub[c], sub["label"].to_numpy(); g = sub["position"].to_numpy()
    if len(set(y)) < 2 or len(sub) < 40:
        return None, None
    oof = np.zeros(len(y))
    try:
        for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=RNG).split(X, y, g):
            p = _build_pipeline(X.iloc[a], random_state=RNG); p.fit(X.iloc[a], y[a])
            oof[b] = p.predict_proba(X.iloc[b])[:, 1]
        return round(float(roc_auc_score(y, oof)), 3), (y, oof)
    except Exception:
        return None, None


def boot_ci(y, s, B=2000, seed=RNG):
    rng = np.random.default_rng(seed); n = len(y); a = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        a.append(roc_auc_score(y[idx], s[idx]))
    return [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)] if a else None


result = {}
print(f"{'gene':7s}{'n':>5s}{'pat':>5s}  {'bioq':>6s}{'+dom':>7s}{'+ESM':>7s}  IC95%(+ESM)")
for g in CRITICAL:
    sub = built[built.gene == g].reset_index(drop=True)
    ab, _ = cv_oof(sub, biochem)
    ad, _ = cv_oof(sub, domain)
    ae, oof = cv_oof(sub, domain_esm)
    ci = boot_ci(*oof) if oof else None
    result[g] = {"syndrome": SYND[g], "n": int(len(sub)), "n_pathogenic": int(sub.label.sum()),
                 "auc_biochem": ab, "auc_domain": ad, "auc_domain_esm": ae, "ci95_domain_esm": ci}
    print(f"{g:7s}{len(sub):5d}{int(sub.label.sum()):5d}  {ab!s:>6}{ad!s:>7}{ae!s:>7}  {ci}")

json.dump(result, open(os.path.join(ANL, "multigene_panel_expanded.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- figure: flagship AUC per gene, grouped by syndrome, with CIs ------------
order = [g for g in ["VHL", "MLH1", "MSH2", "MSH6", "RET"] if result[g]["auc_domain_esm"] is not None]
vals = [result[g]["auc_domain_esm"] for g in order]
cis = [result[g]["ci95_domain_esm"] for g in order]
err = [[v - c[0] for v, c in zip(vals, cis)], [c[1] - v for v, c in zip(vals, cis)]]
labs = [f"{g}\n{SYND[g]}\n(n={result[g]['n']})" for g in order]
cmap = {"von Hippel-Lindau": "#c0392b", "Lynch": "#2e6fb0", "MEN2": "#d59a00"}
colors = [cmap[SYND[g]] for g in order]
fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=200)
x = np.arange(len(order))
ax.bar(x, vals, 0.62, color=colors, yerr=err, capsize=5, edgecolor="white")
for i, v in enumerate(vals):
    ax.text(i, min(cis[i][1] + 0.012, 1.015), f"{v:.3f}", ha="center", va="bottom",
            fontsize=12, fontweight="bold")
ax.axhline(0.5, ls=":", color="#aaa")
ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=12.3)
ax.set_ylim(0.5, 1.06); ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
ax.set_ylabel("AUC-ROC do carro-chefe (CV bloqueada por posição)")
ax.set_title("A receita generaliza além do câncer de mama/ovário\n"
             "domínio funcional + ESM-2 (mesmo modelo do BRCA) — VHL, Lynch (MLH1/MSH2/MSH6) e MEN2 (RET), "
             "rótulos reais do ClinVar", fontsize=13.7, pad=14)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/multigene_panel_expanded.json and {FIG}")
