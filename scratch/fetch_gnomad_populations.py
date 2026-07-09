"""Fetch per-ancestry allele frequencies for BRCA1/BRCA2 missense variants from
the gnomAD v4 GraphQL API. Used for the health-equity analysis: which variants
are seen mostly in populations under-represented in clinical databases.

Run: python scratch/fetch_gnomad_populations.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.request

import pandas as pd

OUT = "data/raw/gnomad/gnomad_brca_populations.csv"
GENES = {"BRCA1": "P38398", "BRCA2": "P51587"}
# ancestry groups (clinical databases are dominated by European-ancestry data)
EURO = {"nfe", "fin", "asj"}
NONEURO = {"afr", "amr", "eas", "sas", "mid", "ami"}
A3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q", "Glu": "E",
         "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F",
         "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V"}
PV = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})")

QUERY = """{ gene(gene_symbol: "%s", reference_genome: GRCh38) {
  variants(dataset: gnomad_r4) { hgvsp consequence
    exome { populations { id ac an } } genome { populations { id ac an } } } } }"""


def fetch(gene):
    body = json.dumps({"query": QUERY % gene}).encode()
    req = urllib.request.Request("https://gnomad.broadinstitute.org/api", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["data"]["gene"]["variants"]


rows = []
for gene in GENES:
    for attempt in range(3):
        try:
            variants = fetch(gene); break
        except Exception as e:
            print("retry", attempt, e); time.sleep(5)
    else:
        continue
    n = 0
    for v in variants:
        if v.get("consequence") != "missense_variant" or not v.get("hgvsp"):
            continue
        m = PV.search(v["hgvsp"])
        if not m or m.group(1) not in A3TO1 or m.group(3) not in A3TO1:
            continue
        # combine exome + genome AC/AN per population
        pop_ac, pop_an = {}, {}
        for src in ("exome", "genome"):
            if v.get(src):
                for p in v[src]["populations"]:
                    pop_ac[p["id"]] = pop_ac.get(p["id"], 0) + p["ac"]
                    pop_an[p["id"]] = pop_an.get(p["id"], 0) + p["an"]
        af = {p: (pop_ac[p] / pop_an[p]) if pop_an.get(p) else 0.0
              for p in pop_ac if p in EURO | NONEURO}
        if not any(af.values()):
            continue
        predom = max(af, key=af.get)
        rows.append({
            "gene": gene, "aa_ref": A3TO1[m.group(1)], "position": int(m.group(2)),
            "aa_alt": A3TO1[m.group(3)],
            "af_total": sum(pop_ac.values()) / max(sum(pop_an.values()), 1),
            "predominant_pop": predom,
            "predominant_group": "europeu" if predom in EURO else "não-europeu",
            "af_euro": max((af.get(p, 0) for p in EURO), default=0),
            "af_noneuro": max((af.get(p, 0) for p in NONEURO), default=0),
        })
        n += 1
    print(f">> {gene}: {n} missense with ancestry AF")

df = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"])
df.to_csv(OUT, index=False)
print(f">> wrote {OUT}  ({len(df)} variants)")
print(df.predominant_group.value_counts().to_string())
