from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .public_bootstrap import build_public_benchmark_readiness, load_public_source_sync_history
from .versioning import load_release_manifest


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except Exception:
        return float("nan")
    if np.isnan(numeric):
        return float("nan")
    return numeric


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _fmt_percent(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.0f}%"


def _fmt_metric(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.4f}"


def _readiness_status(percent: int) -> str:
    if percent >= 85:
        return "ready"
    if percent >= 60:
        return "partial"
    return "gap"


def _evidence_label(delta_mean: float, ci_lower: float) -> str:
    if not np.isnan(ci_lower) and ci_lower > 0:
        return "supported_gain"
    if not np.isnan(delta_mean) and delta_mean > 0:
        return "suggestive_gain"
    if not np.isnan(delta_mean):
        return "no_gain"
    return "not_available"


def _artifact_exists(path: Any) -> bool:
    if not path:
        return False
    try:
        return Path(str(path)).exists()
    except Exception:
        return False


def _load_cohort_release_manifest(ingestion_output_dir: str | None) -> dict:
    if not ingestion_output_dir:
        return {}
    manifest_path = Path(ingestion_output_dir) / "data_release_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return load_release_manifest(str(manifest_path))
    except Exception:
        return {}


def _build_cohort_tables(results: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    cohort_manifest = results.get("cohort_manifest")
    cohort_results = dict(results.get("cohort_results") or {})
    if not isinstance(cohort_manifest, pd.DataFrame) or cohort_manifest.empty:
        return pd.DataFrame(), pd.DataFrame()

    cohort_rows: List[dict] = []
    source_rows: List[dict] = []

    for _, row in cohort_manifest.iterrows():
        cohort_name = str(row.get("cohort_name"))
        role = str(row.get("role"))
        cohort_payload = dict(cohort_results.get(cohort_name) or {})
        ingestion_output_dir = cohort_payload.get("ingestion_output_dir")
        release_manifest = _load_cohort_release_manifest(ingestion_output_dir)
        public_source_assessment = dict(release_manifest.get("public_source_assessment") or {})
        public_source_summary = dict(public_source_assessment.get("summary") or {})
        public_source_sync_plan = dict(release_manifest.get("public_source_sync_plan") or {})
        public_source_sync_summary = dict(public_source_sync_plan.get("summary") or {})
        sync_history = load_public_source_sync_history(
            output_dir=ingestion_output_dir or "",
            public_source_assessment=public_source_assessment,
            public_source_sync_plan=public_source_sync_plan,
        ) if ingestion_output_dir else {}
        benchmark_readiness = build_public_benchmark_readiness(
            public_source_assessment=public_source_assessment,
            public_source_sync_plan=public_source_sync_plan,
            sync_history=sync_history,
            bootstrap_bundle={},
        ) if public_source_assessment else {}
        benchmark_summary = dict(benchmark_readiness.get("summary") or {})

        data_release_manifest_path = release_manifest.get("manifest_path") or (
            str((Path(ingestion_output_dir) / "data_release_manifest.json").resolve())
            if ingestion_output_dir and (Path(ingestion_output_dir) / "data_release_manifest.json").exists()
            else None
        )
        integrated_fingerprint = dict(release_manifest.get("integrated_dataset_fingerprint") or {})

        cohort_rows.append(
            {
                "cohort_name": cohort_name,
                "role": role,
                "source_config": row.get("source_config"),
                "valid_rows": _safe_int(row.get("valid_rows")),
                "n_classes": _safe_int(row.get("n_classes")),
                "n_source_tables": _safe_int(row.get("n_source_tables")),
                "processed_dataset_path": cohort_payload.get("processed_dataset_path"),
                "source_report_path": cohort_payload.get("source_report_path"),
                "ingestion_output_dir": ingestion_output_dir,
                "data_release_manifest_path": data_release_manifest_path,
                "has_data_release_manifest": bool(data_release_manifest_path and _artifact_exists(data_release_manifest_path)),
                "has_integrated_dataset_fingerprint": bool(integrated_fingerprint.get("sha256_csv")),
                "recognized_public_sources": _safe_int(public_source_summary.get("n_recognized_public_sources")),
                "release_coverage_percent": _safe_int(public_source_summary.get("release_coverage_percent")),
                "schema_coverage_percent": _safe_int(public_source_summary.get("schema_coverage_percent")),
                "public_catalog_readiness_percent": _safe_int(public_source_summary.get("overall_readiness_percent")),
                "public_ready_for_benchmark": bool(public_source_summary.get("ready_for_public_benchmark")),
                "sync_candidates": _safe_int(public_source_sync_summary.get("n_sync_candidates")),
                "automatable_sources": _safe_int(public_source_sync_summary.get("n_automatable_sources")),
                "sync_readiness_percent": _safe_int((sync_history.get("summary") or {}).get("sync_readiness_percent")),
                "benchmark_readiness_percent": _safe_int(benchmark_summary.get("benchmark_readiness_percent")),
            }
        )

        for source in public_source_assessment.get("sources") or []:
            source_rows.append(
                {
                    "cohort_name": cohort_name,
                    "role": role,
                    "source_name": source.get("source_name"),
                    "display_name": source.get("display_name"),
                    "recognized_public_source": bool(source.get("recognized_public_source")),
                    "release_value": source.get("release_value"),
                    "release_coverage_percent": _safe_int(source.get("coverage_percent")),
                    "schema_coverage_percent": _safe_int(source.get("schema_coverage_percent")),
                    "catalog_readiness_percent": _safe_int(source.get("readiness_percent")),
                    "ready_for_public_use": bool(source.get("ready_for_public_use")),
                    "citation_url": source.get("citation_url"),
                }
            )

    return pd.DataFrame(cohort_rows), pd.DataFrame(source_rows)


def _build_external_evidence_table(results: dict) -> pd.DataFrame:
    external_metrics = results.get("external_evaluation_metrics")
    pairwise = results.get("external_pairwise_comparisons")
    cohort_manifest = results.get("cohort_manifest")
    if not isinstance(cohort_manifest, pd.DataFrame) or cohort_manifest.empty:
        return pd.DataFrame()

    metrics_df = external_metrics if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()
    pairwise_df = pairwise if isinstance(pairwise, pd.DataFrame) else pd.DataFrame()

    rows: List[dict] = []
    for _, cohort_row in cohort_manifest.iterrows():
        cohort_name = str(cohort_row.get("cohort_name"))
        role = str(cohort_row.get("role"))
        if role == "train":
            continue

        combined_metrics = pd.DataFrame()
        if not metrics_df.empty:
            combined_metrics = metrics_df[
                (metrics_df["cohort"].astype(str) == cohort_name)
                & (metrics_df["evaluation_group"].astype(str) == "combined")
            ].copy()
        pairwise_auc = pd.DataFrame()
        if not pairwise_df.empty:
            pairwise_auc = pairwise_df[
                (pairwise_df["cohort"].astype(str) == cohort_name)
                & (pairwise_df["metric"].astype(str) == "auc_roc")
            ].copy()

        best_external = combined_metrics.sort_values(
            ["auc_roc", "auc_pr", "mcc", "experiment"],
            ascending=[False, False, False, True],
        ).head(1)
        best_pairwise = pairwise_auc.sort_values(
            ["delta_mean", "ci_lower_95", "experiment"],
            ascending=[False, False, True],
        ).head(1)

        best_external_row = best_external.iloc[0].to_dict() if not best_external.empty else {}
        best_pairwise_row = best_pairwise.iloc[0].to_dict() if not best_pairwise.empty else {}
        delta_mean = _safe_float(best_pairwise_row.get("delta_mean"))
        ci_lower = _safe_float(best_pairwise_row.get("ci_lower_95"))
        ci_upper = _safe_float(best_pairwise_row.get("ci_upper_95"))

        rows.append(
            {
                "cohort": cohort_name,
                "cohort_role": role,
                "best_external_experiment": best_external_row.get("experiment"),
                "best_external_auc_roc": _safe_float(best_external_row.get("auc_roc")),
                "best_external_auc_pr": _safe_float(best_external_row.get("auc_pr")),
                "best_external_mcc": _safe_float(best_external_row.get("mcc")),
                "pairwise_experiment": best_pairwise_row.get("experiment"),
                "pairwise_baseline_experiment": best_pairwise_row.get("baseline_experiment"),
                "pairwise_delta_auc_roc": delta_mean,
                "pairwise_ci_lower_95": ci_lower,
                "pairwise_ci_upper_95": ci_upper,
                "pairwise_evidence": _evidence_label(delta_mean, ci_lower),
                "has_combined_external_metrics": not best_external.empty,
                "has_pairwise_auc_roc": not best_pairwise.empty,
            }
        )

    return pd.DataFrame(rows)


def _build_artifact_table(results: dict) -> pd.DataFrame:
    artifact_specs = [
        ("training_metrics_path", "Training metrics"),
        ("training_repeated_holdout_path", "Repeated holdout"),
        ("feature_set_leaderboard_path", "Feature-set leaderboard"),
        ("model_family_summary_path", "Model family summary"),
        ("consensus_members_path", "Consensus members"),
        ("cohort_manifest_path", "Cohort manifest"),
        ("study_summary_report_path", "Study summary report"),
        ("scientific_dossier_markdown_path", "Scientific dossier (Markdown)"),
        ("scientific_dossier_html_path", "Scientific dossier (HTML)"),
        ("scientific_dossier_manifest_path", "Scientific dossier manifest"),
        ("external_evaluation_path", "External evaluation"),
        ("external_pairwise_path", "External pairwise"),
        ("external_consensus_path", "External consensus"),
        ("external_robustness_report_markdown_path", "External robustness (Markdown)"),
        ("external_robustness_report_html_path", "External robustness (HTML)"),
        ("external_robustness_manifest_path", "External robustness manifest"),
        ("prime_intelligence_report_markdown_path", "Prime intelligence (Markdown)"),
        ("prime_intelligence_report_html_path", "Prime intelligence (HTML)"),
        ("prime_intelligence_manifest_path", "Prime intelligence manifest"),
        ("claim_strength_report_markdown_path", "Claim strength (Markdown)"),
        ("claim_strength_report_html_path", "Claim strength (HTML)"),
        ("claim_strength_manifest_path", "Claim strength manifest"),
        ("model_registry_path", "Model registry"),
    ]

    model_registry_path = (results.get("model_paths") or {}).get("registry")
    rows = []
    for key, label in artifact_specs:
        path = model_registry_path if key == "model_registry_path" else results.get(key)
        rows.append(
            {
                "artifact_key": key,
                "artifact_label": label,
                "path": path,
                "exists": _artifact_exists(path),
            }
        )
    return pd.DataFrame(rows)


def _criterion_row(
    criterion_id: str,
    title: str,
    weight: float,
    score_percent: int,
    evidence: str,
    next_step: str,
    critical: bool = False,
) -> dict:
    normalized = max(0, min(100, int(score_percent)))
    return {
        "criterion_id": criterion_id,
        "title": title,
        "weight": float(weight),
        "score_percent": normalized,
        "status": _readiness_status(normalized),
        "passed": bool(normalized >= 85),
        "critical": bool(critical),
        "evidence": evidence,
        "next_step": next_step,
    }


def build_publication_readiness_assessment(
    results: dict,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Publication Readiness")
    title = str(context.get("report_title") or f"{study_name} - Publication Readiness")

    cohort_table, source_table = _build_cohort_tables(results)
    external_table = _build_external_evidence_table(results)
    artifact_table = _build_artifact_table(results)

    n_cohorts = int(len(cohort_table))
    n_external_cohorts = int(len(cohort_table[cohort_table["role"].astype(str) != "train"])) if not cohort_table.empty else 0
    train_count = int((cohort_table["role"].astype(str) == "train").sum()) if not cohort_table.empty else 0

    cohort_label_ready = int(round(cohort_table["n_classes"].ge(2).mean() * 100)) if not cohort_table.empty else 0
    cohort_design_score = int(round(np.mean([
        100 if train_count == 1 else 0,
        100 if n_external_cohorts >= 1 else 0,
        cohort_label_ready,
    ])))

    manifest_coverage = int(round(cohort_table["has_data_release_manifest"].mean() * 100)) if not cohort_table.empty else 0
    fingerprint_coverage = int(round(cohort_table["has_integrated_dataset_fingerprint"].mean() * 100)) if not cohort_table.empty else 0
    data_versioning_score = int(round(np.mean([manifest_coverage, fingerprint_coverage])))

    public_traceability_inputs = []
    if not cohort_table.empty:
        public_traceability_inputs.extend([
            float(cohort_table["release_coverage_percent"].mean()),
            float(cohort_table["schema_coverage_percent"].mean()),
            float(cohort_table["public_catalog_readiness_percent"].mean()),
        ])
    public_source_traceability_score = int(round(np.mean(public_traceability_inputs))) if public_traceability_inputs else 0
    cohort_independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    cohort_independence_score = _safe_int(cohort_independence_summary.get("overall_independence_percent"))
    cohort_freeze_summary = dict(results.get("study_cohort_freeze_summary") or {})
    cohort_freeze_score = _safe_int(cohort_freeze_summary.get("overall_real_data_readiness_percent"))

    repeated_holdout = results.get("training_repeated_holdout")
    repeated_holdout_ready = 100 if isinstance(repeated_holdout, pd.DataFrame) and not repeated_holdout.empty else 0
    gene_training_paths = dict(results.get("gene_training_paths") or {})
    gene_training_ready = 100 if gene_training_paths else 0
    model_registry_ready = 100 if _artifact_exists((results.get("model_paths") or {}).get("registry")) else 0
    training_metrics_ready = 100 if _artifact_exists(results.get("training_metrics_path")) else 0
    internal_validation_score = int(round(np.mean([
        training_metrics_ready,
        repeated_holdout_ready,
        gene_training_ready,
        model_registry_ready,
    ])))

    combined_external_coverage = int(round(external_table["has_combined_external_metrics"].mean() * 100)) if not external_table.empty else 0
    pairwise_availability = int(round(external_table["has_pairwise_auc_roc"].mean() * 100)) if not external_table.empty else 0
    external_validation_score = int(round(np.mean([
        100 if n_external_cohorts >= 1 else 0,
        combined_external_coverage,
        pairwise_availability,
    ])))

    comparative_assessment = dict(results.get("comparative_evidence_assessment") or {})
    comparative_summary = dict(comparative_assessment.get("summary") or {})
    claim_assessment = dict(results.get("claim_strength_assessment") or {})
    claim_summary = dict(claim_assessment.get("summary") or {})
    external_robustness_assessment = dict(results.get("external_robustness_assessment") or {})
    external_robustness_summary = dict(external_robustness_assessment.get("summary") or {})
    if comparative_summary:
        suggestive_gain = _safe_int(comparative_summary.get("positive_gain_rate_percent"))
        supported_gain = _safe_int(comparative_summary.get("supported_gain_rate_percent"))
        comparative_evidence_strength_score = _safe_int(comparative_summary.get("overall_comparative_strength_percent"))
        comparative_evidence_text = (
            f"{supported_gain}% das coortes com ganho suportado, "
            f"{suggestive_gain}% com ganho positivo e melhor experimento "
            f"{comparative_summary.get('best_supported_experiment') or '-'}."
        )
    else:
        suggestive_gain = int(round(external_table["pairwise_delta_auc_roc"].gt(0).mean() * 100)) if not external_table.empty else 0
        supported_gain = int(round(external_table["pairwise_ci_lower_95"].gt(0).mean() * 100)) if not external_table.empty else 0
        comparative_evidence_strength_score = int(round(np.mean([
            pairwise_availability,
            suggestive_gain,
            supported_gain,
        ]))) if n_external_cohorts else 0
        comparative_evidence_text = (
            f"{suggestive_gain}% das coortes com delta medio positivo e "
            f"{supported_gain}% com suporte bootstrap estrito (IC inferior > 0)."
        )

    claim_strength_score = _safe_int(claim_summary.get("overall_claim_strength_percent"))
    claim_tier = str(claim_summary.get("claim_tier") or "insufficient")
    claim_strength_text = (
        f"Claim tier {claim_tier} em {claim_strength_score}% para "
        f"{claim_summary.get('selected_experiment') or '-'} vs "
        f"{claim_summary.get('selected_baseline_experiment') or '-'}."
    )
    external_robustness_score = _safe_int(external_robustness_summary.get("overall_external_robustness_percent"))
    external_robustness_text = (
        f"Robustez externa em {external_robustness_score}%, "
        f"sign confidence={_safe_int(external_robustness_summary.get('exact_sign_confidence_percent'))}% e "
        f"clinical robustness={_safe_int(external_robustness_summary.get('high_confidence_clinical_robustness_percent'))}%."
        if external_robustness_summary
        else "Pacote de robustez externa ainda nao materializado."
    )

    artifact_coverage = int(round(artifact_table["exists"].mean() * 100)) if not artifact_table.empty else 0
    artifact_package_score = artifact_coverage

    criteria = [
        _criterion_row(
            "cohort_design",
            "Cohort design and labels",
            1.0,
            cohort_design_score,
            (
                f"{train_count} cohort(s) de treino, {n_external_cohorts} coorte(s) externas e "
                f"{cohort_label_ready}% das coortes com pelo menos duas classes."
            ),
            "Garantir exatamente uma coorte de treino e ampliar coortes externas rotuladas quando necessario.",
            critical=True,
        ),
        _criterion_row(
            "data_versioning",
            "Data versioning and manifests",
            1.15,
            data_versioning_score,
            (
                f"{manifest_coverage}% das coortes com data release manifest e "
                f"{fingerprint_coverage}% com fingerprint do dataset integrado."
            ),
            "Assegurar manifests e fingerprints para todas as coortes usadas no estudo.",
            critical=True,
        ),
        _criterion_row(
            "public_source_traceability",
            "Public source traceability",
            1.1,
            public_source_traceability_score,
            (
                f"Media de release={_fmt_percent(cohort_table['release_coverage_percent'].mean() if not cohort_table.empty else np.nan)}, "
                f"schema={_fmt_percent(cohort_table['schema_coverage_percent'].mean() if not cohort_table.empty else np.nan)} e "
                f"catalog readiness={_fmt_percent(cohort_table['public_catalog_readiness_percent'].mean() if not cohort_table.empty else np.nan)}."
            ),
            "Completar tracking de release e cobertura estrutural das fontes publicas reais por coorte.",
            critical=True,
        ),
        _criterion_row(
            "cohort_independence",
            "Cohort independence",
            1.2,
            cohort_independence_score,
            (
                f"Independencia global em {cohort_independence_score}% com "
                f"max overlap treino/externo={_safe_int(cohort_independence_summary.get('max_variant_overlap_percent'))}%."
            ),
            "Eliminar sobreposicao de variantes entre treino e validacao externa antes da submissao final.",
            critical=True,
        ),
        _criterion_row(
            "real_data_freeze",
            "Real-data cohort freeze",
            1.15,
            cohort_freeze_score,
            (
                f"Freeze de coortes em {cohort_freeze_score}% com "
                f"{_safe_int(cohort_freeze_summary.get('n_example_blocked_cohorts'))} coorte(s) ainda bloqueadas por demo/example."
            ),
            "Substituir datasets de exemplo por coortes reais versionadas antes da submissao final.",
            critical=True,
        ),
        _criterion_row(
            "internal_validation",
            "Internal validation package",
            0.9,
            internal_validation_score,
            (
                f"Training metrics={training_metrics_ready}%, repeated holdout={repeated_holdout_ready}%, "
                f"gene-stratified metrics={gene_training_ready}% e model registry={model_registry_ready}%."
            ),
            "Manter repeated holdout, modelos versionados e analise gene-estratificada em toda release.",
        ),
        _criterion_row(
            "external_validation",
            "External validation coverage",
            1.2,
            external_validation_score,
            (
                f"{combined_external_coverage}% das coortes externas com metrica combinada e "
                f"{pairwise_availability}% com comparacao pareada AUC-ROC."
            ),
            "Executar validacao externa para todas as coortes planejadas e preservar comparacoes pareadas.",
            critical=True,
        ),
        _criterion_row(
            "comparative_evidence",
            "Comparative evidence strength",
            1.35,
            comparative_evidence_strength_score,
            comparative_evidence_text,
            "Rodar o benchmark em dados reais e buscar ganho consistente contra o baseline declarado.",
            critical=True,
        ),
        _criterion_row(
            "external_robustness",
            "External robustness",
            1.15,
            external_robustness_score,
            external_robustness_text,
            "Consolidar wins de calibracao, seguranca e estabilidade cross-cohort antes de ampliar a alegacao translacional.",
            critical=True,
        ),
        _criterion_row(
            "claim_strength",
            "Claim strength and framing",
            1.2,
            claim_strength_score,
            claim_strength_text,
            "Fortalecer a alegacao central do estudo ate um tier moderado ou forte antes da submissao.",
            critical=True,
        ),
        _criterion_row(
            "artifact_package",
            "Artifact package completeness",
            0.9,
            artifact_package_score,
            f"{artifact_coverage}% dos artefatos centrais do estudo foram materializados no output final.",
            "Garantir que tabelas, dossie e manifestos sejam exportados em toda execucao de estudo.",
            critical=True,
        ),
    ]

    weighted_total = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_readiness_percent = int(round(weighted_score / weighted_total)) if weighted_total else 0

    strengths = [item["title"] for item in criteria if item["score_percent"] >= 85]
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]
    ready_for_submission = bool(
        overall_readiness_percent >= 85
        and not critical_gaps
        and all(item["score_percent"] >= 80 for item in criteria if item["critical"])
    )

    best_external_summary = external_table.sort_values(
        ["best_external_auc_roc", "best_external_auc_pr", "cohort"],
        ascending=[False, False, True],
    ).head(1)
    best_external_row = best_external_summary.iloc[0].to_dict() if not best_external_summary.empty else {}

    summary = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "n_cohorts": n_cohorts,
        "n_external_cohorts": n_external_cohorts,
        "overall_readiness_percent": overall_readiness_percent,
        "overall_status": _readiness_status(overall_readiness_percent),
        "claim_tier": claim_tier,
        "claim_strength_percent": claim_strength_score,
        "external_robustness_percent": external_robustness_score,
        "real_data_freeze_percent": cohort_freeze_score,
        "ready_for_submission": ready_for_submission,
        "n_strengths": int(len(strengths)),
        "n_critical_gaps": int(len(critical_gaps)),
        "best_external_cohort": best_external_row.get("cohort"),
        "best_external_experiment": best_external_row.get("best_external_experiment"),
        "best_external_auc_roc": _safe_float(best_external_row.get("best_external_auc_roc")),
        "best_pairwise_evidence": best_external_row.get("pairwise_evidence"),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Overall readiness: {summary['overall_readiness_percent']}%",
        f"- Overall status: {summary['overall_status']}",
        f"- Claim tier: {summary['claim_tier']} ({summary['claim_strength_percent']}%)",
        f"- External robustness: {summary['external_robustness_percent']}%",
        f"- Real-data freeze: {summary['real_data_freeze_percent']}%",
        f"- Ready for high-impact submission: {'yes' if ready_for_submission else 'not yet'}",
        f"- Cohorts: {n_cohorts} total / {n_external_cohorts} external",
        "",
        "## Executive Summary",
        "",
    ]
    if strengths:
        markdown_lines.append(f"- Strong areas: {', '.join(strengths)}")
    else:
        markdown_lines.append("- Strong areas: none yet.")
    if critical_gaps:
        markdown_lines.append(f"- Critical gaps: {', '.join(critical_gaps)}")
    else:
        markdown_lines.append("- Critical gaps: none.")
    if best_external_row:
        markdown_lines.append(
            f"- Best external signal: {best_external_row.get('cohort')} -> "
            f"{best_external_row.get('best_external_experiment')} "
            f"(AUC-ROC={_fmt_metric(best_external_row.get('best_external_auc_roc'))}, "
            f"delta={_fmt_metric(best_external_row.get('pairwise_delta_auc_roc'))}, "
            f"evidence={best_external_row.get('pairwise_evidence') or '-'})"
        )
    else:
        markdown_lines.append("- Best external signal: unavailable.")

    markdown_lines.extend(["", "## Criteria", ""])
    for item in criteria:
        markdown_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Score: {item['score_percent']}%",
                f"- Status: {item['status']}",
                f"- Critical: {'yes' if item['critical'] else 'no'}",
                f"- Evidence: {item['evidence']}",
                f"- Next step: {item['next_step']}",
                "",
            ]
        )

    markdown_lines.extend(["## Cohort Evidence", ""])
    if cohort_table.empty:
        markdown_lines.append("- Cohort evidence unavailable.")
    else:
        for _, item in cohort_table.iterrows():
            markdown_lines.append(
                f"- {item['cohort_name']} ({item['role']}): n={int(item['valid_rows'])}, "
                f"release={int(item['release_coverage_percent'])}%, "
                f"schema={int(item['schema_coverage_percent'])}%, "
                f"benchmark={int(item['benchmark_readiness_percent'])}%."
            )

    markdown_lines.extend(["", "## External Comparative Evidence", ""])
    if external_table.empty:
        markdown_lines.append("- External comparative evidence unavailable.")
    else:
        for _, item in external_table.iterrows():
            markdown_lines.append(
                f"- {item['cohort']}: best={item['best_external_experiment'] or '-'} "
                f"(AUC-ROC={_fmt_metric(item['best_external_auc_roc'])}) | "
                f"delta vs baseline={_fmt_metric(item['pairwise_delta_auc_roc'])} "
                f"[{_fmt_metric(item['pairwise_ci_lower_95'])}, {_fmt_metric(item['pairwise_ci_upper_95'])}] "
                f"=> {item['pairwise_evidence']}"
            )

    markdown_lines.extend(["", "## Recommended Next Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- Seguir para consolidacao do manuscrito e submissao.")

    assessment = {
        "summary": summary,
        "criteria": criteria,
        "strengths": strengths,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "cohorts": cohort_table.to_dict(orient="records"),
        "sources": source_table.to_dict(orient="records"),
        "external_evidence": external_table.to_dict(orient="records"),
        "artifacts": artifact_table.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }
    return assessment


def build_publication_readiness_html(assessment: dict) -> str:
    markdown = str(assessment.get("markdown_report") or "")
    blocks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            blocks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Publication Readiness</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f3ee;color:#1b2530;max-width:1040px;margin:0 auto;padding:32px;line-height:1.7;}"
        "h1{font-size:2.3rem;margin-bottom:0.4rem;}h2{margin-top:2rem;color:#7b3f24;}h3{margin-top:1.4rem;color:#305d66;}"
        "ul{background:#fff;border:1px solid #e6ded2;border-radius:18px;padding:18px 24px;}"
        "p{background:#fffdf8;padding:14px 18px;border-left:4px solid #d28b2d;border-radius:12px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_publication_readiness_package(
    results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    assessment = build_publication_readiness_assessment(results, report_context=report_context)
    html_report = build_publication_readiness_html(assessment)

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    cohorts_df = pd.DataFrame(assessment.get("cohorts") or [])
    sources_df = pd.DataFrame(assessment.get("sources") or [])
    external_df = pd.DataFrame(assessment.get("external_evidence") or [])
    artifacts_df = pd.DataFrame(assessment.get("artifacts") or [])

    markdown_path = output_root / "publication_readiness_report.md"
    html_path = output_root / "publication_readiness_report.html"
    manifest_path = output_root / "publication_readiness_manifest.json"
    criteria_path = output_root / "publication_readiness_criteria.csv"
    cohorts_path = output_root / "publication_readiness_cohorts.csv"
    sources_path = output_root / "publication_readiness_sources.csv"
    external_path = output_root / "publication_readiness_external_evidence.csv"
    artifacts_path = output_root / "publication_readiness_artifacts.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    cohorts_df.to_csv(cohorts_path, index=False)
    sources_df.to_csv(sources_path, index=False)
    external_df.to_csv(external_path, index=False)
    artifacts_df.to_csv(artifacts_path, index=False)

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "strengths": assessment.get("strengths"),
        "critical_gaps": assessment.get("critical_gaps"),
        "recommended_actions": assessment.get("recommended_actions"),
        "report_context": assessment.get("report_context"),
        "criteria_path": str(criteria_path),
        "cohorts_path": str(cohorts_path),
        "sources_path": str(sources_path),
        "external_evidence_path": str(external_path),
        "artifacts_path": str(artifacts_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "publication_readiness_assessment": assessment,
        "publication_readiness_report_markdown_path": str(markdown_path),
        "publication_readiness_report_html_path": str(html_path),
        "publication_readiness_manifest_path": str(manifest_path),
        "publication_readiness_criteria_path": str(criteria_path),
        "publication_readiness_cohorts_path": str(cohorts_path),
        "publication_readiness_sources_path": str(sources_path),
        "publication_readiness_external_evidence_path": str(external_path),
        "publication_readiness_artifacts_path": str(artifacts_path),
    }
