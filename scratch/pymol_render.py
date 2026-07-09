"""Publication-quality ray-traced renders of the target protein structures
using PyMOL (real experimental PDB coordinates). Run headless via:
  C:\\PyMOL\\python.exe -m pymol -cq scratch/pymol_render.py
"""
import os

from pymol import cmd, util

os.makedirs("scratch/pymol", exist_ok=True)
PDB = "scratch/pdb"


def setup():
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("antialias", 2)
    cmd.set("ray_shadows", 0)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("specular", 0.15)
    cmd.set("ambient", 0.45)
    cmd.set("cartoon_highlight_color", "grey60")


def render(pdb, out, recipe, w=1600, h=1500):
    cmd.reinitialize()
    setup()
    cmd.load(f"{PDB}/{pdb}.pdb", "m")
    cmd.hide("everything")
    cmd.show("cartoon", "polymer")
    recipe()
    cmd.orient()
    cmd.zoom("all", 2)
    cmd.ray(w, h)
    cmd.png(out, dpi=300)
    print("rendered", out)


def ring():
    # BRCA1/BARD1 RING heterodimer: color by chain, zinc spheres, Cys sticks (red)
    util.cbc(selection="polymer")
    cmd.show("spheres", "elem Zn")
    cmd.color("purple", "elem Zn")
    cmd.set("sphere_scale", 0.5, "elem Zn")
    cmd.show("sticks", "resn CYS and not name N+C+O")
    cmd.color("red", "resn CYS and not name N+C+O")


def brct():
    # BRCA1 BRCT repeats: rainbow N->C
    cmd.spectrum("resi", "rainbow", "polymer")


def dbd():
    # BRCA2 DBD + DSS1 + ssDNA
    util.cbc(selection="polymer.protein")
    cmd.show("cartoon", "polymer.nucleic")
    cmd.set("cartoon_ring_mode", 3, "polymer.nucleic")
    cmd.set("cartoon_ring_finder", 1)
    cmd.color("orange", "polymer.nucleic")


render("1JM7", "scratch/pymol/1JM7.png", ring)
render("1JNX", "scratch/pymol/1JNX.png", brct)
render("1MJE", "scratch/pymol/1MJE.png", dbd)
cmd.quit()
