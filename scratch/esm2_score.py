"""Real ESM-2 masked-marginal scoring of BRCA1/BRCA2 missense variants.

ESM-2 (Lin et al., Science 2023; Meier et al., NeurIPS 2021). Because BRCA1
(1863 aa) and BRCA2 (3418 aa) exceed the model's context, we score each variant
with a WINDOWED masked-marginal LLR: for a residue position p we take the
window [p-W, p+W], mask position p, run one forward pass, and read the
log-softmax over amino acids at p. One forward pass per unique position yields
the LLR for every substitution at that position:

    LLR(ref->alt) = log P(alt | context, pos masked) - log P(ref | context)

Run: python scratch/esm2_score.py
"""
from __future__ import annotations

import os
import time

import pandas as pd
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

torch.set_num_threads(max(1, os.cpu_count() or 1))
MODEL = "facebook/esm2_t30_150M_UR50D"
W = 510  # half-window (window <= ~1021 residues, under ESM-2's 1024 limit)
OUT = "scratch/esm_input/esm2_scores.csv"

SEQ = {
    "BRCA1": open("scratch/esm_input/BRCA1_P38398.txt", encoding="utf-8").read().strip(),
    "BRCA2": open("scratch/esm_input/BRCA2_P51587.txt", encoding="utf-8").read().strip(),
}
AAS = list("ACDEFGHIKLMNPQRSTVWY")

print(f">> loading {MODEL} (CPU) ...")
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForMaskedLM.from_pretrained(MODEL)
model.eval()
mask_id = tok.mask_token_id
aa_ids = {a: tok.convert_tokens_to_ids(a) for a in AAS}

var = pd.read_csv("scratch/esm_input/brca_variants_unique.csv")
positions = var[["gene", "position", "aa_ref"]].drop_duplicates().reset_index(drop=True)
print(f">> scoring {len(positions)} unique positions ({len(var)} variants) ...")

logp_cache = {}  # (gene,pos) -> {aa: logprob}
t0 = time.time(); done = 0; skipped = 0
for _, r in positions.iterrows():
    gene, pos, ref = str(r["gene"]), int(r["position"]), str(r["aa_ref"])
    seq = SEQ[gene]
    if pos < 1 or pos > len(seq) or seq[pos - 1] != ref:
        skipped += 1
        continue
    start = max(0, pos - 1 - W)
    end = min(len(seq), pos - 1 + W + 1)
    window = seq[start:end]
    local = (pos - 1) - start  # 0-based index in window
    enc = tok(window, return_tensors="pt")
    ids = enc["input_ids"]
    tpos = local + 1  # +1 for the <cls> token
    ids[0, tpos] = mask_id
    with torch.no_grad():
        logits = model(ids).logits[0, tpos]
    logprobs = torch.log_softmax(logits, dim=-1)
    logp_cache[(gene, pos)] = {a: float(logprobs[aa_ids[a]]) for a in AAS}
    done += 1
    if done % 100 == 0:
        el = time.time() - t0
        print(f"   {done}/{len(positions)}  ({el:.0f}s, {el/done:.2f}s/pos)")

rows = []
for _, r in var.iterrows():
    gene, pos, ref, alt = str(r["gene"]), int(r["position"]), str(r["aa_ref"]), str(r["aa_alt"])
    lp = logp_cache.get((gene, pos))
    if lp is None or ref not in lp or alt not in lp:
        continue
    rows.append({"gene": gene, "position": pos, "aa_ref": ref, "aa_alt": alt,
                 "esm2_llr": round(lp[alt] - lp[ref], 5)})
out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print(f">> DONE. scored {len(out)} variants, skipped {skipped} positions (seq mismatch).")
print(f">> wrote {OUT}  | LLR range [{out.esm2_llr.min():.2f}, {out.esm2_llr.max():.2f}] mean {out.esm2_llr.mean():.2f}")
