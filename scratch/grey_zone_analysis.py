"""AlphaMissense grey-zone complement analysis on REAL ClinVar variants, now for
BOTH BRCA1 and BRCA2 (the "complement, not competitor" thesis).

AlphaMissense source:
  BRCA1 -> alphamissense_brca_full.csv (complete, from AlphaFold DB)
  BRCA2 -> alphamissense_brca_live.csv (from Ensembl VEP; AlphaFold DB has no
           single-fragment file for the 3418-aa BRCA2)

Part 1 (rigour): among CLASSIFIED variants that AlphaMissense leaves 'ambiguous',
  how accurately does PrimeVarClass classify?
Part 2 (impact): among VUS that AlphaMissense also leaves 'ambiguous', for how
  many does PrimeVarClass provide a calibrated ACMG call?
Part 3: same, for ClinVar 'Conflicting' variants (labs disagree).

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
import os, sys
sys.path.insert(0, os.path.abspath("src"))
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_grey_zone.png"
key = ["gene", "position", "aa_ref", "aa_alt"]

clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))

# unified AlphaMissense: complete BRCA1 file + BRCA2 from the live VEP fetch
am1 = pd.read_csv("data/raw/alphamissense/alphamissense_brca_full.csv")
am1 = am1[am1.gene == "BRCA1"][key + ["am_pathogenicity", "am_class"]]
live = pd.read_csv("data/raw/alphamissense/alphamissense_brca_live.csv")
am2 = live[(live.gene == "BRCA2") & live.am_pathogenicity.notna()][key + ["am_pathogenicity", "am_class"]]
am = pd.concat([am1, am2], ignore_index=True)

df = (clin.merge(am, on=key, how="inner")
          .merge(res[key + ["pathogenicity_prob", "acmg_evidence"]], on=key, how="inner"))


def truth(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


df["label"] = df.clinsig.map(truth)
df["is_vus"] = df.clinsig.str.contains("ncertain", na=False)
df["is_conflicting"] = df.clinsig.str.contains("Conflicting", na=False)
df["am_ambiguous"] = df.am_class.eq("ambiguous")


def yield_on(sub):
    out = {"n": int(len(sub))}
    for lvl in ["PP3_Strong", "BP4_Moderate", "uninformative"]:
        out[lvl] = int((sub.acmg_evidence == lvl).sum())
    out["resolved_frac"] = round(float((sub.acmg_evidence != "uninformative").mean()), 3) if len(sub) else 0.0
    return out


result = {}
for scope in ["BRCA1", "BRCA2", "BRCA1+BRCA2"]:
    d = df if scope == "BRCA1+BRCA2" else df[df.gene == scope]
    amb = d[d.am_ambiguous]
    cls = d[d.label.notna() & d.am_ambiguous]
    p1 = {}
    if len(cls) >= 8:
        y = cls.label.to_numpy().astype(int)
        call = np.where(cls.acmg_evidence == "PP3_Strong", 1,
                        np.where(cls.acmg_evidence == "BP4_Moderate", 0, -1))
        rr = call != -1
        p1 = {"n_classified_ambiguous": int(len(cls)),
              "our_auc": round(float(roc_auc_score(y, cls.pathogenicity_prob)), 3) if len(set(y)) > 1 else None,
              "n_resolved": int(rr.sum()),
              "resolved_accuracy": round(float((call[rr] == y[rr]).mean()), 3) if rr.sum() else None}
    result[scope] = {"n_am_ambiguous_total": int(len(amb)),
                     "part1_classified": p1,
                     "part2_vus": yield_on(d[d.is_vus & d.am_ambiguous]),
                     "part3_conflicting": yield_on(d[d.is_conflicting & d.am_ambiguous])}
    print(f">> {scope}: AM-ambiguous={len(amb)} | "
          f"VUS amb={result[scope]['part2_vus']['n']} (resolvemos {result[scope]['part2_vus']['resolved_frac']*100:.0f}%) | "
          f"conflitantes amb={result[scope]['part3_conflicting']['n']} (resolvemos {result[scope]['part3_conflicting']['resolved_frac']*100:.0f}%)")

json.dump(result, open(os.path.join(ANL, "grey_zone_analysis.json"), "w"), indent=2, ensure_ascii=False)

# ---- figure: VUS (A) and conflicting (B), stacked by resolution, per gene ----
genes = ["BRCA1", "BRCA2"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.8, 6.2), dpi=200)
for ax, letra, part, titulo, unidade in [(a1, "A", "part2_vus", "VUS reais", "VUS"),
                                         (a2, "B", "part3_conflicting", "Variantes conflitantes (laboratórios discordam)", "variantes")]:
    pp3 = [result[g][part]["PP3_Strong"] for g in genes]
    bp4 = [result[g][part]["BP4_Moderate"] for g in genes]
    uni = [result[g][part]["uninformative"] for g in genes]
    x = np.arange(len(genes))
    ax.bar(x, pp3, 0.6, label="PP3_Forte (patogênico)", color="#c0392b")
    ax.bar(x, bp4, 0.6, bottom=pp3, label="BP4_Moderado (benigno)", color="#2e6fb0")
    ax.bar(x, uni, 0.6, bottom=np.array(pp3) + np.array(bp4), label="não informativo", color="#c8ccd0")
    top = max((result[g][part]["n"] for g in genes), default=1)
    ax.set_ylim(0, top * 1.30)
    for i, g in enumerate(genes):
        tot = result[g][part]["n"]
        frac = result[g][part]["resolved_frac"] * 100
        ax.text(i, tot + top * 0.03, f"{frac:.0f}% resolvidas", ha="center", fontsize=15, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(genes, fontsize=14.5, fontweight="bold")
    ax.set_ylabel(f"nº de {unidade} na zona cinzenta do AlphaMissense", fontsize=13)
    ax.tick_params(axis="y", labelsize=12)
    ax.set_title(f"{letra}. {titulo}", fontsize=14.5, fontweight="bold")
    ax.legend(fontsize=12, loc="upper left", framealpha=0.95)
fig.suptitle("Complemento ao AlphaMissense: evidência calibrada onde ele se abstém (BRCA1 e BRCA2, ClinVar real)",
             fontweight="bold", fontsize=15.5)
fig.tight_layout(rect=[0, 0, 1, 0.95])
for _fp in (FIG, FIG.replace("suplementar", "manuscrito")):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    fig.savefig(_fp, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {ANL}/grey_zone_analysis.json and the figure (suplementar + manuscrito)")
