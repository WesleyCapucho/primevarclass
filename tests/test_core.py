"""Tests for the PrimeVarClass core: variant parsing, feature engineering,
domain-aware feature subsets, ESM-2 ingestion and ACMG evidence mapping.

These exercise the public API used by the manuscript's reproduction scripts and
the CLI — no scaffolding, no network, no fabricated data.
"""
import numpy as np
import pandas as pd

from primevarclass import (
    annotate_domain,
    attach_esm_scores,
    build_dataset_from_dataframe,
    classify_acmg_strength_from_lr,
    clinvar_binary_label,
    get_feature_subsets,
    parse_variant,
)


def _raw_variants():
    return pd.DataFrame(
        [
            {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": 1},
            {"gene": "BRCA1", "hgvs_p": "p.Met1775Arg", "label": 1},
            {"gene": "BRCA1", "hgvs_p": "p.Ala1453Gly", "label": 0},
            {"gene": "BRCA2", "hgvs_p": "p.Asp2723His", "label": 1},
            {"gene": "BRCA2", "hgvs_p": "p.Ala2466Val", "label": 0},
        ]
    )


def test_parse_variant_roundtrip():
    v = parse_variant("BRCA1 p.Arg1699Trp")
    assert v.gene == "BRCA1"
    assert v.position == 1699
    assert v.aa_ref == "R"
    assert v.aa_alt == "W"


def test_annotate_domain_critical_regions():
    # BRCA1 RING and BRCT are critical; a linker position is not.
    assert annotate_domain("BRCA1", 61) == ("RING", 1)
    assert annotate_domain("BRCA1", 1775)[1] == 1
    assert annotate_domain("BRCA2", 2723)[1] == 1          # DBD OB1
    assert annotate_domain("BRCA1", 800) == ("linker", 0)
    # messy input never raises
    assert annotate_domain("UNKNOWN", 10) == ("linker", 0)
    assert annotate_domain("BRCA1", -5) == ("linker", 0)


def test_build_dataset_and_feature_subsets():
    built, _ = build_dataset_from_dataframe(_raw_variants(), mode="hybrid", keep_metadata=True)
    assert len(built) == 5
    subsets = get_feature_subsets(built)
    # the domain-aware and flagship subsets exist and carry the region features
    assert "domain_aware" in subsets and "domain_aware_plus_esm" in subsets
    assert {"functional_domain", "in_critical_domain"} & set(built.columns)
    assert any("in_critical_domain" == c for c in built.columns)
    # prime features are the tested-and-refuted hypothesis and are isolated
    assert "prime_only" in subsets


def test_attach_esm_scores_matches_by_position():
    built, _ = build_dataset_from_dataframe(_raw_variants(), mode="hybrid", keep_metadata=True)
    esm = pd.DataFrame(
        [
            {"gene": "BRCA1", "position": 61, "aa_ref": "C", "aa_alt": "G", "esm2_llr": -10.9},
            {"gene": "BRCA1", "position": 1775, "aa_ref": "M", "aa_alt": "R", "esm2_llr": -12.0},
        ]
    )
    out = attach_esm_scores(built, esm)
    assert "esm2_llr" in out.columns
    # the two supplied variants get their real LLRs; pathogenic direction is negative
    c61 = out[(out["position"] == 61)]["esm2_llr"].iloc[0]
    assert float(c61) < -2


def test_acmg_strength_monotonic_in_lr():
    weak = classify_acmg_strength_from_lr(1.0)
    strong = classify_acmg_strength_from_lr(50.0)
    assert classify_acmg_strength_from_lr(np.nan) == "uninformative"
    assert "strong" in strong
    assert strong != weak


def test_clinvar_binary_label_covers_every_real_significance_string():
    """Every ClinicalSignificance string that occurs in the BRCA1/BRCA2 data,
    including the 'Likely ...' forms a case-sensitive test silently drops."""
    pathogenic = ["Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"]
    benign = ["Benign", "Likely benign", "Benign/Likely benign"]
    undefined = [
        "Uncertain significance",
        "Conflicting classifications of pathogenicity",
        "Conflicting interpretations of pathogenicity",
        "not provided",
        "no interpretation for the single variant",
        "",
        None,
        np.nan,
    ]
    for s in pathogenic:
        assert clinvar_binary_label(s) == 1, s
        assert clinvar_binary_label(s.upper()) == 1, s      # case must not matter
        assert clinvar_binary_label(s.lower()) == 1, s
    for s in benign:
        assert clinvar_binary_label(s) == 0, s
        assert clinvar_binary_label(s.upper()) == 0, s
        assert clinvar_binary_label(s.lower()) == 0, s
    for s in undefined:
        assert clinvar_binary_label(s) is None, s
