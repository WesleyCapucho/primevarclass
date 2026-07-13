"""MSH2 and RET detection maps in the house PyMOL style (open-source PyMOL).

Same recipe as scratch/pymol_vhl_detection.py, for two more genes of the expanded
panel, on REAL structures:
  MSH2 (Lynch, AUC 0,926) -> PDB 2O8B chain A (human MutS-alpha)
  RET  (MEN2,  AUC 0,813) -> PDB 2IVT chain A (RET kinase domain)
Per-residue ESM-2 detection colours the cartoon blue (tolerant) -> gold (detected);
real ClinVar-pathogenic residues in the resolved region are drawn as sticks.

Run:
  "$HOME/.conda/envs/pymolopen/python.exe" -m pymol -cq scratch/pymol_panel_detection.py
"""
import csv
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)
cmd.set("fetch_path", cmd.exp_path(OUT))

GENES = [
    dict(gene="MSH2", pdb="2o8b", chain="A"),
    dict(gene="RET",  pdb="2ivt", chain="A"),
]


def load_track(gene):
    det = {}
    with open(f"primevarclass_manuscript_analysis/detected_per_residue_{gene.lower()}.csv") as fh:
        for r in csv.DictReader(fh):
            det[int(r["position"])] = float(r["detect"])
    patho = set()
    with open("primevarclass_manuscript_analysis/panel_new_clinvar_labels.csv") as fh:
        for r in csv.DictReader(fh):
            if r["gene"] == gene and r["label"] == "1":
                patho.add(int(r["position"]))
    return det, patho


def base():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("specular", 0.25)
    cmd.set("ambient", 0.5)
    cmd.set("stick_radius", 0.18)


for cfg in GENES:
    g, pdb, ch = cfg["gene"], cfg["pdb"], cfg["chain"]
    det, patho = load_track(g)
    cmd.reinitialize(); base()
    cmd.set_color("det_tol", [0.09, 0.12, 0.36])
    cmd.set_color("det_mid", [0.74, 0.15, 0.42])
    cmd.set_color("det_hi", [1.00, 0.80, 0.22])
    cmd.fetch(pdb, g, type="pdb")
    cmd.remove(f"{g} and not chain {ch}")
    cmd.remove(f"{g} and not polymer.protein")   # drop DNA / ligands / solvent
    cmd.remove("hydro")
    sel = f"{g} and polymer"
    cmd.alter(g, "b=0.0")
    for pos, d in det.items():
        cmd.alter(f"{g} and resi {pos}", f"b={d}")
    cmd.rebuild()
    cmd.hide("everything")
    cmd.show("cartoon", sel)
    cmd.spectrum("b", "det_tol det_mid det_hi", sel, minimum=0.0, maximum=1.0)
    # pathogenic residues that fall inside the resolved region -> sticks
    resolved = set(int(a.resi) for a in cmd.get_model(f"{sel} and name CA").atom)
    show_p = sorted(patho & resolved)
    n_p = len(show_p)
    if show_p:
        psel = f"{g} and resi {'+'.join(map(str, show_p))} and not (name N+C+O) and sidechain"
        cmd.show("sticks", psel)
        cmd.spectrum("b", "det_tol det_mid det_hi", psel, minimum=0.0, maximum=1.0)
    cmd.orient(sel)
    cmd.ray(2000, 1600)
    cmd.png(f"{OUT}/{g.lower()}_detection.png", dpi=300)
    print(f">> {g}: rendered {g.lower()}_detection.png | pathogenic sticks shown: {n_p}/{len(patho)}")

cmd.quit()
