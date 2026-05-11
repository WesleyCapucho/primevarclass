from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

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


def _fmt_metric(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.4f}"


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


def build_methods_package(results: dict, report_context: Dict[str, Any] | None = None) -> dict:
    context = dict(report_context or {})
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Methods Package")
    title = str(context.get("report_title") or f"{study_name} - Methods Package")

    cohort_manifest = results.get("cohort_manifest")
    cohort_results = dict(results.get("cohort_results") or {})
    training_metrics = results.get("training_metrics")
    model_family_summary = results.get("model_family_summary")
    cohort_freeze_summary = dict(results.get("study_cohort_freeze_summary") or {})

    cohort_df = cohort_manifest.copy() if isinstance(cohort_manifest, pd.DataFrame) else pd.DataFrame()
    model_family_df = model_family_summary.copy() if isinstance(model_family_summary, pd.DataFrame) else pd.DataFrame()
    training_df = training_metrics.copy() if isinstance(training_metrics, pd.DataFrame) else pd.DataFrame()

    source_rows: List[dict] = []
    for cohort_name, payload in cohort_results.items():
        release_manifest = _load_cohort_release_manifest(payload.get("ingestion_output_dir"))
        for source in release_manifest.get("sources") or []:
            source_rows.append(
                {
                    "cohort_name": cohort_name,
                    "source_name": source.get("name"),
                    "source_type": source.get("source_type"),
                    "kind": source.get("kind"),
                    "preset": source.get("preset"),
                    "path": source.get("path"),
                    "url": source.get("url"),
                    "has_file_fingerprint": bool((source.get("file_fingerprint") or {}).get("sha256")),
                    "has_provenance": bool(source.get("provenance")),
                }
            )
    sources_df = pd.DataFrame(source_rows)

    checklist = [
        {
            "item": "Study config declared",
            "status": "yes" if study_design is not None else "no",
            "evidence": getattr(study_design, "name", None),
        },
        {
            "item": "Training metrics exported",
            "status": "yes" if _artifact_exists(results.get("training_metrics_path")) else "no",
            "evidence": results.get("training_metrics_path"),
        },
        {
            "item": "Repeated holdout exported",
            "status": "yes" if _artifact_exists(results.get("training_repeated_holdout_path")) else "no",
            "evidence": results.get("training_repeated_holdout_path"),
        },
        {
            "item": "External evaluation exported",
            "status": "yes" if _artifact_exists(results.get("external_evaluation_path")) else "no",
            "evidence": results.get("external_evaluation_path"),
        },
        {
            "item": "Pairwise comparison exported",
            "status": "yes" if _artifact_exists(results.get("external_pairwise_path")) else "no",
            "evidence": results.get("external_pairwise_path"),
        },
        {
            "item": "Cohort independence audit exported",
            "status": "yes" if _artifact_exists(results.get("cohort_independence_manifest_path")) else "no",
            "evidence": results.get("cohort_independence_manifest_path"),
        },
        {
            "item": "Real-data cohort freeze exported",
            "status": "yes" if _artifact_exists(results.get("study_cohort_freeze_manifest_path")) else "no",
            "evidence": results.get("study_cohort_freeze_manifest_path"),
        },
        {
            "item": "Claim strength package exported",
            "status": "yes" if _artifact_exists(results.get("claim_strength_manifest_path")) else "no",
            "evidence": results.get("claim_strength_manifest_path"),
        },
        {
            "item": "Model registry exported",
            "status": "yes" if _artifact_exists((results.get("model_paths") or {}).get("registry")) else "no",
            "evidence": (results.get("model_paths") or {}).get("registry"),
        },
        {
            "item": "Per-cohort data release manifests exported",
            "status": "yes" if not cohort_results or all(_load_cohort_release_manifest(item.get("ingestion_output_dir")) for item in cohort_results.values()) else "no",
            "evidence": len(cohort_results),
        },
    ]
    checklist_df = pd.DataFrame(checklist)

    best_training_row = training_df.sort_values(
        ["auc_roc", "auc_pr", "mcc", "experiment"],
        ascending=[False, False, False, True],
    ).head(1)
    best_row = best_training_row.iloc[0].to_dict() if not best_training_row.empty else {}

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Study name: {study_name}",
        f"- Primary metric: {getattr(study_design, 'primary_metric', 'auc_roc') if study_design is not None else 'auc_roc'}",
        f"- Baseline experiment: {getattr(study_design, 'baseline_experiment', 'external_predictors_only') if study_design is not None else 'external_predictors_only'}",
        f"- Bootstrap replicates: {getattr(study_design, 'n_bootstrap', '-') if study_design is not None else '-'}",
        "",
        "## Cohort Methods Snapshot",
        "",
    ]
    if cohort_df.empty:
        markdown_lines.append("- Cohort manifest unavailable.")
    else:
        for _, row in cohort_df.iterrows():
            markdown_lines.append(
                f"- {row.get('cohort_name')}: role={row.get('role')}, n={int(row.get('valid_rows', 0))}, "
                f"classes={int(row.get('n_classes', 0))}, source_tables={int(row.get('n_source_tables', 0))}"
            )

    markdown_lines.extend(["", "## Model Families", ""])
    if model_family_df.empty:
        markdown_lines.append("- Model family summary unavailable.")
    else:
        for _, row in model_family_df.iterrows():
            markdown_lines.append(
                f"- {row.get('model_family')}: n={int(row.get('n_experiments', 0))}, "
                f"best AUC-ROC={_fmt_metric(row.get('best_auc_roc'))}, best AUC-PR={_fmt_metric(row.get('best_auc_pr'))}"
            )

    markdown_lines.extend(["", "## Best Internal Configuration", ""])
    if best_row:
        markdown_lines.append(
            f"- {best_row.get('experiment')} ({best_row.get('model_family')}) with "
            f"AUC-ROC={_fmt_metric(best_row.get('auc_roc'))}, "
            f"AUC-PR={_fmt_metric(best_row.get('auc_pr'))}, "
            f"MCC={_fmt_metric(best_row.get('mcc'))}."
        )
    else:
        markdown_lines.append("- Best internal configuration unavailable.")

    markdown_lines.extend(["", "## Data Provenance Snapshot", ""])
    if sources_df.empty:
        markdown_lines.append("- No cohort source provenance available.")
    else:
        for _, row in sources_df.iterrows():
            markdown_lines.append(
                f"- {row.get('cohort_name')}: {row.get('source_name')} ({row.get('source_type')}/{row.get('kind')}) "
                f"preset={row.get('preset') or '-'} | provenance={'yes' if row.get('has_provenance') else 'no'}"
            )

    markdown_lines.extend(["", "## Reproducibility Checklist", ""])
    for _, row in checklist_df.iterrows():
        markdown_lines.append(f"- {row['item']}: {row['status']} ({row['evidence']})")

    independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    if independence_summary:
        markdown_lines.extend(
            [
                "",
                "## Cohort Independence Audit",
                "",
                f"- Independence score: {int(independence_summary.get('overall_independence_percent') or 0)}%",
                f"- Max train/external overlap: {int(independence_summary.get('max_variant_overlap_percent') or 0)}%",
                f"- Ready for external validation: {'yes' if independence_summary.get('ready_for_external_validation') else 'not yet'}",
            ]
        )
    if cohort_freeze_summary:
        markdown_lines.extend(
            [
                "",
                "## Real-data Cohort Freeze",
                "",
                f"- Real-data readiness: {int(cohort_freeze_summary.get('overall_real_data_readiness_percent') or 0)}%",
                f"- Ready for real-data study: {'yes' if cohort_freeze_summary.get('ready_for_real_data_study') else 'not yet'}",
                f"- Example-blocked cohorts: {int(cohort_freeze_summary.get('n_example_blocked_cohorts') or 0)}",
            ]
        )
    claim_summary = dict((results.get("claim_strength_assessment") or {}).get("summary") or {})
    if claim_summary:
        markdown_lines.extend(
            [
                "",
                "## Claim Strength Audit",
                "",
                f"- Claim strength: {int(claim_summary.get('overall_claim_strength_percent') or 0)}%",
                f"- Claim tier: {claim_summary.get('claim_tier') or '-'}",
                f"- Candidate experiment: {claim_summary.get('selected_experiment') or '-'}",
            ]
        )

    markdown_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Este pacote resume desenho experimental, familias de modelo, proveniencia de dados e itens minimos de reproducibilidade.",
            "- O texto pode ser adaptado para a secao de Metodos do manuscrito e para materiais suplementares.",
        ]
    )

    summary = {
        "generated_at": _now_utc(),
        "study_name": study_name,
        "n_cohorts": int(len(cohort_df)),
        "n_source_rows": int(len(sources_df)),
        "n_checklist_items": int(len(checklist_df)),
        "real_data_readiness_percent": int(cohort_freeze_summary.get("overall_real_data_readiness_percent") or 0),
        "best_internal_experiment": best_row.get("experiment"),
    }
    return {
        "summary": summary,
        "cohorts": cohort_df.to_dict(orient="records"),
        "sources": sources_df.to_dict(orient="records"),
        "checklist": checklist_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_methods_package_html(bundle: dict) -> str:
    markdown = str(bundle.get("markdown_report") or "")
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
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Methods Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f8f3ea;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}ul{background:#fff;border:1px solid #eadfce;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_methods_package(results: dict, output_dir: str, report_context: Dict[str, Any] | None = None) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    bundle = build_methods_package(results, report_context=report_context)
    html_report = build_methods_package_html(bundle)

    cohorts_df = pd.DataFrame(bundle.get("cohorts") or [])
    sources_df = pd.DataFrame(bundle.get("sources") or [])
    checklist_df = pd.DataFrame(bundle.get("checklist") or [])

    markdown_path = root / "methods_package.md"
    html_path = root / "methods_package.html"
    manifest_path = root / "methods_package_manifest.json"
    cohorts_path = root / "methods_package_cohorts.csv"
    sources_path = root / "methods_package_sources.csv"
    checklist_path = root / "methods_package_checklist.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    cohorts_df.to_csv(cohorts_path, index=False)
    sources_df.to_csv(sources_path, index=False)
    checklist_df.to_csv(checklist_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "cohorts_path": str(cohorts_path),
        "sources_path": str(sources_path),
        "checklist_path": str(checklist_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "methods_package_summary": bundle.get("summary"),
        "methods_package_markdown_path": str(markdown_path),
        "methods_package_html_path": str(html_path),
        "methods_package_manifest_path": str(manifest_path),
        "methods_package_cohorts_path": str(cohorts_path),
        "methods_package_sources_path": str(sources_path),
        "methods_package_checklist_path": str(checklist_path),
    }
