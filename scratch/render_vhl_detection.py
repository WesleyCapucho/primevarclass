"""VHL per-residue detection — computes the ESM-2 detection track that drives VHL
(AUC 0,966) and a quick matplotlib 3D preview. The CANONICAL supplement figure is
the ray-traced PyMOL render (scratch/pymol_vhl_detection.py -> scratch/compose_vhl_figure.py);
this script's job is to produce detected_per_residue_vhl.csv, which PyMOL then reads.

Inputs : scratch/esm_input/esm2_650M_expanded_scores.csv (VHL saturation LLR),
         primevarclass_manuscript_analysis/panel_new_clinvar_labels.csv (real labels)
Outputs: primevarclass_manuscript_analysis/detected_per_residue_vhl.csv  (used by PyMOL)
         primevarclass_manuscript_analysis/fig_vhl_detection_mpl.png     (preview only)

Run: python scratch/render_vhl_detection.py
"""
from __future__ import annotations

import json
import os
import urllib.request

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from scipy.interpolate import splev, splprep

ANL = "primevarclass_manuscript_analysis"
FIG = "primevarclass_manuscript_analysis/fig_vhl_detection_mpl.png"  # preview; canonical fig is PyMOL
CORE_START = 54   # folded β+α core; the disordered N-terminus (1-53) is dropped for clarity
RAMP = [(0.09, 0.12, 0.36), (0.74, 0.15, 0.42), (1.00, 0.80, 0.22)]

# ---- per-residue ESM-2 detection (mean masked-marginal LLR over 19 alts) -----
e = pd.read_csv("scratch/esm_input/esm2_650M_expanded_scores.csv")
per = (e[e.gene == "VHL"].groupby("position").agg(mean_llr=("esm2_llr", "mean")).reset_index())
d = -per.mean_llr.to_numpy()
lo, hi = np.percentile(d, 5), np.percentile(d, 95)
per["detect"] = np.clip((d - lo) / (hi - lo + 1e-9), 0, 1)
per.to_csv(os.path.join(ANL, "detected_per_residue_vhl.csv"), index=False)
detmap = dict(zip(per.position.astype(int), per.detect))

# ---- AlphaFold structure ------------------------------------------------------
api = json.loads(urllib.request.urlopen("https://alphafold.ebi.ac.uk/api/prediction/P40337", timeout=60).read().decode())
pdb = urllib.request.urlopen(api[0]["pdbUrl"], timeout=60).read().decode()
rows = []
for ln in pdb.splitlines():
    if ln.startswith("ATOM") and ln[12:16].strip() == "CA":
        resi = int(ln[22:26])
        rows.append((resi, float(ln[30:38]), float(ln[38:46]), float(ln[46:54]), detmap.get(resi, 0.0)))
ca = pd.DataFrame(rows, columns=["resi", "x", "y", "z", "det"]).sort_values("resi")
ca = ca[ca.resi >= CORE_START].reset_index(drop=True)

lab = pd.read_csv(os.path.join(ANL, "panel_new_clinvar_labels.csv"))
patho = set(int(p) for p in lab[(lab.gene == "VHL") & (lab.label == 1)].position)
cmap = LinearSegmentedColormap.from_list("det", RAMP)

# ---- render -------------------------------------------------------------------
P = ca[["x", "y", "z"]].to_numpy()
tck, u = splprep(P.T, s=2.0, k=3)
uu = np.linspace(0, 1, 900)
sp = np.array(splev(uu, tck)).T
di = np.interp(uu, u, ca.det.to_numpy())
fig = plt.figure(figsize=(9.6, 8.4), dpi=200)
ax = fig.add_subplot(111, projection="3d")
ax.set_position([0.0, 0.02, 0.80, 0.80])
segs = np.stack([sp[:-1], sp[1:]], axis=1)
ax.add_collection3d(Line3DCollection(segs, colors=cmap((di[:-1] + di[1:]) / 2), linewidths=7, capstyle="round"))
hp = ca[ca.resi.isin(patho)]
ax.scatter(hp.x, hp.y, hp.z, facecolors=cmap(hp.det), edgecolors="#111", s=95, linewidths=1.1, depthshade=True)
ax.set_axis_off()
mid = P.mean(0); rng = (P.max(0) - P.min(0)).max() / 2 * 0.82
for s, c in zip("xyz", mid):
    getattr(ax, f"set_{s}lim")(c - rng, c + rng)
ax.view_init(elev=14, azim=35)
fig.text(0.5, 0.965, "VHL (von Hippel-Lindau) — mapa de detecção do PrimeVarClass",
         ha="center", fontsize=15, fontweight="bold", color="#12203a")
fig.text(0.5, 0.918, "sinal ESM-2 por resíduo no núcleo dobrado (β+α, AlphaFold P40337) — azul = tolerante · "
         "dourado = detectado; AUC 0,966 (CV bloqueada, ClinVar real).", ha="center", fontsize=9, color="#7a5a00")
fig.text(0.5, 0.895, "Esferas com contorno preto = resíduos com variante patogênica real — concentram-se nas zonas douradas.",
         ha="center", fontsize=9, color="#7a5a00")
sm = plt.cm.ScalarMappable(cmap=cmap); sm.set_array([0, 1])
cax = fig.add_axes([0.86, 0.34, 0.02, 0.34])
cb = fig.colorbar(sm, cax=cax); cb.set_ticks([0, 1]); cb.set_ticklabels(["tolerante", "detectado"])
cb.ax.tick_params(labelsize=9)
os.makedirs(os.path.dirname(FIG), exist_ok=True)
fig.savefig(FIG, dpi=200, bbox_inches="tight", facecolor="white")
print(f">> wrote {FIG} and detected_per_residue_vhl.csv (core residues {len(ca)}, pathogenic {len(hp)})")
