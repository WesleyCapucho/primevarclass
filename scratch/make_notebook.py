"""Generate a ready-to-run Colab notebook for ESM-2 (650M, GPU) variant scoring."""
import json

def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": [l + "\n" for l in src.split("\n")]}

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in src.split("\n")]}

cells = [
    md("""# PrimeVarClass — Pontuação ESM-2 (GPU)

Este notebook pontua as variantes missense de BRCA1/BRCA2 com o **ESM-2 (650M)** de
Lin et al. (Science, 2023), usando LLR *masked-marginal* em janela.

**Como usar:**
1. `Ambiente de execução` → `Alterar o tipo de ambiente de execução` → **GPU (T4)**.
2. `Ambiente de execução` → `Executar tudo`.
3. Ao final, o arquivo **`esm2_scores.csv`** será baixado automaticamente.
4. Salve esse arquivo em `scratch/esm_input/esm2_scores.csv` no projeto e avise o assistente.

Tempo esperado na T4: ~5–10 minutos."""),
    code("""# 1) Instalar dependências e checar GPU
!pip -q install "transformers>=4.40" "torch" 2>/dev/null
import torch
print("GPU disponível:", torch.cuda.is_available(), "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")"""),
    code("""# 2) Baixar insumos públicos do repositório (sequências UniProt + lista de variantes)
import urllib.request
BASE = "https://raw.githubusercontent.com/WesleyCapucho/primevarclass/main/scratch/esm_input/"
for f in ["BRCA1_P38398.txt", "BRCA2_P51587.txt", "brca_variants_unique.csv"]:
    urllib.request.urlretrieve(BASE + f, f)
import pandas as pd
SEQ = {"BRCA1": open("BRCA1_P38398.txt").read().strip(),
       "BRCA2": open("BRCA2_P51587.txt").read().strip()}
print("BRCA1:", len(SEQ["BRCA1"]), "aa | BRCA2:", len(SEQ["BRCA2"]), "aa")
var = pd.read_csv("brca_variants_unique.csv")
print("variantes:", len(var))"""),
    code("""# 3) Carregar ESM-2 650M
from transformers import AutoTokenizer, AutoModelForMaskedLM
MODEL = "facebook/esm2_t33_650M_UR50D"
dev = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForMaskedLM.from_pretrained(MODEL).to(dev).eval()
AAS = list("ACDEFGHIKLMNPQRSTVWY")
aa_ids = {a: tok.convert_tokens_to_ids(a) for a in AAS}
mask_id = tok.mask_token_id
print("modelo carregado em", dev)"""),
    code("""# 4) Pontuar (masked-marginal em janela; uma passagem por posição -> todas as substituições)
import numpy as np, time
W = 511
pos_df = var[["gene", "position", "aa_ref"]].drop_duplicates().reset_index(drop=True)
cache = {}
t0 = time.time(); skipped = 0
for i, r in pos_df.iterrows():
    g, p, ref = str(r["gene"]), int(r["position"]), str(r["aa_ref"])
    seq = SEQ[g]
    if p < 1 or p > len(seq) or seq[p-1] != ref:
        skipped += 1; continue
    s = max(0, p-1-W); e = min(len(seq), p-1+W+1); win = seq[s:e]; loc = (p-1)-s
    enc = tok(win, return_tensors="pt").to(dev); ids = enc["input_ids"]; tp = loc + 1
    ids[0, tp] = mask_id
    with torch.no_grad():
        lp = torch.log_softmax(model(ids).logits[0, tp], dim=-1)
    cache[(g, p)] = {a: float(lp[aa_ids[a]]) for a in AAS}
    if (i+1) % 200 == 0:
        print(f"{i+1}/{len(pos_df)}  ({time.time()-t0:.0f}s)")
print("posições pontuadas:", len(cache), "| puladas (mismatch):", skipped, f"| {time.time()-t0:.0f}s")"""),
    code("""# 5) Montar LLR por variante e baixar
rows = []
for _, r in var.iterrows():
    g, p, ref, alt = str(r["gene"]), int(r["position"]), str(r["aa_ref"]), str(r["aa_alt"])
    lp = cache.get((g, p))
    if lp and ref in lp and alt in lp:
        rows.append({"gene": g, "position": p, "aa_ref": ref, "aa_alt": alt,
                     "esm2_llr": round(lp[alt] - lp[ref], 5)})
out = pd.DataFrame(rows)
out.to_csv("esm2_scores.csv", index=False)
print("variantes pontuadas:", len(out), "| LLR mean", round(out.esm2_llr.mean(), 3))
# sanity: pathogenic RING cysteines should be strongly negative
print(out[(out.gene=="BRCA1") & (out.position.isin([61, 64]))])
from google.colab import files
files.download("esm2_scores.csv")"""),
]

nb = {"cells": cells,
      "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}

with open("scratch/esm2_colab.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("wrote scratch/esm2_colab.ipynb")
