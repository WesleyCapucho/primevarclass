"""Structural-consequence renders (PyMOL open-source) showing how pathogenic
missense variants damage the target proteins' critical domains.

Panel A (1JM7): close-up of a BRCA1 RING zinc-coordination site — the cysteines
that hold the structural Zn2+ (their mutation, e.g. Cys61Gly/Cys64Gly, abolishes
zinc binding and collapses the domain).
Panel B (1N5O): BRCA1 BRCT carrying the cancer-causing missense p.Met1775Arg —
the mutated residue shown as sticks.

Run: C:\\Users\\...\\pymolopen\\python.exe -m pymol -cq scratch/pymol_mutation.py
"""
import os
from pymol import cmd

os.makedirs("scratch/pymol", exist_ok=True)


def base():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("cartoon_transparency", 0.55)
    cmd.set("specular", 0.15)
    cmd.set("ambient", 0.5)
    cmd.set("label_size", 24)
    cmd.set("label_color", "black")
    cmd.set("label_outline_color", "white")
    cmd.set("stick_radius", 0.22)


# ---------- Panel A: BRCA1 RING zinc site with Cys61/Cys64 ----------
cmd.reinitialize(); base()
cmd.load("scratch/pdb/1JM7.pdb", "m")
# pick the BRCA1 chain = the chain that contains residues 61 and 64 as CYS
brca1_chain = "A"
for ch in cmd.get_chains("m"):
    if cmd.count_atoms(f"m and chain {ch} and resi 61+64 and resn CYS and name CA") == 2:
        brca1_chain = ch
        break
sel = f"m and chain {brca1_chain}"
cmd.hide("everything")
cmd.show("cartoon", sel)
cmd.color("palegreen", sel)
cmd.set("cartoon_transparency", 0.5, sel)
# zinc ions near this chain
cmd.show("spheres", f"elem Zn within 12 of ({sel})")
cmd.color("purple", "elem Zn")
cmd.set("sphere_scale", 0.4, "elem Zn")
# all zinc-coordinating Cys/His of BRCA1 chain (context, orange)
cmd.select("lig", f"({sel}) and (resn CYS+HIS) within 2.8 of (elem Zn)")
cmd.show("sticks", "lig and not name N+C+O")
cmd.color("orange", "lig and elem C")
# the two classic pathogenic cysteines Cys61 / Cys64 (red, labeled)
cmd.select("hot", f"{sel} and resi 61+64")
cmd.show("sticks", "hot and not name N+C+O")
cmd.color("red", "hot and elem C")
cmd.label("hot and name CA", "'Cys%s' % resi")
cmd.orient("hot")
cmd.zoom("hot", 9)
cmd.ray(1500, 1400)
cmd.png("scratch/pymol/ring_zinc.png", dpi=300)
print("rendered ring_zinc.png (BRCA1 chain %s)" % brca1_chain)

# ---------- Panel B: BRCT cancer mutant (1N5O, M1775R) ----------
cmd.reinitialize(); base()
cmd.set("cartoon_transparency", 0.0)
cmd.load("scratch/pdb/1N5O.pdb", "n")
cmd.hide("everything")
cmd.show("cartoon", "polymer")
cmd.spectrum("resi", "marine_white_orange", "polymer")
cmd.select("mut", "resi 1775")
cmd.show("sticks", "mut and not name N+C+O")
cmd.color("red", "mut and elem C")
cmd.set("stick_radius", 0.3, "mut")
cmd.label("mut and name CA", "'1775'")
cmd.orient("polymer")
cmd.zoom("mut", 12)
cmd.ray(1500, 1400)
cmd.png("scratch/pymol/brct_mut.png", dpi=300)
print("rendered brct_mut.png")
cmd.quit()
