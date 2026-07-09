"""Explainability (SHAP) for the domain-aware classifier — turns the paper's
'explainable AI' claim into a demonstrated, auditable analysis.

Computes SHAP values (TreeExplainer) for the domain-aware Random Forest trained
on the real internal cohort, and saves a beeswarm summary of the features that
most drive pathogenicity predictions.

Run: python scratch/shap_explain.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))
os.environ.setdefault("PRIMEVARCLASS_N_JOBS", "1")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

from primevarclass.core import _build_pipeline, get_feature_subsets
from primevarclass.data_sources import build_dataset_from_source_config
from primevarclass.esm_scores import attach_esm_scores

RNG = 42
OUT = "primevarclass_manuscript_analysis"
os.makedirs(OUT, exist_ok=True)
ESM = pd.read_csv("scratch/esm_input/esm2_scores.csv")


def load(cfg):
    df, _, _ = build_dataset_from_source_config(cfg, mode="hybrid", keep_metadata=True)
    y = pd.to_numeric(df["label"], errors="coerce"); keep = y.notna()
    df = attach_esm_scores(df.loc[keep].reset_index(drop=True), ESM)
    return df, y.loc[keep].astype(int).to_numpy()


print(">> loading cohort + training domain-aware + ESM-2 model ...")
df, y = load("configs/public_brca_real.toml")
cols = [c for c in get_feature_subsets(df)["domain_aware_plus_esm"] if c in df.columns and not df[c].isna().all()]
pipe = _build_pipeline(df[cols], random_state=RNG)
pipe.fit(df[cols], y)

# transform through the pipeline's preprocessor to get the model-input matrix + names
pre = pipe[:-1]
model = pipe[-1]
Xt = pre.transform(df[cols])
try:
    names = list(pre.get_feature_names_out())
except Exception:
    names = [f"f{i}" for i in range(Xt.shape[1])]
Xt = np.asarray(Xt.todense()) if hasattr(Xt, "todense") else np.asarray(Xt)
Xt_df = pd.DataFrame(Xt, columns=[n.split("__")[-1] for n in names])

print(f">> computing SHAP values on {Xt_df.shape[0]}x{Xt_df.shape[1]} matrix ...")
expl = shap.TreeExplainer(model)
sv = expl.shap_values(Xt_df)
if isinstance(sv, list):                 # older SHAP: list per class
    sv_pos = sv[1]
elif getattr(sv, "ndim", 2) == 3:        # SHAP >=0.45: (n_samples, n_features, n_classes)
    sv_pos = sv[:, :, 1]
else:
    sv_pos = sv
sv_pos = np.asarray(sv_pos)

plt.figure()
shap.summary_plot(sv_pos, Xt_df, max_display=15, show=False)
plt.title("Explicabilidade (SHAP): características que mais influenciam a predição de patogenicidade", fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fig_shap.png"), dpi=170, bbox_inches="tight")
plt.close()

imp = pd.DataFrame({"feature": Xt_df.columns, "mean_abs_shap": np.abs(sv_pos).mean(0)})
imp = imp.sort_values("mean_abs_shap", ascending=False).head(15)
imp.to_csv(os.path.join(OUT, "shap_top_features.csv"), index=False)
print(">> top features by mean|SHAP|:")
print(imp.to_string(index=False))
print(f">> wrote {OUT}/fig_shap.png and shap_top_features.csv")
