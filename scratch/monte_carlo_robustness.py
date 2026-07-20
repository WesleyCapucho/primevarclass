"""Monte Carlo + robustness battery for the domain-aware classifier.

Produces, on the REAL BRCA1/BRCA2 cohorts:
  (1) Bootstrap 95% CIs for external AUC of each model + paired differences.
  (2) Label-permutation null test for the domain-aware external AUC.
  (3) Repeated position-blocked CV over many seeds -> AUC distribution.
  (4) Calibration (Brier score + reliability curve) for the domain-aware model.

Saves results.json and publication figures to primevarclass_manuscript_analysis/.
Run: python scratch/monte_carlo_robustness.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedGroupKFold

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config

OUT = "primevarclass_manuscript_analysis"
os.makedirs(OUT, exist_ok=True)
RNG = 42
N_BOOT = 2000
N_PERM = 2000
N_SEEDS = 12
rng = np.random.default_rng(RNG)


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce")
    keep = y.notna()
    return df.loc[keep].reset_index(drop=True), y.loc[keep].astype(int).to_numpy()


print(">> loading real cohorts...")
tr_df, ytr = load("configs/public_brca_real.toml")
ext = [load(c) for c in [
    "configs/public_brca_external_real_clinvar_expert_brca1.toml",
    "configs/public_brca_external_real_clinvar_expert_brca2.toml",
    "configs/public_brca_external_real_brca1.toml",
    "configs/public_brca_external_real_brca2.toml"]]
ext_df = pd.concat([f[0] for f in ext], ignore_index=True)
yext = np.concatenate([f[1] for f in ext])
print(f"   train n={len(tr_df)}  external n={len(ext_df)}  pathogenic ext={yext.mean():.2%}")

subs = get_feature_subsets(tr_df)
MODELS = {
    "Bioquímico (sem posição)": [c for c in subs["biochemical_only"] if c != "position"],
    "Domínio-consciente": subs["domain_aware"],
    "Posição bruta": subs["biochemical_only"],
}
def ok(cols, df): return [c for c in cols if c in df.columns and not df[c].isna().all()]

# ---- fit once, predict external ----
extP = {}
for name, cols in MODELS.items():
    c = [x for x in ok(cols, tr_df) if x in ext_df.columns]
    p = _build_pipeline(tr_df[c], random_state=RNG); p.fit(tr_df[c], ytr)
    extP[name] = p.predict_proba(ext_df[c])[:, 1]

results = {"n_train": int(len(tr_df)), "n_external": int(len(ext_df)),
           "pathogenic_rate_external": float(yext.mean()),
           "n_bootstrap": N_BOOT, "n_permutation": N_PERM, "n_seeds": N_SEEDS}

# ---- (1) bootstrap external AUC + paired differences ----
print(">> (1) bootstrap external AUC...")
n = len(yext)
boot = {name: np.empty(N_BOOT) for name in MODELS}
diff_dom_bio = np.empty(N_BOOT); diff_dom_pos = np.empty(N_BOOT)
b = 0
while b < N_BOOT:
    idx = rng.integers(0, n, n)
    yb = yext[idx]
    if yb.min() == yb.max():
        continue
    for name in MODELS:
        boot[name][b] = roc_auc_score(yb, extP[name][idx])
    diff_dom_bio[b] = boot["Domínio-consciente"][b] - boot["Bioquímico (sem posição)"][b]
    diff_dom_pos[b] = boot["Domínio-consciente"][b] - boot["Posição bruta"][b]
    b += 1
def ci(a): return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
results["external_auc"] = {name: {"point": float(roc_auc_score(yext, extP[name])),
                                   "boot_mean": float(boot[name].mean()), "ci95": ci(boot[name])}
                            for name in MODELS}
results["auc_diff"] = {
    "domain_vs_biochem": {"mean": float(diff_dom_bio.mean()), "ci95": ci(diff_dom_bio),
                           "p_gt_0": float((diff_dom_bio <= 0).mean())},
    "domain_vs_position": {"mean": float(diff_dom_pos.mean()), "ci95": ci(diff_dom_pos),
                            "p_gt_0": float((diff_dom_pos <= 0).mean())},
}
for name in MODELS:
    r = results["external_auc"][name]
    print(f"   {name:26s} AUC={r['point']:.3f}  95% CI [{r['ci95'][0]:.3f}, {r['ci95'][1]:.3f}]")

# ---- (2) label-permutation null for domain-aware ----
print(">> (2) permutation null test...")
obs = roc_auc_score(yext, extP["Domínio-consciente"])
null = np.empty(N_PERM)
for i in range(N_PERM):
    null[i] = roc_auc_score(rng.permutation(yext), extP["Domínio-consciente"])
p_perm = float((null >= obs).mean())
results["permutation"] = {"observed_auc": float(obs), "null_mean": float(null.mean()),
                          "null_ci95": ci(null), "p_value": max(p_perm, 1.0 / N_PERM)}
print(f"   observed={obs:.3f}  null mean={null.mean():.3f}  p={results['permutation']['p_value']:.2e}")

# ---- (3) repeated position-blocked CV ----
print(">> (3) repeated multi-seed position-blocked CV...")
groups = (tr_df["gene"].astype(str) + ":" + tr_df["position"].astype(str)).to_numpy()
cv_auc = {name: [] for name in MODELS}
oof_dom_ref = None
for s in range(N_SEEDS):
    for name, cols in MODELS.items():
        c = ok(cols, tr_df); X = tr_df[c].copy(); oof = np.zeros(len(ytr))
        for a, bb in StratifiedGroupKFold(5, shuffle=True, random_state=1000 + s).split(X, ytr, groups):
            p = _build_pipeline(X.iloc[a], random_state=RNG); p.fit(X.iloc[a], ytr[a])
            oof[bb] = p.predict_proba(X.iloc[bb])[:, 1]
        cv_auc[name].append(roc_auc_score(ytr, oof))
        if name == "Domínio-consciente" and s == 0:
            oof_dom_ref = oof.copy()
results["repeated_cv"] = {name: {"mean": float(np.mean(v)), "sd": float(np.std(v)),
                                 "min": float(np.min(v)), "max": float(np.max(v))}
                          for name, v in cv_auc.items()}
for name, v in cv_auc.items():
    print(f"   {name:26s} CV AUC={np.mean(v):.3f} ± {np.std(v):.3f}")

# ---- (4) calibration (domain-aware, external) ----
print(">> (4) calibration...")
def reliability(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1); mids = []; obs_f = []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum() > 0:
            mids.append(float(p[m].mean())); obs_f.append(float(y[m].mean()))
    return mids, obs_f
brier = float(brier_score_loss(yext, extP["Domínio-consciente"]))
mids, obs_f = reliability(yext, extP["Domínio-consciente"])
results["calibration"] = {"brier_score": brier, "reliability_x": mids, "reliability_y": obs_f}
print(f"   Brier score (external) = {brier:.3f}")

with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# ============================= FIGURES =============================
plt.rcParams.update({"figure.dpi": 150, "font.size": 10})
COL = {"Bioquímico (sem posição)": "#7f7f7f", "Domínio-consciente": "#1b7837", "Posição bruta": "#d55e00"}

# Fig A: ROC external
plt.figure(figsize=(5.2, 5))
for name in MODELS:
    fpr, tpr, _ = roc_curve(yext, extP[name])
    a = roc_auc_score(yext, extP[name])
    plt.plot(fpr, tpr, color=COL[name], lw=2, label=f"{name} (AUC={a:.3f})")
plt.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
plt.xlabel("Taxa de falsos positivos"); plt.ylabel("Taxa de verdadeiros positivos")
plt.title("Curva ROC — coortes externas independentes"); plt.legend(loc="lower right", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_roc_external.png")); plt.close()

# Fig B: bootstrap AUC distributions
plt.figure(figsize=(6, 4))
for name in MODELS:
    plt.hist(boot[name], bins=40, alpha=0.55, color=COL[name], label=name)
plt.xlabel("AUC (bootstrap externo)"); plt.ylabel("Frequência")
plt.title(f"Distribuição bootstrap da AUC externa (B={N_BOOT})"); plt.legend(fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_bootstrap_auc.png")); plt.close()

# Fig C: permutation null
plt.figure(figsize=(6, 4))
plt.hist(null, bins=40, color="#999999", alpha=0.8, label="AUC sob H0 (rótulos permutados)")
plt.axvline(obs, color="#1b7837", lw=2.5, label=f"AUC observada = {obs:.3f}")
plt.xlabel("AUC"); plt.ylabel("Frequência")
plt.title(f"Teste de permutação (N={N_PERM}, p={results['permutation']['p_value']:.1e})")
plt.legend(fontsize=12); plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_permutation.png")); plt.close()

# Fig D: repeated CV boxplot
plt.figure(figsize=(6, 4))
data = [cv_auc[name] for name in MODELS]
bp = plt.boxplot(data, labels=[n.replace(" ", "\n") for n in MODELS], patch_artist=True)
for patch, name in zip(bp["boxes"], MODELS):
    patch.set_facecolor(COL[name]); patch.set_alpha(0.6)
plt.ylabel("AUC (CV bloqueada por posição)")
plt.title(f"Estabilidade em {N_SEEDS} sementes de validação cruzada")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_repeated_cv.png")); plt.close()

# Fig E: calibration
plt.figure(figsize=(5, 5))
plt.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Perfeitamente calibrado")
plt.plot(mids, obs_f, "o-", color="#1b7837", lw=2, label=f"Domínio-consciente (Brier={brier:.3f})")
plt.xlabel("Probabilidade prevista"); plt.ylabel("Frequência observada de patogenicidade")
plt.title("Curva de calibração — coortes externas"); plt.legend(fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_calibration.png")); plt.close()

print(f"\n>> DONE. Wrote {OUT}/results.json and 5 figures.")
