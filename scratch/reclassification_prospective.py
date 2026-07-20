"""Exp #2 — Genuinely prospective reclassification test.

Uses a HISTORICAL ClinVar snapshot (2023-06) versus the current release (2026-07)
to identify BRCA1/BRCA2 missense variants that were VUS or 'conflicting' in 2023
and were RESOLVED to pathogenic/benign by 2026. The flagship model is trained ONLY
on variants that were already definitive in the 2023 snapshot — so it is blind to
these variants' eventual labels — and then asked to predict them. This mimics
deploying the tool in mid-2023 and checking, three years later, whether it
foresaw how the community would reclassify the then-uncertain variants.

Run: python scratch/reclassification_prospective.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
from sklearn.metrics import accuracy_score, roc_auc_score

from primevarclass.core import _build_pipeline, build_dataset_from_dataframe, get_feature_subsets
from primevarclass.esm_scores import attach_esm_scores
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
PMIS = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")


def definitive(s):
    lab = clinvar_binary_label(s)
    return np.nan if lab is None else lab


def is_uncertain_2023(s):
    s = str(s)
    return ("Uncertain" in s) or ("Conflicting" in s)


# ---- parse the 2023 snapshot (missense only, GRCh38) ------------------------
rows = []
with open("data/raw/clinvar/variant_summary_2023-06_BRCA.tsv", encoding="utf-8") as fh:
    header = fh.readline().rstrip("\n").split("\t")
    idx = {name: i for i, name in enumerate(header)}
    gi, ni, ci, ai = idx["GeneSymbol"], idx["Name"], idx["ClinicalSignificance"], idx["Assembly"]
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) <= ai or f[ai] != "GRCh38" or f[gi] not in ("BRCA1", "BRCA2"):
            continue
        m = PMIS.search(f[ni])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
            continue
        rows.append({"gene": f[gi], "position": int(m.group(2)),
                     "aa_ref": AA3TO1[m.group(1)], "aa_alt": AA3TO1[m.group(3)],
                     "sig_2023": f[ci]})
old = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"], keep="first")
print(f">> 2023 snapshot: {len(old)} unique BRCA missense variants")

# ---- current (2026) labels --------------------------------------------------
cur = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
cur["label_2026"] = cur["clinsig"].map(definitive)
key = ["gene", "position", "aa_ref", "aa_alt"]
m = old.merge(cur[key + ["label_2026"]], on=key, how="inner")

old["unc23"] = old["sig_2023"].map(is_uncertain_2023)
old["def23"] = old["sig_2023"].map(definitive)
m = m.merge(old[key + ["unc23", "def23", "sig_2023"]], on=key, how="left")

# reclassified: uncertain in 2023 -> definitive in 2026
recl = m[m["unc23"] & m["label_2026"].notna()].copy()
print(f">> reclassified (VUS/conflitante 2023 -> P/B 2026): {len(recl)} "
      f"({int(recl.label_2026.sum())} patogênicas, {int((1-recl.label_2026).sum())} benignas)")

# training set: variants already DEFINITIVE in the 2023 snapshot
train_ids = old[old["def23"].notna()].copy()
train_ids["label"] = train_ids["def23"].astype(int)
print(f">> training on 2023-definitive variants: {len(train_ids)} "
      f"({int(train_ids.label.sum())} patogênicas)")


def engineer(frame):
    frame = frame.copy()
    frame["hgvs_p"] = ["p." + str(r) + str(p) + str(a) for r, p, a in
                       zip(frame.aa_ref, frame.position, frame.aa_alt)]
    built, _ = build_dataset_from_dataframe(
        frame[["gene", "hgvs_p", "position", "aa_ref", "aa_alt"]].assign(label=frame.get("label", 0)),
        mode="hybrid", keep_metadata=True)
    panel = pd.read_csv("scratch/esm_input/esm2_scores_panel.csv")
    return attach_esm_scores(built, panel)


tr = engineer(train_ids); tr["label"] = train_ids["label"].to_numpy()
te = engineer(recl); yte = recl["label_2026"].astype(int).to_numpy()
cols = [c for c in get_feature_subsets(tr)["domain_aware_plus_esm"]
        if c in tr.columns and not tr[c].isna().all() and c in te.columns]
pipe = _build_pipeline(tr[cols], random_state=42); pipe.fit(tr[cols], tr["label"].to_numpy())
p = pipe.predict_proba(te[cols])[:, 1]

auc = float(roc_auc_score(yte, p)) if len(set(yte)) > 1 else float("nan")
acc = float(accuracy_score(yte, (p >= 0.5).astype(int)))
# among those the model called with high confidence
hi = (p >= 0.675) | (p <= 0.255)
acc_hi = float(accuracy_score(yte[hi], (p[hi] >= 0.5).astype(int))) if hi.any() else float("nan")
print(f"\n=== PROSPECTIVE RECLASSIFICATION (model blind to 2026 labels) ===")
print(f"   n reclassified = {len(yte)}  | AUC = {auc:.3f}  | acurácia@0.5 = {acc:.3f}")
print(f"   chamadas de alta confiança: {int(hi.sum())}/{len(yte)}  | acurácia = {acc_hi:.3f}")

out = {"n_2023_snapshot": int(len(old)), "n_reclassified": int(len(yte)),
       "n_reclassified_pathogenic": int(yte.sum()), "n_train_2023_definitive": int(len(tr)),
       "auc": round(auc, 3), "accuracy_0p5": round(acc, 3),
       "n_high_confidence": int(hi.sum()), "accuracy_high_confidence": round(acc_hi, 3)}
json.dump(out, open(os.path.join(ANL, "reclassification_prospective.json"), "w",
                    encoding="utf-8"), indent=2, ensure_ascii=False)
print(f">> wrote {ANL}/reclassification_prospective.json")
