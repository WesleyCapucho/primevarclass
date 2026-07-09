from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

from .core import (
    OPTIONAL_DATASET_COLUMNS,
    encode_variant_features,
    normalize_gene,
    normalize_hgvs_protein,
    parse_variant,
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _to_builtin(value: Any) -> Any:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _extract_metric_lookup(metrics_df: pd.DataFrame | None) -> Dict[str, dict]:
    if not isinstance(metrics_df, pd.DataFrame) or metrics_df.empty or "experiment" not in metrics_df.columns:
        return {}
    return {
        str(row["experiment"]): {key: _to_builtin(value) for key, value in row.items()}
        for row in metrics_df.to_dict(orient="records")
    }


def _select_external_overrides(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {column: payload[column] for column in OPTIONAL_DATASET_COLUMNS if column in payload}


def prepare_variant_prediction_row(
    gene: str,
    hgvs_p: str,
    mode: str = "hybrid",
    feature_payload: Dict[str, Any] | None = None,
    metadata_payload: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    resolved_gene = normalize_gene(gene)
    if resolved_gene is None:
        raise ValueError(f"Gene nao suportado para inferencia: {gene}")

    resolved_hgvs_p = normalize_hgvs_protein(hgvs_p, gene=resolved_gene)
    if resolved_hgvs_p is None:
        raise ValueError(f"HGVS proteico invalido: {hgvs_p}")

    variant = parse_variant(resolved_hgvs_p)
    merged_payload = dict(feature_payload or {})
    features = encode_variant_features(
        variant,
        mode=mode,
        external_features=_select_external_overrides(merged_payload),
    )

    for key, value in merged_payload.items():
        if key.startswith("feature_"):
            features[key] = value

    for key, value in dict(metadata_payload or {}).items():
        if key.startswith("meta_"):
            features[key] = value

    features["variant"] = variant.variant_str
    features["hgvs_p"] = resolved_hgvs_p
    features["gene"] = resolved_gene
    return pd.DataFrame([features])


def build_model_registry(
    model_paths: Dict[str, str],
    feature_sets: Dict[str, List[str]],
    metrics_df: pd.DataFrame | None,
    output_dir: str,
    training_mode: str | None = None,
) -> Dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    metric_lookup = _extract_metric_lookup(metrics_df)
    manifest_paths: Dict[str, str] = {}
    rows = []

    for experiment_name, model_path in model_paths.items():
        feature_columns = list(feature_sets.get(experiment_name, []))
        metric_row = metric_lookup.get(experiment_name, {})
        manifest = {
            "experiment": experiment_name,
            "model_path": str(Path(model_path).resolve()),
            "feature_columns": feature_columns,
            "n_features": len(feature_columns),
            "feature_set": metric_row.get("feature_set"),
            "model_family": metric_row.get("model_family"),
            "training_mode": training_mode,
            "metrics": {
                key: value
                for key, value in metric_row.items()
                if key not in {"experiment", "feature_set", "model_family", "is_primary_experiment", "n_features"}
            },
        }
        manifest_path = output_root / f"{experiment_name}_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest_paths[experiment_name] = str(manifest_path)
        rows.append(
            {
                "experiment": experiment_name,
                "model_path": manifest["model_path"],
                "manifest_path": str(manifest_path.resolve()),
                "feature_set": manifest.get("feature_set"),
                "model_family": manifest.get("model_family"),
                "training_mode": training_mode,
                "n_features": len(feature_columns),
                "is_primary_experiment": metric_row.get("is_primary_experiment"),
                "auc_roc": metric_row.get("auc_roc"),
                "auc_pr": metric_row.get("auc_pr"),
                "mcc": metric_row.get("mcc"),
            }
        )

    registry_df = pd.DataFrame(rows)
    registry_path = output_root / "model_registry.csv"
    registry_df.to_csv(registry_path, index=False)
    return {
        "registry": registry_df,
        "registry_path": str(registry_path.resolve()),
        "manifest_paths": manifest_paths,
    }


def load_model_registry(model_dir: str) -> pd.DataFrame:
    registry_path = Path(model_dir) / "model_registry.csv"
    if not registry_path.exists():
        raise FileNotFoundError(f"Registro de modelos nao encontrado em: {registry_path}")
    return pd.read_csv(registry_path)


@lru_cache(maxsize=32)
def _load_model_manifest_cached(model_dir: str, experiment: str) -> dict:
    registry_df = load_model_registry(model_dir)
    subset = registry_df.loc[registry_df["experiment"].astype(str) == str(experiment)]
    if subset.empty:
        raise KeyError(f"Experimento nao encontrado no registro: {experiment}")
    manifest_path = Path(str(subset.iloc[0]["manifest_path"]))
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def _load_pipeline_cached(model_path: str):
    return joblib.load(model_path)


def load_model_bundle(model_dir: str, experiment: str) -> tuple[object, dict]:
    manifest = _load_model_manifest_cached(str(Path(model_dir).resolve()), str(experiment))
    model = _load_pipeline_cached(str(Path(manifest["model_path"]).resolve()))
    return model, manifest


def build_variant_evidence_summary(feature_row: pd.Series, predicted_probability: float) -> List[str]:
    lines = [
        f"Probabilidade predita de patogenicidade: {predicted_probability:.4f}.",
        f"Transicao prima: {int(feature_row.get('prime_ref', 0))}->{int(feature_row.get('prime_alt', 0))} com delta {int(feature_row.get('prime_diff', 0))}.",
        f"Severidade bioquimica estimada: {float(feature_row.get('biochemical_severity_score', 0.0)):.4f}.",
    ]

    if pd.notna(feature_row.get("conservation_signal_mean")):
        lines.append(f"Sinal medio de conservacao: {float(feature_row['conservation_signal_mean']):.4f}.")
    if pd.notna(feature_row.get("structure_signal_mean")):
        lines.append(f"Sinal estrutural medio: {float(feature_row['structure_signal_mean']):.4f}.")

    external_signals = []
    for field_name in ["revel", "bayesdel", "alphamissense", "cadd"]:
        if field_name in feature_row.index and pd.notna(feature_row[field_name]):
            external_signals.append(f"{field_name}={_to_builtin(feature_row[field_name])}")
    for field_name in feature_row.index:
        if field_name.startswith("feature_") and pd.notna(feature_row[field_name]):
            external_signals.append(f"{field_name}={_to_builtin(feature_row[field_name])}")
    if external_signals:
        lines.append("Preditores externos observados: " + ", ".join(external_signals) + ".")

    return lines


def classify_priority_tier(predicted_probability: float, threshold: float = 0.5) -> str:
    if predicted_probability >= 0.9:
        return "tier_1_immediate_review"
    if predicted_probability >= 0.7:
        return "tier_2_high_priority"
    if predicted_probability >= threshold:
        return "tier_3_review"
    return "tier_4_low_priority"


def score_variant_with_model(
    model_dir: str,
    experiment: str,
    gene: str,
    hgvs_p: str,
    mode: str | None = None,
    feature_payload: Dict[str, Any] | None = None,
    metadata_payload: Dict[str, Any] | None = None,
    threshold: float = 0.5,
) -> dict:
    model, manifest = load_model_bundle(model_dir, experiment)
    resolved_mode = str(mode or manifest.get("training_mode") or "hybrid")
    prediction_df = prepare_variant_prediction_row(
        gene=gene,
        hgvs_p=hgvs_p,
        mode=resolved_mode,
        feature_payload=feature_payload,
        metadata_payload=metadata_payload,
    )

    feature_columns = [str(column) for column in manifest.get("feature_columns", [])]
    aligned = prediction_df.copy()
    for column in feature_columns:
        if column not in aligned.columns:
            aligned[column] = np.nan
    X = aligned[feature_columns].copy()
    probability = float(model.predict_proba(X)[:, 1][0])
    predicted_label = int(probability >= threshold)
    feature_row = prediction_df.iloc[0]

    used_features = {
        column: _to_builtin(X.iloc[0][column])
        for column in feature_columns
    }
    return {
        "experiment": manifest.get("experiment", experiment),
        "feature_set": manifest.get("feature_set"),
        "model_family": manifest.get("model_family"),
        "training_mode": resolved_mode,
        "variant": str(feature_row.get("variant")),
        "gene": str(feature_row.get("gene")),
        "hgvs_p": str(feature_row.get("hgvs_p")),
        "predicted_probability": probability,
        "predicted_label": predicted_label,
        "priority_tier": classify_priority_tier(probability, threshold=threshold),
        "threshold": threshold,
        "used_features": used_features,
        "evidence_summary": build_variant_evidence_summary(feature_row, probability),
    }


def _build_batch_report_csv(records: List[dict]) -> str:
    if not records:
        return ""
    table = pd.DataFrame(records)
    output = io.StringIO()
    table.to_csv(output, index=False)
    return output.getvalue()


def _build_batch_report_markdown(
    *,
    records: List[dict],
    summary: Dict[str, Any],
    model_dir: str,
    experiment: str,
    threshold: float,
    report_title: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> str:
    context = dict(report_context or {})
    title = report_title or context.get("report_title") or "PrimeVarClass Laboratory Screening Report"
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Model directory: {model_dir}",
        f"- Experiment: {experiment}",
        f"- Threshold: {threshold}",
    ]
    for key, label in [
        ("batch_name", "Batch"),
        ("laboratory_name", "Laboratory"),
        ("institution", "Institution"),
        ("team_name", "Team"),
        ("team_id", "Team ID"),
        ("operator_name", "Operator"),
        ("operator_role", "Operator role"),
        ("operator_profile_id", "Operator profile"),
    ]:
        value = context.get(key)
        if value:
            lines.append(f"- {label}: {value}")

    lines.extend(
        [
            "",
            "## Executive Summary",
            "",
            f"- Total variants: {summary.get('total_variants', 0)}",
            f"- Successful classifications: {summary.get('n_success', 0)}",
            f"- Errors: {summary.get('n_error', 0)}",
            f"- Tier 1 immediate review: {summary.get('n_tier_1', 0)}",
            f"- Tier 2 high priority: {summary.get('n_tier_2', 0)}",
            f"- Tier 3 review: {summary.get('n_tier_3', 0)}",
            f"- Tier 4 low priority: {summary.get('n_tier_4', 0)}",
            "",
            "## Prioritized Variants",
            "",
            "| Sample | Variant | Status | Probability | Tier |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in records:
        probability = row.get("predicted_probability")
        probability_text = "-" if probability is None else f"{float(probability):.4f}"
        variant_label = row.get("variant") or f"{row.get('gene') or ''} {row.get('hgvs_p') or ''}".strip()
        lines.append(
            f"| {row.get('sample_id') or ''} | {variant_label} | {row.get('status')} | "
            f"{probability_text} | {row.get('priority_tier') or '-'} |"
        )

    lines.extend(["", "## Notes", ""])
    if summary.get("n_error", 0):
        lines.append("- Alguns itens nao puderam ser classificados e devem ser revisados manualmente.")
    lines.append("- Este relatorio apoia triagem e priorizacao de pesquisa; nao substitui interpretacao clinica independente.")
    return "\n".join(lines)


def score_variant_batch_with_model(
    model_dir: str,
    experiment: str,
    variants: List[Dict[str, Any]],
    default_mode: str | None = None,
    threshold: float = 0.5,
    report_title: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    records = []
    for index, payload in enumerate(variants):
        sample_id = str(payload.get("sample_id") or f"variant_{index + 1:03d}")
        try:
            result = score_variant_with_model(
                model_dir=model_dir,
                experiment=experiment,
                gene=str(payload["gene"]),
                hgvs_p=str(payload["hgvs_p"]),
                mode=payload.get("mode") or default_mode,
                feature_payload=dict(payload.get("feature_payload", {})),
                metadata_payload=dict(payload.get("metadata_payload", {})),
                threshold=threshold,
            )
            records.append(
                {
                    "sample_id": sample_id,
                    "status": "ok",
                    "gene": result["gene"],
                    "hgvs_p": result["hgvs_p"],
                    "variant": result["variant"],
                    "experiment": result["experiment"],
                    "feature_set": result.get("feature_set"),
                    "model_family": result.get("model_family"),
                    "predicted_probability": result["predicted_probability"],
                    "predicted_label": result["predicted_label"],
                    "priority_tier": result["priority_tier"],
                    "threshold": result["threshold"],
                    "evidence_summary": " | ".join(result["evidence_summary"]),
                }
            )
        except Exception as exc:
            records.append(
                {
                    "sample_id": sample_id,
                    "status": "error",
                    "gene": payload.get("gene"),
                    "hgvs_p": payload.get("hgvs_p"),
                    "variant": None,
                    "experiment": experiment,
                    "feature_set": None,
                    "model_family": None,
                    "predicted_probability": None,
                    "predicted_label": None,
                    "priority_tier": "error",
                    "threshold": threshold,
                    "evidence_summary": str(exc),
                }
            )

    success_records = [row for row in records if row["status"] == "ok"]
    success_records = sorted(
        success_records,
        key=lambda row: float(row.get("predicted_probability") or 0.0),
        reverse=True,
    )
    error_records = [row for row in records if row["status"] != "ok"]
    sorted_records = success_records + error_records

    summary = {
        "total_variants": len(records),
        "n_success": len(success_records),
        "n_error": len(error_records),
        "n_pathogenic_like": int(sum(int(row["predicted_label"]) for row in success_records)),
        "n_benign_like": int(sum(1 - int(row["predicted_label"]) for row in success_records)),
        "n_tier_1": int(sum(row["priority_tier"] == "tier_1_immediate_review" for row in success_records)),
        "n_tier_2": int(sum(row["priority_tier"] == "tier_2_high_priority" for row in success_records)),
        "n_tier_3": int(sum(row["priority_tier"] == "tier_3_review" for row in success_records)),
        "n_tier_4": int(sum(row["priority_tier"] == "tier_4_low_priority" for row in success_records)),
        "max_predicted_probability": float(max([row["predicted_probability"] for row in success_records], default=0.0)),
    }
    markdown_report = _build_batch_report_markdown(
        records=sorted_records,
        summary=summary,
        model_dir=model_dir,
        experiment=experiment,
        threshold=threshold,
        report_title=report_title,
        report_context=report_context,
    )
    return {
        "model_dir": model_dir,
        "experiment": experiment,
        "threshold": threshold,
        "summary": summary,
        "report": sorted_records,
        "csv_report": _build_batch_report_csv(sorted_records),
        "markdown_report": markdown_report,
        "report_metadata": {
            "report_title": report_title or "PrimeVarClass Laboratory Screening Report",
            "generated_at": _now_utc(),
            "report_context": dict(report_context or {}),
        },
    }
