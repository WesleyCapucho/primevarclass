"""AlphaMissense grey-zone complement analysis (core of "complement, not
competitor") on REAL, COMPLETE BRCA1 data:
  - ClinVar labels (live)                          clinvar_brca_missense_live.csv
  - AlphaMissense for every possible substitution  alphamissense_brca_full.csv
  - PrimeVarClass calibrated evidence for all       brca_missense_evidence_resource.csv

Part 1 (rigour): among CLASSIFIED variants (ClinVar Pathogenic vs Benign) that
  AlphaMissense leaves 'ambiguous', how accurately does PrimeVarClass classify?
Part 2 (impact): among current VUS that AlphaMissense also leaves 'ambiguous',
  for how many does PrimeVarClass provide a calibrated ACMG call?
Bonus: the same, for ClinVar 'Conflicting' variants (labs disagree).

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
GENE = "BRCA1"  # AlphaMissense full coverage available; BRCA2 (fragmented) added later

clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
am = pd.read_csv("data/raw/alphamissense/alphamissense_brca_full.csv")
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))
key = ["gene", "position", "aa_ref", "aa_alt"]

df = (clin[clin.gene == GENE]
      .merge(am[key + ["am_pathogenicity", "am_class"]], on=key, how="inner")
      .merge(res[key + ["pathogenicity_prob", "acmg_evidence"]], on=key, how="inner"))


def truth(s):
    s = str(s)
    if "Pathogenic" in s and "Conflicting" not in s:
        return 1
    if "Benign" in s and "Conflicting" not in s:
        return 0
    return np.nan


df["label"] = df.clinsig.map(truth)
df["is_vus"] = df.clinsig.str.contains("ncertain", na=False)
df["is_conflicting"] = df.clinsig.str.contains("Conflicting", na=False)
df["am_ambiguous"] = df.am_class.eq("ambiguous")
print(f">> {GENE}: {len(df)} ClinVar variants with AM + our evidence")
print("   AlphaMissense class:\n" + df.am_class.value_counts().to_string())

# ---- Part 1: accuracy where AlphaMissense is ambiguous (classified) ----------
cls = df[df.label.notna() & df.am_ambiguous]
p1 = {}
if len(cls) >= 8:
    y = cls.label.to_numpy().astype(int)
    call = np.where(cls.acmg_evidence == "PP3_Strong", 1,
                    np.where(cls.acmg_evidence == "BP4_Moderate", 0, -1))
    resolved = call != -1
    p1 = {"n_classified_ambiguous": int(len(cls)), "n_pathogenic": int(y.sum()),
          "our_auc": round(float(roc_auc_score(y, cls.pathogenicity_prob)), 3) if len(set(y)) > 1 else None,
          "n_resolved": int(resolved.sum()),
          "resolved_accuracy": round(float((call[resolved] == y[resolved]).mean()), 3) if resolved.sum() else None}


def yield_on(mask):
    sub = df[mask & df.am_ambiguous]
    out = {"n_am_ambiguous": int(len(sub))}
    for lvl in ["PP3_Strong", "BP4_Moderate", "uninformative"]:
        out[lvl] = int((sub.acmg_evidence == lvl).sum())
    out["resolved_fraction"] = round(float((sub.acmg_evidence != "uninformative").mean()), 3) if len(sub) else 0.0
    return out


p2 = yield_on(df.is_vus)          # real VUS that AM leaves ambiguous
p3 = yield_on(df.is_conflicting)  # labs disagree AND AM ambiguous
result = {"gene": GENE, "am_class_counts": df.am_class.value_counts().to_dict(),
          "part1_accuracy_in_am_greyzone": p1,
          "part2_yield_on_ambiguous_VUS": p2,
          "part3_yield_on_ambiguous_conflicting": p3}
json.dump(result, open(os.path.join(ANL, "grey_zone_analysis.json"), "w"), indent=2, ensure_ascii=False)

# ---- figure: the two impactful panels (VUS and conflicting) -----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 5.0), dpi=200)
for ax, p, titulo, unidade in [
        (a1, p2, "VUS reais", "VUS"),
        (a2, p3, "variantes CONFLITANTES (laboratórios discordam)", "variantes")]:
    ax.bar(["PP3_Forte\n(patogênico)", "BP4_Moderado\n(benigno)", "Não informativo\n(mantém incerta)"],
           [p["PP3_Strong"], p["BP4_Moderate"], p["uninformative"]],
           color=["#c0392b", "#2e6fb0", "#bbbbbb"])
    ax.set_ylabel(f"nº de {unidade}")
    ax.set_title(f"{titulo} que o AlphaMissense deixa ambíguas (n={p['n_am_ambiguous']})\n"
                 f"PrimeVarClass fornece evidência para {p['resolved_fraction']*100:.0f}%", fontsize=9.5)
fig.suptitle(f"Complemento ao AlphaMissense — evidência onde ele se abstém ({GENE}, ClinVar real)",
             fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")

print("\n===== GREY-ZONE COMPLEMENT (BRCA1) =====")
print("Part 1 (accuracy where AM ambiguous):", json.dumps(p1, ensure_ascii=False))
print("Part 2 (yield on ambiguous VUS):     ", json.dumps(p2, ensure_ascii=False))
print("Part 3 (yield on ambiguous conflicting):", json.dumps(p3, ensure_ascii=False))
print(f">> wrote {ANL}/grey_zone_analysis.json and {FIG}")
