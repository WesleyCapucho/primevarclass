"""Molecular-SURFACE renders of whole domains, coloured by PrimeVarClass detection
intensity per residue — the 'detection landscape' on the solvent-accessible
surface. BRCA1 BRCT (1JNX) and BRCA2 DBD (1MJE, mouse numbering; detection values
already mapped to its residues by prep_brca2_structural.py).

Surface + ambient occlusion but NO ray_shadows and a moderate size, so it ray-
traces in a couple of minutes instead of hanging.

Run: ~/.conda/envs/pymolopen/python.exe -m pymol -cq scratch/pymol_domain_surface.py
"""
import csv
import os

from pymol import cmd

OUT = "scratch/pymol"
os.makedirs(OUT, exist_ok=True)


def load_frac(path, kcol, vcol="frac_detected"):
    d = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            d[int(float(row[kcol]))] = float(row[vcol])
    return d


def cinematic():
    cmd.bg_color("black")
    cmd.set("ray_opaque_background", 0)
    cmd.set("antialias", 2)
    cmd.set("ambient_occlusion_mode", 1)
    cmd.set("ambient_occlusion_scale", 22)
    cmd.set("ambient_occlusion_smooth", 15)
    cmd.set("ambient", 0.12)
    cmd.set("direct", 0.5)
    cmd.set("reflect", 0.4)
    cmd.set("spec_count", 2)
    cmd.set("specular", 0.35)
    cmd.set("shininess", 40)
    cmd.set("light_count", 4)
    cmd.set("ray_shadows", 0)               # off -> reliable, fast surface ray-trace
    cmd.set("depth_cue", 1)
    cmd.set("fog_start", 0.45)
    cmd.set("ray_trace_fog", 1)
    cmd.set("surface_quality", 1)
    cmd.set("solvent_radius", 1.4)
    cmd.set("transparency", 0.0)
    cmd.set_color("cold", [0.10, 0.13, 0.38])
    cmd.set_color("mid", [0.74, 0.15, 0.42])
    cmd.set_color("hot", [1.00, 0.80, 0.22])


def paint(sel, fracmap):
    cmd.alter(sel, "b=0.0")
    for resi, fr in fracmap.items():
        cmd.alter(f"{sel} and resi {resi}", f"b={fr}")
    cmd.spectrum("b", "cold mid hot", f"{sel} and polymer", minimum=0.0, maximum=1.0)


def render_surface(pdb, chain, fracmap, out, size=1500, turns=(("y", 15),)):
    cmd.reinitialize(); cinematic()
    cmd.load(f"scratch/pdb/{pdb}.pdb", "full")
    cmd.create("m", "full", 1, 1); cmd.delete("full"); cmd.remove("hydro or solvent")
    sel = f"m and chain {chain}"
    cmd.hide("everything")
    cmd.show("surface", sel)
    paint(sel, fracmap)
    cmd.orient(sel)
    for ax, ang in turns:
        cmd.turn(ax, ang)
    cmd.ray(size, size)
    cmd.png(out, dpi=300)
    print("rendered", os.path.basename(out))


# BRCA1 BRCT (1JNX): residue numbers already human (1649-1859)
brct = load_frac("primevarclass_manuscript_analysis/detected_per_residue_brca1.csv", "position")
render_surface("1JNX", "X", brct, f"{OUT}/surf_brct.png", turns=(("y", 15),))

# BRCA2 DBD (1MJE chain A): frac already keyed by the structure's own residues
dbd = load_frac("primevarclass_manuscript_analysis/detected_per_pdbresi_1MJE.csv", "struct_pos")
render_surface("1MJE", "A", dbd, f"{OUT}/surf_dbd.png", turns=(("y", 20),))

cmd.quit()
