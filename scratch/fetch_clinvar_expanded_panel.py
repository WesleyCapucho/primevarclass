"""Fetch real ClinVar records for the expanded-panel genes (VHL, MLH1, MSH2,
MSH6, RET) via NCBI E-utilities and rebuild the label table used by
scratch/multigene_panel_expanded.py.

Why this exists: the previous panel_new_clinvar_labels.csv was produced ad hoc
and was never versioned, so it could not be reproduced or audited. It was also
built with a case-sensitive significance filter that silently dropped every
"Likely benign"/"Likely pathogenic" record, leaving the label set 66-93%
pathogenic (real ClinVar missense data is benign-dominated). This script fixes
both problems: it is versioned, and it labels through
primevarclass.core.clinvar_binary_label.

Run: python scratch/fetch_clinvar_expanded_panel.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
from primevarclass.core import clinvar_binary_label

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ANL = "primevarclass_manuscript_analysis"
RAW_OUT = "data/raw/clinvar/clinvar_expanded_panel_missense_live.csv"
LABELS_OUT = os.path.join(ANL, "panel_new_clinvar_labels.csv")
GENES = ["VHL", "MLH1", "MSH2", "MSH6", "RET"]

AA3 = {"Ala", "Arg", "Asn", "Asp", "Cys", "Gln", "Glu", "Gly", "His", "Ile", "Leu",
       "Lys", "Met", "Phe", "Pro", "Ser", "Thr", "Trp", "Tyr", "Val"}
A3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q", "Glu": "E",
         "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F",
         "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V"}
PVAR = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})")


def _get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("   retry", k, e)
            time.sleep(3 * (k + 1))
    return None


def esearch(gene):
    term = f"{gene}[gene] AND single_gene[prop] AND missense_variant[molecular consequence]"
    url = f"{EUTILS}/esearch.fcgi?db=clinvar&term={urllib.parse.quote(term)}&retmax=100000&retmode=json"
    res = _get(url)
    return res["esearchresult"]["idlist"] if res else []


rows = []
for gene in GENES:
    ids = esearch(gene)
    print(f">> {gene}: {len(ids)} missense UIDs")
    for i in range(0, len(ids), 300):
        chunk = ids[i:i + 300]
        res = _get(f"{EUTILS}/esummary.fcgi?db=clinvar&id={','.join(chunk)}&retmode=json")
        if not res:
            continue
        for uid in res.get("result", {}).get("uids", []):
            rec = res["result"][uid]
            germ = rec.get("germline_classification", {}) or {}
            vs = rec.get("variation_set", [{}])
            name = vs[0].get("variation_name", "") if vs else ""
            m = PVAR.search(name)
            if not m or m.group(1) not in AA3 or m.group(3) not in AA3:
                continue
            rows.append({
                "uid": uid, "gene": gene,
                "aa_ref": A3TO1[m.group(1)], "position": int(m.group(2)), "aa_alt": A3TO1[m.group(3)],
                "clinsig": germ.get("description", ""),
                "review_status": germ.get("review_status", ""),
                "last_evaluated": germ.get("last_evaluated", ""),
            })
        print(f"   {gene}: {min(i + 300, len(ids))}/{len(ids)}")
        time.sleep(0.4)

df = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"]).reset_index(drop=True)
os.makedirs(os.path.dirname(RAW_OUT), exist_ok=True)
df.to_csv(RAW_OUT, index=False)
print(f"\n>> wrote {RAW_OUT} ({len(df)} unique missense)")
print(df.clinsig.value_counts().head(12).to_string())

df["label"] = df.clinsig.map(clinvar_binary_label)
lab = df.dropna(subset=["label"]).copy()
lab["label"] = lab["label"].astype(int)
lab[["gene", "position", "aa_ref", "aa_alt", "label"]].to_csv(LABELS_OUT, index=False)

print(f"\n>> wrote {LABELS_OUT} ({len(lab)} definitive labels)")
summary = lab.groupby("gene").label.agg(n="count", pathogenic="sum")
summary["pct_pathogenic"] = (100 * summary.pathogenic / summary.n).round(1)
print(summary.to_string())
