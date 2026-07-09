"""Cover-quality panels showing ClinVar-confirmed pathogenic BRCA2 variants the
model caught, on the real BRCA2 DBD structure (1MJE, mouse numbering; detection
values and the target residues were mapped to it by prep_brca2_structural.py).

Transparent renders -> labels/badges added in compose_brca2_panel.py.

Run: ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_brca2_panel.py
"""
import csv
import json
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)

frac = {}
with open("primevarclass_manuscript_analysis/detected_per_pdbresi_1MJE.csv") as fh:
    for row in csv.DictReader(fh):
        frac[int(float(row["struct_pos"]))] = float(row["frac_detected"])
PANEL = json.load(open("scratch/brca2_panel.json", encoding="utf-8"))


def cinematic():
    cmd.bg_color("black")
    cmd.set("ray_opaque_background", 0)
    cmd.set("antialias", 2)
    cmd.set("ambient_occlusion_mode", 1)
    cmd.set("ambient_occlusion_scale", 18)
    cmd.set("ambient_occlusion_smooth", 15)
    cmd.set("ambient", 0.11)
    cmd.set("direct", 0.55)
    cmd.set("reflect", 0.45)
    cmd.set("spec_count", 3)
    cmd.set("specular", 0.6)
    cmd.set("shininess", 50)
    cmd.set("light_count", 5)
    cmd.set("ray_shadows", 1)
    cmd.set("depth_cue", 1)
    cmd.set("fog_start", 0.42)
    cmd.set("ray_trace_fog", 1)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("cartoon_smooth_loops", 1)
    cmd.set("cartoon_side_chain_helper", 1)
    cmd.set("cartoon_highlight_color", "grey20")
    cmd.set("sphere_mode", 9)
    cmd.set("ray_interior_color", "grey10")
    cmd.set("valence", 0)
    cmd.set_color("cold", [0.10, 0.13, 0.38])
    cmd.set_color("mid", [0.74, 0.15, 0.42])
    cmd.set_color("hot", [1.00, 0.80, 0.22])
    cmd.set_color("flare", [1.00, 0.86, 0.30])


def paint(sel):
    cmd.alter(sel, "b=0.0")
    for pos, fr in frac.items():
        cmd.alter(f"{sel} and resi {pos}", f"b={fr}")
    cmd.spectrum("b", "cold mid hot", f"{sel} and polymer", minimum=0.0, maximum=1.0)


for v in PANEL:
    cmd.reinitialize(); cinematic()
    cmd.load("scratch/pdb/1MJE.pdb", "full")
    cmd.create("m", "full", 1, 1); cmd.delete("full"); cmd.remove("hydro or solvent")
    sel = "m and chain A"
    cmd.hide("everything")
    cmd.show("cartoon", sel)
    cmd.set("cartoon_transparency", 0.28, sel)
    paint(sel)

    res = f"({sel}) and resi {v['pdb_resi']}"
    cmd.show("sticks", f"{res} and not name N+C+O")
    cmd.set("stick_radius", 0.38, res)
    cmd.color("flare", f"{res} and elem C"); cmd.util.cnc(res)
    cmd.show("spheres", f"{res} and name CA")
    cmd.set("sphere_scale", 0.42, f"{res} and name CA")
    cmd.color("flare", f"{res} and name CA")

    cmd.orient(f"byres (({res}) around 11)")
    cmd.zoom(res, 8.5)
    cmd.turn("y", 6)
    cmd.ray(1180, 1180)
    cmd.png(f"{OUT}/b2_{v['name']}.png", dpi=300)
    print(f"rendered b2_{v['name']}.png")

cmd.quit()
