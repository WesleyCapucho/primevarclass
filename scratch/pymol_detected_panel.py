"""Cover-quality panels demonstrating that the algorithm CAPTURED real, ClinVar-
confirmed pathogenic mutations. Each panel renders one confirmed-pathogenic
variant on its real crystal structure, with the mutated residue highlighted in
gold on a detection-coloured cartoon (RING panels also show the structural Zn2+).

Transparent renders -> text/badges are added later in compose_detected_panel.py
so every label stays large and legible.

Run: ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_detected_panel.py
"""
import csv
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)

frac = {}
with open("primevarclass_manuscript_analysis/detected_per_residue_brca1.csv") as fh:
    for row in csv.DictReader(fh):
        frac[int(row["position"])] = float(row["frac_detected"])

# 6 ClinVar-CONFIRMED pathogenic variants the model caught at high probability
VARIANTS = [
    dict(name="C39G", pdb="1JM7", resi=39,   ring=True),   # Pathogenic/LP, prob 0.997
    dict(name="C64G", pdb="1JM7", resi=64,   ring=True),   # Pathogenic,    prob 0.997
    dict(name="C61Y", pdb="1JM7", resi=61,   ring=True),   # Pathogenic,    prob 0.997
    dict(name="M1689R", pdb="1JNX", resi=1689, ring=False),  # Pathogenic/LP, prob 0.979
    dict(name="L1705P", pdb="1JNX", resi=1705, ring=False),  # Pathogenic/LP, prob 0.967
    dict(name="W1837C", pdb="1JNX", resi=1837, ring=False),  # Pathogenic/LP, prob 0.963
]
RINGCYS = [24, 27, 39, 44, 47, 61, 64]


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
    cmd.set_color("platinum", [0.68, 0.90, 1.00])
    cmd.set_color("flare", [1.00, 0.86, 0.30])


def paint(sel):
    cmd.alter(sel, "b=0.0")
    for pos, fr in frac.items():
        cmd.alter(f"{sel} and resi {pos}", f"b={fr}")
    cmd.spectrum("b", "cold mid hot", f"{sel} and polymer", minimum=0.0, maximum=1.0)


def brca1_chain(pdb):
    if pdb == "1JNX":
        return "X"
    for ch in cmd.get_chains("m"):
        if cmd.count_atoms(f"m and chain {ch} and resi 61+64 and resn CYS and name CA") == 2:
            return ch
    return "A"


for v in VARIANTS:
    cmd.reinitialize(); cinematic()
    cmd.load(f"scratch/pdb/{v['pdb']}.pdb", "full")
    cmd.create("m", "full", 1, 1); cmd.delete("full"); cmd.remove("hydro")
    ch = brca1_chain(v["pdb"])
    sel = f"m and chain {ch}"
    cmd.hide("everything")
    cmd.show("cartoon", sel)
    cmd.set("cartoon_transparency", 0.28, sel)   # ghosted so the caught residue pops
    paint(sel)

    if v["ring"]:
        cmd.select("zn", f"m and elem Zn within 6 of ({sel})")
        cmd.show("spheres", "zn"); cmd.set("sphere_scale", 0.9, "zn"); cmd.color("platinum", "zn")
        cmd.select("cys", f"({sel}) and resi {'+'.join(map(str, RINGCYS))} and not name N+C+O")
        cmd.show("sticks", "cys"); cmd.set("stick_radius", 0.16, "cys")
        cmd.set("stick_transparency", 0.35, "cys")
        cmd.color("grey70", "cys and elem C"); cmd.util.cnc("cys")

    # the CAUGHT residue: bright gold sticks + a marker sphere at the CA
    res = f"({sel}) and resi {v['resi']}"
    cmd.show("sticks", f"{res} and not name N+C+O")
    cmd.set("stick_radius", 0.38, res)
    cmd.set("stick_transparency", 0.0, res)
    cmd.color("flare", f"{res} and elem C"); cmd.util.cnc(res)
    cmd.show("spheres", f"{res} and name CA")
    cmd.set("sphere_scale", 0.42, f"{res} and name CA")
    cmd.color("flare", f"{res} and name CA")

    # frame the residue with local context
    cmd.orient(f"byres (({res}) around 11)")
    cmd.zoom(res, 8.5)
    cmd.turn("y", 6)
    cmd.ray(1180, 1180)
    cmd.png(f"{OUT}/detect_{v['name']}.png", dpi=300)
    print(f"rendered detect_{v['name']}.png")

cmd.quit()
