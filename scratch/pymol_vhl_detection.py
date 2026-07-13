"""VHL detection map in the house PyMOL style (open-source PyMOL).

Maps the per-residue ESM-2 detection intensity onto the REAL VHL crystal structure
(PDB 1LM8, chain V = VHL 54-213), B-factor coloured blue (tolerant) -> gold
(detected), with the real ClinVar-pathogenic residues drawn as sticks. Same
recipe as scratch/pymol_detection_maps.py (BRCA1), reused for a gene of another
hereditary-cancer syndrome.

Run:
  "$HOME/.conda/envs/pymolopen/python.exe" -m pymol -cq scratch/pymol_vhl_detection.py
"""
import csv
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)
cmd.set("fetch_path", cmd.exp_path(OUT))          # keep the fetched PDB out of the repo root

det = {}
with open("primevarclass_manuscript_analysis/detected_per_residue_vhl.csv") as fh:
    for r in csv.DictReader(fh):
        det[int(r["position"])] = float(r["detect"])
patho = set()
with open("primevarclass_manuscript_analysis/panel_new_clinvar_labels.csv") as fh:
    for r in csv.DictReader(fh):
        if r["gene"] == "VHL" and r["label"] == "1":
            patho.add(int(r["position"]))


def base():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("specular", 0.25)
    cmd.set("ambient", 0.5)
    cmd.set("cartoon_transparency", 0.0)
    cmd.set("stick_radius", 0.18)


cmd.reinitialize(); base()
cmd.set_color("det_tol", [0.09, 0.12, 0.36])      # after reinitialize, which resets colors
cmd.set_color("det_mid", [0.74, 0.15, 0.42])
cmd.set_color("det_hi", [1.00, 0.80, 0.22])
cmd.fetch("1lm8", "vhl", type="pdb")
cmd.remove("vhl and not chain V")
cmd.remove("solvent"); cmd.remove("hydro")
sel = "vhl and polymer"
cmd.alter("vhl", "b=0.0")
for pos, d in det.items():
    cmd.alter(f"vhl and resi {pos}", f"b={d}")
cmd.rebuild()
cmd.hide("everything")
cmd.show("cartoon", sel)
cmd.spectrum("b", "det_tol det_mid det_hi", sel, minimum=0.0, maximum=1.0)
# real pathogenic residues as sticks (side chains), coloured by their own detection
if patho:
    psel = f"vhl and resi {'+'.join(map(str, sorted(patho)))} and not (name N+C+O) and sidechain"
    cmd.show("sticks", psel)
    cmd.spectrum("b", "det_tol det_mid det_hi", psel, minimum=0.0, maximum=1.0)
cmd.orient(sel)
cmd.turn("y", 20); cmd.turn("x", -8)
cmd.ray(2000, 1600)
cmd.png(f"{OUT}/vhl_detection.png", dpi=300)
print(">> rendered", f"{OUT}/vhl_detection.png")
cmd.quit()
