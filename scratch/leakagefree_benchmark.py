"""Exp #3 — A genuinely leakage-free head-to-head benchmark.

The variants that were VUS/conflicting in ClinVar 2023 and only got a definitive
label by 2026 are the ideal fair test set: NO predictor — ours or the third-party
tools — could have trained on their definitive label, because that label did not
exist when the tools were built. On exactly these variants we compare PrimeVarClass
against AlphaMissense, REVEL and CADD, settling the 'vazamento a favor de terceiros'
question quantitatively rather than by proxy.

Run: python scratch/leakagefree_benchmark.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
CACHE = "scratch/leakagefree_vep_cache.json"
MANE = {"BRCA1": "ENST00000357654", "BRCA2": "ENST00000380152"}
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
AA1TO3 = {v: k for k, v in AA3TO1.items()}
PMIS = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")
key = ["gene", "position", "aa_ref", "aa_alt"]


def definitive(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


def unc23(s):
    s = str(s)
    return ("Uncertain" in s) or ("Conflicting" in s)


# ---- rebuild the reclassified set (VUS 2023 -> definitive 2026) --------------
rows = []
with open("data/raw/clinvar/variant_summary_2023-06_BRCA.tsv", encoding="utf-8") as fh:
    h = fh.readline().rstrip("\n").split("\t"); idx = {n: i for i, n in enumerate(h)}
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) <= idx["Assembly"] or f[idx["Assembly"]] != "GRCh38" or f[idx["GeneSymbol"]] not in ("BRCA1", "BRCA2"):
            continue
        m = PMIS.search(f[idx["Name"]])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
            continue
        rows.append({"gene": f[idx["GeneSymbol"]], "position": int(m.group(2)),
                     "aa_ref": AA3TO1[m.group(1)], "aa_alt": AA3TO1[m.group(3)],
                     "sig_2023": f[idx["ClinicalSignificance"]]})
old = pd.DataFrame(rows).drop_duplicates(key, keep="first")
cur = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
cur["label"] = cur["clinsig"].map(definitive)
old["unc23"] = old["sig_2023"].map(unc23); old["def23"] = old["sig_2023"].map(definitive)
recl = old[old.unc23].merge(cur[key + ["label"]], on=key, how="inner").dropna(subset=["label"])
recl = recl.drop_duplicates(key)
y = recl["label"].astype(int).to_numpy()
print(f">> leakage-free test set (VUS 2023 -> P/B 2026): n={len(recl)} (pat={int(y.sum())})")

# ---- our model: trained on 2023-definitive variants only --------------------
train = old[old.def23.notna()].copy(); train["label"] = train.def23.astype(int)
panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")


def eng(fr):
    fr = fr.copy(); fr["hgvs_p"] = ["p."+r+str(p)+a for r, p, a in zip(fr.aa_ref, fr.position, fr.aa_alt)]
    b, _ = build_dataset_from_dataframe(fr[["gene", "hgvs_p", "position", "aa_ref", "aa_alt"]].assign(label=fr.get("label", 0)),
                                        mode="hybrid", keep_metadata=True)
    return attach_esm_scores(b, panel)


tr = eng(train); tr["label"] = train.label.to_numpy(); te = eng(recl)
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all() and c in te.columns]
pipe = _build_pipeline(tr[cols], random_state=42); pipe.fit(tr[cols], tr.label.to_numpy())
prime = pipe.predict_proba(te[cols])[:, 1]

# ---- third-party scores via Ensembl VEP -------------------------------------
cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
queries = [f"{g}:p.{AA1TO3[r]}{p}{AA1TO3[a]}" for g, p, r, a in
           zip(recl.gene, recl.position, recl.aa_ref, recl.aa_alt)]
todo = sorted(set(queries) - set(cache))
print(f">> VEP: {len(cache)} cached, {len(todo)} to fetch")
for i in range(0, len(todo), 40):
    chunk = todo[i:i+40]
    body = json.dumps({"hgvs_notations": chunk}).encode()
    req = urllib.request.Request(
        "https://rest.ensembl.org/vep/human/hgvs?AlphaMissense=1;CADD=1;dbNSFP=REVEL_score",
        data=body, headers={"Content-Type": "application/json", "Accept": "application/json"})
    for att in range(4):
        try:
            res = json.load(urllib.request.urlopen(req, timeout=240)); break
        except Exception as e:
            print("   retry", att, e); time.sleep(5*(att+1))
    else:
        continue
    for it in res:
        cache[it.get("input", "")] = it
    for q in chunk:
        cache.setdefault(q, None)
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
    time.sleep(1)


def extract(item, g):
    out = {"am": np.nan, "revel": np.nan, "cadd": np.nan}
    if not item:
        return out
    tcs = [t for t in item.get("transcript_consequences", []) if t.get("transcript_id") == MANE.get(g)]
    if not tcs:
        return out
    t = tcs[0]
    out["am"] = (t.get("alphamissense") or {}).get("am_pathogenicity", np.nan)
    rv = [float(x) for x in str(t.get("revel_score", ".")).split(",") if x not in (".", "", "nan")]
    out["revel"] = max(rv) if rv else np.nan
    out["cadd"] = t.get("cadd_raw", np.nan)
    return out


sc = pd.DataFrame([extract(cache.get(q), g) for q, g in zip(queries, recl.gene)])
sc["PrimeVarClass"] = prime; sc["label"] = y


def boot_ci(yy, ss, B=2000, seed=42):
    rng = np.random.default_rng(seed); a = []
    for _ in range(B):
        idx = rng.integers(0, len(yy), len(yy))
        if len(np.unique(yy[idx])) > 1:
            a.append(roc_auc_score(yy[idx], ss[idx]))
    return (round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)) if a else (None, None)


TOOLS = {"PrimeVarClass": "PrimeVarClass", "AlphaMissense": "am", "REVEL": "revel", "CADD": "cadd"}
result = {"full": {}, "pairwise_common": {}}
print("\n=== LEAKAGE-FREE HEAD-TO-HEAD (variantes reclassificadas, cegas a todos) ===")
for name, col in TOOLS.items():
    s = sc[col].to_numpy(float); mask = ~np.isnan(s)
    if len(set(y[mask])) < 2:
        continue
    lo, hi = boot_ci(y[mask], s[mask])
    result["full"][name] = {"n": int(mask.sum()), "auc": round(float(roc_auc_score(y[mask], s[mask])), 3),
                            "ci95": [lo, hi]}
    print(f"   {name:14s} n={int(mask.sum()):3d}  AUC={result['full'][name]['auc']:.3f}  IC95%[{lo},{hi}]")

# fair pairwise: PrimeVarClass vs each competitor on that competitor's covered subset
print("\n   -- comparação pareada justa (mesmo subconjunto coberto) --")
for name, col in [("AlphaMissense", "am"), ("REVEL", "revel"), ("CADD", "cadd")]:
    s = sc[col].to_numpy(float); mask = ~np.isnan(s)
    if len(set(y[mask])) < 2:
        continue
    auc_them = float(roc_auc_score(y[mask], s[mask]))
    auc_us = float(roc_auc_score(y[mask], prime[mask]))
    result["pairwise_common"][name] = {"n": int(mask.sum()), "auc_them": round(auc_them, 3),
                                       "auc_primevarclass": round(auc_us, 3)}
    print(f"   vs {name:14s} (n={int(mask.sum())}): PrimeVarClass={auc_us:.3f}  {name}={auc_them:.3f}")

json.dump(result, open(os.path.join(ANL, "leakagefree_benchmark.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print(f">> wrote {ANL}/leakagefree_benchmark.json")
