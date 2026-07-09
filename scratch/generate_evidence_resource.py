"""Pre-computed clinical-evidence resource for EVERY possible BRCA1/BRCA2
missense variant — the complementary layer AlphaMissense does not provide.

For each variant we output: functional domain, zero-shot ESM-2 LLR, the flagship
model's pathogenicity probability and a calibrated **ACMG/AMP evidence call**.
Only the two externally-validated, transferable evidence levels are asserted
(see Material Suplementar S3): PP3_Strong (escore >= 0.675; 94% patogênicas na
coorte externa) and BP4_Moderate (escore <= 0.255; 3% patogênicas). Everything
between is left 'uninformative' — a genuine VUS stays a VUS.

Output: primevarclass_manuscript_analysis/brca_missense_evidence_resource.csv

Run: python scratch/generate_evidence_resource.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.domain_annotation import annotate_domain
from primevarclass.esm_scores import attach_esm_scores

OUT = "primevarclass_manuscript_analysis/brca_missense_evidence_resource.csv"
AA3 = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln", "E": "Glu",
       "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe",
       "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val"}
PP3_STRONG, BP4_MODERATE = 0.675, 0.255

panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")
panel = panel[panel.gene.isin(["BRCA1", "BRCA2"])].reset_index(drop=True)

# train flagship on the clinical cohort (ESM values identical to the panel)
tr, _, _ = build_dataset_from_source_config("configs/public_brca_real.toml", mode="hybrid", keep_metadata=True)
ytr = pd.to_numeric(tr["label"], errors="coerce"); keep = ytr.notna()
tr = attach_esm_scores(tr.loc[keep].reset_index(drop=True), panel)
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all()]
pipe = _build_pipeline(tr[cols], random_state=42)
pipe.fit(tr[cols], ytr.loc[keep].astype(int).to_numpy())
print(f">> flagship trained on n={keep.sum()} clinical variants; scoring {len(panel)} possible missense ...")

# engineer features for every possible missense and predict
q = panel.rename(columns={}).copy()
q["hgvs_p"] = ["p." + AA3[r] + str(int(p)) + AA3[a] for r, p, a in zip(q.aa_ref, q.position, q.aa_alt)]
q["label"] = 0
built, _ = build_dataset_from_dataframe(q[["gene", "hgvs_p", "label", "position", "aa_ref", "aa_alt"]],
                                        mode="hybrid", keep_metadata=True)
built = attach_esm_scores(built, panel)
for c in cols:
    if c not in built.columns:
        built[c] = np.nan
prob = pipe.predict_proba(built[cols])[:, 1]

dom = [annotate_domain(g, p) for g, p in zip(q.gene, q.position)]
res = pd.DataFrame({
    "gene": q.gene, "position": q.position, "aa_ref": q.aa_ref, "aa_alt": q.aa_alt,
    "hgvs_p": q.hgvs_p,
    "functional_domain": [d[0] for d in dom],
    "in_critical_domain": [d[1] for d in dom],
    "esm2_llr": q.esm2_llr,
    "pathogenicity_prob": np.round(prob, 4),
})
res["acmg_evidence"] = np.where(res.pathogenicity_prob >= PP3_STRONG, "PP3_Strong",
                        np.where(res.pathogenicity_prob <= BP4_MODERATE, "BP4_Moderate", "uninformative"))
res = res.sort_values(["gene", "position", "aa_alt"]).reset_index(drop=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
res.to_csv(OUT, index=False)

print(f">> wrote {OUT}  ({len(res)} variants)")
print("   evidence distribution:")
for lvl in ["PP3_Strong", "uninformative", "BP4_Moderate"]:
    m = res.acmg_evidence == lvl
    print(f"     {lvl:14s} {m.sum():6d}  ({100*m.mean():.1f}%)")
print("   por gene:")
print(res.groupby("gene").acmg_evidence.value_counts().unstack(fill_value=0).to_string())
