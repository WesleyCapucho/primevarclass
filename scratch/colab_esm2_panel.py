"""
PrimeVarClass — ESM-2 650M scorer for a hereditary breast/ovarian cancer (HBOC)
gene panel. RUN THIS IN GOOGLE COLAB with a GPU runtime
(Runtime > Change runtime type > GPU: T4/A100).

Paste this whole file into a single Colab cell and run. It:
  1. installs transformers,
  2. downloads each gene's canonical protein sequence from UniProt,
  3. scores EVERY possible missense substitution (all positions x 19 amino acids)
     with the real ESM-2 650M model via the masked-marginal log-likelihood ratio
     LLR = log P(alt | context) - log P(ref | context) (windowed for long proteins),
  4. writes and downloads `esm2_panel_scores.csv` (gene, position, aa_ref, aa_alt, esm2_llr).

It saves progress after every gene, so a disconnect only loses the current gene.
Send me the resulting `esm2_panel_scores.csv` and I'll intersect it with the
real ClinVar / gnomAD / expert-panel labels locally to build the multi-gene study.

Approx. compute: ~14k positions across the panel -> under ~1 h on a T4, less on A100.
"""
# ---------------------------------------------------------------------------
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers>=4.40", "torch", "requests", "tqdm"], check=True)

import io, csv, os, time
import requests
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
from tqdm.auto import tqdm

# --- HBOC panel: gene -> UniProt accession (canonical isoform) ---------------
PANEL = {
    "BRCA1": "P38398", "BRCA2": "P51587", "PALB2": "Q86YC2", "ATM": "Q13315",
    "CHEK2": "O96017", "TP53": "P04637", "PTEN": "P60484", "RAD51C": "O43502",
    "RAD51D": "O75771", "BARD1": "Q99728", "BRIP1": "Q9BX63", "NBN": "O60934",
}
MODEL = "facebook/esm2_t33_650M_UR50D"
WINDOW = 511            # +/- residues around the scored position (<= model context)
BATCH = 16             # masked windows per forward pass
AAS = list("ACDEFGHIKLMNPQRSTVWY")
OUT = "esm2_panel_scores.csv"

device = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", device, "| torch", torch.__version__)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForMaskedLM.from_pretrained(MODEL).to(device).eval()
aa_tok = {a: tok.convert_tokens_to_ids(a) for a in AAS}


def fetch_seq(acc: str) -> str:
    r = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc}.fasta", timeout=60)
    r.raise_for_status()
    return "".join(r.text.splitlines()[1:])


@torch.no_grad()
def score_positions(seq: str):
    """Yield (position1, ref_aa, {alt: llr}) for every residue via masked-marginal."""
    L = len(seq)
    # build one masked window per position
    windows, metas = [], []
    for p in range(L):                       # 0-based residue index
        lo = max(0, p - WINDOW)
        hi = min(L, p + WINDOW + 1)
        sub = list(seq[lo:hi])
        mp = p - lo                          # masked index within the window
        ref = sub[mp]
        if ref not in aa_tok:
            continue
        sub[mp] = tok.mask_token
        windows.append("".join(sub))
        metas.append((p + 1, ref, mp))
    for i in range(0, len(windows), BATCH):
        chunk = windows[i:i + BATCH]
        meta = metas[i:i + BATCH]
        enc = tok(chunk, return_tensors="pt", padding=True).to(device)
        logits = model(**enc).logits            # [B, T, V]
        logp = torch.log_softmax(logits, dim=-1)
        for b, (pos1, ref, mp) in enumerate(meta):
            # +1 for the <cls> token at index 0
            row = logp[b, mp + 1]
            lref = row[aa_tok[ref]].item()
            for alt in AAS:
                if alt == ref:
                    continue
                yield pos1, ref, alt, row[aa_tok[alt]].item() - lref


done_genes = set()
if os.path.exists(OUT):
    with open(OUT) as f:
        done_genes = {r["gene"] for r in csv.DictReader(f)}
    print("resuming; already scored:", sorted(done_genes))

write_header = not os.path.exists(OUT)
with open(OUT, "a", newline="") as fh:
    w = csv.writer(fh)
    if write_header:
        w.writerow(["gene", "position", "aa_ref", "aa_alt", "esm2_llr"])
    for gene, acc in PANEL.items():
        if gene in done_genes:
            continue
        seq = fetch_seq(acc)
        print(f"\n=== {gene} ({acc}) — {len(seq)} aa ===")
        t0 = time.time()
        for pos1, ref, alt, llr in tqdm(score_positions(seq), total=len(seq) * 19):
            w.writerow([gene, pos1, ref, alt, round(llr, 5)])
        fh.flush()
        print(f"    {gene} done in {(time.time()-t0)/60:.1f} min")

print("\nALL DONE ->", OUT)
try:
    from google.colab import files
    files.download(OUT)
except Exception:
    print("Baixe manualmente o arquivo:", OUT)
