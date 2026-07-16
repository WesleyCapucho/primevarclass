"""Head-to-head benchmark of PrimeVarClass (flagship domain + ESM-2) against
established missense predictors — AlphaMissense, REVEL, CADD, PolyPhen-2, SIFT —
on the SAME external cohorts and labels used throughout the paper.

Third-party scores are pulled from the Ensembl VEP REST API (MANE Select
transcript), cached locally. Notes:
  * PrimeVarClass is trained on the internal cohort and evaluated on the external
    cohorts under the paper's anti-leakage protocol.
  * The third-party tools are used as published (their own training data is
    outside our control and may overlap ClinVar labels -> if anything this
    favours them). We benchmark them on the same test variants for a fair,
    reproducible comparison.

Run: python scratch/benchmark_sota.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

RNG = 42
OUT = "primevarclass_manuscript_analysis"
CACHE = "scratch/benchmark_cache.json"
os.makedirs(OUT, exist_ok=True)
MANE = {"BRCA1": "ENST00000357654", "BRCA2": "ENST00000380152"}

esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
    return df, y.loc[keep].astype(int).to_numpy()


# ---------------------------------------------------------------- our model
tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])
print(f">> external cohort n={len(ext_df)}  (pathogenic={int(yext.sum())}, benign={int((1-yext).sum())})")

cols = [c for c in get_feature_subsets(tr_df)["domain_aware_plus_esm"]
        if c in tr_df.columns and c in ext_df.columns and not tr_df[c].isna().all()]
pipe = _build_pipeline(tr_df[cols], random_state=RNG); pipe.fit(tr_df[cols], ytr)
prime = pipe.predict_proba(ext_df[cols])[:, 1]

# variant identifiers for VEP (GENE:p.RefPosAlt, 3-letter HGVS)
AA3 = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln",
       "E": "Glu", "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys",
       "M": "Met", "F": "Phe", "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp",
       "Y": "Tyr", "V": "Val"}


def three(aa):
    aa = str(aa).strip()
    return aa if len(aa) == 3 else AA3.get(aa.upper(), aa)


gene = ext_df["gene"].astype(str).to_numpy()
pos = ext_df["position"].astype(int).to_numpy()
ref3 = [three(a) for a in ext_df["aa_ref"]]
alt3 = [three(a) for a in ext_df["aa_alt"]]
queries = [f"{g}:p.{r}{p}{a}" for g, r, p, a in zip(gene, ref3, pos, alt3)]


# ---------------------------------------------------------------- VEP fetch
def load_cache():
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    return {}


def vep_batch(hgvses):
    body = json.dumps({"hgvs_notations": hgvses}).encode()
    url = ("https://rest.ensembl.org/vep/human/hgvs"
           "?AlphaMissense=1;CADD=1;dbNSFP=REVEL_score")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json",
                                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r)


cache = load_cache()
todo = sorted(set(queries) - set(cache.keys()))
print(f">> VEP: {len(cache)} cached, {len(todo)} to fetch")
B = 40
for i in range(0, len(todo), B):
    chunk = todo[i:i + B]
    for attempt in range(4):
        try:
            res = vep_batch(chunk)
            break
        except Exception as e:
            print(f"   retry {attempt} ({e})"); time.sleep(5 * (attempt + 1))
    else:
        print("   giving up on chunk"); continue
    for item in res:
        cache[item.get("input", "")] = item
    for q in chunk:                       # mark unfound so we don't refetch
        cache.setdefault(q, None)
    json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
    print(f"   fetched {min(i+B,len(todo))}/{len(todo)}"); time.sleep(1)


def parse_revel(v):
    vals = [float(x) for x in str(v).split(",") if x not in (".", "", "nan")]
    return max(vals) if vals else np.nan


def extract(item, g):
    """Return dict of third-party scores from the MANE transcript."""
    out = {"am": np.nan, "revel": np.nan, "cadd": np.nan,
           "polyphen": np.nan, "sift": np.nan}
    if not item:
        return out
    tcs = item.get("transcript_consequences", [])
    pick = [t for t in tcs if t.get("transcript_id") == MANE.get(g)]
    if not pick:
        pick = [t for t in tcs if t.get("gene_symbol") == g and "alphamissense" in t]
    if not pick:
        return out
    t = pick[0]
    am = t.get("alphamissense") or {}
    out["am"] = am.get("am_pathogenicity", np.nan)
    out["revel"] = parse_revel(t.get("revel_score", "."))
    out["cadd"] = t.get("cadd_raw", np.nan)
    # SIFT is deleterious when LOW -> flip so higher = more pathogenic
    if t.get("sift_score") is not None:
        out["sift"] = 1.0 - float(t["sift_score"])
    if t.get("polyphen_score") is not None:
        out["polyphen"] = float(t["polyphen_score"])
    return out


rows = [extract(cache.get(q), g) for q, g in zip(queries, gene)]
scores = pd.DataFrame(rows)
scores["PrimeVarClass"] = prime
scores["label"] = yext

TOOLS = {"PrimeVarClass (domínio + ESM-2)": "PrimeVarClass",
         "AlphaMissense": "am", "REVEL": "revel", "CADD": "cadd",
         "PolyPhen-2": "polyphen", "SIFT": "sift"}


# ---------------------------------------------------------------- stats
def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    T2 = np.empty(N); T2[J] = T; return T2


def delong(y, p1, p2):
    o = np.argsort(-y); y = y[o]; m = int(y.sum())
    P = np.vstack((p1[o], p2[o])); k, n = P.shape
    tx = np.empty([k, m]); ty = np.empty([k, n - m]); tz = np.empty([k, n])
    for r in range(k):
        tx[r] = _midrank(P[r, :m]); ty[r] = _midrank(P[r, m:]); tz[r] = _midrank(P[r])
    aucs = (tz[:, :m].sum(1) / m - (m + 1) / 2.0) / (n - m)
    v01 = (tz[:, :m] - tx) / (n - m); v10 = 1 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / (n - m)
    var = max(np.array([[1, -1]]).dot(cov).dot(np.array([[1], [-1]]))[0, 0], 1e-12)
    return float(aucs[0]), float(aucs[1]), float(2 * norm.sf(abs((aucs[0] - aucs[1]) / np.sqrt(var))))


def boot_ci(y, s, B=2000, seed=RNG):
    rng = np.random.default_rng(seed); n = len(y); a = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        a.append(roc_auc_score(y[idx], s[idx]))
    return float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


results = {}
prime_col = scores["PrimeVarClass"].to_numpy()
print("\n===== BENCHMARK (external cohorts, same variants) =====")
print(f"{'Tool':32s} {'n':>5s} {'AUC':>7s}  {'IC95%':>16s}  {'DeLong vs Prime':>16s}")
for label, col in TOOLS.items():
    s = scores[col].to_numpy(dtype=float)
    m = ~np.isnan(s)
    y = yext[m]; sv = s[m]
    if len(np.unique(y)) < 2:
        continue
    auc = roc_auc_score(y, sv); lo, hi = boot_ci(y, sv)
    # DeLong vs PrimeVarClass on the intersection where both are present
    mm = m & ~np.isnan(prime_col)
    if col == "PrimeVarClass":
        p = "-"
    else:
        _, _, pv = delong(yext[mm], prime_col[mm], scores[col].to_numpy(float)[mm])
        p = f"{pv:.2g}"
    results[label] = {"n": int(m.sum()), "auc": auc, "ci": [lo, hi],
                      "delong_vs_prime_p": None if col == "PrimeVarClass" else pv}
    print(f"{label:32s} {int(m.sum()):5d} {auc:7.4f}  [{lo:.3f}, {hi:.3f}]  {p:>16s}")

json.dump(results, open(os.path.join(OUT, "benchmark_sota.json"), "w"),
          indent=2, ensure_ascii=False)
scores.to_csv(os.path.join(OUT, "benchmark_scores.csv"), index=False)
print(f"\n>> wrote {OUT}/benchmark_sota.json and benchmark_scores.csv")
