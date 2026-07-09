"""
PrimeVarClass — ESM-2 *3B* scorer (upgrade do 650M) para o painel HBOC.
RODE NO GOOGLE COLAB com GPU (Runtime > Change runtime type > GPU; A100 de
preferência — na T4 funciona em fp16, porém mais lento).

Idêntico ao colab_esm2_panel.py, mudando só: modelo 3B, fp16 e batch menor para
caber na memória. Salva por gene (BRCA1/BRCA2 primeiro), então um disconnect só
perde o gene atual. Ao final baixa `esm2_3b_panel_scores.csv` — me envie o arquivo
e eu re-rodo benchmark/calibração/zona-cinzenta com o sinal mais forte.

Custo: 3B é ~5x mais pesado que o 650M. Em A100 roda o painel em ~1–2 h; na T4,
prefira deixar rodando (BRCA1+BRCA2 saem primeiro e já valem por si).
"""
# ---------------------------------------------------------------------------
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "transformers>=4.40", "torch", "requests", "tqdm"], check=True)

import csv, os, time
import requests
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
from tqdm.auto import tqdm

# BRCA1/BRCA2 primeiro (é onde está toda a nossa validação); depois o resto do painel.
PANEL = {
    "BRCA1": "P38398", "BRCA2": "P51587", "PALB2": "Q86YC2", "ATM": "Q13315",
    "CHEK2": "O96017", "TP53": "P04637", "PTEN": "P60484", "RAD51C": "O43502",
    "RAD51D": "O75771", "BARD1": "Q99728", "BRIP1": "Q9BX63", "NBN": "O60934",
}
MODEL = "facebook/esm2_t36_3B_UR50D"   # <-- 3 bilhões de parâmetros
WINDOW = 511
BATCH = 4                              # menor: o 3B ocupa muito mais memória
AAS = list("ACDEFGHIKLMNPQRSTVWY")
OUT = "esm2_3b_panel_scores.csv"

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
print("device:", device, "| dtype:", dtype, "| torch", torch.__version__)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForMaskedLM.from_pretrained(MODEL, torch_dtype=dtype).to(device).eval()
aa_tok = {a: tok.convert_tokens_to_ids(a) for a in AAS}


def fetch_seq(acc: str) -> str:
    r = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc}.fasta", timeout=60)
    r.raise_for_status()
    return "".join(r.text.splitlines()[1:])


@torch.no_grad()
def score_positions(seq: str):
    L = len(seq)
    windows, metas = [], []
    for p in range(L):
        lo = max(0, p - WINDOW); hi = min(L, p + WINDOW + 1)
        sub = list(seq[lo:hi]); mp = p - lo; ref = sub[mp]
        if ref not in aa_tok:
            continue
        sub[mp] = tok.mask_token
        windows.append("".join(sub)); metas.append((p + 1, ref, mp))
    for i in range(0, len(windows), BATCH):
        chunk = windows[i:i + BATCH]; meta = metas[i:i + BATCH]
        enc = tok(chunk, return_tensors="pt", padding=True).to(device)
        logp = torch.log_softmax(model(**enc).logits.float(), dim=-1)
        for b, (pos1, ref, mp) in enumerate(meta):
            row = logp[b, mp + 1]; lref = row[aa_tok[ref]].item()
            for alt in AAS:
                if alt != ref:
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
    print("Baixe manualmente:", OUT)
