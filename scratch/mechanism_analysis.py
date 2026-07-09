"""Mechanism decomposition for BRCA1 — the genuinely novel layer.

For each residue we compute, from the REAL experimental structures, the
structural context that explains WHY a substitution is damaging:
  * burial (relative solvent accessibility, Shrake-Rupley) -> fold core vs surface
  * distance to the structural zinc ion (RING) -> metal coordination
  * buried surface at the BARD1 interface (1JM7 heterodimer) -> protein-protein
Crossed with the ESM-2 sequence signal, every DETECTED variant (PP3_Strong) is
assigned a mechanism — something a single pathogenicity score cannot provide.

Run: python scratch/mechanism_analysis.py
"""
from __future__ import annotations

import json
import os
import warnings

import numpy as np
import pandas as pd
from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley

warnings.filterwarnings("ignore")
ANL = "primevarclass_manuscript_analysis"
# Tien et al. 2013 theoretical maximum accessible surface area (A^2)
MAXASA = {"A": 129, "R": 274, "N": 195, "D": 193, "C": 167, "E": 223, "Q": 225,
          "G": 104, "H": 224, "I": 197, "L": 201, "K": 236, "M": 224, "F": 240,
          "P": 159, "S": 155, "T": 172, "W": 285, "Y": 263, "V": 174}
THREE2ONE = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLU": "E",
             "GLN": "Q", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
             "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
             "TYR": "Y", "VAL": "V"}


def per_residue_context(pdb, brca1_chain_hint=("A",)):
    """Return DataFrame: position, resname, rsa, zinc_dist, interface (bool)."""
    s = PDBParser(QUIET=True).get_structure("m", pdb)[0]
    # identify BRCA1 chain (the one with Cys residues at 61 & 64 when present)
    chains = list(s.get_chains())
    brca1 = None
    for ch in chains:
        ids = {r.id[1]: r.resname for r in ch if r.id[0] == " "}
        if ids.get(61) == "CYS" and ids.get(64) == "CYS":
            brca1 = ch; break
    if brca1 is None:
        brca1 = max(chains, key=lambda c: sum(1 for r in c if r.id[0] == " "))
    partner = [c for c in chains if c.id != brca1.id and any(r.id[0] == " " for r in c)]
    zns = [a for a in s.get_atoms() if a.element == "ZN"]

    sr = ShrakeRupley()
    sr.compute(brca1, level="R")           # SASA of BRCA1 chain in isolation
    sasa_alone = {r.id[1]: r.sasa for r in brca1 if r.id[0] == " "}
    sr.compute(s, level="R")               # SASA in the full complex
    sasa_cplx = {r.id[1]: r.sasa for r in brca1 if r.id[0] == " "}

    rows = []
    for r in brca1:
        if r.id[0] != " " or r.resname not in THREE2ONE:
            continue
        pos = r.id[1]; aa = THREE2ONE[r.resname]
        rsa = min(1.0, sasa_alone.get(pos, 0) / MAXASA[aa])
        zdist = min((a - z for a in r for z in zns), default=np.inf) if zns else np.inf
        iface = (sasa_alone.get(pos, 0) - sasa_cplx.get(pos, 0)) > 5.0
        rows.append({"position": pos, "aa_ref": aa, "rsa": round(rsa, 3),
                     "zinc_dist": round(float(zdist), 2), "interface": bool(iface)})
    return pd.DataFrame(rows)


def mechanism(row):
    if row.zinc_dist < 3.0:
        return "Coordenação de zinco"
    if row.interface:
        return "Interface BARD1"
    if row.rsa < 0.15:
        return "Núcleo estrutural (dobramento)"
    if row.rsa < 0.40:
        return "Intermediário"
    return "Superfície"


ring = per_residue_context("scratch/pdb/1JM7.pdb")
ring["mechanism"] = ring.apply(mechanism, axis=1)
print(f">> RING (1JM7): {len(ring)} residues")
print(ring.mechanism.value_counts().to_string())

# cross with the detected pathogenic variants + ESM-2
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))
det = res[(res.gene == "BRCA1") & (res.functional_domain == "RING") &
          (res.acmg_evidence == "PP3_Strong")].merge(ring, on=["position", "aa_ref"], how="inner")
print(f"\n>> detected pathogenic RING variants with structural context: {len(det)}")
mech_counts = det.mechanism.value_counts()
print("   mechanism of DETECTED variants:")
print(mech_counts.to_string())

det[["gene", "hgvs_p", "position", "aa_ref", "aa_alt", "esm2_llr", "pathogenicity_prob",
     "rsa", "zinc_dist", "interface", "mechanism"]].to_csv(
    os.path.join(ANL, "mechanism_brca1_ring.csv"), index=False)
json.dump({"ring_residue_mechanism": ring.mechanism.value_counts().to_dict(),
           "detected_variant_mechanism": mech_counts.to_dict(),
           "n_detected_ring": int(len(det))},
          open(os.path.join(ANL, "mechanism_analysis.json"), "w"), indent=2, ensure_ascii=False)

# figure: sequence axis (ESM-2) vs structure axis (burial), coloured by mechanism
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"Coordenação de zinco": "#8e44ad", "Interface BARD1": "#e67e22",
       "Núcleo estrutural (dobramento)": "#c0392b", "Intermediário": "#7f8c8d",
       "Superfície": "#2e86c1"}
fig, ax = plt.subplots(figsize=(8.4, 5.6), dpi=200)
for mech, g in det.groupby("mechanism"):
    ax.scatter(g.esm2_llr, g.rsa, s=26, alpha=0.75, color=COL.get(mech, "#333"), label=f"{mech} (n={len(g)})")
ax.axhline(0.15, ls="--", color="#aaa", lw=1); ax.text(det.esm2_llr.min(), 0.16, "enterrado ↓", fontsize=8, color="#888")
ax.set_xlabel("Sinal de sequência — ESM-2 LLR (mais negativo = mais deletério)", fontsize=10.5)
ax.set_ylabel("Sinal de estrutura — exposição ao solvente (RSA)", fontsize=10.5)
ax.set_title("Decomposição de MECANISMO das variantes detectadas no RING de BRCA1\n"
             "cada variante patogênica recebe um porquê estrutural, não só um escore", fontsize=10.5, fontweight="bold")
ax.legend(fontsize=8.4, loc="upper right"); ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig("docs/suplementar/figuras/fig_mechanism_ring.png", dpi=200, bbox_inches="tight", facecolor="white")
print(">> wrote mechanism_brca1_ring.csv, mechanism_analysis.json and fig_mechanism_ring.png")
