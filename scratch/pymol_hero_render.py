"""Cover-quality ('Nature cover') renders of the key result: the pathogenic
mutations PrimeVarClass detects, mapped onto real BRCA1 structures with cinematic
lighting and ambient occlusion. Cartoon-based (no full surface) so it ray-traces
reliably in a couple of minutes.

Run: ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_hero_render.py
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


def cinematic():
    cmd.bg_color("black")
    cmd.set("ray_opaque_background", 0)      # transparent -> composite our own backdrop
    cmd.set("antialias", 2)
    cmd.set("ambient_occlusion_mode", 1)
    cmd.set("ambient_occlusion_scale", 18)
    cmd.set("ambient_occlusion_smooth", 15)
    cmd.set("ambient", 0.10)
    cmd.set("direct", 0.55)
    cmd.set("reflect", 0.45)
    cmd.set("spec_count", 3)
    cmd.set("specular", 0.6)
    cmd.set("shininess", 50)
    cmd.set("light_count", 5)
    cmd.set("ray_shadows", 1)
    cmd.set("depth_cue", 1)
    cmd.set("fog_start", 0.40)
    cmd.set("ray_trace_fog", 1)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("cartoon_smooth_loops", 1)
    cmd.set("cartoon_side_chain_helper", 1)
    cmd.set("cartoon_highlight_color", "grey20")
    cmd.set("valence", 0)
    # 'vulnerability' ramp: deep indigo (tolerant) -> magenta -> gold (detected)
    cmd.set_color("cold", [0.10, 0.13, 0.38])
    cmd.set_color("mid", [0.74, 0.15, 0.42])
    cmd.set_color("hot", [1.00, 0.80, 0.22])
    cmd.set_color("platinum", [0.82, 0.85, 0.90])   # metallic zinc


def paint(sel):
    cmd.alter(sel, "b=0.0")
    for pos, fr in frac.items():
        cmd.alter(f"{sel} and resi {pos}", f"b={fr}")
    cmd.spectrum("b", "cold mid hot", f"{sel} and polymer", minimum=0.0, maximum=1.0)


# ---------------- HERO A: BRCA1 RING zinc site (1JM7) ------------------------
cmd.reinitialize(); cinematic()
cmd.load("scratch/pdb/1JM7.pdb", "full")
cmd.create("m", "full", 1, 1); cmd.delete("full"); cmd.remove("hydro")
brca1 = "A"
for ch in cmd.get_chains("m"):
    if cmd.count_atoms(f"m and chain {ch} and resi 61+64 and resn CYS and name CA") == 2:
        brca1 = ch; break
sel = f"m and chain {brca1}"
cmd.hide("everything")
cmd.show("cartoon", sel)
cmd.set("cartoon_transparency", 0.10, sel)
paint(sel)
cmd.select("zn", f"m and elem Zn within 6 of ({sel})")
cmd.show("spheres", "zn"); cmd.set("sphere_scale", 0.6, "zn"); cmd.color("platinum", "zn")
RINGCYS = [24, 27, 39, 44, 47, 61, 64]
cmd.select("cys", f"({sel}) and resi {'+'.join(map(str, RINGCYS))} and not (name N+C+O)")
cmd.show("sticks", "cys"); cmd.set("stick_radius", 0.32, "cys")
cmd.color("hot", "cys and elem C"); cmd.util.cnc("cys")
cmd.orient(sel)
cmd.turn("y", 10); cmd.turn("x", -4); cmd.turn("z", 6)
cmd.zoom(sel, -1)
cmd.ray(2400, 1500)
cmd.png(f"{OUT}/hero_ring.png", dpi=350)
print("rendered hero_ring.png")

# ---------------- HERO B: BRCA1 BRCT vulnerability map (1JNX) ----------------
cmd.reinitialize(); cinematic()
cmd.load("scratch/pdb/1JNX.pdb", "n"); cmd.remove("hydro")
cmd.hide("everything")
cmd.show("cartoon", "n and polymer")
paint("n")
cmd.orient("n and polymer")
cmd.turn("y", 12); cmd.turn("z", 3)
cmd.ray(2200, 1650)
cmd.png(f"{OUT}/hero_brct.png", dpi=350)
print("rendered hero_brct.png")
cmd.quit()
