"""Clinical-utility / triage-efficiency test on the REAL external cohort.

Turns the AUC into a concrete operational claim a public lab can act on: how much
variant-review burden PrimeVarClass safely removes, and whether using it beats the
default strategies ("review every VUS" / "review none"). Two standard tools:

  (A) Triage efficiency — rank variants by score (most suspicious first) and measure
      the sensitivity achieved per fraction reviewed. Rank-based, so it is fair to
      every predictor (CADD/REVEL/AM included). Reports the work saved at fixed
      pathogenic sensitivity and the safety of the calibrated BP4 rule-out.
  (B) Decision-curve analysis (Vickers & Elkin, 2006) — net benefit of acting on the
      calibrated PrimeVarClass probability vs. "review all" and "review none" across
      the clinically relevant threshold range. Needs a calibrated probability, which
      is itself a differential: raw CADD/REVEL are not probabilities.

All numbers come from primevarclass_manuscript_analysis/benchmark_scores.csv
(836 external variants, real ClinVar labels; nothing simulated).

Run: python scratch/clinical_utility.py
"""
from __future__ import annotations

import json
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ANL = "primevarclass_manuscript_analysis"
FIGS = ["docs/suplementar/figuras/fig_clinical_utility.png",
        os.path.join(ANL, "fig_clinical_utility.png")]
d = pd.read_csv(os.path.join(ANL, "benchmark_scores.csv"))
y = d["label"].to_numpy().astype(int)
n = len(y); npos = int(y.sum()); prev = npos / n
TOOLS = {"PrimeVarClass": "#c0392b", "am": "#5a7fb0", "revel": "#3a8f5b", "cadd": "#9a7db0"}
NAMES = {"PrimeVarClass": "PrimeVarClass", "am": "AlphaMissense", "revel": "REVEL", "cadd": "CADD"}


def triage_curve(score):
    m = ~np.isnan(score)
    s = score[m]; yy = y[m]
    order = np.argsort(-s); yy = yy[order]
    frac = np.arange(1, len(yy) + 1) / len(yy)
    sens = np.cumsum(yy) / yy.sum()
    return frac, sens, int(m.sum()), int(yy.sum())


def reviewed_for(frac, sens, target):
    i = int(np.argmax(sens >= target))
    return float(frac[i])


out = {"n": n, "n_pathogenic": npos, "prevalence": round(prev, 4), "tools": {}}
plt.rcParams.update({"figure.dpi": 200, "font.size": 11})
fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.6, 5.2))

# ---- Panel A: triage efficiency ----
for tool, col in TOOLS.items():
    frac, sens, cov, pos = triage_curve(d[tool].to_numpy(float))
    r = {t: round(reviewed_for(frac, sens, t), 4) for t in (0.90, 0.95, 0.99)}
    out["tools"][NAMES[tool]] = {"coverage": cov, "positives": pos,
                                 "reviewed_for_0.90sens": r[0.90],
                                 "reviewed_for_0.95sens": r[0.95],
                                 "reviewed_for_0.99sens": r[0.99],
                                 "work_saved_at_0.95sens": round(1 - r[0.95], 4)}
    axA.plot(frac * 100, sens * 100, color=col, lw=2.0 if tool == "PrimeVarClass" else 1.3,
             label=f"{NAMES[tool]} (n={cov})", zorder=3 if tool == "PrimeVarClass" else 2)
axA.plot([0, 100], [0, 100], "--", color="#999", lw=1, label="triagem aleatória")
axA.set_xlabel("Variantes revisadas (%)"); axA.set_ylabel("Patogênicas capturadas: sensibilidade (%)")
axA.set_title("A. Eficiência de triagem (coorte externa real, n = 836)", fontsize=14.3)
axA.legend(fontsize=12, loc="lower right"); axA.grid(alpha=0.22)
axA.set_xlim(0, 100); axA.set_ylim(0, 101)

# ---- BP4 rule-out safety operating points (calibrated PrimeVarClass probability) ----
p = d["PrimeVarClass"].to_numpy(float)
ruleout = {}
for thr in (0.10, 0.15, 0.20):
    cleared = p < thr
    miss = int((cleared & (y == 1)).sum())
    ruleout[f"P<{thr}"] = {"deprioritised": int(cleared.sum()),
                           "deprioritised_frac": round(cleared.mean(), 4),
                           "pathogenic_missed": miss,
                           "sensitivity_retained": round(1 - miss / npos, 4)}
out["bp4_rule_out"] = ruleout

# ---- Panel B: decision curve (net benefit) for the calibrated probability ----
def net_benefit(prob, pt):
    pred = prob >= pt
    tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum())
    return tp / n - fp / n * (pt / (1 - pt))


pts = np.linspace(0.01, 0.5, 60)
nb_model = np.array([net_benefit(p, t) for t in pts])
nb_all = np.array([prev - (1 - prev) * (t / (1 - t)) for t in pts])
axB.plot(pts, nb_model, color="#c0392b", lw=2.2, label="PrimeVarClass (prob. calibrada)")
axB.plot(pts, nb_all, color="#777", lw=1.3, ls="-.", label="revisar todas as VUS")
axB.axhline(0, color="#333", lw=1, ls="--", label="revisar nenhuma")
axB.set_xlabel("Limiar de probabilidade (custo relativo revisão/erro)")
axB.set_ylabel("Benefício líquido")
axB.set_title("B. Curva de decisão clínica (Vickers & Elkin)", fontsize=14.3)
axB.legend(fontsize=12, loc="upper right"); axB.grid(alpha=0.22)
axB.set_xlim(0, 0.5)
out["decision_curve"] = {f"pt={t:.2f}": {"nb_model": round(float(net_benefit(p, t)), 4),
                                         "nb_review_all": round(float(prev - (1 - prev) * (t / (1 - t))), 4)}
                         for t in (0.05, 0.10, 0.20, 0.30)}

fig.suptitle("Utilidade clínica em dados reais: quanto trabalho de revisão o modelo poupa com segurança",
             fontweight="bold", fontsize=12.5)
fig.tight_layout(rect=[0, 0, 1, 0.95])
for f in FIGS:
    os.makedirs(os.path.dirname(f), exist_ok=True)
    fig.savefig(f, dpi=200, bbox_inches="tight", facecolor="white")

json.dump(out, open(os.path.join(ANL, "clinical_utility.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- report ----
pv = out["tools"]["PrimeVarClass"]
print(f">> n={n}  patogênicas={npos} ({prev:.1%})")
print(f">> PrimeVarClass: p/ 95% sens revisar {pv['reviewed_for_0.95sens']:.1%} "
      f"(poupa {pv['work_saved_at_0.95sens']:.1%})")
ro = ruleout["P<0.1"]
print(f">> BP4 rule-out P<0.10: desprioriza {ro['deprioritised']} ({ro['deprioritised_frac']:.1%}) "
      f"| sensibilidade mantida {ro['sensitivity_retained']:.1%} (perde {ro['pathogenic_missed']})")
print(f">> Net benefit pt=0.10: modelo {out['decision_curve']['pt=0.10']['nb_model']:+.3f} "
      f"vs revisar-todas {out['decision_curve']['pt=0.10']['nb_review_all']:+.3f}")
print(">> wrote clinical_utility.json + fig_clinical_utility.png")
