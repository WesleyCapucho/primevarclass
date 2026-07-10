"""Adds (a) AUPRC/MCC for every competitor on the same 836 external variants,
and (b) EVE (Frazer et al., 2021) — the fair, NON-circular comparator (an
unsupervised generative model, like our ESM-2 component, never trained on ClinVar
labels). EVE scores are pulled from dbNSFP via myvariant.info, matched at the
amino-acid level (dual genomic orientation + HGVSp validation so the minus-strand
BRCA1 never grabs the wrong SNV). All aligned to the exact benchmark_sota order.

Run: python scratch/eve_metrics_benchmark.py
"""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.parse
import numpy as np, pandas as pd

sys.path.insert(0, os.path.abspath("src")); os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score, average_precision_score, matthews_corrcoef, roc_curve
from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

OUT = "primevarclass_manuscript_analysis"
CACHE = "scratch/benchmark_cache.json"
EVE_CACHE = "scratch/eve_cache.json"
RNG = 42
MANE = {"BRCA1": "ENST00000357654", "BRCA2": "ENST00000380152"}
AA3 = {"A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys", "Q": "Gln",
       "E": "Glu", "G": "Gly", "H": "His", "I": "Ile", "L": "Leu", "K": "Lys",
       "M": "Met", "F": "Phe", "P": "Pro", "S": "Ser", "T": "Thr", "W": "Trp",
       "Y": "Tyr", "V": "Val"}
COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}
esm_df = pd.read_csv("scratch/esm_input/esm2_scores.csv")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), esm_df)
    return df, y.loc[keep].astype(int).to_numpy()


tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])
cols = [c for c in get_feature_subsets(tr_df)["domain_aware_plus_esm"]
        if c in tr_df.columns and c in ext_df.columns and not tr_df[c].isna().all()]
pipe = _build_pipeline(tr_df[cols], random_state=RNG); pipe.fit(tr_df[cols], ytr)
prime = pipe.predict_proba(ext_df[cols])[:, 1]
gene = ext_df["gene"].astype(str).to_numpy()
pos = ext_df["position"].astype(int).to_numpy()
ref1 = ext_df["aa_ref"].astype(str).str.upper().to_numpy()
alt1 = ext_df["aa_alt"].astype(str).str.upper().to_numpy()
queries = [f"{g}:p.{AA3.get(r,r)}{p}{AA3.get(a,a)}" for g, r, p, a in zip(gene, ref1, pos, alt1)]
print(f">> external n={len(ext_df)} (pat={int(yext.sum())})")

cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def parse_revel(v):
    vals = [float(x) for x in str(v).split(",") if x not in (".", "", "nan")]
    return max(vals) if vals else np.nan


def extract(item, g):
    out = {"am": np.nan, "revel": np.nan, "cadd": np.nan, "polyphen": np.nan,
           "sift": np.nan, "chrom": None, "gpos": None, "a1": None, "a2": None}
    if not item:
        return out
    out["chrom"] = item.get("seq_region_name"); out["gpos"] = item.get("start")
    al = str(item.get("allele_string", "")).split("/")
    if len(al) == 2:
        out["a1"], out["a2"] = al[0], al[1]
    tcs = item.get("transcript_consequences", [])
    pick = [t for t in tcs if t.get("transcript_id") == MANE.get(g)] or \
           [t for t in tcs if t.get("gene_symbol") == g and "alphamissense" in t]
    if pick:
        t = pick[0]
        out["am"] = (t.get("alphamissense") or {}).get("am_pathogenicity", np.nan)
        out["revel"] = parse_revel(t.get("revel_score", "."))
        out["cadd"] = t.get("cadd_raw", np.nan)
        if t.get("sift_score") is not None:
            out["sift"] = 1.0 - float(t["sift_score"])
        if t.get("polyphen_score") is not None:
            out["polyphen"] = float(t["polyphen_score"])
    return out


meta = pd.DataFrame([extract(cache.get(q), g) for q, g in zip(queries, gene)])

# ---------------------------------------------------------------- EVE fetch
eve_cache = json.load(open(EVE_CACHE, encoding="utf-8")) if os.path.exists(EVE_CACHE) else {}


def fetch_eve(chrom, gpos, a1, a2, gname, hgvs_short):
    """Return EVE score for the variant, matching aa change; None if unavailable."""
    if not chrom or gpos is None or (isinstance(gpos, float) and np.isnan(gpos)) or not a1 or not a2:
        return None
    gpos = int(gpos); chrom = str(chrom).replace(".0", "")  # avoid float '43104258.0'
    for x, y in [(a1, a2), (COMP.get(a1, "?"), COMP.get(a2, "?"))]:
        hid = f"chr{chrom}:g.{gpos}{x}>{y}"
        try:
            url = ("https://myvariant.info/v1/variant/" + urllib.parse.quote(hid) +
                   "?assembly=hg38&fields=dbnsfp.eve.score,dbnsfp.hgvsp,dbnsfp.genename")
            r = json.load(urllib.request.urlopen(url, timeout=45))
        except Exception:
            continue
        d = r.get("dbnsfp", {}) if isinstance(r, dict) else {}
        if not d:
            continue
        gs = d.get("genename"); gs = gs if isinstance(gs, list) else [gs]
        hp = d.get("hgvsp"); hp = hp if isinstance(hp, list) else [hp]
        if gname in gs and any(hgvs_short == str(h) for h in hp):
            eve = d.get("eve")
            if isinstance(eve, dict) and eve.get("score") is not None:
                return float(eve["score"])
    return None


eve_vals = []
todo = 0
for i, (g, p, r, a) in enumerate(zip(gene, pos, ref1, alt1)):
    key = f"{g}:p.{r}{p}{a}"
    if key not in eve_cache:
        hgvs_short = f"p.{r}{p}{a}"
        eve_cache[key] = fetch_eve(meta.chrom[i], meta.gpos[i], meta.a1[i], meta.a2[i], g, hgvs_short)
        todo += 1
        if todo % 25 == 0:
            json.dump(eve_cache, open(EVE_CACHE, "w"), ensure_ascii=False)
            print(f"   EVE fetched {todo}...", flush=True)
        time.sleep(0.05)
    eve_vals.append(eve_cache[key])
json.dump(eve_cache, open(EVE_CACHE, "w"), ensure_ascii=False)
eve = np.array([np.nan if v is None else float(v) for v in eve_vals])
print(f">> EVE coverage: {int((~np.isnan(eve)).sum())}/{len(eve)}")

# ---------------------------------------------------------------- metrics
scores = meta[["am", "revel", "cadd"]].copy()
scores["PrimeVarClass"] = prime; scores["EVE"] = eve; scores["label"] = yext
scores.to_csv(os.path.join(OUT, "benchmark_scores_with_eve.csv"), index=False)


def mcc_youden(y, s):
    m = ~np.isnan(s)
    if len(set(y[m])) < 2:
        return None
    fpr, tpr, thr = roc_curve(y[m], s[m]); j = np.argmax(tpr - fpr)
    return round(float(matthews_corrcoef(y[m], (s[m] >= thr[j]).astype(int))), 3)


def boot_ci(y, s, B=2000, seed=RNG):
    m = ~np.isnan(s); yy, ss = y[m], s[m]; rng = np.random.default_rng(seed); a = []
    for _ in range(B):
        idx = rng.integers(0, len(yy), len(yy))
        if len(np.unique(yy[idx])) > 1:
            a.append(roc_auc_score(yy[idx], ss[idx]))
    return [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)]


def _midrank(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]:
            j += 1
        T[i:j] = 0.5 * (i + j - 1) + 1; i = j
    out = np.empty(N); out[J] = T; return out


def delong(y, p1, p2):
    m = (~np.isnan(p1)) & (~np.isnan(p2)); y, p1, p2 = y[m], p1[m], p2[m]
    pos_i, neg_i = y == 1, y == 0
    m_, n_ = int(pos_i.sum()), int(neg_i.sum())
    if m_ < 2 or n_ < 2:
        return None, None
    res = {}
    for name, pp in [("1", p1), ("2", p2)]:
        X, Y = pp[pos_i], pp[neg_i]
        tx, ty, tz = _midrank(X), _midrank(Y), _midrank(np.r_[X, Y])
        auc = (tz[:m_].sum() - tx.sum()) / m_ / n_ + 0.5
        v01 = (tz[:m_] - tx) / n_; v10 = 1 - (tz[m_:] - ty) / m_
        res[name] = (auc, v01, v10)
    (a1, v01a, v10a), (a2, v01b, v10b) = res["1"], res["2"]
    s01 = np.cov(np.vstack([v01a, v01b])); s10 = np.cov(np.vstack([v10a, v10b]))
    S = s01 / m_ + s10 / n_
    var = S[0, 0] + S[1, 1] - 2 * S[0, 1]
    if var <= 0:
        return round(a1 - a2, 4), 1.0
    from scipy.stats import norm
    z = (a1 - a2) / np.sqrt(var)
    return round(float(a1 - a2), 4), round(float(2 * (1 - norm.cdf(abs(z)))), 4)


TOOLS = {"PrimeVarClass": "PrimeVarClass", "EVE": "EVE", "AlphaMissense": "am",
         "REVEL": "revel", "CADD": "cadd"}
result = {"metrics": {}, "delong_vs_prime": {}}
y = yext
print("\n=== tool            n    AUC    AUPRC  MCC@J   IC95%(AUC) ===")
base = float(y.mean())
for name, col in TOOLS.items():
    s = scores[col].to_numpy(float); m = ~np.isnan(s)
    if len(set(y[m])) < 2:
        continue
    auc = round(float(roc_auc_score(y[m], s[m])), 3)
    ap = round(float(average_precision_score(y[m], s[m])), 3)
    result["metrics"][name] = {"n": int(m.sum()), "auc": auc, "auprc": ap,
                               "mcc_youden": mcc_youden(y, s), "ci95": boot_ci(y, s)}
    print(f"  {name:14s} {int(m.sum()):4d}  {auc:.3f}  {ap:.3f}  "
          f"{result['metrics'][name]['mcc_youden']}  {result['metrics'][name]['ci95']}")
print(f"  (prevalência de patogênicas = {base:.3f}; AUPRC trivial = {base:.3f})")

# EVE vs PrimeVarClass on EVE-covered subset (fair, both non-circular)
for name, col in [("EVE", "EVE"), ("AlphaMissense", "am"), ("REVEL", "revel"), ("CADD", "cadd")]:
    d, p = delong(y, scores[col].to_numpy(float), prime)
    if d is not None:
        result["delong_vs_prime"][name] = {"delta_auc_tool_minus_prime": d, "p": p}
        print(f"  DeLong {name:14s} vs Prime: delta={d:+.4f}  p={p}")

json.dump(result, open(os.path.join(OUT, "eve_metrics_benchmark.json"), "w",
                       encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n>> wrote {OUT}/eve_metrics_benchmark.json and benchmark_scores_with_eve.csv")
