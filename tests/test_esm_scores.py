"""Tests for ESM-2 score ingestion and its wiring into the feature subsets."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from primevarclass.esm_scores import (
    ESM_SCORE_COLUMN,
    attach_esm_scores,
    build_esm_lookup,
    load_esm_scores,
)
from primevarclass.core import MissenseVariant, encode_variant_features, get_feature_subsets


def _variants():
    return pd.DataFrame(
        [
            {"gene": "BRCA1", "position": 61, "aa_ref": "C", "aa_alt": "G"},
            {"gene": "BRCA2", "position": 2723, "aa_ref": "D", "aa_alt": "H"},
            {"gene": "BRCA1", "position": 900, "aa_ref": "S", "aa_alt": "N"},  # no score
        ]
    )


def test_load_and_alias_resolution(tmp_path):
    csv = tmp_path / "esm.csv"
    # deliberately use alias headers (pos, ref, mut, llr) and lowercase gene
    csv.write_text(
        "gene,pos,ref,mut,llr\n"
        "brca1,61,c,g,-8.4\n"
        "BRCA2,2723,D,H,-5.1\n",
        encoding="utf-8",
    )
    scores = load_esm_scores(csv)
    assert set(scores.columns) == {"gene", "position", "aa_ref", "aa_alt", ESM_SCORE_COLUMN}
    assert scores.loc[scores["position"] == 61, ESM_SCORE_COLUMN].iloc[0] == pytest.approx(-8.4)
    # normalisation upper-cased gene/residues
    assert set(scores["gene"]) == {"BRCA1", "BRCA2"}


def test_missing_required_column_raises(tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("gene,position,aa_ref\nBRCA1,61,C\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_esm_scores(csv)


def test_attach_from_dict_and_graceful_missing():
    lookup = {("BRCA1", 61, "C", "G"): -8.4, ("BRCA2", 2723, "D", "H"): -5.1}
    out = attach_esm_scores(_variants(), lookup)
    assert out.loc[0, ESM_SCORE_COLUMN] == pytest.approx(-8.4)
    assert out.loc[0, "has_esm_score"] == 1
    # the unmatched variant degrades gracefully
    assert np.isnan(out.loc[2, ESM_SCORE_COLUMN])
    assert out.loc[2, "has_esm_score"] == 0


def test_attach_from_dataframe_roundtrip():
    frame = pd.DataFrame(
        [{"gene": "BRCA1", "position": 61, "aa_ref": "C", "aa_alt": "G", ESM_SCORE_COLUMN: -8.4}]
    )
    lookup = build_esm_lookup(frame)
    out = attach_esm_scores(_variants(), frame)
    assert lookup[("BRCA1", 61, "C", "G")] == pytest.approx(-8.4)
    assert out.loc[0, "has_esm_score"] == 1


def test_duplicate_keys_are_averaged():
    frame = pd.DataFrame(
        [
            {"gene": "BRCA1", "position": 61, "aa_ref": "C", "aa_alt": "G", ESM_SCORE_COLUMN: -8.0},
            {"gene": "BRCA1", "position": 61, "aa_ref": "C", "aa_alt": "G", ESM_SCORE_COLUMN: -9.0},
        ]
    )
    lookup = build_esm_lookup(frame)
    assert lookup[("BRCA1", 61, "C", "G")] == pytest.approx(-8.5)


def test_esm_flows_through_encode_and_subsets():
    v = MissenseVariant(gene="BRCA1", aa_ref="C", position=61, aa_alt="G")
    # default: no score
    base = encode_variant_features(v)
    assert np.isnan(base["esm2_llr"])
    assert base["has_esm_score"] == 0
    # supplied via external_features
    scored = encode_variant_features(v, external_features={"esm2_llr": -8.4})
    assert scored["esm2_llr"] == pytest.approx(-8.4)
    assert scored["has_esm_score"] == 1

    subsets = get_feature_subsets(pd.DataFrame([scored]))
    assert "domain_aware_plus_esm" in subsets
    assert "esm2_llr" in subsets["domain_aware_plus_esm"]
    # flagship still excludes raw position
    assert "position" not in subsets["domain_aware_plus_esm"]
