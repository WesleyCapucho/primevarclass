"""Prepare BRCA2 structural inputs for PyMOL:
  1. detected_per_residue_brca2.csv   — per-residue detection intensity (human numbering)
  2. detected_per_pdbresi_1MJE.csv    — same, keyed by 1MJE (mouse) residue number,
                                        so PyMOL can colour the structure directly
  3. brca2_panel.json                 — 6 ClinVar-confirmed pathogenic BRCA2 DBD
                                        variants the model caught, with their 1MJE resi

1MJE is the mouse BRCA2 DBD; residues are aligned to human P51587 by global
pairwise alignment (same procedure already used in mechanism_domains.py).

Run: python scratch/prep_brca2_structural.py
"""
from __future__ import annotations

import json
import os
import urllib.request

import pandas as pd
from Bio import Align
from Bio.PDB import PDBParser
from Bio.Data.IUPACData import protein_letters_3to1_extended as _3to1
import os, sys
sys.path.insert(0, os.path.abspath("src"))
from primevarclass.core import clinvar_binary_label

ANL = "primevarclass_manuscript_analysis"
T2O = {k.upper(): v for k, v in _3to1.items()}
THRESH = 0.5

# ---------- 1. per-residue detection intensity for BRCA2 (human numbering) ----
res = pd.read_csv(os.path.join(ANL, "brca_missense_evidence_resource.csv"))
b2 = res[res.gene == "BRCA2"].copy()
grp = b2.groupby("position")
per = pd.DataFrame({
    "n_alt": grp.size(),
    "n_detected": grp.apply(lambda d: int((d.pathogenicity_prob >= THRESH).sum()), include_groups=False),
    "max_prob": grp.pathogenicity_prob.max(),
    "mean_prob": grp.pathogenicity_prob.mean(),
}).reset_index()
per["frac_detected"] = (per.n_detected / per.n_alt).round(4)
per.to_csv(os.path.join(ANL, "detected_per_residue_brca2.csv"), index=False)
frac = dict(zip(per.position, per.frac_detected))
print(f"BRCA2 per-residue: {len(per)} positions")

# ---------- 2. map 1MJE (mouse) -> human, write per-PDB-residue detection -----
human2 = "".join(urllib.request.urlopen(
    "https://rest.uniprot.org/uniprotkb/P51587.fasta", timeout=60).read().decode().splitlines()[1:])
model = PDBParser(QUIET=True).get_structure("d", "scratch/pdb/1MJE.pdb")[0]
chain = "A"
resl = [(r.id[1], T2O[r.resname]) for r in model[chain] if r.id[0] == " " and r.resname in T2O]
mouse_seq = "".join(a for _, a in resl)
aligner = Align.PairwiseAligner()
aligner.mode = "global"; aligner.open_gap_score = -10; aligner.extend_gap_score = -0.5
aligner.match_score = 2; aligner.mismatch_score = -1
aln = aligner.align(human2, mouse_seq)[0]
m2h, h2m = {}, {}
for (h0, h1), (m0, m1) in zip(*aln.aligned):
    for k in range(h1 - h0):
        pdb_resi = resl[m0 + k][0]
        human_pos = h0 + k + 1
        m2h[pdb_resi] = human_pos
        h2m[human_pos] = pdb_resi
rows = [{"struct_pos": p, "frac_detected": frac.get(h, 0.0)} for p, h in m2h.items()]
pd.DataFrame(rows).to_csv(os.path.join(ANL, "detected_per_pdbresi_1MJE.csv"), index=False)
print(f"1MJE mapped residues: {len(m2h)} (human {min(m2h.values())}-{max(m2h.values())})")

# ---------- 3. pick 6 confirmed-pathogenic BRCA2 variants present in structure -
clin = pd.read_csv("data/raw/clinvar/clinvar_brca_missense_live.csv")
key = ["gene", "position", "aa_ref", "aa_alt"]
m = clin.merge(res, on=key, how="inner", suffixes=("", "_r"))
m = m[m.gene == "BRCA2"].copy()
m["isP"] = m.clinsig.map(lambda s: clinvar_binary_label(s) == 1)
cand = m[m.isP & (m.pathogenicity_prob > 0.5) & m.position.isin(h2m)].copy()
cand = cand.sort_values("pathogenicity_prob", ascending=False).drop_duplicates("position")

DOMLABEL = {"DBD_helical": "DBD — hélice", "DBD_OB1": "DBD — OB1 (liga ssDNA)",
            "DBD_OB2": "DBD — OB2 (liga ssDNA)", "DBD_OB3": "DBD — OB3 (liga ssDNA)",
            "DBD_tower": "DBD — torre (liga dsDNA)"}
AA3 = {v: k for k, v in T2O.items()}


def hgvs(r):
    return f"p.{AA3[r.aa_ref].title()}{int(r.position)}{AA3[r.aa_alt].title()}"


# Curated set: diverse across the three DBD OB-folds and the helical bundle, and
# including textbook BRCA2 pathogenic variants (G2748D, R3052W, W2626C). Every
# entry is verified below against the real merged ClinVar+model data.
CURATED = [(2653, "L", "P"), (2686, "L", "P"), (2660, "Y", "D"),
           (2748, "G", "D"), (3052, "R", "W"), (2626, "W", "C")]
by_key = {(int(r.position), r.aa_ref, r.aa_alt): r for _, r in cand.iterrows()}
picks = []
for pos, a, b in CURATED:
    r = by_key.get((pos, a, b))
    assert r is not None, f"{a}{pos}{b} is not a confirmed-pathogenic caught variant in structure"
    picks.append(dict(name=f"{a}{pos}{b}", title=f"BRCA2  {hgvs(r)}",
                      dom=DOMLABEL[r.functional_domain],
                      human=pos, pdb_resi=int(h2m[pos]),
                      prob=f"{r.pathogenicity_prob*100:.1f}".replace(".", ",") + "%",
                      clin="Patogênica / Provavelmente patogênica"
                           if "Likely" in str(r.clinsig) else "Patogênica"))

json.dump(picks, open("scratch/brca2_panel.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("panel picks:")
for p in picks:
    print(f"  {p['title']:24s} {p['dom']:24s} 1MJE resi {p['pdb_resi']:4d}  {p['prob']}")
