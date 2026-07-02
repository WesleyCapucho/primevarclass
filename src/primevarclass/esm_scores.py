"""Ingestion of ESM-2 zero-shot variant-effect scores.

The protein language model ESM-2 (Lin et al., Science 2023; Meier et al.,
NeurIPS 2021) scores a missense substitution *without any supervision* using the
masked-marginal log-likelihood ratio (LLR):

    LLR = log P(aa_alt | context) - log P(aa_ref | context)

computed with the reference residue masked. A strongly negative LLR means the
model finds the substitution unlikely given the evolutionary/structural grammar
it learned -- an orthogonal, authentic deep-learning signal that does *not* leak
from the other in-silico predictors (REVEL/CADD/AlphaMissense) or from labels.

The heavy forward passes run in the companion Colab notebook
(``scratch/esm_colab``); this module only *ingests* the resulting CSV and merges
it onto the variant table. Keeping scoring and ingestion separate means the
package has no hard dependency on ``torch``/``fair-esm``.

Expected CSV columns (header names are matched case-insensitively, with a few
common aliases): ``gene, position, aa_ref, aa_alt, esm2_llr``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "ESM_SCORE_COLUMN",
    "load_esm_scores",
    "build_esm_lookup",
    "attach_esm_scores",
]

ESM_SCORE_COLUMN = "esm2_llr"

_KEY_COLUMNS = ("gene", "position", "aa_ref", "aa_alt")

# Accept a few reasonable header spellings from the scoring notebook.
_ALIASES = {
    "gene": {"gene", "symbol", "gene_symbol"},
    "position": {"position", "pos", "aa_pos", "residue", "resid"},
    "aa_ref": {"aa_ref", "ref", "wt", "wildtype", "aa_wt", "from_aa"},
    "aa_alt": {"aa_alt", "alt", "mut", "mutant", "aa_mut", "to_aa"},
    ESM_SCORE_COLUMN: {"esm2_llr", "esm_llr", "llr", "esm2_score", "esm_score", "score"},
}


def _resolve_columns(columns) -> Dict[str, str]:
    lower = {str(c).strip().lower(): c for c in columns}
    resolved: Dict[str, str] = {}
    for canonical, names in _ALIASES.items():
        for name in names:
            if name in lower:
                resolved[canonical] = lower[name]
                break
    missing = [c for c in (*_KEY_COLUMNS, ESM_SCORE_COLUMN) if c not in resolved]
    if missing:
        raise ValueError(
            f"ESM score file is missing required column(s): {missing}. "
            f"Found columns: {list(columns)}"
        )
    return resolved


def _norm_key(gene, position, aa_ref, aa_alt) -> Tuple[str, int, str, str]:
    return (
        str(gene).strip().upper(),
        int(position),
        str(aa_ref).strip().upper(),
        str(aa_alt).strip().upper(),
    )


def load_esm_scores(path: str | Path) -> pd.DataFrame:
    """Load and normalise an ESM-2 score CSV to columns
    ``gene, position, aa_ref, aa_alt, esm2_llr``.

    Rows with an unparseable position or a non-numeric score are dropped. On
    duplicate (gene, position, ref, alt) keys the mean LLR is kept.
    """
    path = Path(path)
    raw = pd.read_csv(path)
    cols = _resolve_columns(raw.columns)
    out = pd.DataFrame(
        {
            "gene": raw[cols["gene"]].astype(str).str.strip().str.upper(),
            "position": pd.to_numeric(raw[cols["position"]], errors="coerce"),
            "aa_ref": raw[cols["aa_ref"]].astype(str).str.strip().str.upper(),
            "aa_alt": raw[cols["aa_alt"]].astype(str).str.strip().str.upper(),
            ESM_SCORE_COLUMN: pd.to_numeric(raw[cols[ESM_SCORE_COLUMN]], errors="coerce"),
        }
    )
    out = out.dropna(subset=["position", ESM_SCORE_COLUMN]).copy()
    out["position"] = out["position"].astype(int)
    out = (
        out.groupby(list(_KEY_COLUMNS), as_index=False)[ESM_SCORE_COLUMN].mean()
    )
    return out


def build_esm_lookup(scores: pd.DataFrame) -> Dict[Tuple[str, int, str, str], float]:
    """Map normalised (gene, position, aa_ref, aa_alt) -> ESM-2 LLR.

    Keys are normalised (upper-cased gene/residues, int position) and duplicate
    keys are averaged, so the result is well-defined regardless of whether the
    input came from a CSV, a raw DataFrame, or was concatenated from several
    scoring runs.
    """
    sums: Dict[Tuple[str, int, str, str], float] = {}
    counts: Dict[Tuple[str, int, str, str], int] = {}
    for r in scores.itertuples(index=False):
        try:
            key = _norm_key(r.gene, r.position, r.aa_ref, r.aa_alt)
        except (TypeError, ValueError):
            continue
        val = float(getattr(r, ESM_SCORE_COLUMN))
        if np.isnan(val):
            continue
        sums[key] = sums.get(key, 0.0) + val
        counts[key] = counts.get(key, 0) + 1
    return {key: sums[key] / counts[key] for key in sums}


def attach_esm_scores(
    variants: pd.DataFrame,
    scores: str | Path | pd.DataFrame | Dict[Tuple[str, int, str, str], float],
) -> pd.DataFrame:
    """Return a copy of ``variants`` with ``esm2_llr`` and ``has_esm_score`` columns.

    ``scores`` may be a CSV path, a loaded score DataFrame, or a prebuilt lookup
    dict. Variants without a matching score get ``esm2_llr = NaN`` and
    ``has_esm_score = 0`` -- the model degrades gracefully, exactly as with the
    other optional annotations.
    """
    if isinstance(scores, dict):
        lookup = scores
    else:
        frame = scores if isinstance(scores, pd.DataFrame) else load_esm_scores(scores)
        lookup = build_esm_lookup(frame)

    out = variants.copy()

    def _score(row) -> float:
        try:
            key = _norm_key(row["gene"], row["position"], row["aa_ref"], row["aa_alt"])
        except (KeyError, TypeError, ValueError):
            return np.nan
        return lookup.get(key, np.nan)

    out[ESM_SCORE_COLUMN] = out.apply(_score, axis=1)
    out["has_esm_score"] = out[ESM_SCORE_COLUMN].notna().astype(int)
    return out
