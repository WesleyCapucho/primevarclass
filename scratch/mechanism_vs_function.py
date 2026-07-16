"""Validate the mechanism decomposition against EXPERIMENTAL function.

If our structure-based mechanism labels are meaningful, then variants at residues
we call fold-core / zinc-coordination / interface / phosphopeptide-pocket should
lose more function in a deep-mutational-scanning assay than surface variants.

We use the Starita et al. (2015) homology-directed-repair (HDR) assay for BRCA1
(MaveDB urn:mavedb:00000081-a-2), which uses correct BRCA1 protein numbering and
covers the RING + BRCT domains. Lower HDR score = greater loss of function.

Run: python scratch/mechanism_vs_function.py
"""
from __future__ import annotations

import json
import os
import re
import warnings

import numpy as np
import pandas as pd
from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley
from scipy.stats import kruskal, spearmanr

warnings.filterwarnings("ignore")
ANL = "primevarclass_manuscript_analysis"
FIG = "docs/suplementar/figuras/fig_mechanism_vs_function.png"
MAXASA = {"A": 129, "R": 274, "N": 195, "D": 193, "C": 167, "E": 223, "Q": 225,
          "G": 104, "H": 224, "I": 197, "L": 201, "K": 236, "M": 224, "F": 240,
          "P": 159, "S": 155, "T": 172, "W": 285, "Y": 263, "V": 174}
T2O = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLU": "E", "GLN": "Q",
       "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F",
       "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V"}
A3TO1 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q", "Glu": "E",
         "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F",
         "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V"}


def per_residue(pdb, chain, lig_atoms, kind):
    s = PDBParser(QUIET=True).get_structure("m", pdb)[0]
    tgt = s[chain]
    sr = ShrakeRupley(); sr.compute(tgt, level="R")
    alone = {r.id[1]: r.sasa for r in tgt if r.id[0] == " "}
    sr.compute(s, level="R"); cplx = {r.id[1]: r.sasa for r in tgt if r.id[0] == " "}
    zns = [a for a in s.get_atoms() if a.element == "ZN"]
    out = {}
    for r in tgt:
        if r.id[0] != " " or r.resname not in T2O:
            continue
        p = r.id[1]; aa = T2O[r.resname]
        rsa = min(1.0, alone.get(p, 0) / MAXASA[aa])
        zd = min((a - z for a in r for z in zns), default=np.inf)
        ld = min((a - b for a in r for b in lig_atoms), default=np.inf) if lig_atoms else np.inf
        iface = (alone.get(p, 0) - cplx.get(p, 0)) > 5.0
        if kind == "RING" and zd < 3.0:
            m = "Coordenação de zinco"
        elif kind == "RING" and iface:
            m = "Interface BARD1"
        elif kind == "BRCT" and ld < 4.5:
            m = "Bolso de fosfopeptídeo"
        elif rsa < 0.15:
            m = "Núcleo (dobramento)"
        elif rsa < 0.40:
            m = "Intermediário"
        else:
            m = "Superfície"
        out[p] = (m, rsa)
    return out


mech = {}
mech.update(per_residue("scratch/pdb/1JM7.pdb", "A", None, "RING"))
s2 = PDBParser(QUIET=True).get_structure("t", "scratch/pdb/1T29.pdb")[0]
pep = [a for a in s2["B"].get_atoms()]
mech.update(per_residue("scratch/pdb/1T29.pdb", "A", pep, "BRCT"))

# ---- Starita HDR functional scores -----------------------------------------
dms = pd.read_csv("data/raw/mavedb/brca_function_scores.csv")
dms = dms[dms.score_set_urn == "urn:mavedb:00000081-a-2"].copy()
PV = re.compile(r"^p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$")
rows = []
for _, r in dms.iterrows():
    m = PV.match(str(r.hgvs_p))
    if not m or m.group(1) not in A3TO1:
        continue
    pos = int(m.group(2))
    if pos in mech and pd.notna(r.score):
        rows.append({"position": pos, "hdr": r.score, "mechanism": mech[pos][0], "rsa": mech[pos][1]})
d = pd.DataFrame(rows)
print(f">> Starita HDR variants mapped to a mechanism: {len(d)}")

order = ["Coordenação de zinco", "Bolso de fosfopeptídeo", "Núcleo (dobramento)",
         "Interface BARD1", "Intermediário", "Superfície"]
present = [m for m in order if (d.mechanism == m).sum() >= 5]
groups = [d[d.mechanism == m].hdr.values for m in present]
kw = kruskal(*groups)
rho = spearmanr(d.rsa, d.hdr)  # buried (low RSA) should have lower HDR

summ = {"n": int(len(d)), "kruskal_p": float(kw.pvalue),
        "spearman_rsa_vs_hdr": round(float(rho.correlation), 3),
        "median_hdr_by_mechanism": {m: round(float(np.median(d[d.mechanism == m].hdr)), 3) for m in present}}
json.dump(summ, open(os.path.join(ANL, "mechanism_vs_function.json"), "w"), indent=2, ensure_ascii=False)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"Coordenação de zinco": "#8e44ad", "Bolso de fosfopeptídeo": "#16a085",
       "Núcleo (dobramento)": "#c0392b", "Interface BARD1": "#e67e22",
       "Intermediário": "#7f8c8d", "Superfície": "#2e86c1"}
fig, ax = plt.subplots(figsize=(10.6, 6.2), dpi=200)
bp = ax.boxplot(groups, labels=[m.replace(" ", "\n") for m in present], patch_artist=True, showfliers=False)
for patch, m in zip(bp["boxes"], present):
    patch.set_facecolor(COL.get(m, "#999")); patch.set_alpha(0.75)
ax.set_ylabel("Função HDR medida (Starita 2015); menor = perda de função", fontsize=13.5)
ax.set_title("Validação do mecanismo contra função experimental (BRCA1, ensaio HDR)\n"
             f"mecanismos deletérios perdem mais função (Kruskal-Wallis p = {kw.pvalue:.1e})",
             fontsize=15, fontweight="bold")
ax.tick_params(axis="x", labelsize=13)
ax.tick_params(axis="y", labelsize=12.5)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
for _fp in (FIG, FIG.replace("suplementar", "manuscrito")):
    os.makedirs(os.path.dirname(_fp), exist_ok=True)
    fig.savefig(_fp, dpi=200, bbox_inches="tight", facecolor="white")

print("median HDR by mechanism:", summ["median_hdr_by_mechanism"])
print(f"Kruskal-Wallis p={kw.pvalue:.2e} | Spearman(RSA,HDR)={rho.correlation:+.3f}")
print(f">> wrote {ANL}/mechanism_vs_function.json and {FIG}")
