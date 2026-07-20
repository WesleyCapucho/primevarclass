"""Pontuação ESM-2 (masked-marginal LLR) das variantes missense de TP53 e demais
genes do painel HBOC, em CPU.

Calcula logP(alt) - logP(ref) com o resíduo mascarado, em janela de +/-511
posições (Meier et al., 2021). Alimenta o teste de generalização multigênica
(scratch/multigene_panel.py). Para execução em GPU, use os equivalentes de
Colab: scratch/colab_esm2_650M_panel.py.

Entrada : data/raw/clinvar/variant_summary_current_HBOC.tsv
Saída   : scratch/esm_input/esm2_scores_tp53.csv

Run: python scratch/esm2_score_tp53.py
"""
import os, re, time, pandas as pd, torch
from transformers import AutoModelForMaskedLM, AutoTokenizer
import os, sys
sys.path.insert(0, os.path.abspath("src"))
from primevarclass.core import clinvar_binary_label
torch.set_num_threads(max(1, os.cpu_count() or 1))
AAS=list("ACDEFGHIKLMNPQRSTVWY")
AA3TO1={"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G","His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S","Thr":"T","Trp":"W","Tyr":"Y","Val":"V"}
PMIS=re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)")
seq=open("scratch/esm_input/TP53_P04637.txt").read().strip()
def defin(s):
    return clinvar_binary_label(s)
rows=[]
with open("data/raw/clinvar/variant_summary_current_HBOC.tsv",encoding="utf-8") as fh:
    h=fh.readline().rstrip("\n").split("\t"); ix={n:i for i,n in enumerate(h)}
    for line in fh:
        f=line.rstrip("\n").split("\t")
        if len(f)<=ix["Assembly"] or f[ix["Assembly"]]!="GRCh38" or f[ix["GeneSymbol"]]!="TP53": continue
        m=PMIS.search(f[ix["Name"]])
        if not m or m.group(1) not in AA3TO1 or m.group(3) not in AA3TO1 or defin(f[ix["ClinicalSignificance"]]) is None: continue
        rows.append({"gene":"TP53","position":int(m.group(2)),"aa_ref":AA3TO1[m.group(1)],"aa_alt":AA3TO1[m.group(3)]})
var=pd.DataFrame(rows).drop_duplicates()
pos=var[["position","aa_ref"]].drop_duplicates().reset_index(drop=True)
print(f">> TP53 {len(var)} variants, {len(pos)} positions",flush=True)
tok=AutoTokenizer.from_pretrained("facebook/esm2_t30_150M_UR50D")
model=AutoModelForMaskedLM.from_pretrained("facebook/esm2_t30_150M_UR50D").eval()
mid=tok.mask_token_id; aaid={a:tok.convert_tokens_to_ids(a) for a in AAS}
cache={}; t0=time.time()
for i,r in pos.iterrows():
    p=int(r["position"]); ref=r["aa_ref"]
    if p<1 or p>len(seq) or seq[p-1]!=ref: continue
    enc=tok(seq,return_tensors="pt"); ids=enc["input_ids"]; ids[0,p]=mid
    with torch.no_grad(): lg=model(ids).logits[0,p]
    lp=torch.log_softmax(lg,-1); cache[p]={a:float(lp[aaid[a]]) for a in AAS}
    if (i+1)%40==0: print(f"   {i+1}/{len(pos)} {time.time()-t0:.0f}s",flush=True)
out=[{"gene":"TP53","position":int(r["position"]),"aa_ref":r["aa_ref"],"aa_alt":r["aa_alt"],"esm2_llr":round(cache[int(r["position"])][r["aa_alt"]]-cache[int(r["position"])][r["aa_ref"]],5)} for _,r in var.iterrows() if int(r["position"]) in cache and r["aa_alt"] in cache[int(r["position"])] and r["aa_ref"] in cache[int(r["position"])]]
pd.DataFrame(out).to_csv("scratch/esm_input/esm2_scores_tp53.csv",index=False)
print(f">> DONE scored {len(out)} TP53 variants",flush=True)
