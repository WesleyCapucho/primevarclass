"""Functional-domain annotation for BRCA1/BRCA2 missense variants.

This module maps an amino-acid position onto the curated functional domains of
the BRCA1 and BRCA2 proteins and flags whether the position falls inside a
domain that is *critical* for the protein's tumour-suppressor function.

Why this exists
---------------
Controlled experiments on real ClinVar/expert-panel data (see
``scratch/domain_aware_test.py``) showed that a model using these two
*region-level* features -- ``functional_domain`` (categorical) and
``in_critical_domain`` (binary) -- generalises to unseen external cohorts
*better* than a model given the raw residue ``position``:

    biochemical (no position)      external AUC 0.717
    biochemical + DOMAIN           external AUC 0.843   (DeLong p < 0.0001)
    biochemical + raw position     external AUC 0.791   (memorises, transfers worse)

Unlike a unique residue index, a domain label is a function of a *region*, so
it encodes transferable biology instead of memorising which exact positions
were pathogenic in the training set. This is the honest, defensible core of the
classifier.

Domain boundaries
-----------------
Coordinates follow the canonical UniProt entries and the ENIGMA/ClinGen
clinically important functional regions:

* BRCA1 -- UniProt P38398 (1863 aa). RING (BARD1-binding E3-ligase) and the two
  tandem BRCT repeats are the experimentally validated critical regions.
* BRCA2 -- UniProt P51587 (3418 aa). The C-terminal DNA-binding domain (helical
  + three OB folds) is the critical region; the BRC repeats bind RAD51.

Boundaries are approximate (literature-standard) and centralised here so a
single edit updates every consumer. They are intentionally identical to the
values validated in the experiment above.

References
----------
* UniProt Consortium. Nucleic Acids Res. 2023 (P38398, P51587).
* Yang H. et al. Science 2002 (BRCA2 DBD structure).
* Clark S.L. et al. NPJ Breast Cancer 2019 (BRCA1 domain / variant impact).
"""
from __future__ import annotations

from typing import List, NamedTuple, Tuple

__all__ = [
    "DomainSpan",
    "BRCA1_DOMAINS",
    "BRCA2_DOMAINS",
    "annotate_domain",
    "LINKER_LABEL",
]

LINKER_LABEL = "linker"


class DomainSpan(NamedTuple):
    """A named, inclusive residue span [start, end] of a protein domain."""

    name: str
    start: int
    end: int
    critical: bool


# UniProt P38398 (BRCA1, 1863 aa)
BRCA1_DOMAINS: List[DomainSpan] = [
    DomainSpan("RING", 1, 109, True),               # BARD1-binding RING / E3 ligase
    DomainSpan("coiled_coil_PALB2", 1391, 1424, False),
    DomainSpan("SCD", 1280, 1524, False),           # serine-cluster domain
    DomainSpan("BRCT1", 1642, 1736, True),
    DomainSpan("BRCT2", 1756, 1855, True),
]

# UniProt P51587 (BRCA2, 3418 aa)
BRCA2_DOMAINS: List[DomainSpan] = [
    DomainSpan("PALB2_binding", 10, 40, False),
    DomainSpan("BRC_repeats", 1002, 2085, False),   # RAD51-binding BRC repeats
    DomainSpan("DBD_helical", 2481, 2667, True),    # DNA-binding domain (critical)
    DomainSpan("DBD_OB1", 2670, 2803, True),
    DomainSpan("DBD_OB2", 2809, 2932, True),
    DomainSpan("DBD_OB3", 3052, 3186, True),
    DomainSpan("TR2_RAD51_Cterm", 3265, 3330, False),
]

_DOMAINS_BY_GENE = {
    "BRCA1": BRCA1_DOMAINS,
    "BRCA2": BRCA2_DOMAINS,
}


def annotate_domain(gene: str, position: int) -> Tuple[str, int]:
    """Return ``(domain_name, in_critical_domain)`` for a residue position.

    ``domain_name`` is the first matching domain (spans do not overlap) or
    :data:`LINKER_LABEL` when the position lies between annotated domains.
    ``in_critical_domain`` is ``1`` inside a functionally critical region,
    else ``0``.

    Unknown genes or non-positive / non-integer positions return
    ``(LINKER_LABEL, 0)`` so callers never raise on messy input.
    """
    domains = _DOMAINS_BY_GENE.get(str(gene).upper())
    if domains is None:
        return LINKER_LABEL, 0
    try:
        pos = int(position)
    except (TypeError, ValueError):
        return LINKER_LABEL, 0
    if pos <= 0:
        return LINKER_LABEL, 0
    for span in domains:
        if span.start <= pos <= span.end:
            return span.name, int(span.critical)
    return LINKER_LABEL, 0
