"""3D structural renders of the two flagship pathogenic variants our classifier
flags in BRCA1 — on real, experimentally-determined human coordinates (no
modelled/fabricated atoms).

Panel A  BRCA1 p.Cys61Gly  (RING domain, PDB 1JM7, model 1)
    Cys61 is a thiol ligand of the structural Zn2+ of the second zinc module of
    the BRCA1 RING. Substitution by Gly removes the sulfur that coordinates the
    ion -> zinc is released -> the RING fold collapses -> loss of the
    BRCA1-BARD1 E3 ubiquitin-ligase. ESM-2 LLR = -10.9 (pathogenic direction).

Panel B  BRCA1 p.Met1775Arg  (BRCT domain)
    True superposition of the wild-type BRCT (PDB 1JNX, Met1775) and the
    experimentally-determined cancer mutant (PDB 1N5O, Arg1775). The compact,
    buried Met is replaced by a longer, positively-charged Arg that cannot pack
    in the hydrophobic BRCT core, destabilising the phosphopeptide-reader fold
    (recognition of pSer partners BACH1/BRIP1, CtIP). ESM-2 LLR = -12.0.

Run (open-source PyMOL, watermark-free):
  ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_variants_found.py
"""
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)


def base():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("ray_trace_mode", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("specular", 0.2)
    cmd.set("ambient", 0.5)
    cmd.set("stick_radius", 0.22)
    cmd.set("label_size", 26)
    cmd.set("label_color", "black")
    cmd.set("label_outline_color", "white")
    cmd.set("label_font_id", 7)


# ------------------------------------------------------------------ Panel A
# BRCA1 RING zinc site with the pathogenic Cys61 (1JM7 is an NMR ensemble ->
# collapse to a single model so selections/renders are clean).
cmd.reinitialize(); base()
cmd.load("scratch/pdb/1JM7.pdb", "full")
cmd.create("m", "full", 1, 1)      # keep model/state 1 only
cmd.delete("full")
cmd.remove("hydro")                 # NMR ensemble carries H's -> hide for clarity

# BRCA1 chain = the one carrying Cys61/Cys64 (chain A here)
brca1 = "A"
for ch in cmd.get_chains("m"):
    if cmd.count_atoms(f"m and chain {ch} and resi 61+64 and resn CYS and name CA") == 2:
        brca1 = ch; break
sel = f"m and chain {brca1}"

cmd.hide("everything")
cmd.show("cartoon", sel)
cmd.color("palegreen", sel)
cmd.set("cartoon_transparency", 0.55, sel)

# the two structural zinc ions of THIS RING (near the BRCA1 chain)
cmd.select("zn", f"m and elem Zn within 6 of ({sel})")
cmd.show("spheres", "zn")
cmd.color("slate", "zn")
cmd.set("sphere_scale", 0.42, "zn")

# zinc-coordinating Cys/His of the BRCA1 RING (context, orange sticks)
cmd.select("lig", f"({sel}) and (resn CYS+HIS) within 3.0 of zn")
cmd.show("sticks", "lig and not (name N+C+O)")
cmd.color("orange", "lig and elem C")

# the native residue Cys61 (green, the position mutated to Gly) and its zinc
cmd.select("hot", f"{sel} and resi 61")
cmd.show("sticks", "hot and not (name N+C+O)")
cmd.color("forest", "hot and elem C")
cmd.util.cnc("hot")
cmd.set("stick_radius", 0.32, "hot")
cmd.select("zn1", "zn within 3.2 of (hot and name SG)")
if cmd.count_atoms("zn1") == 0:
    cmd.select("zn1", "zn within 6 of (hot and name SG)")
cmd.set("sphere_scale", 0.5, "zn1")
# dashed coordination bond thiol -> zinc
cmd.distance("coord", "hot and name SG", "zn1", 3.2)
cmd.hide("labels", "coord")
cmd.color("grey40", "coord")

cmd.set("cartoon_transparency", 0.6, sel)
cmd.orient("(hot or zn1) expand 5")
cmd.turn("y", 10)
cmd.zoom("(hot or zn1)", 4.2)
cmd.ray(1700, 1600)
cmd.png(f"{OUT}/var_ring_c61.png", dpi=300)
print("rendered var_ring_c61.png  (BRCA1 chain %s)" % brca1)


# ------------------------------------------------------------------ Panel B
# BRCT: wild-type Met1775 (1JNX) superposed on the cancer mutant Arg1775 (1N5O).
cmd.reinitialize(); base()
cmd.load("scratch/pdb/1JNX.pdb", "wt")
cmd.load("scratch/pdb/1N5O.pdb", "mut")
# structural superposition of the two BRCT copies
try:
    cmd.super("mut", "wt")
except Exception:
    cmd.align("mut", "wt")

cmd.hide("everything")
# wild-type fold as context
cmd.show("cartoon", "wt")
cmd.color("palecyan", "wt")
cmd.set("cartoon_transparency", 0.35, "wt")

# hydrophobic pocket around residue 1775 (wild-type neighbours, thin grey sticks)
cmd.select("pocket", "wt and byres (polymer within 5 of (wt and resi 1775)) and not resi 1775")
cmd.show("sticks", "pocket and not (name N+C+O)")
cmd.set("stick_radius", 0.12, "pocket")
cmd.color("grey70", "pocket and elem C")

# wild-type Met1775 (green) vs mutant Arg1775 (red)
cmd.select("wtres", "wt and resi 1775")
cmd.select("mutres", "mut and resi 1775")
for s, col in (("wtres", "forest"), ("mutres", "red")):
    cmd.show("sticks", f"{s} and not (name N+C+O)")
    cmd.color(col, f"{s} and elem C")
    cmd.set("stick_radius", 0.32, s)
cmd.util.cnc("mutres")   # colour N (blue) / O (red) heteroatoms of the Arg

cmd.orient("(wtres or mutres) expand 8")
cmd.turn("x", -8)
cmd.zoom("(wtres or mutres)", 7.0)
cmd.ray(1700, 1600)
cmd.png(f"{OUT}/var_brct_m1775.png", dpi=300)
print("rendered var_brct_m1775.png")
cmd.quit()
