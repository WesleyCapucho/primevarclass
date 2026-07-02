"""Tests for functional-domain annotation and its wiring into the feature pipeline."""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from primevarclass.domain_annotation import annotate_domain, LINKER_LABEL
from primevarclass.core import MissenseVariant, encode_variant_features, get_feature_subsets


@pytest.mark.parametrize(
    "gene,position,expected_domain,expected_critical",
    [
        ("BRCA1", 61, "RING", 1),         # RING E3-ligase (1-109)
        ("BRCA1", 1, "RING", 1),          # left boundary inclusive
        ("BRCA1", 109, "RING", 1),        # right boundary inclusive
        ("BRCA1", 1700, "BRCT1", 1),      # first BRCT repeat
        ("BRCA1", 1800, "BRCT2", 1),      # second BRCT repeat
        ("BRCA1", 900, LINKER_LABEL, 0),  # between domains
        ("BRCA2", 2723, "DBD_OB1", 1),    # DNA-binding OB fold
        ("BRCA2", 2500, "DBD_helical", 1),
        ("BRCA2", 25, "PALB2_binding", 0),  # real domain, not critical
        ("BRCA2", 75, LINKER_LABEL, 0),   # outside all spans
    ],
)
def test_annotate_domain_boundaries(gene, position, expected_domain, expected_critical):
    name, critical = annotate_domain(gene, position)
    assert name == expected_domain
    assert critical == expected_critical


@pytest.mark.parametrize(
    "gene,position",
    [("UNKNOWN", 61), ("BRCA1", 0), ("BRCA1", -5), ("BRCA1", None), ("BRCA1", "x")],
)
def test_annotate_domain_is_robust_to_bad_input(gene, position):
    assert annotate_domain(gene, position) == (LINKER_LABEL, 0)


def test_critical_domain_boundaries_are_ordered_and_valid():
    from primevarclass.domain_annotation import BRCA1_DOMAINS, BRCA2_DOMAINS

    for domains in (BRCA1_DOMAINS, BRCA2_DOMAINS):
        for span in domains:
            assert 1 <= span.start <= span.end
            assert isinstance(span.critical, bool)


def test_encode_populates_real_domain_features():
    v = MissenseVariant(gene="BRCA1", aa_ref="C", position=61, aa_alt="G")
    f = encode_variant_features(v)
    assert f["functional_domain"] == "RING"
    assert f["in_critical_domain"] == 1
    assert f["in_functional_domain"] == 1

    linker = encode_variant_features(
        MissenseVariant(gene="BRCA1", aa_ref="S", position=900, aa_alt="N")
    )
    assert linker["functional_domain"] == LINKER_LABEL
    assert linker["in_critical_domain"] == 0
    assert linker["in_functional_domain"] == 0


def test_domain_aware_subset_excludes_raw_position():
    rows = [
        encode_variant_features(MissenseVariant(gene="BRCA1", aa_ref="C", position=61, aa_alt="G")),
        encode_variant_features(MissenseVariant(gene="BRCA2", aa_ref="D", position=2723, aa_alt="H")),
    ]
    subsets = get_feature_subsets(pd.DataFrame(rows))
    assert "domain_aware" in subsets
    cols = subsets["domain_aware"]
    # The whole point of the leakage-free hook: no raw residue index.
    assert "position" not in cols
    assert "functional_domain" in cols
    assert "in_critical_domain" in cols
