"""Map the algorithm's per-residue DETECTION intensity onto real BRCA1 structures
(open-source PyMOL). For each residue, the fraction of the 19 possible
substitutions flagged PP3_Strong is written into the B-factor column and coloured
blue (low) -> red (high). This shows *where* the algorithm concentrates its
pathogenic detections — precisely at the functionally critical residues.

Panels rendered (to scratch/pymol/):
  ring_detection.png        BRCA1 RING (1JM7) coloured by detection + zinc site
  brct_detection.png        BRCA1 BRCT (1JNX) coloured by detection
  ring_detection_closeup.png  zinc-coordinating cysteines (labelled) — supplement
  brct_detection_closeup.png  BRCT core hotspots (labelled) — supplement

Run: ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_detection_maps.py
"""
import csv
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)

# per-residue detection fraction (BRCA1)
frac = {}
with open("primevarclass_manuscript_analysis/detected_per_residue_brca1.csv") as fh:
    for row in csv.DictReader(fh):
        frac[int(row["position"])] = float(row["frac_detected"])

RING_COORD = [24, 27, 39, 41, 44, 47, 61, 64]  # zinc-coordinating Cys/His


def base():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("specular", 0.2)
    cmd.set("ambient", 0.5)
    cmd.set("cartoon_putty_scale_min", 0.6)
    cmd.set("label_size", 22)
    cmd.set("label_color", "black")
    cmd.set("label_outline_color", "white")
    cmd.set("label_font_id", 7)


def paint(sel):
    cmd.alter(f"{sel}", "b=0.0")
    for pos, fr in frac.items():
        cmd.alter(f"{sel} and resi {pos}", f"b={fr}")
    cmd.spectrum("b", "blue_white_red", f"{sel} and polymer", minimum=0.0, maximum=1.0)


# ---------------- Panel A: RING detection (1JM7, NMR -> state 1) -------------
cmd.reinitialize(); base()
cmd.load("scratch/pdb/1JM7.pdb", "full")
cmd.create("m", "full", 1, 1); cmd.delete("full"); cmd.remove("hydro")
brca1 = "A"
for ch in cmd.get_chains("m"):
    if cmd.count_atoms(f"m and chain {ch} and resi 61+64 and resn CYS and name CA") == 2:
        brca1 = ch; break
sel = f"m and chain {brca1}"
cmd.hide("everything")
cmd.show("cartoon", sel)
paint(sel)
cmd.select("zn", f"m and elem Zn within 6 of ({sel})")
cmd.show("spheres", "zn"); cmd.color("grey40", "zn"); cmd.set("sphere_scale", 0.35, "zn")
cmd.show("sticks", f"({sel}) and resi {'+'.join(map(str, RING_COORD))} and not (name N+C+O)")
cmd.set("stick_radius", 0.2, sel)
cmd.orient(sel)
cmd.ray(1700, 1500)
cmd.png(f"{OUT}/ring_detection.png", dpi=300)
print("rendered ring_detection.png")

# closeup of the zinc site with labelled detected cysteines
cmd.set("cartoon_transparency", 0.6, sel)
cmd.color("orange", f"({sel}) and resi {'+'.join(map(str, RING_COORD))} and elem C")
cmd.util.cnc(f"({sel}) and resi {'+'.join(map(str, RING_COORD))}")
cmd.label(f"({sel}) and resi 61+64+39+24 and name CA", "'%s%s' % (resn[0]+resn[1:3].lower(), resi)")
cmd.orient("zn expand 8")
cmd.zoom("zn expand 8", 2)
cmd.ray(1700, 1500)
cmd.png(f"{OUT}/ring_detection_closeup.png", dpi=300)
print("rendered ring_detection_closeup.png")

# ---------------- Panel B: BRCT detection (1JNX) ----------------------------
cmd.reinitialize(); base()
cmd.load("scratch/pdb/1JNX.pdb", "n"); cmd.remove("hydro")
cmd.hide("everything")
cmd.show("cartoon", "n and polymer")
paint("n")
cmd.orient("n and polymer")
cmd.ray(1700, 1500)
cmd.png(f"{OUT}/brct_detection.png", dpi=300)
print("rendered brct_detection.png")

# closeup: BRCT hotspots (fully-detected residues) labelled
HOT = [1699, 1712, 1718, 1775, 1788, 1815]
cmd.set("cartoon_transparency", 0.55, "n")
cmd.show("sticks", f"n and resi {'+'.join(map(str, HOT))} and not (name N+C+O)")
cmd.color("orange", f"n and resi {'+'.join(map(str, HOT))} and elem C")
cmd.util.cnc(f"n and resi {'+'.join(map(str, HOT))}")
cmd.label(f"n and resi {'+'.join(map(str, HOT))} and name CA", "'%s%s' % (resn[0]+resn[1:3].lower(), resi)")
cmd.orient(f"n and resi {'+'.join(map(str, HOT))}")
cmd.zoom(f"n and resi {'+'.join(map(str, HOT))}", 4)
cmd.ray(1700, 1500)
cmd.png(f"{OUT}/brct_detection_closeup.png", dpi=300)
print("rendered brct_detection_closeup.png")
cmd.quit()
