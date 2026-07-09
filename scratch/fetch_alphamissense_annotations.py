"""Download the COMPLETE AlphaMissense per-substitution predictions for BRCA1 and
BRCA2 directly from the AlphaFold DB (one CSV per UniProt) — far faster and more
complete than variant-by-variant VEP calls. Every possible missense is covered.

Run: python scratch/fetch_alphamissense_annotations.py
"""
from __future__ import annotations

import io
import os
import re
import urllib.request

import pandas as pd

UNIPROT = {"BRCA1": "P38398", "BRCA2": "P51587"}
CLASS = {"LPath": "likely_pathogenic", "Amb": "ambiguous", "LBen": "likely_benign"}
OUT = "data/raw/alphamissense/alphamissense_brca_full.csv"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
PV = re.compile(r"^([A-Z])(\d+)([A-Z])$")

frames = []
for gene, up in UNIPROT.items():
    url = f"https://alphafold.ebi.ac.uk/files/AF-{up}-F1-aa-substitutions.csv"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = pd.read_csv(io.BytesIO(r.read()))
    except Exception as e:
        # BRCA2 (P51587) is fragmented in AlphaFold DB -> no single AM file.
        print(f">> {gene} ({up}): indisponível ({e}); usar VEP para este gene.")
        continue
    m = d.protein_variant.str.extract(PV)
    d["aa_ref"], d["position"], d["aa_alt"] = m[0], m[1].astype(int), m[2]
    d["gene"] = gene
    d["am_class"] = d["am_class"].map(CLASS).fillna(d["am_class"])
    frames.append(d[["gene", "position", "aa_ref", "aa_alt", "am_pathogenicity", "am_class"]])
    print(f">> {gene} ({up}): {len(d)} substitutions")

am = pd.concat(frames, ignore_index=True)
am.to_csv(OUT, index=False)
print(f">> wrote {OUT}  ({len(am)} rows)")
print(am.am_class.value_counts().to_string())
