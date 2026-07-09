"""AlphaMissense grey-zone complement analysis (the core of the "complement, not
competitor" thesis), on REAL ClinVar BRCA1/2 variants.

Part 1 (rigour): among CLASSIFIED variants (ClinVar Pathogenic vs Benign) that
  AlphaMissense leaves 'ambiguous', how accurately does PrimeVarClass classify
  them? (AlphaMissense abstains on all of these by construction.)
Part 2 (impact): among current VUS that AlphaMissense also leaves 'ambiguous',
  for how many does PrimeVarClass provide a calibrated ACMG call (PP3_Strong /
  BP4_Moderate)?

Reads data/raw/alphamissense/alphamissense_brca_live.csv (ClinVar + AM) and the
pre-computed evidence resource. Writes JSON + figure.

Run: python scratch/grey_zone_analysis.py
"""
from __future__ import annotations

import json
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_grey_zone.png"
os.makedirs(os.path.dirname(FIG), exist_ok=True)

am = pd.read_csv("data/raw/alphamissense/alphamissense_brca_live.csv")
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))
df = am.merge(res[["gene", "position", "aa_ref", "aa_alt", "pathogenicity_prob", "acmg_evidence"]],
              on=["gene", "position", "aa_ref", "aa_alt"], how="inner")


def truth(s):
    s = str(s)
    if "Pathogenic" in s and "Conflicting" not in s:
        return 1
    if "Benign" in s and "Conflicting" not in s:
        return 0
    return np.nan


df["label"] = df.clinsig.map(truth)
df["is_vus"] = df.clinsig.str.contains("ncertain", na=False)
# AlphaMissense grey zone (its own 3-class output)
df["am_ambiguous"] = df.am_class.astype(str).eq("ambiguous")

n_am = int(df.am_pathogenicity.notna().sum())
print(f">> merged ClinVar∩AM∩resource: {len(df)} (AM present {n_am})")
print(f"   AlphaMissense class distribution:\n{df.am_class.value_counts().to_string()}")

# ---- Part 1: accuracy where AlphaMissense is ambiguous (classified variants) --
cls = df[(df.label.notna()) & (df.am_ambiguous)].copy()
p1 = {}
if len(cls) >= 10:
    y = cls.label.to_numpy().astype(int)
    p1["n_classified_ambiguous"] = int(len(cls))
    p1["n_pathogenic"] = int(y.sum())
    p1["our_auc"] = round(float(roc_auc_score(y, cls.pathogenicity_prob)), 3) if len(set(y)) > 1 else None
    # our resolved calls (PP3_Strong -> path, BP4_Moderate -> benign), else abstain
    call = np.where(cls.acmg_evidence == "PP3_Strong", 1,
                    np.where(cls.acmg_evidence == "BP4_Moderate", 0, -1))
    resolved = call != -1
    correct = (call[resolved] == y[resolved]).sum()
    p1["n_resolved"] = int(resolved.sum())
    p1["resolved_accuracy"] = round(float(correct / resolved.sum()), 3) if resolved.sum() else None

# ---- Part 2: yield on real VUS that AlphaMissense leaves ambiguous ------------
vus = df[(df.is_vus) & (df.am_ambiguous)].copy()
p2 = {"n_vus_ambiguous": int(len(vus))}
for lvl in ["PP3_Strong", "BP4_Moderate", "uninformative"]:
    p2[lvl] = int((vus.acmg_evidence == lvl).sum())
p2["resolved_fraction"] = round(float((vus.acmg_evidence != "uninformative").mean()), 3) if len(vus) else 0.0

# overall VUS resolution (regardless of AM), for context
allvus = df[df.is_vus]
p2["total_vus"] = int(len(allvus))
p2["total_vus_resolved"] = int((allvus.acmg_evidence != "uninformative").sum())

result = {"part1_accuracy_in_am_greyzone": p1, "part2_yield_on_ambiguous_vus": p2}
json.dump(result, open(os.path.join(ANL, "grey_zone_analysis.json"), "w"), indent=2, ensure_ascii=False)

# ---- figure -----------------------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.6, 5.0), dpi=200)
if p1:
    a1.bar(["Resolvidas\ncorretamente", "Resolvidas\nincorretas", "Abstém\n(VUS mantida)"],
           [int(p1["resolved_accuracy"] * p1["n_resolved"]),
            p1["n_resolved"] - int(p1["resolved_accuracy"] * p1["n_resolved"]),
            p1["n_classified_ambiguous"] - p1["n_resolved"]],
           color=["#2e8b57", "#c0392b", "#bbbbbb"])
    a1.set_title(f"A  Variantes classificadas que o AlphaMissense deixa AMBÍGUAS\n"
                 f"(n={p1['n_classified_ambiguous']}) — PrimeVarClass resolve {p1['n_resolved']} "
                 f"com {p1.get('resolved_accuracy', 0)*100:.0f}% de acerto", fontsize=9.5)
    a1.set_ylabel("nº de variantes")
a2.bar(["PP3_Forte\n(patogênico)", "BP4_Moderado\n(benigno)", "Não informativo\n(VUS mantida)"],
       [p2["PP3_Strong"], p2["BP4_Moderate"], p2["uninformative"]],
       color=["#c0392b", "#2e6fb0", "#bbbbbb"])
a2.set_title(f"B  VUS reais que o AlphaMissense deixa AMBÍGUAS (n={p2['n_vus_ambiguous']})\n"
             f"PrimeVarClass fornece evidência para {p2['resolved_fraction']*100:.0f}%", fontsize=9.5)
a2.set_ylabel("nº de VUS")
fig.suptitle("Complemento ao AlphaMissense: resolvendo a zona cinzenta (ClinVar real)", fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")

print("\n===== GREY-ZONE COMPLEMENT =====")
print("Part 1 (accuracy where AM is ambiguous):", json.dumps(p1, ensure_ascii=False))
print("Part 2 (yield on ambiguous VUS):", json.dumps(p2, ensure_ascii=False))
print(f">> wrote {ANL}/grey_zone_analysis.json and {FIG}")
