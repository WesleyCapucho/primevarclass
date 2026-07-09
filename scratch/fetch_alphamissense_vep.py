"""Fetch AlphaMissense pathogenicity + class for the live ClinVar BRCA1/2
missense set, via Ensembl VEP REST (MANE Select transcript), cached.

Run: python scratch/fetch_alphamissense_vep.py
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

import numpy as np
import pandas as pd

CLIN = "data/raw/clinvar/clinvar_brca_missense_live.csv"
CACHE = "scratch/am_vep_cache.json"
OUT = "data/raw/alphamissense/alphamissense_brca_live.csv"
MANE = {"BRCA1": "ENST00000357654", "BRCA2": "ENST00000380152"}
AA3 = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln", "E": "Glu",
       "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe",
       "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val"}

clin = pd.read_csv(CLIN)
queries = [f"{g}:p.{AA3[r]}{int(p)}{AA3[a]}" for g, r, p, a in
           zip(clin.gene, clin.aa_ref, clin.position, clin.aa_alt)]


def vep_batch(hgvses):
    body = json.dumps({"hgvs_notations": hgvses}).encode()
    url = "https://rest.ensembl.org/vep/human/hgvs?AlphaMissense=1"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
todo = sorted(set(queries) - set(cache.keys()))
print(f">> AM/VEP: {len(cache)} cached, {len(todo)} to fetch")
for i in range(0, len(todo), 150):
    chunk = todo[i:i + 150]
    for k in range(4):
        try:
            res = vep_batch(chunk); break
        except Exception as e:
            print("   retry", k, e); time.sleep(5 * (k + 1))
    else:
        continue
    for item in res:
        cache[item.get("input", "")] = item
    for q in chunk:
        cache.setdefault(q, None)
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
    print(f"   fetched {min(i+150, len(todo))}/{len(todo)}"); time.sleep(1)


def extract(item, g):
    if not item:
        return np.nan, ""
    for t in item.get("transcript_consequences", []):
        if t.get("transcript_id") == MANE.get(g) and "alphamissense" in t:
            am = t["alphamissense"]
            return am.get("am_pathogenicity", np.nan), am.get("am_class", "")
    return np.nan, ""


am_path, am_class = [], []
for q, g in zip(queries, clin.gene):
    p, c = extract(cache.get(q), g)
    am_path.append(p); am_class.append(c)
clin["am_pathogenicity"] = am_path
clin["am_class"] = am_class
clin.to_csv(OUT, index=False)
cov = clin.am_pathogenicity.notna().mean()
print(f">> wrote {OUT}  (AM coverage {cov:.0%})")
print(clin.am_class.value_counts().to_string())
