from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned or "release"


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _file_fingerprint(path: str | None) -> dict | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    payload = candidate.read_bytes()
    stat = candidate.stat()
    return {
        "path": str(candidate.resolve()),
        "size_bytes": int(stat.st_size),
        "sha256": _sha256_bytes(payload),
        "modified_at_epoch": float(stat.st_mtime),
    }


def _artifact_fingerprints(paths: dict[str, str | None]) -> dict[str, dict]:
    fingerprints: dict[str, dict] = {}
    for label, path in paths.items():
        fingerprint = _file_fingerprint(path)
        if fingerprint is not None:
            fingerprints[str(label)] = fingerprint
    return fingerprints


def _dataframe_fingerprint(df: pd.DataFrame) -> dict:
    serialized = df.to_csv(index=False).encode("utf-8")
    return {
        "n_rows": int(len(df)),
        "n_columns": int(len(df.columns)),
        "sha256_csv": _sha256_bytes(serialized),
    }


def _source_summary(catalog_sources: Iterable[Any], source_provenance: list[dict] | None = None) -> list[dict]:
    provenance_by_name = {
        str(item.get("source_name") or item.get("name")): item for item in (source_provenance or []) if isinstance(item, dict)
    }
    rows = []
    for spec in catalog_sources:
        row = {
            "name": getattr(spec, "name", None),
            "kind": getattr(spec, "kind", None),
            "source_type": getattr(spec, "source_type", None),
            "format": getattr(spec, "format", None),
            "preset": getattr(spec, "preset", None),
            "join_on": list(getattr(spec, "join_on", []) or []),
            "path": getattr(spec, "path", None),
            "url": getattr(spec, "url", None),
            "query": getattr(spec, "query", None),
            "table": getattr(spec, "table", None),
        }
        fingerprint = _file_fingerprint(getattr(spec, "path", None))
        if fingerprint is not None:
            row["file_fingerprint"] = fingerprint
        provenance = provenance_by_name.get(str(getattr(spec, "name", None)))
        if provenance is not None:
            row["provenance"] = _jsonify(provenance)
        rows.append(row)
    return rows


def load_release_manifest(manifest_path: str) -> dict:
    candidate = Path(manifest_path).expanduser().resolve()
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Manifest nao encontrado: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("O manifest informado nao contem um objeto JSON valido.")
    payload.setdefault("manifest_path", str(candidate))
    return payload


def export_data_release_manifest(
    *,
    config_path: str,
    catalog: Any,
    integrated_df: pd.DataFrame,
    source_report: pd.DataFrame,
    source_provenance: list[dict] | None = None,
    public_source_assessment: dict | None = None,
    public_source_sync_plan: dict | None = None,
    output_paths: Dict[str, str] | None = None,
    output_dir: str,
) -> dict:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    config_file = Path(config_path).resolve()
    generated_at = _now_utc()
    config_text = _safe_read_text(config_file)
    release_id = f"data_{_slugify(config_file.stem)}_{generated_at.replace(':', '').replace('-', '')}"
    manifest = {
        "release_id": release_id,
        "release_type": "data_ingestion",
        "generated_at": generated_at,
        "config_path": str(config_file),
        "config_sha256": _sha256_text(config_text) if config_text else None,
        "output_dir": str(output_root),
        "n_rows": int(len(integrated_df)),
        "n_columns": int(len(integrated_df.columns)),
        "columns": [str(column) for column in integrated_df.columns],
        "integrated_dataset_fingerprint": _dataframe_fingerprint(integrated_df),
        "sources": _source_summary(getattr(catalog, "sources", []), source_provenance=source_provenance),
        "source_report": source_report.to_dict(orient="records"),
        "public_source_assessment": _jsonify(public_source_assessment or {}),
        "public_source_sync_plan": _jsonify(public_source_sync_plan or {}),
        "artifact_fingerprints": _artifact_fingerprints(dict(output_paths or {})),
    }
    manifest_path = output_root / "data_release_manifest.json"
    registry_path = output_root / "data_release_registry.csv"
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "release_id": release_id,
                "release_type": "data_ingestion",
                "generated_at": generated_at,
                "config_path": str(config_file),
                "config_sha256": manifest["config_sha256"],
                "n_rows": int(len(integrated_df)),
                "n_columns": int(len(integrated_df.columns)),
                "n_sources": int(len(getattr(catalog, "sources", []))),
                "manifest_path": str(manifest_path),
            }
        ]
    ).to_csv(registry_path, index=False)
    return {
        "data_release_manifest_path": str(manifest_path),
        "data_release_registry_path": str(registry_path),
        "data_release_id": release_id,
    }


def _best_external_summary(external_metrics: pd.DataFrame, primary_metric: str) -> dict:
    if external_metrics.empty:
        return {
            "top_external_experiment": None,
            "mean_external_primary_metric": np.nan,
            "mean_external_auc_roc": np.nan,
            "mean_external_auc_pr": np.nan,
            "mean_external_mcc": np.nan,
        }
    subset = external_metrics.loc[external_metrics["evaluation_group"].astype(str) == "combined"].copy()
    if subset.empty:
        subset = external_metrics.copy()
    metric_name = primary_metric if primary_metric in subset.columns else "auc_roc"
    top_rows = subset.sort_values(
        ["cohort", metric_name, "auc_pr", "mcc", "experiment"],
        ascending=[True, False, False, False, True],
    ).groupby("cohort", as_index=False).head(1)
    overall = subset.sort_values([metric_name, "auc_pr", "mcc", "experiment"], ascending=[False, False, False, True]).iloc[0]
    return {
        "top_external_experiment": overall.get("experiment"),
        "mean_external_primary_metric": float(top_rows[metric_name].mean()) if metric_name in top_rows.columns else np.nan,
        "mean_external_auc_roc": float(top_rows["auc_roc"].mean()) if "auc_roc" in top_rows.columns else np.nan,
        "mean_external_auc_pr": float(top_rows["auc_pr"].mean()) if "auc_pr" in top_rows.columns else np.nan,
        "mean_external_mcc": float(top_rows["mcc"].mean()) if "mcc" in top_rows.columns else np.nan,
    }


def export_study_release_manifest(
    *,
    config_path: str,
    results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    config_file = Path(config_path).resolve()
    generated_at = _now_utc()
    config_text = _safe_read_text(config_file)
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", config_file.stem)
    primary_metric = getattr(study_design, "primary_metric", "auc_roc")
    training_metrics = results.get("training_metrics")
    external_metrics = results.get("external_evaluation_metrics")
    best_internal = {}
    if isinstance(training_metrics, pd.DataFrame) and not training_metrics.empty:
        metric_name = primary_metric if primary_metric in training_metrics.columns else "auc_roc"
        best_row = training_metrics.sort_values(
            [metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).iloc[0]
        best_internal = {
            "top_internal_experiment": best_row.get("experiment"),
            "top_internal_feature_set": best_row.get("feature_set"),
            "top_internal_model_family": best_row.get("model_family"),
            "internal_primary_metric": float(best_row.get(metric_name)),
            "internal_auc_roc": float(best_row.get("auc_roc")),
            "internal_auc_pr": float(best_row.get("auc_pr")),
            "internal_mcc": float(best_row.get("mcc")),
        }
    else:
        best_internal = {
            "top_internal_experiment": None,
            "top_internal_feature_set": None,
            "top_internal_model_family": None,
            "internal_primary_metric": np.nan,
            "internal_auc_roc": np.nan,
            "internal_auc_pr": np.nan,
            "internal_mcc": np.nan,
        }
    external_summary = _best_external_summary(external_metrics if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame(), primary_metric)
    release_id = f"study_{_slugify(study_name)}_{generated_at.replace(':', '').replace('-', '')}"
    manifest = {
        "release_id": release_id,
        "release_type": "study_benchmark",
        "generated_at": generated_at,
        "study_name": study_name,
        "primary_metric": primary_metric,
        "config_path": str(config_file),
        "config_sha256": _sha256_text(config_text) if config_text else None,
        "output_dir": str(output_root),
        "report_context": dict(report_context or {}),
        "cohort_manifest_path": results.get("cohort_manifest_path"),
        "cohort_independence_report_markdown_path": results.get("cohort_independence_report_markdown_path"),
        "cohort_independence_report_html_path": results.get("cohort_independence_report_html_path"),
        "cohort_independence_manifest_path": results.get("cohort_independence_manifest_path"),
        "cohort_independence_cohorts_path": results.get("cohort_independence_cohorts_path"),
        "cohort_independence_pairs_path": results.get("cohort_independence_pairs_path"),
        "study_cohort_freeze_markdown_path": results.get("study_cohort_freeze_markdown_path"),
        "study_cohort_freeze_html_path": results.get("study_cohort_freeze_html_path"),
        "study_cohort_freeze_manifest_path": results.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_cohorts_path": results.get("study_cohort_freeze_cohorts_path"),
        "study_cohort_freeze_sources_path": results.get("study_cohort_freeze_sources_path"),
        "training_metrics_path": results.get("training_metrics_path"),
        "study_summary_report_path": results.get("study_summary_report_path"),
        "scientific_dossier_markdown_path": results.get("scientific_dossier_markdown_path"),
        "scientific_dossier_html_path": results.get("scientific_dossier_html_path"),
        "scientific_dossier_manifest_path": results.get("scientific_dossier_manifest_path"),
        "claim_strength_report_markdown_path": results.get("claim_strength_report_markdown_path"),
        "claim_strength_report_html_path": results.get("claim_strength_report_html_path"),
        "claim_strength_manifest_path": results.get("claim_strength_manifest_path"),
        "claim_strength_criteria_path": results.get("claim_strength_criteria_path"),
        "claim_strength_candidates_path": results.get("claim_strength_candidates_path"),
        "claim_strength_metric_cohort_path": results.get("claim_strength_metric_cohort_path"),
        "claim_strength_head_to_head_path": results.get("claim_strength_head_to_head_path"),
        "publication_readiness_report_markdown_path": results.get("publication_readiness_report_markdown_path"),
        "publication_readiness_report_html_path": results.get("publication_readiness_report_html_path"),
        "publication_readiness_manifest_path": results.get("publication_readiness_manifest_path"),
        "publication_readiness_criteria_path": results.get("publication_readiness_criteria_path"),
        "publication_readiness_cohorts_path": results.get("publication_readiness_cohorts_path"),
        "publication_readiness_sources_path": results.get("publication_readiness_sources_path"),
        "publication_readiness_external_evidence_path": results.get("publication_readiness_external_evidence_path"),
        "publication_readiness_artifacts_path": results.get("publication_readiness_artifacts_path"),
        "comparative_evidence_report_markdown_path": results.get("comparative_evidence_report_markdown_path"),
        "comparative_evidence_report_html_path": results.get("comparative_evidence_report_html_path"),
        "comparative_evidence_manifest_path": results.get("comparative_evidence_manifest_path"),
        "comparative_evidence_criteria_path": results.get("comparative_evidence_criteria_path"),
        "comparative_evidence_cohorts_path": results.get("comparative_evidence_cohorts_path"),
        "comparative_evidence_experiments_path": results.get("comparative_evidence_experiments_path"),
        "comparative_evidence_feature_sets_path": results.get("comparative_evidence_feature_sets_path"),
        "comparative_evidence_pairwise_auc_roc_path": results.get("comparative_evidence_pairwise_auc_roc_path"),
        "external_robustness_report_markdown_path": results.get("external_robustness_report_markdown_path"),
        "external_robustness_report_html_path": results.get("external_robustness_report_html_path"),
        "external_robustness_manifest_path": results.get("external_robustness_manifest_path"),
        "external_robustness_criteria_path": results.get("external_robustness_criteria_path"),
        "external_robustness_calibration_path": results.get("external_robustness_calibration_path"),
        "external_robustness_discrimination_path": results.get("external_robustness_discrimination_path"),
        "prime_intelligence_report_markdown_path": results.get("prime_intelligence_report_markdown_path"),
        "prime_intelligence_report_html_path": results.get("prime_intelligence_report_html_path"),
        "prime_intelligence_manifest_path": results.get("prime_intelligence_manifest_path"),
        "prime_intelligence_criteria_path": results.get("prime_intelligence_criteria_path"),
        "prime_intelligence_internal_leaderboard_path": results.get("prime_intelligence_internal_leaderboard_path"),
        "prime_intelligence_external_leadership_path": results.get("prime_intelligence_external_leadership_path"),
        "prime_intelligence_pairwise_support_path": results.get("prime_intelligence_pairwise_support_path"),
        "prime_intelligence_feature_attribution_path": results.get("prime_intelligence_feature_attribution_path"),
        "prime_intelligence_biological_alignment_path": results.get("prime_intelligence_biological_alignment_path"),
        "prime_intelligence_expansion_runway_path": results.get("prime_intelligence_expansion_runway_path"),
        "baseline_coverage_report_markdown_path": results.get("baseline_coverage_report_markdown_path"),
        "baseline_coverage_report_html_path": results.get("baseline_coverage_report_html_path"),
        "baseline_coverage_manifest_path": results.get("baseline_coverage_manifest_path"),
        "baseline_coverage_criteria_path": results.get("baseline_coverage_criteria_path"),
        "baseline_coverage_feature_sets_path": results.get("baseline_coverage_feature_sets_path"),
        "baseline_coverage_prime_vs_baseline_path": results.get("baseline_coverage_prime_vs_baseline_path"),
        "methods_package_markdown_path": results.get("methods_package_markdown_path"),
        "methods_package_html_path": results.get("methods_package_html_path"),
        "methods_package_manifest_path": results.get("methods_package_manifest_path"),
        "methods_package_cohorts_path": results.get("methods_package_cohorts_path"),
        "methods_package_sources_path": results.get("methods_package_sources_path"),
        "methods_package_checklist_path": results.get("methods_package_checklist_path"),
        "manuscript_package_markdown_path": results.get("manuscript_package_markdown_path"),
        "manuscript_package_html_path": results.get("manuscript_package_html_path"),
        "manuscript_package_manifest_path": results.get("manuscript_package_manifest_path"),
        "manuscript_table_cohorts_path": results.get("manuscript_table_cohorts_path"),
        "manuscript_table_internal_path": results.get("manuscript_table_internal_path"),
        "manuscript_table_external_path": results.get("manuscript_table_external_path"),
        "manuscript_table_pairwise_path": results.get("manuscript_table_pairwise_path"),
        "manuscript_figure_internal_path": results.get("manuscript_figure_internal_path"),
        "manuscript_figure_external_path": results.get("manuscript_figure_external_path"),
        "study_validation_lock_markdown_path": results.get("study_validation_lock_markdown_path"),
        "study_validation_lock_html_path": results.get("study_validation_lock_html_path"),
        "study_validation_lock_manifest_path": results.get("study_validation_lock_manifest_path"),
        "study_validation_lock_criteria_path": results.get("study_validation_lock_criteria_path"),
        "external_evaluation_path": results.get("external_evaluation_path"),
        "external_pairwise_path": results.get("external_pairwise_path"),
        "consensus_members_path": results.get("consensus_members_path"),
        "model_registry_path": (results.get("model_paths") or {}).get("registry"),
        "claim_strength_percent": ((results.get("claim_strength_assessment") or {}).get("summary") or {}).get("overall_claim_strength_percent"),
        "claim_tier": ((results.get("claim_strength_assessment") or {}).get("summary") or {}).get("claim_tier"),
        "publication_readiness_percent": ((results.get("publication_readiness_assessment") or {}).get("summary") or {}).get("overall_readiness_percent"),
        "publication_ready_for_submission": ((results.get("publication_readiness_assessment") or {}).get("summary") or {}).get("ready_for_submission"),
        "cohort_independence_percent": ((results.get("cohort_independence_assessment") or {}).get("summary") or {}).get("overall_independence_percent"),
        "cohort_ready_for_external_validation": ((results.get("cohort_independence_assessment") or {}).get("summary") or {}).get("ready_for_external_validation"),
        "real_data_readiness_percent": (results.get("study_cohort_freeze_summary") or {}).get("overall_real_data_readiness_percent"),
        "ready_for_real_data_study": (results.get("study_cohort_freeze_summary") or {}).get("ready_for_real_data_study"),
        "comparative_evidence_percent": ((results.get("comparative_evidence_assessment") or {}).get("summary") or {}).get("overall_comparative_strength_percent"),
        "comparative_best_supported_experiment": ((results.get("comparative_evidence_assessment") or {}).get("summary") or {}).get("best_supported_experiment"),
        "external_robustness_percent": ((results.get("external_robustness_assessment") or {}).get("summary") or {}).get("overall_external_robustness_percent"),
        "external_robustness_exact_sign_confidence_percent": ((results.get("external_robustness_assessment") or {}).get("summary") or {}).get("exact_sign_confidence_percent"),
        "prime_intelligence_percent": ((results.get("prime_intelligence_assessment") or {}).get("summary") or {}).get("overall_prime_intelligence_percent"),
        "prime_intelligence_tier": ((results.get("prime_intelligence_assessment") or {}).get("summary") or {}).get("prime_intelligence_tier"),
        "prime_best_internal_experiment": ((results.get("prime_intelligence_assessment") or {}).get("summary") or {}).get("best_prime_internal_experiment"),
        "prime_best_external_experiment": ((results.get("prime_intelligence_assessment") or {}).get("summary") or {}).get("best_prime_external_experiment"),
        "baseline_coverage_percent": ((results.get("baseline_coverage_assessment") or {}).get("summary") or {}).get("overall_coverage_percent"),
        "baseline_best_prime_experiment": ((results.get("baseline_coverage_assessment") or {}).get("summary") or {}).get("best_prime_experiment"),
        "methods_best_internal_experiment": ((results.get("methods_package_summary") or {}).get("best_internal_experiment")),
        "manuscript_best_internal_experiment": ((results.get("manuscript_package_summary") or {}).get("best_internal_experiment")),
        "manuscript_best_external_experiment": ((results.get("manuscript_package_summary") or {}).get("best_external_experiment")),
        "validation_lock_percent": ((results.get("study_validation_lock") or {}).get("summary") or {}).get("overall_validation_lock_percent"),
        "validation_ready_for_statistical_validation": ((results.get("study_validation_lock") or {}).get("summary") or {}).get("ready_for_statistical_validation"),
        "validation_ready_for_submission_lock": ((results.get("study_validation_lock") or {}).get("summary") or {}).get("ready_for_submission_lock"),
        "validation_ready_for_translational_pilot": ((results.get("study_validation_lock") or {}).get("summary") or {}).get("ready_for_translational_pilot"),
        "artifact_fingerprints": _artifact_fingerprints(
            {
                "cohort_manifest": results.get("cohort_manifest_path"),
                "cohort_independence_markdown": results.get("cohort_independence_report_markdown_path"),
                "cohort_independence_html": results.get("cohort_independence_report_html_path"),
                "cohort_independence_manifest": results.get("cohort_independence_manifest_path"),
                "cohort_independence_cohorts": results.get("cohort_independence_cohorts_path"),
                "cohort_independence_pairs": results.get("cohort_independence_pairs_path"),
                "study_cohort_freeze_markdown": results.get("study_cohort_freeze_markdown_path"),
                "study_cohort_freeze_html": results.get("study_cohort_freeze_html_path"),
                "study_cohort_freeze_manifest": results.get("study_cohort_freeze_manifest_path"),
                "study_cohort_freeze_cohorts": results.get("study_cohort_freeze_cohorts_path"),
                "study_cohort_freeze_sources": results.get("study_cohort_freeze_sources_path"),
                "training_metrics": results.get("training_metrics_path"),
                "study_summary_report": results.get("study_summary_report_path"),
                "scientific_dossier_markdown": results.get("scientific_dossier_markdown_path"),
                "scientific_dossier_html": results.get("scientific_dossier_html_path"),
                "scientific_dossier_manifest": results.get("scientific_dossier_manifest_path"),
                "claim_strength_markdown": results.get("claim_strength_report_markdown_path"),
                "claim_strength_html": results.get("claim_strength_report_html_path"),
                "claim_strength_manifest": results.get("claim_strength_manifest_path"),
                "claim_strength_criteria": results.get("claim_strength_criteria_path"),
                "claim_strength_candidates": results.get("claim_strength_candidates_path"),
                "claim_strength_metric_cohort": results.get("claim_strength_metric_cohort_path"),
                "claim_strength_head_to_head": results.get("claim_strength_head_to_head_path"),
                "publication_readiness_markdown": results.get("publication_readiness_report_markdown_path"),
                "publication_readiness_html": results.get("publication_readiness_report_html_path"),
                "publication_readiness_manifest": results.get("publication_readiness_manifest_path"),
                "publication_readiness_criteria": results.get("publication_readiness_criteria_path"),
                "publication_readiness_cohorts": results.get("publication_readiness_cohorts_path"),
                "publication_readiness_sources": results.get("publication_readiness_sources_path"),
                "publication_readiness_external_evidence": results.get("publication_readiness_external_evidence_path"),
                "publication_readiness_artifacts": results.get("publication_readiness_artifacts_path"),
                "comparative_evidence_markdown": results.get("comparative_evidence_report_markdown_path"),
                "comparative_evidence_html": results.get("comparative_evidence_report_html_path"),
                "comparative_evidence_manifest": results.get("comparative_evidence_manifest_path"),
                "comparative_evidence_criteria": results.get("comparative_evidence_criteria_path"),
                "comparative_evidence_cohorts": results.get("comparative_evidence_cohorts_path"),
                "comparative_evidence_experiments": results.get("comparative_evidence_experiments_path"),
                "comparative_evidence_feature_sets": results.get("comparative_evidence_feature_sets_path"),
                "comparative_evidence_pairwise_auc_roc": results.get("comparative_evidence_pairwise_auc_roc_path"),
                "external_robustness_markdown": results.get("external_robustness_report_markdown_path"),
                "external_robustness_html": results.get("external_robustness_report_html_path"),
                "external_robustness_manifest": results.get("external_robustness_manifest_path"),
                "external_robustness_criteria": results.get("external_robustness_criteria_path"),
                "external_robustness_calibration": results.get("external_robustness_calibration_path"),
                "external_robustness_discrimination": results.get("external_robustness_discrimination_path"),
                "prime_intelligence_markdown": results.get("prime_intelligence_report_markdown_path"),
                "prime_intelligence_html": results.get("prime_intelligence_report_html_path"),
                "prime_intelligence_manifest": results.get("prime_intelligence_manifest_path"),
                "prime_intelligence_criteria": results.get("prime_intelligence_criteria_path"),
                "prime_intelligence_internal": results.get("prime_intelligence_internal_leaderboard_path"),
                "prime_intelligence_external": results.get("prime_intelligence_external_leadership_path"),
                "prime_intelligence_pairwise": results.get("prime_intelligence_pairwise_support_path"),
                "prime_intelligence_attribution": results.get("prime_intelligence_feature_attribution_path"),
                "prime_intelligence_biological": results.get("prime_intelligence_biological_alignment_path"),
                "prime_intelligence_expansion": results.get("prime_intelligence_expansion_runway_path"),
                "baseline_coverage_markdown": results.get("baseline_coverage_report_markdown_path"),
                "baseline_coverage_html": results.get("baseline_coverage_report_html_path"),
                "baseline_coverage_manifest": results.get("baseline_coverage_manifest_path"),
                "baseline_coverage_criteria": results.get("baseline_coverage_criteria_path"),
                "baseline_coverage_feature_sets": results.get("baseline_coverage_feature_sets_path"),
                "baseline_coverage_prime_vs_baseline": results.get("baseline_coverage_prime_vs_baseline_path"),
                "methods_package_markdown": results.get("methods_package_markdown_path"),
                "methods_package_html": results.get("methods_package_html_path"),
                "methods_package_manifest": results.get("methods_package_manifest_path"),
                "methods_package_cohorts": results.get("methods_package_cohorts_path"),
                "methods_package_sources": results.get("methods_package_sources_path"),
                "methods_package_checklist": results.get("methods_package_checklist_path"),
                "manuscript_package_markdown": results.get("manuscript_package_markdown_path"),
                "manuscript_package_html": results.get("manuscript_package_html_path"),
                "manuscript_package_manifest": results.get("manuscript_package_manifest_path"),
                "manuscript_table_cohorts": results.get("manuscript_table_cohorts_path"),
                "manuscript_table_internal": results.get("manuscript_table_internal_path"),
                "manuscript_table_external": results.get("manuscript_table_external_path"),
                "manuscript_table_pairwise": results.get("manuscript_table_pairwise_path"),
                "manuscript_figure_internal": results.get("manuscript_figure_internal_path"),
                "manuscript_figure_external": results.get("manuscript_figure_external_path"),
                "study_validation_lock_markdown": results.get("study_validation_lock_markdown_path"),
                "study_validation_lock_html": results.get("study_validation_lock_html_path"),
                "study_validation_lock_manifest": results.get("study_validation_lock_manifest_path"),
                "study_validation_lock_criteria": results.get("study_validation_lock_criteria_path"),
                "external_evaluation": results.get("external_evaluation_path"),
                "external_pairwise": results.get("external_pairwise_path"),
                "consensus_members": results.get("consensus_members_path"),
                "model_registry": (results.get("model_paths") or {}).get("registry"),
            }
        ),
        **best_internal,
        **external_summary,
    }
    manifest_path = output_root / "study_release_manifest.json"
    registry_path = output_root / "study_release_registry.csv"
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([_jsonify(manifest)]).to_csv(registry_path, index=False)
    return {
        "study_release_manifest_path": str(manifest_path),
        "study_release_registry_path": str(registry_path),
        "study_release_id": release_id,
    }
