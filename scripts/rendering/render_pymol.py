# /// script
# requires-python = ">=3.10, <3.13"
# dependencies = [
#     "pymol-open-source-whl",
# ]
# ///

import os
import sys

os.environ["PYOPENGL_PLATFORM"] = "osmesa"

import pymol # pytype: disable=import-error
pymol.pymol_argv = ["pymol", "-cq"]
pymol.finish_launching()

from pymol import cmd # pytype: disable=import-error

OUT_DIR = r"C:\Users\Wesley Capucho\.gemini\antigravity\brain\e6786eab-3800-49c0-a947-eb1781f7bdbd"
PDB_DIR = r"C:\Users\Wesley Capucho\Documents\IA dos números primos\pdbs"

# 1. BRCA1 Wild-Type (from 1JM7, chain A is BRCA1)
cmd.reinitialize()
cmd.load(os.path.join(PDB_DIR, "1JM7.pdb"), "brca1")
cmd.hide("all")
cmd.show("cartoon", "chain A")
cmd.color("teal", "chain A")
cmd.show("spheres", "resn ZN and chain A")
cmd.color("orange", "resn ZN and chain A")
cmd.show("sticks", "resn CYS+HIS and chain A and (resn ZN around 4)")
cmd.color("yellow", "resn CYS and chain A")
# Highlight Cys61
cmd.show("sticks", "chain A and resi 61")
cmd.color("magenta", "chain A and resi 61")
cmd.zoom("chain A and resi 61", buffer=15)
cmd.set("ray_opaque_background", 1)
cmd.png(os.path.join(OUT_DIR, "brca1_C61_wildtype.png"), width=1200, height=900, dpi=150)

# 2. BRCA1 C61G Mutant In-Silico
cmd.wizard("mutagenesis")
cmd.refresh_wizard()
cmd.get_wizard().do_select("chain A and resi 61")
cmd.get_wizard().set_mode("GLY")
cmd.get_wizard().apply()
cmd.set_wizard() # close wizard
cmd.hide("all")
cmd.show("cartoon", "chain A")
cmd.color("salmon", "chain A")
# show zinc and coordinating residues again to see lack of connection
cmd.show("spheres", "resn ZN and chain A")
cmd.color("orange", "resn ZN and chain A")
cmd.show("sticks", "resn CYS+HIS+GLY and chain A and (resn ZN around 4)")
cmd.color("yellow", "resn CYS and chain A")
cmd.color("red", "chain A and resi 61")
cmd.zoom("chain A and resi 61", buffer=15)
cmd.png(os.path.join(OUT_DIR, "brca1_C61G_mutant.png"), width=1200, height=900, dpi=150)

# 3. BRCA1-BARD1 Interaction (1JM7 full structure)
cmd.reinitialize()
cmd.load(os.path.join(PDB_DIR, "1JM7.pdb"), "complex")
cmd.hide("all")
cmd.show("surface", "all")
cmd.set("transparency", 0.3)
cmd.show("cartoon", "all")
cmd.color("blue", "chain A") # BRCA1
cmd.color("red", "chain B")  # BARD1
cmd.zoom("all", buffer=5)
cmd.png(os.path.join(OUT_DIR, "brca1_bard1_interaction.png"), width=1200, height=900, dpi=150)

# 4. BRCA2 OB-Fold (1MJE)
cmd.reinitialize()
cmd.load(os.path.join(PDB_DIR, "1MJE.pdb"), "brca2")
cmd.hide("all")
cmd.show("cartoon", "all")
# Color by secondary structure
cmd.color("green", "ss h")
cmd.color("yellow", "ss s")
cmd.color("gray", "ss l+''")
cmd.zoom("all", buffer=5)
cmd.png(os.path.join(OUT_DIR, "brca2_obfold_wt.png"), width=1200, height=900, dpi=150)

cmd.quit()
