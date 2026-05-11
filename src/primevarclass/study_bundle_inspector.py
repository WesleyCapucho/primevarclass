from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .versioning import load_release_manifest


def _safe_load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return load_release_manifest(str(path))
    except Exception:
        return {}


def inspect_study_bundle(result_dir: str) -> dict:
    root = Path(result_dir).resolve()
    study_release = _safe_load_manifest(root / "study_release_manifest.json")
    publication_readiness = _safe_load_manifest(root / "publication_readiness_manifest.json")
    cohort_independence = _safe_load_manifest(root / "cohort_independence_manifest.json")
    cohort_freeze = _safe_load_manifest(root / "study_cohort_freeze_manifest.json")
    comparative_evidence = _safe_load_manifest(root / "comparative_evidence_manifest.json")
    claim_strength = _safe_load_manifest(root / "claim_strength_manifest.json")
    external_robustness = _safe_load_manifest(root / "external_robustness_manifest.json")
    baseline_coverage = _safe_load_manifest(root / "baseline_coverage_manifest.json")
    methods_package = _safe_load_manifest(root / "methods_package_manifest.json")
    manuscript_package = _safe_load_manifest(root / "manuscript_package_manifest.json")
    validation_lock = _safe_load_manifest(root / "study_validation_lock_manifest.json")
    scientific_dossier = _safe_load_manifest(root / "study_scientific_dossier_manifest.json")

    availability = {
        "study_release": bool(study_release),
        "publication_readiness": bool(publication_readiness),
        "cohort_independence": bool(cohort_independence),
        "cohort_freeze": bool(cohort_freeze),
        "comparative_evidence": bool(comparative_evidence),
        "claim_strength": bool(claim_strength),
        "external_robustness": bool(external_robustness),
        "baseline_coverage": bool(baseline_coverage),
        "methods_package": bool(methods_package),
        "manuscript_package": bool(manuscript_package),
        "validation_lock": bool(validation_lock),
        "scientific_dossier": bool(scientific_dossier),
    }

    summary = {
        "result_dir": str(root),
        "has_study_release_manifest": availability["study_release"],
        "has_publication_readiness": availability["publication_readiness"],
        "has_cohort_independence": availability["cohort_independence"],
        "has_cohort_freeze": availability["cohort_freeze"],
        "has_comparative_evidence": availability["comparative_evidence"],
        "has_claim_strength": availability["claim_strength"],
        "has_external_robustness": availability["external_robustness"],
        "has_baseline_coverage": availability["baseline_coverage"],
        "has_methods_package": availability["methods_package"],
        "has_manuscript_package": availability["manuscript_package"],
        "has_validation_lock": availability["validation_lock"],
        "has_scientific_dossier": availability["scientific_dossier"],
        "publication_readiness_percent": (publication_readiness.get("summary") or {}).get("overall_readiness_percent"),
        "publication_ready_for_submission": (publication_readiness.get("summary") or {}).get("ready_for_submission"),
        "cohort_independence_percent": (cohort_independence.get("summary") or {}).get("overall_independence_percent"),
        "cohort_ready_for_external_validation": (cohort_independence.get("summary") or {}).get("ready_for_external_validation"),
        "real_data_readiness_percent": (cohort_freeze.get("summary") or {}).get("overall_real_data_readiness_percent"),
        "ready_for_real_data_study": (cohort_freeze.get("summary") or {}).get("ready_for_real_data_study"),
        "comparative_evidence_percent": (comparative_evidence.get("summary") or {}).get("overall_comparative_strength_percent"),
        "comparative_best_supported_experiment": (comparative_evidence.get("summary") or {}).get("best_supported_experiment"),
        "claim_strength_percent": (claim_strength.get("summary") or {}).get("overall_claim_strength_percent"),
        "claim_tier": (claim_strength.get("summary") or {}).get("claim_tier"),
        "external_robustness_percent": (external_robustness.get("summary") or {}).get("overall_external_robustness_percent"),
        "external_exact_sign_confidence_percent": (external_robustness.get("summary") or {}).get("exact_sign_confidence_percent"),
        "baseline_coverage_percent": (baseline_coverage.get("summary") or {}).get("overall_coverage_percent"),
        "baseline_best_prime_experiment": (baseline_coverage.get("summary") or {}).get("best_prime_experiment"),
        "methods_best_internal_experiment": (methods_package.get("summary") or {}).get("best_internal_experiment"),
        "manuscript_best_external_experiment": (manuscript_package.get("summary") or {}).get("best_external_experiment"),
        "validation_lock_percent": (validation_lock.get("summary") or {}).get("overall_validation_lock_percent"),
        "validation_ready_for_submission_lock": (validation_lock.get("summary") or {}).get("ready_for_submission_lock"),
    }

    return {
        "summary": summary,
        "availability": availability,
        "study_release_manifest": study_release,
        "publication_readiness_manifest": publication_readiness,
        "cohort_independence_manifest": cohort_independence,
        "study_cohort_freeze_manifest": cohort_freeze,
        "comparative_evidence_manifest": comparative_evidence,
        "claim_strength_manifest": claim_strength,
        "external_robustness_manifest": external_robustness,
        "baseline_coverage_manifest": baseline_coverage,
        "methods_package_manifest": methods_package,
        "manuscript_package_manifest": manuscript_package,
        "study_validation_lock_manifest": validation_lock,
        "scientific_dossier_manifest": scientific_dossier,
    }
