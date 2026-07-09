"""Fetch real ClinVar records for BRCA1/BRCA2 missense variants (live, via NCBI
E-utilities): clinical significance, review status and last-evaluated date.

Used by the AlphaMissense grey-zone complement analysis and by the temporal
(quasi-prospective) validation. No fabricated data — everything comes from the
public ClinVar API and is cached to disk.

Run: python scratch/fetch_clinvar.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

import pandas as pd

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT = "data/raw/clinvar/clinvar_brca_missense_live.csv"
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
        except Exception as e:
            print("   retry", k, e); time.sleep(3 * (k + 1))
    return None


def esearch(gene):
    term = f"{gene}[gene] AND single_gene[prop] AND missense_variant[molecular consequence]"
    url = f"{EUTILS}/esearch.fcgi?db=clinvar&term={urllib.parse.quote(term)}&retmax=100000&retmode=json"
    return _get(url)["esearchresult"]["idlist"]


def esummary(ids):
    url = f"{EUTILS}/esummary.fcgi?db=clinvar&id={','.join(ids)}&retmode=json"
    return _get(url)


rows = []
for gene in ["BRCA1", "BRCA2"]:
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
            clinsig = germ.get("description", "")
            review = germ.get("review_status", "")
            last_eval = germ.get("last_evaluated", "")
            vs = rec.get("variation_set", [{}])
            name = vs[0].get("variation_name", "") if vs else ""
            m = PVAR.search(name)
            if not m or m.group(1) not in AA3 or m.group(3) not in AA3:
                continue
            rows.append({
                "uid": uid, "gene": gene,
                "aa_ref": A3TO1[m.group(1)], "position": int(m.group(2)), "aa_alt": A3TO1[m.group(3)],
                "hgvs_p": f"p.{m.group(1)}{m.group(2)}{m.group(3)}",
                "clinsig": clinsig, "review_status": review, "last_evaluated": last_eval,
            })
        print(f"   {gene}: fetched {min(i+300, len(ids))}/{len(ids)}")
        time.sleep(0.4)

df = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"]).reset_index(drop=True)
df.to_csv(OUT, index=False)
print(f"\n>> wrote {OUT}  ({len(df)} unique missense)")
print("clinical significance distribution:")
print(df.clinsig.value_counts().head(15).to_string())
