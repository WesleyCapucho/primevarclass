"""Canonical prospective analysis (supersedes the separate numbers in
reclassification_prospective.py and leakagefree_benchmark.py so the manuscript
cites ONE consistent set): the reclassified set = BRCA missense variants that were
VUS/conflicting in ClinVar 2023-06 and definitive (P/B) by 2026-07. The flagship
is trained only on 2023-definitive variants (blind to these). Produces the
prospective AUC, the high-confidence accuracy, the leakage-free head-to-head, and
a two-panel figure.

Run: python scratch/prospective_analysis.py
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
from sklearn.metrics import accuracy_score, roc_auc_score

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_prospective.png"
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
PMIS = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")
key = ["gene", "position", "aa_ref", "aa_alt"]


def definitive(s):
    s = str(s)
    if "Conflicting" in s:
        return np.nan
    if "Pathogenic" in s:
        return 1
    if "Benign" in s:
        return 0
    return np.nan


rows = []
with open("data/raw/clinvar/variant_summary_2023-06_BRCA.tsv", encoding="utf-8") as fh:
    h = fh.readline().rstrip("\n").split("\t"); idx = {n: i for i, n in enumerate(h)}
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) <= idx["Assembly"] or f[idx["Assembly"]] != "GRCh38" or f[idx["GeneSymbol"]] not in ("BRCA1", "BRCA2"):
            continue
        m = PMIS.search(f[idx["Name"]])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
            continue
        rows.append({"gene": f[idx["GeneSymbol"]], "position": int(m.group(2)),
                     "aa_ref": AA3TO1[m.group(1)], "aa_alt": AA3TO1[m.group(3)],
                     "sig_2023": f[idx["ClinicalSignificance"]]})
old = pd.DataFrame(rows).drop_duplicates(key, keep="first")
old["unc23"] = old.sig_2023.map(lambda s: ("Uncertain" in str(s)) or ("Conflicting" in str(s)))
old["def23"] = old.sig_2023.map(definitive)
cur = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
cur["label"] = cur.clinsig.map(definitive)

recl = old[old.unc23].merge(cur[key + ["label"]], on=key, how="inner").dropna(subset=["label"]).drop_duplicates(key)
y = recl.label.astype(int).to_numpy()
train = old[old.def23.notna()].copy(); train["label"] = train.def23.astype(int)
panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")


def eng(fr):
    fr = fr.copy(); fr["hgvs_p"] = ["p."+r+str(p)+a for r, p, a in zip(fr.aa_ref, fr.position, fr.aa_alt)]
    b, _ = build_dataset_from_dataframe(fr[["gene", "hgvs_p", "position", "aa_ref", "aa_alt"]].assign(label=fr.get("label", 0)),
                                        mode="hybrid", keep_metadata=True)
    return attach_esm_scores(b, panel)


tr = eng(train); tr["label"] = train.label.to_numpy(); te = eng(recl)
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all() and c in te.columns]
pipe = _build_pipeline(tr[cols], random_state=42); pipe.fit(tr[cols], tr.label.to_numpy())
p = pipe.predict_proba(te[cols])[:, 1]

auc = float(roc_auc_score(y, p))
hi = (p >= 0.675) | (p <= 0.255)
acc_hi = float(accuracy_score(y[hi], (p[hi] >= 0.5).astype(int)))
out = {"n_reclassified": int(len(y)), "n_pathogenic": int(y.sum()),
       "n_train_2023_definitive": int(len(tr)), "auc": round(auc, 3),
       "n_high_confidence": int(hi.sum()), "accuracy_high_confidence": round(acc_hi, 3)}
print(json.dumps(out, indent=2))
json.dump(out, open(os.path.join(ANL, "reclassification_prospective.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# leakage-free comparison numbers (read the already-computed pairwise result)
lf = json.load(open(os.path.join(ANL, "leakagefree_benchmark.json"), encoding="utf-8"))

# ---- figure -----------------------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.6, 5.2), dpi=200,
                             gridspec_kw={"width_ratios": [1.15, 1]})
rng = np.random.default_rng(0)
for lab, color, xc, name in [(0, "#2e6fb0", 0, "benignas"), (1, "#c0392b", 1, "patogênicas")]:
    yy = p[y == lab]; xx = xc + rng.uniform(-0.18, 0.18, len(yy))
    a1.scatter(xx, yy, c=color, s=42, alpha=0.75, edgecolor="white", linewidth=0.5,
               label=f"{name} (2026)")
a1.axhline(0.675, ls="--", color="#c0392b", lw=1, alpha=0.6)
a1.axhline(0.255, ls="--", color="#2e6fb0", lw=1, alpha=0.6)
a1.set_xticks([0, 1]); a1.set_xticklabels(["eventualmente\nbenignas", "eventualmente\npatogênicas"])
a1.set_ylabel("probabilidade do modelo (cego ao rótulo de 2026)")
a1.set_ylim(0, 1)
a1.set_title(f"A · Previsão prospectiva das VUS de 2023 (n={len(y)})\n"
             f"AUC = {auc:.3f} · alta confiança: {acc_hi:.0%} de acerto",
             fontsize=10.5, fontweight="bold")
a1.legend(fontsize=8.5, loc="center left")
a1.grid(axis="y", alpha=0.2)

tools = ["PrimeVarClass", "AlphaMissense", "REVEL", "CADD"]
full = lf["full"]
aucs = [full[t]["auc"] for t in tools]
cols_b = ["#c0392b", "#5a7fb0", "#5a7fb0", "#5a7fb0"]
x = np.arange(len(tools))
b = a2.bar(x, aucs, 0.6, color=cols_b, edgecolor="white")
for bi, t in zip(b, tools):
    a2.text(bi.get_x()+bi.get_width()/2, bi.get_height()+0.006, f"{full[t]['auc']:.3f}",
            ha="center", va="bottom", fontsize=9.5, fontweight="bold")
a2.set_xticks(x); a2.set_xticklabels(tools, fontsize=9, rotation=12)
a2.set_ylim(0.5, 1.0); a2.set_ylabel("AUC-ROC (conjunto livre de vazamento)")
a2.set_title("B · Head-to-head livre de vazamento\n(nenhuma ferramenta viu os rótulos)",
             fontsize=10.5, fontweight="bold")
a2.grid(axis="y", alpha=0.25)
fig.suptitle("Validação prospectiva: o modelo prevê como a comunidade reclassifica VUS — "
             "e lidera onde ninguém teve as respostas", fontweight="bold", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/reclassification_prospective.json and {FIG}")
