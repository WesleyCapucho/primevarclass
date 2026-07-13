# =============================================================================
# PrimeVarClass — ESM-2 650M saturation scoring on Colab GPU (EXPANDED panel)
# -----------------------------------------------------------------------------
# WHY: broaden the multigene generalization test beyond BRCA1/2 + TP53/ATM to a
#      wider set of cancer-predisposition genes where missense is informative,
#      using the SAME model as the flagship (facebook/esm2_t33_650M_UR50D).
# METHOD: masked-marginal LLR (Meier et al., 2021) = logP(alt) - logP(ref),
#         with a +/-511-residue window centered on each masked position — byte
#         for byte the same procedure as colab_esm2_650M_panel.py.
# OUTPUT: esm2_650M_expanded_scores.csv  ->  columns exactly:
#         gene, position, aa_ref, aa_alt, esm2_llr   (saturation: all 19 alts)
#         Same format multigene_panel.py / attach_esm_scores() already consume.
#
# HOW TO RUN:
#   1. Colab -> Runtime -> Change runtime type -> GPU (T4 is enough).
#   2. Paste this whole file into ONE cell and run it.
#   3. When it finishes it auto-downloads esm2_650M_expanded_scores.csv.
#   4. Send that CSV back; it drops into scratch/esm_input/ locally, and the
#      evaluation (multigene_panel.py, expanded) scores each gene that has
#      enough real ClinVar labels.
#
# TIME: ~15-25 min on a T4 (these 5 genes total ~4.4k residues). The score is
#       checkpointed after every gene, so a disconnect loses at most one gene.
#
# NOTE: these 5 genes already passed the label threshold on real ClinVar data
#       (>=40 definitive missense, both classes, minority >=8), so every gene
#       scored here is used in the final panel.
# =============================================================================

import os, sys, time, urllib.request
import torch

try:
    import transformers  # noqa
except Exception:
    os.system(f"{sys.executable} -m pip -q install transformers")

import pandas as pd
from transformers import AutoModelForMaskedLM, AutoTokenizer

MODEL_ID = "facebook/esm2_t33_650M_UR50D"   # the flagship's primary ESM-2
WINDOW   = 511                               # +/- residues around the target
BATCH    = 16
AAS      = list("ACDEFGHIKLMNPQRSTVWY")

# UniProt canonical accessions — FINAL panel: the 5 genes that pass the label
# threshold (>=40 definitive ClinVar missense, both classes, minority >=8), across
# von Hippel-Lindau, Lynch (mismatch repair) and MEN2. (BRCA1/2, TP53, ATM, PALB2,
# CHEK2 are already in esm2_650M_panel_scores.csv and are NOT re-scored here.)
GENES = {
    "VHL":  "P40337",   # 213 aa  — von Hippel-Lindau (117 path / 8 benign)
    "MLH1": "P40692",   # 756 aa  — Lynch, mismatch repair (93 / 21)
    "MSH2": "P43246",   # 934 aa  — Lynch (75 / 37)
    "MSH6": "P52701",   # 1360 aa — Lynch (30 / 12)
    "RET":  "P07949",   # 1114 aa — MEN2 oncogene, GoF missense (47 / 10)
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
            return "".join(raw.splitlines()[1:])
        except Exception as e:
            print("   retry", att, e); time.sleep(3 * (att + 1))
    raise RuntimeError(f"could not fetch {acc}")

print(">> loading", MODEL_ID)
tok   = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForMaskedLM.from_pretrained(MODEL_ID).eval().to(device)
if device == "cuda":
    model = model.half()
MASK  = tok.mask_token_id
AAID  = {a: tok.convert_tokens_to_ids(a) for a in AAS}

def score_gene(gene: str, seq: str) -> list:
    L = len(seq)
    jobs = []
    for p in range(1, L + 1):
        lo = max(0, (p - 1) - WINDOW)
        hi = min(L, (p - 1) + WINDOW + 1)
        jobs.append((p, seq[p - 1], seq[lo:hi], (p - 1) - lo))
    rows, t0 = [], time.time()
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i:i + BATCH]
        enc = tok([w for (_, _, w, _) in batch], return_tensors="pt",
                  padding=True).to(device)
        for row, (_, _, _, mi) in enumerate(batch):
            enc["input_ids"][row, mi + 1] = MASK
        with torch.no_grad():
            logits = model(**enc).logits
        logp = torch.log_softmax(logits.float(), dim=-1)
        for row, (p, ref, _, mi) in enumerate(batch):
            lp = logp[row, mi + 1]
            if ref not in AAID:
                continue
            ref_lp = float(lp[AAID[ref]])
            for alt in AAS:
                if alt == ref:
                    continue
                rows.append({"gene": gene, "position": p, "aa_ref": ref,
                             "aa_alt": alt,
                             "esm2_llr": round(float(lp[AAID[alt]]) - ref_lp, 5)})
        if (i // BATCH) % 20 == 0:
            done = min(i + BATCH, len(jobs))
            print(f"   {gene}: {done}/{len(jobs)} pos  {time.time()-t0:.0f}s", flush=True)
    return rows

all_rows = []
for gene, acc in GENES.items():
    seq = fetch_seq(acc)
    print(f">> {gene} ({acc}) len={len(seq)}", flush=True)
    all_rows.extend(score_gene(gene, seq))
    pd.DataFrame(all_rows).to_csv("esm2_650M_expanded_scores.csv", index=False)
    print(f"   ...checkpoint saved ({len(all_rows)} rows so far)", flush=True)

out = pd.DataFrame(all_rows)
out.to_csv("esm2_650M_expanded_scores.csv", index=False)
print(f">> DONE: {len(out)} rows for {out.gene.nunique()} genes")
print(out.gene.value_counts().to_dict())

try:
    from google.colab import files
    files.download("esm2_650M_expanded_scores.csv")
except Exception as e:
    print("download hook unavailable (not on Colab?):", e)
