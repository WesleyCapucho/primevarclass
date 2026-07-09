"""Summarise which mutations the algorithm detects (PP3_Strong evidence) and
where they fall on the BRCA1 structure. Feeds the PyMOL result figures.

Outputs:
  primevarclass_manuscript_analysis/detected_per_residue_brca1.csv
      one row per BRCA1 residue: fraction of the 19 substitutions flagged
      PP3_Strong, plus max/mean pathogenicity probability.
  primevarclass_manuscript_analysis/detected_top_variants.csv
      the highest-confidence detected variants (RING + BRCT), cross-referenced
      with the curated clinical labels when available.

Run: python scratch/detected_mutations_analysis.py
"""
from __future__ import annotations

import os

import pandas as pd

ANL = "primevarclass_manuscript_analysis"
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))
b1 = res[res.gene == "BRCA1"].copy()

# ---- per-residue detection intensity (BRCA1) --------------------------------
per = b1.groupby("position").agg(
    n_detected=("acmg_evidence", lambda s: (s == "PP3_Strong").sum()),
    n_alt=("acmg_evidence", "size"),
    max_prob=("pathogenicity_prob", "max"),
    mean_prob=("pathogenicity_prob", "mean"),
    domain=("functional_domain", "first"),
    critical=("in_critical_domain", "first"),
).reset_index()
per["frac_detected"] = (per.n_detected / per.n_alt).round(4)
per.to_csv(os.path.join(ANL, "detected_per_residue_brca1.csv"), index=False)

# ---- cross-reference with curated clinical labels ---------------------------
lab_path = "data/raw/clinvar/brca_missense_variant_summary.tsv"
labels = None
if os.path.exists(lab_path):
    lb = pd.read_csv(lab_path, sep="\t")
    sig = "ClinicalSignificance"
    lb = lb[lb.GeneSymbol == "BRCA1"][["Protein change", sig]].dropna()
    lb["key"] = lb["Protein change"].str.replace("p.", "", regex=False)
    labels = dict(zip(lb["key"], lb[sig]))

AA3 = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln", "E": "Glu",
       "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe",
       "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val"}


def clin(row):
    if labels is None:
        return ""
    k = f"{AA3[row.aa_ref]}{row.position}{AA3[row.aa_alt]}"
    return labels.get(k, "")


det = b1[b1.acmg_evidence == "PP3_Strong"].copy()
det["clinvar"] = det.apply(clin, axis=1)
det["region"] = det.functional_domain.where(det.in_critical_domain == 1, "outro")
top = (det.sort_values("pathogenicity_prob", ascending=False)
          .groupby("functional_domain").head(8)
          .sort_values(["functional_domain", "pathogenicity_prob"], ascending=[True, False]))
top[["gene", "hgvs_p", "position", "functional_domain", "esm2_llr",
     "pathogenicity_prob", "clinvar"]].to_csv(
    os.path.join(ANL, "detected_top_variants.csv"), index=False)

print(f">> BRCA1 variants flagged PP3_Strong (detected): {len(det)}")
print("   por domínio crítico:")
print(det[det.in_critical_domain == 1].functional_domain.value_counts().to_string())
print("\n>> residues with the strongest detection (frac of 19 substitutions):")
print(per.sort_values("frac_detected", ascending=False).head(12)
         [["position", "domain", "n_detected", "frac_detected", "max_prob"]].to_string(index=False))
print("\n>> top detected variants also curated in ClinVar (validation):")
val = det[det.clinvar.str.contains("athogenic", na=False)].sort_values("pathogenicity_prob", ascending=False)
print(val.head(12)[["hgvs_p", "functional_domain", "pathogenicity_prob", "clinvar"]].to_string(index=False))
print(f"   ({len(val)} detected variants are curated Pathogenic/Likely pathogenic in ClinVar)")
