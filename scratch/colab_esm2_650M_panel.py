# =============================================================================
# PrimeVarClass — ESM-2 650M saturation scoring on Colab GPU (HBOC panel)
# -----------------------------------------------------------------------------
# WHY: unify the multigene generalization on the SAME model as the flagship
#      (facebook/esm2_t33_650M_UR50D), instead of the 150M CPU fallback.
# METHOD: masked-marginal LLR (Meier et al., 2021) = logP(alt) - logP(ref),
#         with a +/-511-residue window centered on each masked position
#         (identical to scratch/esm2_score_tp53.py, just on GPU + windowed
#         so long proteins like ATM/BRCA2 are handled correctly).
# OUTPUT: esm2_650M_panel_scores.csv  ->  columns exactly:
#         gene, position, aa_ref, aa_alt, esm2_llr   (saturation: all 19 alts)
#         This is the format multigene_panel.py / attach_esm_scores() consume.
#
# HOW TO RUN:
#   1. Colab -> Runtime -> Change runtime type -> GPU (T4 is enough).
#   2. Paste this whole file into ONE cell and run it.
#   3. When it finishes it auto-downloads esm2_650M_panel_scores.csv.
#   4. Send that CSV back; it drops into scratch/esm_input/ locally.
#
# TIME: ~15-35 min on a T4 (ATM at 3056 aa is the bulk). BRCA1/BRCA2 are
#       included so every panel gene comes from one consistent 650M run.
# =============================================================================

import os, sys, time, urllib.request
import torch

# --- install transformers if missing (Colab already has torch) --------------
try:
    import transformers  # noqa
except Exception:
    os.system(f"{sys.executable} -m pip -q install transformers")

import pandas as pd
from transformers import AutoModelForMaskedLM, AutoTokenizer

MODEL_ID = "facebook/esm2_t33_650M_UR50D"   # the flagship's primary ESM-2
WINDOW   = 511                               # +/- residues around the target
BATCH    = 16                                # masked windows per forward pass
AAS      = list("ACDEFGHIKLMNPQRSTVWY")

# UniProt canonical accessions == the sequences used locally (MANE-consistent)
GENES = {
    "TP53":  "P04637",   # 393 aa
    "CHEK2": "O96017",   # 543 aa
    "PALB2": "Q86YC2",   # 1186 aa
    "ATM":   "Q13315",   # 3056 aa
    "BRCA1": "P38398",   # 1863 aa
    "BRCA2": "P51587",   # 3418 aa
}

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f">> device = {device}")
if device == "cpu":
    print("!! WARNING: no GPU detected. Set Runtime -> GPU and re-run.")

def fetch_seq(acc: str) -> str:
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.fasta"
    for att in range(4):
        try:
            raw = urllib.request.urlopen(url, timeout=60).read().decode()
            return "".join(raw.splitlines()[1:])  # drop the FASTA header
        except Exception as e:
            print("   retry", att, e); time.sleep(3 * (att + 1))
    raise RuntimeError(f"could not fetch {acc}")

print(">> loading", MODEL_ID)
tok   = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForMaskedLM.from_pretrained(MODEL_ID).eval().to(device)
if device == "cuda":
    model = model.half()                     # fp16: faster, fits easily
MASK  = tok.mask_token_id
AAID  = {a: tok.convert_tokens_to_ids(a) for a in AAS}

def score_gene(gene: str, seq: str) -> list[dict]:
    """Saturation masked-marginal LLR for every position of `seq`."""
    L = len(seq)
    jobs = []            # (position_1based, ref_aa, window_str, mask_idx_in_window)
    for p in range(1, L + 1):
        lo = max(0, (p - 1) - WINDOW)
        hi = min(L, (p - 1) + WINDOW + 1)
        jobs.append((p, seq[p - 1], seq[lo:hi], (p - 1) - lo))
    rows, t0 = [], time.time()
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i:i + BATCH]
        enc = tok([w for (_, _, w, _) in batch], return_tensors="pt",
                  padding=True).to(device)
        # mask position: +1 offset for the <cls> token that the tokenizer adds
        for row, (_, _, _, mi) in enumerate(batch):
            enc["input_ids"][row, mi + 1] = MASK
        with torch.no_grad():
            logits = model(**enc).logits
        logp = torch.log_softmax(logits.float(), dim=-1)
        for row, (p, ref, _, mi) in enumerate(batch):
            lp = logp[row, mi + 1]
            ref_lp = float(lp[AAID[ref]])
            for alt in AAS:
                if alt == ref:
                    continue
                rows.append({"gene": gene, "position": p, "aa_ref": ref,
                             "aa_alt": alt,
                             "esm2_llr": round(float(lp[AAID[alt]]) - ref_lp, 5)})
        if (i // BATCH) % 20 == 0:
            done = min(i + BATCH, len(jobs))
            print(f"   {gene}: {done}/{len(jobs)} pos  {time.time()-t0:.0f}s",
                  flush=True)
    return rows

all_rows = []
for gene, acc in GENES.items():
    seq = fetch_seq(acc)
    print(f">> {gene} ({acc}) len={len(seq)}", flush=True)
    all_rows.extend(score_gene(gene, seq))
    pd.DataFrame(all_rows).to_csv("esm2_650M_panel_scores.csv", index=False)
    print(f"   ...saved checkpoint ({len(all_rows)} rows so far)", flush=True)

out = pd.DataFrame(all_rows)
out.to_csv("esm2_650M_panel_scores.csv", index=False)
print(f">> DONE: {len(out)} rows for {out.gene.nunique()} genes")
print(out.gene.value_counts().to_dict())

# auto-download to your machine
try:
    from google.colab import files
    files.download("esm2_650M_panel_scores.csv")
except Exception as e:
    print("download hook unavailable (not on Colab?):", e)
