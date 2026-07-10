"""ESM-2 650M masked-marginal LLR scoring for the HBOC panel (TP53, PALB2, CHEK2,
ATM) definitive missense variants — same procedure as the BRCA flagship, run
locally on CPU. Windowed (half-window 510) for the long proteins.

Run: python scratch/esm2_score_hboc.py
"""
from __future__ import annotations

import os
import re
import time

import pandas as pd
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

torch.set_num_threads(max(1, os.cpu_count() or 1))
MODEL = "facebook/esm2_t33_650M_UR50D"
W = 510
OUT = "scratch/esm_input/esm2_scores_hboc.csv"
AAS = list("ACDEFGHIKLMNPQRSTVWY")
AA3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
          "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
          "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
          "Tyr": "Y", "Val": "V"}
PMIS = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")
SEQFILE = {"TP53": "scratch/esm_input/TP53_P04637.txt",
           "PALB2": "scratch/esm_input/PALB2_Q86YC2.txt",
           "CHEK2": "scratch/esm_input/CHEK2_O96017.txt",
           "ATM": "scratch/esm_input/ATM_Q13315.txt"}
SEQ = {g: open(p, encoding="utf-8").read().strip() for g, p in SEQFILE.items()}


def definitive(s):
    s = str(s)
    if "Conflicting" in s:
        return None
    if "Pathogenic" in s:
        return 1
    if "Benign" in s:
        return 0
    return None


rows = []
with open("data/raw/clinvar/variant_summary_current_HBOC.tsv", encoding="utf-8") as fh:
    header = fh.readline().rstrip("\n").split("\t"); idx = {n: i for i, n in enumerate(header)}
    gi, ni, ci, ai = idx["GeneSymbol"], idx["Name"], idx["ClinicalSignificance"], idx["Assembly"]
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) <= ai or f[ai] != "GRCh38" or f[gi] not in SEQ:
            continue
        m = PMIS.search(f[ni])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1:
            continue
        if definitive(f[ci]) is None:
            continue
        rows.append({"gene": f[gi], "position": int(m.group(2)),
                     "aa_ref": AA3TO1[m.group(1)], "aa_alt": AA3TO1[m.group(3)]})
var = pd.DataFrame(rows).drop_duplicates(["gene", "position", "aa_ref", "aa_alt"])
positions = var[["gene", "position", "aa_ref"]].drop_duplicates().reset_index(drop=True)
print(f">> {len(var)} variants, {len(positions)} unique positions")

print(f">> loading {MODEL} (CPU)...")
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForMaskedLM.from_pretrained(MODEL); model.eval()
mask_id = tok.mask_token_id
aa_ids = {a: tok.convert_tokens_to_ids(a) for a in AAS}

cache = {}; t0 = time.time(); done = 0; skipped = 0
for _, r in positions.iterrows():
    gene, pos, ref = str(r["gene"]), int(r["position"]), str(r["aa_ref"])
    seq = SEQ[gene]
    if pos < 1 or pos > len(seq) or seq[pos - 1] != ref:
        skipped += 1; continue
    start = max(0, pos - 1 - W); end = min(len(seq), pos - 1 + W + 1)
    window = seq[start:end]; local = (pos - 1) - start
    enc = tok(window, return_tensors="pt"); ids = enc["input_ids"]; tpos = local + 1
    ids[0, tpos] = mask_id
    with torch.no_grad():
        logits = model(ids).logits[0, tpos]
    logprobs = torch.log_softmax(logits, dim=-1)
    cache[(gene, pos)] = {a: float(logprobs[aa_ids[a]]) for a in AAS}
    done += 1
    if done % 50 == 0:
        el = time.time() - t0
        print(f"   {done}/{len(positions)} ({el:.0f}s, {el/done:.2f}s/pos)")

out = []
for _, r in var.iterrows():
    lp = cache.get((str(r["gene"]), int(r["position"])))
    if lp and r["aa_ref"] in lp and r["aa_alt"] in lp:
        out.append({"gene": r["gene"], "position": int(r["position"]), "aa_ref": r["aa_ref"],
                    "aa_alt": r["aa_alt"], "esm2_llr": round(lp[r["aa_alt"]] - lp[r["aa_ref"]], 5)})
pd.DataFrame(out).to_csv(OUT, index=False)
print(f">> DONE. scored {len(out)}, skipped {skipped} positions. wrote {OUT}")
