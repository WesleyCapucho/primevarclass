"""3D structure figures of the target proteins from REAL experimental PDB
coordinates (RCSB), rendered with Biopython + matplotlib. No fabricated data.

Structures:
  1JM7 - BRCA1/BARD1 RING-domain heterodimer (BRCA1 critical RING domain)
  1JNX - BRCA1 BRCT repeat region (critical BRCT domain)
  1MJE - BRCA2-DSS1-ssDNA complex (BRCA2 DNA-binding domain; Yang et al. 2002)

For BRCA1 RING we highlight the zinc-coordinating cysteines (structural core
where loss-of-function pathogenic missense variants, e.g. Cys61/Cys64, cluster).

Run: python scratch/figures_structures.py
"""
from __future__ import annotations
import os, urllib.request, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
warnings.filterwarnings("ignore")
from Bio.PDB import PDBParser
try:
    from scipy.interpolate import splprep, splev
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

OUT = "primevarclass_manuscript_analysis"
PDBDIR = "scratch/pdb"
os.makedirs(OUT, exist_ok=True)
os.makedirs(PDBDIR, exist_ok=True)
DNA = {"DA", "DT", "DG", "DC", "A", "T", "G", "C", "U"}


def fetch(pid):
    p = os.path.join(PDBDIR, f"{pid}.pdb")
    if not os.path.exists(p):
        urllib.request.urlretrieve(f"https://files.rcsb.org/download/{pid}.pdb", p)
    return p


def ca_trace(chain):
    xs = []
    for res in chain:
        if "CA" in res:
            xs.append(res["CA"].coord)
    return np.array(xs)


def smooth(coords, n=None):
    if len(coords) < 4 or not HAVE_SCIPY:
        return coords
    n = n or len(coords) * 6
    try:
        tck, u = splprep(coords.T, s=len(coords) * 2.0, k=3)
        return np.array(splev(np.linspace(0, 1, n), tck)).T
    except Exception:
        return coords


def set_equal(ax, pts, zoom=0.62):
    mn, mx = pts.min(0), pts.max(0)
    c = (mn + mx) / 2; r = (mx - mn).max() / 2 * zoom
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    try: ax.set_box_aspect((1, 1, 1))
    except Exception: pass
    ax.set_axis_off()


def draw_chain(ax, coords, color, lw=3.5, alpha=1.0):
    if len(coords) == 0:
        return
    s = smooth(coords)
    ax.plot(s[:, 0], s[:, 1], s[:, 2], color=color, lw=lw, alpha=alpha, solid_capstyle="round")


parser = PDBParser(QUIET=True)
plt.rcParams.update({"figure.dpi": 175})
fig = plt.figure(figsize=(13.0, 4.2))

# ---------- Panel 1: BRCA1 RING (1JM7) ----------
ax = fig.add_subplot(1, 3, 1, projection="3d")
st = parser.get_structure("1JM7", fetch("1JM7"))
model = st[0]
chains = list(model)
# heuristic: BRCA1 chain = the one with zinc-coordinating cysteines / first protein chain
allpts = []
brca1 = chains[0]
draw_chain(ax, ca_trace(brca1), "#d55e00", lw=4)          # BRCA1 RING (critical) - orange
allpts.append(ca_trace(brca1))
for ch in chains[1:]:
    t = ca_trace(ch)
    if len(t) > 5:
        draw_chain(ax, t, "#9aa0a6", lw=2.5, alpha=0.7)   # BARD1 - gray
        allpts.append(t)
# highlight zinc-coordinating cysteines of BRCA1 + zinc ions
cys = np.array([res["CA"].coord for res in brca1 if res.get_resname() == "CYS" and "CA" in res])
if len(cys):
    ax.scatter(cys[:, 0], cys[:, 1], cys[:, 2], c="#c1121f", s=42, depthshade=False, edgecolors="k", linewidths=0.4)
zn = np.array([a.coord for a in model.get_atoms() if a.element == "ZN"])
if len(zn):
    ax.scatter(zn[:, 0], zn[:, 1], zn[:, 2], c="#4d4d4d", s=90, depthshade=False, marker="o", edgecolors="k")
set_equal(ax, np.vstack(allpts))
ax.view_init(elev=18, azim=40)
ax.set_title("BRCA1 — domínio RING (PDB 1JM7)\nBRCA1 (laranja) + BARD1 (cinza);\nCys de coordenação de zinco em vermelho", fontsize=7.5)

# ---------- Panel 2: BRCA1 BRCT (1JNX) ----------
ax = fig.add_subplot(1, 3, 2, projection="3d")
st = parser.get_structure("1JNX", fetch("1JNX"))
model = st[0]
pts = []
for i, ch in enumerate(model):
    t = ca_trace(ch)
    if len(t) > 5:
        draw_chain(ax, t, "#1b7837" if i == 0 else "#9aa0a6", lw=4 if i == 0 else 2.5)
        pts.append(t)
set_equal(ax, np.vstack(pts))
ax.view_init(elev=20, azim=-60)
ax.set_title("BRCA1 — repetições BRCT (PDB 1JNX)\ndomínio crítico C-terminal", fontsize=7.5)

# ---------- Panel 3: BRCA2 DBD (1MJE) ----------
ax = fig.add_subplot(1, 3, 3, projection="3d")
st = parser.get_structure("1MJE", fetch("1MJE"))
model = st[0]
pts = []
# largest protein chain = BRCA2 DBD; DNA chains = orange; others gray (DSS1)
prot = []
for ch in model:
    resnames = [r.get_resname().strip() for r in ch]
    is_dna = sum(1 for r in resnames if r in DNA) > max(2, 0.5 * len(resnames))
    t = ca_trace(ch)
    if is_dna:
        # plot nucleic backbone via P or C1' atoms
        d = np.array([res["P"].coord for res in ch if "P" in res])
        if len(d) == 0:
            d = np.array([a.coord for a in ch.get_atoms()])
        if len(d):
            ax.plot(d[:, 0], d[:, 1], d[:, 2], color="#e69f00", lw=3.5)
            pts.append(d)
    elif len(t) > 5:
        prot.append((len(t), ch, t))
prot.sort(reverse=True, key=lambda x: x[0])
for rank, (_, ch, t) in enumerate(prot):
    draw_chain(ax, t, "#0072b2" if rank == 0 else "#9aa0a6", lw=4 if rank == 0 else 2.3, alpha=1 if rank == 0 else 0.7)
    pts.append(t)
set_equal(ax, np.vstack(pts))
ax.view_init(elev=15, azim=60)
ax.set_title("BRCA2 — domínio de ligação ao DNA (PDB 1MJE)\nBRCA2 (azul), DSS1 (cinza), ssDNA (laranja)", fontsize=7.5)

plt.subplots_adjust(left=0.0, right=1.0, top=0.90, bottom=0.0, wspace=0.0)
plt.savefig(os.path.join(OUT, "fig_protein_structures.png"), bbox_inches="tight", pad_inches=0.05)
plt.close()
print("wrote fig_protein_structures.png")
