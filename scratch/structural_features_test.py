"""Test whether CONTINUOUS structural features overcome the hard domain-boundary
limitation. We add: (1) dist_to_critical = residue distance to the nearest critical
functional domain (0 inside, gradient outside) — a soft version of the binary
in_critical_domain; (2) plddt = AlphaFold per-residue confidence (structural order)
where available. We refit the domain-only and flagship models WITH and WITHOUT the
new features and compare external AUC. Honest: integrate only if it helps.

Run: python scratch/structural_features_test.py
"""
from __future__ import annotations
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.abspath("src")); os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

esm_df = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")
CRIT = {"BRCA1": [(1, 109), (1642, 1736), (1756, 1855)], "BRCA2": [(2481, 3186)]}


def dist_to_critical(gene, pos):
    spans = CRIT.get(str(gene), [])
    if not spans:
        return np.nan
    d = []
    for lo, hi in spans:
        d.append(0 if lo <= pos <= hi else min(abs(pos - lo), abs(pos - hi)))
    return float(min(d))


def load_plddt():
    """Per-residue pLDDT (B-factor col) from the local AlphaFold BRCA1 model."""
    path = "primevarclass_brca1_engine_execution_results/reference_structures/AF-P38398-F1.pdb"
    if not os.path.exists(path):
        return {}
    pl = {}
    for line in open(path):
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                pl[("BRCA1", int(line[22:26]))] = float(line[60:66])
            except ValueError:
                pass
    return pl


PLDDT = load_plddt()


def add_struct(df):
    df = df.copy()
    df["dist_to_critical"] = [dist_to_critical(g, p) for g, p in zip(df["gene"], df["position"])]
    df["plddt"] = [PLDDT.get((str(g), int(p)), np.nan) for g, p in zip(df["gene"], df["position"])]
    return df


def load(cfg):
    d, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(d["label"], errors="coerce"); k = y.notna()
    d = attach_esm_scores(d.loc[k].reset_index(drop=True), esm_df)
    return add_struct(d), y.loc[k].astype(int).to_numpy()


tr, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([e[0] for e in ext], ignore_index=True)
yext = np.concatenate([e[1] for e in ext])
gsub = get_feature_subsets(tr)
domain = [c for c in gsub["domain_aware"] if c in tr.columns and not tr[c].isna().all()]
flagship = [c for c in gsub["domain_aware_plus_esm"] if c in tr.columns and not tr[c].isna().all()]
STRUCT = ["dist_to_critical", "plddt"]
grp = (tr["gene"].astype(str) + ":" + tr["position"].astype(str)).to_numpy()


def ext_auc(cols):
    c = [x for x in cols if x in tr.columns and x in ext_df.columns]
    p = _build_pipeline(tr[c], random_state=42); p.fit(tr[c], ytr)
    return round(float(roc_auc_score(yext, p.predict_proba(ext_df[c])[:, 1])), 4)


def cv_auc(cols):
    c = [x for x in cols if x in tr.columns]
    X = tr[c]; o = np.zeros(len(ytr))
    for a, b in StratifiedGroupKFold(5, shuffle=True, random_state=42).split(X, ytr, grp):
        p = _build_pipeline(X.iloc[a], random_state=42); p.fit(X.iloc[a], ytr[a]); o[b] = p.predict_proba(X.iloc[b])[:, 1]
    return round(float(roc_auc_score(ytr, o)), 4)


DIST = ["dist_to_critical"]  # clean, both genes; no gene-confound
print(f">> train n={len(tr)} pat={int(ytr.sum())} | external n={len(ext_df)} pat={int(yext.sum())}")
print(f">> plddt coverage (BRCA1 only): {int(tr['plddt'].notna().sum())}/{len(tr)} train")
print("\n=== external AUC (the honest metric): base | +dist | +dist+plddt ===")
print(f"  domain-only            {ext_auc(domain)} | {ext_auc(domain + DIST)} | {ext_auc(domain + STRUCT)}")
print(f"  flagship (domain+ESM)  {ext_auc(flagship)} | {ext_auc(flagship + DIST)} | {ext_auc(flagship + STRUCT)}")
print("\n=== position-blocked CV AUC (internal): base | +dist | +dist+plddt ===")
print(f"  domain-only            {cv_auc(domain)} | {cv_auc(domain + DIST)} | {cv_auc(domain + STRUCT)}")
print(f"  flagship (domain+ESM)  {cv_auc(flagship)} | {cv_auc(flagship + DIST)} | {cv_auc(flagship + STRUCT)}")
