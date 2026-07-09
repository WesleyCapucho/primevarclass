"""COLAB (GPU) — Escore ESTRUTURAL por variante com ProteinMPNN.

Isto NÃO é "mais um ESM". O ProteinMPNN pontua cada posição *condicionado à
ESTRUTURA 3D* (não à sequência). Cruzando esse eixo estrutural com o ESM-2
(eixo de sequência/conservação), conseguimos DECOMPOR O MECANISMO de cada
variante deletéria:

    ruim no ESM-2 E no ProteinMPNN  -> desestabiliza o dobramento (núcleo)
    ruim só no ProteinMPNN          -> incompatível com o empacotamento local
    ruim só no ESM-2                -> sítio funcional (conservado p/ função,
                                       não p/ estrutura): interface, catálise

É esse "porquê" que o AlphaMissense (um número) não entrega.

COMO USAR NO COLAB:
  1. Ambiente de execução -> GPU (T4).
  2. Executar tudo.
  3. Ao final baixa `structure_scores_panel.csv`; salve em
     scratch/esm_input/structure_scores_panel.csv no projeto.

Cobre os 8 genes HBOC com modelo AlphaFold único (<=2700 aa). ATM e BRCA2 são
fragmentados no AlphaFold DB e serão tratados à parte (estruturas experimentais).
"""
# ---- célula 1: setup --------------------------------------------------------
# !git clone -q https://github.com/dauparas/ProteinMPNN
# !pip -q install biopython

import json
import os
import subprocess
import urllib.request

import numpy as np

# UniProt dos genes HBOC com modelo AlphaFold ÚNICO (<=2700 aa)
PROTEINS = {
    "BRCA1": "P38398", "BARD1": "Q99728", "CHEK2": "O96017", "PALB2": "Q86YC2",
    "PTEN": "P60484", "RAD51C": "O43502", "RAD51D": "O75771", "TP53": "P04637",
}
MPNN_AA = "ACDEFGHIKLMNPQRSTVWYX"  # ordem do alfabeto do ProteinMPNN
os.makedirs("pdbs", exist_ok=True)

# ---- célula 2: baixar estruturas AlphaFold ---------------------------------
# A URL direta muda de versão (v4->v6...). Resolvemos via API (robusto).
for gene, up in PROTEINS.items():
    dst = f"pdbs/{gene}.pdb"
    if os.path.exists(dst):
        continue
    try:
        meta = json.load(urllib.request.urlopen(
            f"https://alphafold.ebi.ac.uk/api/prediction/{up}", timeout=30))
        pdb_url = meta[0]["pdbUrl"]
        urllib.request.urlretrieve(pdb_url, dst)
        print("baixado", gene, up, "->", pdb_url.split("/")[-1])
    except Exception as e:
        print("FALHOU", gene, up, e)

# ---- célula 3: rodar ProteinMPNN (probabilidades incondicionais) -----------
subprocess.run("python ProteinMPNN/helper_scripts/parse_multiple_chains.py "
               "--input_path=pdbs --output_path=parsed.jsonl", shell=True, check=True)
subprocess.run("python ProteinMPNN/protein_mpnn_run.py --jsonl_path parsed.jsonl "
               "--out_folder mpnn_out --unconditional_probs_only 1 "
               "--num_seq_per_target 1 --batch_size 1", shell=True, check=True)

# ---- célula 4: converter para LLR estrutural por variante ------------------
import glob

import pandas as pd

AA20 = "ACDEFGHIKLMNPQRSTVWY"
idx = {a: MPNN_AA.index(a) for a in AA20}
rows = []
for npz in glob.glob("mpnn_out/unconditional_probs_only/*.npz"):
    gene = os.path.basename(npz).split(".")[0]
    d = np.load(npz)
    logp = d["log_probs"]              # [B, L, 21]
    logp = logp[0] if logp.ndim == 3 else logp
    # sequência a partir do PDB (para o aa_ref)
    seq = None
    with open("parsed.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            if o["name"].split(".")[0] == gene or o["name"] == gene:
                seq = o["seq"]; break
    if seq is None or len(seq) != logp.shape[0]:
        print("pulando", gene, "(seq/len mismatch)"); continue
    for i, ref in enumerate(seq):
        if ref not in idx:
            continue
        for alt in AA20:
            if alt == ref:
                continue
            rows.append({"gene": gene, "position": i + 1, "aa_ref": ref, "aa_alt": alt,
                         "struct_llr": float(logp[i, idx[alt]] - logp[i, idx[ref]])})
out = pd.DataFrame(rows)
out.to_csv("structure_scores_panel.csv", index=False)
print("escrito structure_scores_panel.csv:", out.shape)
print(out.groupby("gene").size())

# ---- célula 5: baixar --------------------------------------------------------
# from google.colab import files
# files.download("structure_scores_panel.csv")
