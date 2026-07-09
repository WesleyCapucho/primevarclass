"""Mechanism decomposition across ALL critical BRCA domains (extends
mechanism_analysis.py from the RING to BRCT and the BRCA2 DBD).

For each domain we read the real experimental structure with its FUNCTIONAL
ligand and assign every detected variant a structural mechanism:

  RING (1JM7)  zinc coordination / BARD1 interface / fold core / surface
  BRCT (1T29)  phosphopeptide pocket (BACH1 peptide) / fold core / surface
  DBD  (1MJE)  DNA binding (ssDNA) / DSS1 interface / fold core / surface
               (1MJE is mouse; residues are mapped to human numbering by a
                pairwise alignment to UniProt P51587 — honest & rigorous)

Run: python scratch/mechanism_domains.py
"""
from __future__ import annotations

import json
import os
import urllib.request
import warnings

import numpy as np
import pandas as pd
from Bio import Align
from Bio.PDB import PDBParser
from Bio.PDB.SASA import ShrakeRupley

warnings.filterwarnings("ignore")
ANL = "primevarclass_manuscript_analysis"
MAXASA = {"A": 129, "R": 274, "N": 195, "D": 193, "C": 167, "E": 223, "Q": 225,
          "G": 104, "H": 224, "I": 197, "L": 201, "K": 236, "M": 224, "F": 240,
          "P": 159, "S": 155, "T": 172, "W": 285, "Y": 263, "V": 174}
T2O = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLU": "E",
       "GLN": "Q", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
       "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
       "TYR": "Y", "VAL": "V"}


def min_dist(res, atoms):
    return min((a - b for a in res for b in atoms), default=np.inf)


def context(pdb, chain_id, ligand_atoms, partner_atoms):
    """Per-residue RSA + distance to ligand + interface (buried by partner)."""
    s = PDBParser(QUIET=True).get_structure("m", pdb)[0]
    tgt = s[chain_id]
    sr = ShrakeRupley()
    sr.compute(tgt, level="R"); alone = {r.id[1]: r.sasa for r in tgt if r.id[0] == " "}
    sr.compute(s, level="R"); cplx = {r.id[1]: r.sasa for r in tgt if r.id[0] == " "}
    rows = []
    for r in tgt:
        if r.id[0] != " " or r.resname not in T2O:
            continue
        p = r.id[1]; aa = T2O[r.resname]
        rows.append({"struct_pos": p, "aa_ref": aa,
                     "rsa": min(1.0, alone.get(p, 0) / MAXASA[aa]),
                     "lig_dist": float(min_dist(r, ligand_atoms)) if ligand_atoms else np.inf,
                     "interface": (alone.get(p, 0) - cplx.get(p, 0)) > 5.0})
    return pd.DataFrame(rows), s


def atoms_of(struct, chain_id=None, element=None):
    out = []
    for ch in struct.get_chains():
        if chain_id and ch.id != chain_id:
            continue
        for a in ch.get_atoms():
            if element and a.element != element:
                continue
            out.append(a)
    return out


# ---- map a mouse structure chain to human UniProt numbering -----------------
def map_to_human(struct, chain_id, human_seq):
    tgt = struct[chain_id]
    res = [(r.id[1], T2O[r.resname]) for r in tgt if r.id[0] == " " and r.resname in T2O]
    mouse_seq = "".join(a for _, a in res)
    aligner = Align.PairwiseAligner()
    aligner.mode = "global"; aligner.open_gap_score = -10; aligner.extend_gap_score = -0.5
    aligner.match_score = 2; aligner.mismatch_score = -1
    aln = aligner.align(human_seq, mouse_seq)[0]
    hblocks, mblocks = aln.aligned
    m2h = {}
    for (h0, h1), (m0, m1) in zip(hblocks, mblocks):
        for k in range(h1 - h0):
            m2h[res[m0 + k][0]] = h0 + k + 1   # human position (1-based)
    return m2h


res_all = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))


def assign(df, kind):
    def mech(r):
        if kind == "RING":
            if r.lig_dist < 3.0:
                return "Coordenação de zinco"
            if r.interface:
                return "Interface BARD1"
        elif kind == "BRCT":
            if r.lig_dist < 4.5:
                return "Bolso de fosfopeptídeo"
        elif kind == "DBD":
            if r.lig_dist < 4.5:
                return "Ligação ao DNA"
            if r.interface:
                return "Interface DSS1"
        if r.rsa < 0.15:
            return "Núcleo estrutural (dobramento)"
        if r.rsa < 0.40:
            return "Intermediário"
        return "Superfície"
    df = df.copy(); df["mechanism"] = df.apply(mech, axis=1)
    return df


summary = {}
frames = []

# ---- RING (BRCA1, 1JM7) -----------------------------------------------------
df, s = context("scratch/pdb/1JM7.pdb", "A",
                atoms_of(PDBParser(QUIET=True).get_structure("z", "scratch/pdb/1JM7.pdb")[0], element="ZN"),
                None)
df["position"] = df.struct_pos; df["gene"] = "BRCA1"; df = assign(df, "RING")
frames.append(("RING", "BRCA1", df))

# ---- BRCT (BRCA1, 1T29): ligand = BACH1 phosphopeptide (chain B) ------------
s2 = PDBParser(QUIET=True).get_structure("t", "scratch/pdb/1T29.pdb")[0]
df, _ = context("scratch/pdb/1T29.pdb", "A", atoms_of(s2, chain_id="B"), atoms_of(s2, chain_id="B"))
df["position"] = df.struct_pos; df["gene"] = "BRCA1"; df = assign(df, "BRCT")
frames.append(("BRCT", "BRCA1", df))

# ---- DBD (BRCA2, 1MJE): mouse -> human numbering; ligands = ssDNA + DSS1 ----
human2 = "".join(urllib.request.urlopen(
    "https://rest.uniprot.org/uniprotkb/P51587.fasta", timeout=60).read().decode().splitlines()[1:])
sd = PDBParser(QUIET=True).get_structure("d", "scratch/pdb/1MJE.pdb")[0]
m2h = map_to_human(sd, "A", human2)
df, _ = context("scratch/pdb/1MJE.pdb", "A", atoms_of(sd, chain_id="C"), atoms_of(sd, chain_id="B"))
df["position"] = df.struct_pos.map(m2h)
df = df.dropna(subset=["position"]); df["position"] = df.position.astype(int)
df["gene"] = "BRCA2"; df = assign(df, "DBD")
frames.append(("DBD", "BRCA2", df))

# ---- cross each domain with detected variants (PP3_Strong) ------------------
out_rows = []
for dom, gene, df in frames:
    det = (res_all[(res_all.gene == gene) & (res_all.acmg_evidence == "PP3_Strong")]
           .merge(df[["position", "aa_ref", "rsa", "lig_dist", "interface", "mechanism"]],
                  on=["position", "aa_ref"], how="inner"))
    det["domain"] = dom
    out_rows.append(det)
    summary[dom] = {"n_detected": int(len(det)),
                    "mechanism": det.mechanism.value_counts().to_dict()}
    print(f">> {dom} ({gene}): {len(det)} detected variants")
    print(det.mechanism.value_counts().to_string())
    print()

allv = pd.concat(out_rows, ignore_index=True)
allv[["gene", "domain", "hgvs_p", "position", "aa_ref", "aa_alt", "esm2_llr",
      "pathogenicity_prob", "rsa", "lig_dist", "interface", "mechanism"]].to_csv(
    os.path.join(ANL, "mechanism_all_domains.csv"), index=False)
json.dump(summary, open(os.path.join(ANL, "mechanism_domains.json"), "w"), indent=2, ensure_ascii=False)

# ---- figure: one mechanism panel per domain ---------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"Coordenação de zinco": "#8e44ad", "Interface BARD1": "#e67e22",
       "Bolso de fosfopeptídeo": "#16a085", "Ligação ao DNA": "#2980b9",
       "Interface DSS1": "#e67e22", "Núcleo estrutural (dobramento)": "#c0392b",
       "Intermediário": "#7f8c8d", "Superfície": "#95a5a6"}
fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=200)
for ax, (dom, gene, df) in zip(axes, frames):
    det = allv[allv.domain == dom]
    for mech, g in det.groupby("mechanism"):
        ax.scatter(g.esm2_llr, g.rsa, s=22, alpha=0.7, color=COL.get(mech, "#333"), label=f"{mech} ({len(g)})")
    ax.axhline(0.15, ls="--", color="#ccc", lw=1)
    ax.set_xlabel("ESM-2 LLR (sequência)", fontsize=9.5)
    ax.set_ylabel("Exposição RSA (estrutura)", fontsize=9.5)
    ax.set_title(f"{gene} — {dom} (n={len(det)})", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7.2, loc="upper right"); ax.grid(alpha=0.2)
fig.suptitle("Decomposição de mecanismo das variantes detectadas — domínios críticos de BRCA1/BRCA2",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("docs/suplementar/figuras/fig_mechanism_domains.png", dpi=200, bbox_inches="tight", facecolor="white")
print(">> wrote mechanism_all_domains.csv, mechanism_domains.json, fig_mechanism_domains.png")
