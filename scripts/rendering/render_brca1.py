# /// script
# requires-python = ">=3.10, <3.13"
# dependencies = [
#     "pymol-open-source-whl",
#     "urllib3"
# ]
# ///

import os
import sys

os.environ["PYOPENGL_PLATFORM"] = "osmesa"
import pymol
pymol.pymol_argv = ["pymol", "-cq"]
pymol.finish_launching()
from pymol import cmd

cmd.fetch("1jm7", "brca1")
cmd.hide("all")
cmd.show("cartoon", "brca1")
cmd.color("gray20", "brca1") # Darker gray for the rest of the protein

# The results highlight Leu100Asp and Leu4Gln in the RING domain.
# RING domain is ~ residues 1 to 109. Limiting to chain A to avoid duplicates.
cmd.select("ring_domain", "chain A and resi 1-109")
cmd.color("palecyan", "ring_domain")

# Highlight specific critical residues identified by PrimeVarClass
cmd.select("mut_L100", "chain A and resi 100")
cmd.show("spheres", "mut_L100")
cmd.color("magenta", "mut_L100")
cmd.label("mut_L100 and name CA", '" Leu100 (92.7%)"')

cmd.select("mut_L4", "chain A and resi 4")
cmd.show("spheres", "mut_L4")
cmd.color("orange", "mut_L4")
cmd.label("mut_L4 and name CA", '" Leu4 (92.6%)"')

# Highlight Zinc coordinating cysteines in RING domain
cmd.select("ring_cys", "chain A and resn CYS and resi 1-109")
cmd.show("sticks", "ring_cys")
cmd.color("yellow", "ring_cys")

# Focus on the RING domain
cmd.zoom("ring_domain", buffer=3.0)

# Rendering settings
cmd.bg_color("black")
cmd.set("label_color", "white")
cmd.set("label_size", 14) # Diminuído para caber na tela
cmd.set("label_font_id", 7) # Arial bold
cmd.set("label_position", [1, 1.5, 0]) # Posição mais próxima do átomo
cmd.set("label_connector", 1)
cmd.set("label_connector_color", "white")
cmd.set("label_connector_width", 1)
cmd.set("cartoon_fancy_helices", 1)
cmd.set("cartoon_highlight_color", "grey50")
cmd.set("depth_cue", 0)
cmd.set("ray_opaque_background", 1)

out_dir = "primevarclass_protein_impact_results"
os.makedirs(out_dir, exist_ok=True)
png_path = os.path.join(out_dir, "brca1_ring_domain_mutations.png")
pse_path = os.path.join(out_dir, "brca1_ring_domain.pse")

cmd.png(png_path, width=1600, height=1200, dpi=300, ray=0)
cmd.save(pse_path)
print(f"Gerado: {png_path}")
print(f"Sessão PyMOL salva em: {pse_path}")
cmd.quit()
