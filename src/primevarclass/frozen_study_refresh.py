from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from .claim_strength import export_claim_strength_package
from .comparative_evidence import export_comparative_evidence_package
from .external_robustness import export_external_robustness_package
from .prime_intelligence import export_prime_intelligence_package
from .publication_readiness import export_publication_readiness_package
from .study import load_study_design


def _load_optional_json(root: Path, filename: str) -> dict[str, Any]:
    path = root / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_required_csv(root: Path, filename: str) -> pd.DataFrame:
    path = root / filename
    if not path.exists():
        raise FileNotFoundError(f"Artefato congelado nao encontrado: {path}")
    return pd.read_csv(path)


def _load_optional_csv(root: Path, filename: str) -> pd.DataFrame:
    path = root / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "study"


def _infer_external_score_paths(root: Path, cohort_manifest: pd.DataFrame) -> dict[str, str]:
    if cohort_manifest.empty:
        return {}
    score_paths: dict[str, str] = {}
    for _, row in cohort_manifest.iterrows():
        cohort_name = str(row.get("cohort_name") or "")
        role = str(row.get("role") or "")
        if not cohort_name or role == "train":
            continue
        score_path = root / f"study_scores_{_slugify(cohort_name)}.csv"
        if score_path.exists():
            score_paths[cohort_name] = str(score_path)
    return score_paths


def _infer_existing_path(root: Path, filename: str) -> str | None:
    path = root / filename
    return str(path) if path.exists() else None


def _infer_gene_training_paths(root: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for path in root.glob("study_gene_training_metrics_*.csv"):
        token = path.stem.replace("study_gene_training_metrics_", "").lower()
        if token in {"combined", ""}:
            continue
        paths[token.upper()] = str(path)
    return paths


def _infer_cohort_results(root: Path, cohort_manifest: pd.DataFrame) -> dict[str, dict[str, str]]:
    if cohort_manifest.empty:
        return {}
    cohort_root = root / "cohorts"
    if not cohort_root.exists():
        return {}

    inferred: dict[str, dict[str, str]] = {}
    for _, row in cohort_manifest.iterrows():
        cohort_name = str(row.get("cohort_name") or "")
        if not cohort_name:
            continue
        slug = _slugify(cohort_name)
        payload: dict[str, str] = {}
        ingestion_output_dir = cohort_root / f"{slug}_ingestion"
        processed_dataset_path = cohort_root / f"{slug}_processed_dataset.csv"
        source_report_path = cohort_root / f"{slug}_source_report.csv"
        if ingestion_output_dir.exists():
            payload["ingestion_output_dir"] = str(ingestion_output_dir)
        if processed_dataset_path.exists():
            payload["processed_dataset_path"] = str(processed_dataset_path)
        if source_report_path.exists():
            payload["source_report_path"] = str(source_report_path)
        if payload:
            inferred[cohort_name] = payload
    return inferred


def refresh_frozen_study_assessment(
    study_output_dir: str,
    study_config_path: str,
    *,
    biological_discovery_manifest_path: str | None = None,
    gene_expansion_manifest_path: str | None = None,
) -> Dict[str, Any]:
    root = Path(study_output_dir).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Diretorio do estudo congelado nao encontrado: {root}")

    study_design = load_study_design(study_config_path)
    cohort_manifest = _load_optional_csv(root, "study_cohort_manifest.csv")
    cohort_independence_manifest = _load_optional_json(root, "cohort_independence_manifest.json")
    cohort_freeze_manifest = _load_optional_json(root, "study_cohort_freeze_manifest.json")
    results = {
        "study_design": study_design,
        "training_metrics": _load_required_csv(root, "study_training_metrics.csv"),
        "training_metrics_path": _infer_existing_path(root, "study_training_metrics.csv"),
        "training_repeated_holdout": _load_optional_csv(root, "study_repeated_holdout.csv"),
        "training_repeated_holdout_path": _infer_existing_path(root, "study_repeated_holdout.csv"),
        "external_pairwise_comparisons": _load_required_csv(root, "study_external_pairwise.csv"),
        "external_pairwise_path": _infer_existing_path(root, "study_external_pairwise.csv"),
        "external_evaluation_metrics": _load_required_csv(root, "study_external_evaluation.csv"),
        "external_evaluation_path": _infer_existing_path(root, "study_external_evaluation.csv"),
        "cohort_manifest": cohort_manifest,
        "cohort_manifest_path": _infer_existing_path(root, "study_cohort_manifest.csv"),
        "cohort_results": _infer_cohort_results(root, cohort_manifest),
        "external_score_paths": _infer_external_score_paths(root, cohort_manifest),
        "gene_training_paths": _infer_gene_training_paths(root),
        "study_summary_report_path": _infer_existing_path(root, "study_summary_report.txt"),
        "scientific_dossier_markdown_path": _infer_existing_path(root, "study_scientific_dossier.md"),
        "scientific_dossier_html_path": _infer_existing_path(root, "study_scientific_dossier.html"),
        "scientific_dossier_manifest_path": _infer_existing_path(root, "study_scientific_dossier_manifest.json"),
        "cohort_independence_assessment": {"summary": cohort_independence_manifest.get("summary") or {}},
        "cohort_independence_manifest_path": _infer_existing_path(root, "cohort_independence_manifest.json"),
        "study_cohort_freeze_summary": cohort_freeze_manifest.get("summary") or {},
        "study_cohort_freeze_manifest_path": _infer_existing_path(root, "study_cohort_freeze_manifest.json"),
        "study_cohort_freeze_markdown_path": _infer_existing_path(root, "study_cohort_freeze_report.md"),
        "model_paths": {
            "registry": _infer_existing_path(root / "models", "model_registry.csv"),
        },
    }

    comparative_paths = export_comparative_evidence_package(results, output_dir=str(root))
    claim_paths = export_claim_strength_package(results, output_dir=str(root))
    results.update(comparative_paths)
    results.update(claim_paths)
    external_robustness_paths = export_external_robustness_package(results, output_dir=str(root))
    results.update(external_robustness_paths)
    prime_intelligence_paths = export_prime_intelligence_package(
        results,
        output_dir=str(root),
        biological_discovery_manifest_path=biological_discovery_manifest_path,
        gene_expansion_manifest_path=gene_expansion_manifest_path,
    )
    results.update(prime_intelligence_paths)
    publication_paths = export_publication_readiness_package(results, output_dir=str(root))
    results.update(publication_paths)

    comparative_manifest_path = Path(comparative_paths["comparative_evidence_manifest_path"])
    claim_manifest_path = Path(claim_paths["claim_strength_manifest_path"])
    publication_manifest_path = Path(publication_paths["publication_readiness_manifest_path"])
    external_robustness_manifest_path = Path(external_robustness_paths["external_robustness_manifest_path"])
    prime_intelligence_manifest_path = Path(prime_intelligence_paths["prime_intelligence_manifest_path"])
    comparative_manifest = json.loads(comparative_manifest_path.read_text(encoding="utf-8"))
    claim_manifest = json.loads(claim_manifest_path.read_text(encoding="utf-8"))
    publication_manifest = json.loads(publication_manifest_path.read_text(encoding="utf-8"))
    external_robustness_manifest = json.loads(external_robustness_manifest_path.read_text(encoding="utf-8"))
    prime_intelligence_manifest = json.loads(prime_intelligence_manifest_path.read_text(encoding="utf-8"))

    return {
        "study_output_dir": str(root),
        "study_config_path": str(Path(study_config_path).resolve()),
        "comparative_evidence_manifest_path": str(comparative_manifest_path),
        "claim_strength_manifest_path": str(claim_manifest_path),
        "publication_readiness_manifest_path": str(publication_manifest_path),
        "external_robustness_manifest_path": str(external_robustness_manifest_path),
        "prime_intelligence_manifest_path": str(prime_intelligence_manifest_path),
        "comparative_evidence_report_markdown_path": comparative_paths["comparative_evidence_report_markdown_path"],
        "claim_strength_report_markdown_path": claim_paths["claim_strength_report_markdown_path"],
        "publication_readiness_report_markdown_path": publication_paths["publication_readiness_report_markdown_path"],
        "external_robustness_report_markdown_path": external_robustness_paths["external_robustness_report_markdown_path"],
        "prime_intelligence_report_markdown_path": prime_intelligence_paths["prime_intelligence_report_markdown_path"],
        "comparative_summary": comparative_manifest.get("summary") or {},
        "claim_summary": claim_manifest.get("summary") or {},
        "publication_summary": publication_manifest.get("summary") or {},
        "external_robustness_summary": external_robustness_manifest.get("summary") or {},
        "prime_intelligence_summary": prime_intelligence_manifest.get("summary") or {},
    }
