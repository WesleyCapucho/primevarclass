"""Tests for the continual-learning module: provenance, idempotent feedback,
version registry and the promotion safety gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from primevarclass.continual import (  # noqa: E402
    FeedbackStore,
    ModelRegistry,
    normalize_label,
)


def test_normalize_label_accepts_synonyms():
    assert normalize_label("pathogenic") == 1
    assert normalize_label("Patogênica") == 1
    assert normalize_label("benign") == 0
    assert normalize_label("0") == 0
    with pytest.raises(ValueError):
        normalize_label("maybe")


def test_feedback_store_records_provenance(tmp_path):
    store = FeedbackStore(tmp_path)
    rec = store.add("brca1", 1699, "R", "W", "pathogenic", source="clinvar", submitter="lab_x")
    assert rec is not None
    assert rec.gene == "BRCA1" and rec.label == 1
    assert rec.aa_ref == "R" and rec.aa_alt == "W"
    assert len(rec.sha256) == 64                     # full SHA-256 hex
    assert rec.timestamp.endswith("Z")               # UTC provenance stamp
    assert rec.source == "clinvar" and rec.submitter == "lab_x"


def test_feedback_store_is_idempotent(tmp_path):
    store = FeedbackStore(tmp_path)
    assert store.add("BRCA2", 2748, "G", "D", "pathogenic") is not None
    # same variant + label again -> not re-recorded
    assert store.add("BRCA2", 2748, "G", "D", "pathogenic") is None
    assert len(store.load()) == 1
    # a different label at the same site IS a distinct record
    assert store.add("BRCA2", 2748, "G", "D", "benign") is not None
    assert len(store.load()) == 2


def test_feedback_hash_is_content_addressed(tmp_path):
    a = FeedbackStore(tmp_path / "a").add("BRCA1", 61, "C", "G", "pathogenic")
    b = FeedbackStore(tmp_path / "b").add("BRCA1", 61, "C", "G", "pathogenic")
    # identity hash depends only on the variant + label, not on time/submitter
    assert a.sha256 == b.sha256


def test_model_registry_versions_monotonically(tmp_path):
    reg = ModelRegistry(tmp_path)
    e1 = reg.record(n_feedback=0, holdout_auc=0.90, baseline_auc=0.90,
                    model_sha256="abc", promoted=True)
    e2 = reg.record(n_feedback=5, holdout_auc=0.72, baseline_auc=0.90,
                    model_sha256="def", promoted=False)
    assert e1["version"] == 1 and e2["version"] == 2
    assert reg.latest_version() == 2
    assert e2["promoted"] is False                   # a rejected update is still logged
