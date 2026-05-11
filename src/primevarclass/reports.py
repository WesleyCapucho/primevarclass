from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fmt_metric(value: Any) -> str:
    try:
        numeric = float(value)
    except Exception:
        return "-"
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.4f}"


def _study_dossier_sections(results: dict, report_context: Dict[str, Any] | None = None) -> dict:
    context = dict(report_context or {})
    design = results.get("study_design")
    title = str(context.get("report_title") or (f"{design.name} - Scientific Dossier" if design is not None else "PrimeVarClass Scientific Dossier"))

    cohort_manifest = results.get("cohort_manifest")
    cohort_lines = []
    if isinstance(cohort_manifest, pd.DataFrame) and not cohort_manifest.empty:
        for _, row in cohort_manifest.iterrows():
            cohort_lines.append(
                f"- {row['cohort_name']} ({row['role']}): n={int(row['valid_rows'])}, "
                f"classes={int(row['n_classes'])}, source_tables={int(row['n_source_tables'])}"
            )

    training_metrics = results.get("training_metrics")
    best_internal = None
    if isinstance(training_metrics, pd.DataFrame) and not training_metrics.empty:
        best_internal = training_metrics.iloc[0].to_dict()

    external_metrics = results.get("external_evaluation_metrics")
    external_lines = []
    if isinstance(external_metrics, pd.DataFrame) and not external_metrics.empty:
        combined_rows = external_metrics[external_metrics["evaluation_group"] == "combined"]
        for cohort_name, subset in combined_rows.groupby("cohort"):
            top_row = subset.sort_values(["auc_roc", "auc_pr", "mcc"], ascending=False).iloc[0]
            external_lines.append(
                f"- {cohort_name}: {top_row['experiment']} "
                f"(AUC-ROC={_fmt_metric(top_row.get('auc_roc'))}, "
                f"AUC-PR={_fmt_metric(top_row.get('auc_pr'))}, "
                f"MCC={_fmt_metric(top_row.get('mcc'))})"
            )

    pairwise = results.get("external_pairwise_comparisons")
    pairwise_lines = []
    if isinstance(pairwise, pd.DataFrame) and not pairwise.empty:
        auc_rows = pairwise[pairwise["metric"] == "auc_roc"]
        if not auc_rows.empty:
            for cohort_name, subset in auc_rows.groupby("cohort"):
                row = subset.sort_values("delta_mean", ascending=False).iloc[0]
                pairwise_lines.append(
                    f"- {cohort_name}: {row['experiment']} vs {row['baseline_experiment']} "
                    f"delta={_fmt_metric(row.get('delta_mean'))} "
                    f"[{_fmt_metric(row.get('ci_lower_95'))}, {_fmt_metric(row.get('ci_upper_95'))}]"
                )

    consensus_members = [str(item) for item in results.get("consensus_members", []) if item]
    independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    cohort_freeze_summary = dict(results.get("study_cohort_freeze_summary") or {})
    claim_summary = dict((results.get("claim_strength_assessment") or {}).get("summary") or {})
    validation_summary = dict((results.get("study_validation_lock") or {}).get("summary") or {})
    output_paths = {
        "training_metrics_path": results.get("training_metrics_path"),
        "study_summary_report_path": results.get("study_summary_report_path"),
        "external_evaluation_path": results.get("external_evaluation_path"),
        "external_pairwise_path": results.get("external_pairwise_path"),
        "cohort_independence_manifest_path": results.get("cohort_independence_manifest_path"),
        "study_cohort_freeze_manifest_path": results.get("study_cohort_freeze_manifest_path"),
        "claim_strength_manifest_path": results.get("claim_strength_manifest_path"),
        "study_validation_lock_manifest_path": results.get("study_validation_lock_manifest_path"),
        "consensus_members_path": results.get("consensus_members_path"),
        "model_registry_path": results.get("model_paths", {}).get("registry"),
    }

    return {
        "title": title,
        "generated_at": _now_utc(),
        "context": context,
        "cohort_lines": cohort_lines,
        "best_internal": best_internal,
        "external_lines": external_lines,
        "pairwise_lines": pairwise_lines,
        "consensus_members": consensus_members,
        "independence_summary": independence_summary,
        "cohort_freeze_summary": cohort_freeze_summary,
        "claim_summary": claim_summary,
        "validation_summary": validation_summary,
        "output_paths": output_paths,
    }


def build_study_scientific_dossier_markdown(results: dict, report_context: Dict[str, Any] | None = None) -> str:
    sections = _study_dossier_sections(results, report_context=report_context)
    best_internal = sections["best_internal"] or {}
    context = sections["context"]

    lines = [
        f"# {sections['title']}",
        "",
        f"- Generated at: {sections['generated_at']}",
    ]
    for key, label in [
        ("institution", "Institution"),
        ("team_name", "Team"),
        ("operator_name", "Operator"),
        ("operator_role", "Operator role"),
        ("report_purpose", "Purpose"),
    ]:
        value = context.get(key)
        if value:
            lines.append(f"- {label}: {value}")

    lines.extend(["", "## Executive Summary", ""])
    if best_internal:
        lines.append(
            f"- Best internal experiment: {best_internal.get('experiment')} "
            f"(AUC-ROC={_fmt_metric(best_internal.get('auc_roc'))}, "
            f"AUC-PR={_fmt_metric(best_internal.get('auc_pr'))}, "
            f"MCC={_fmt_metric(best_internal.get('mcc'))})"
        )
    else:
        lines.append("- Internal ranking unavailable.")
    if sections["external_lines"]:
        lines.extend(sections["external_lines"])
    else:
        lines.append("- External validation summary unavailable.")
    independence_summary = sections.get("independence_summary") or {}
    if independence_summary:
        lines.append(
            f"- Cohort independence: {int(independence_summary.get('overall_independence_percent') or 0)}% "
            f"(max overlap={int(independence_summary.get('max_variant_overlap_percent') or 0)}%)."
        )
    cohort_freeze_summary = sections.get("cohort_freeze_summary") or {}
    if cohort_freeze_summary:
        lines.append(
            f"- Real-data cohort freeze: {int(cohort_freeze_summary.get('overall_real_data_readiness_percent') or 0)}% "
            f"(ready={'yes' if cohort_freeze_summary.get('ready_for_real_data_study') else 'not yet'})."
        )
    claim_summary = sections.get("claim_summary") or {}
    if claim_summary:
        lines.append(
            f"- Claim strength: {int(claim_summary.get('overall_claim_strength_percent') or 0)}% "
            f"({claim_summary.get('claim_tier') or '-'}) for {claim_summary.get('selected_experiment') or '-'}."
        )
    validation_summary = sections.get("validation_summary") or {}
    if validation_summary:
        lines.append(
            f"- Validation lock: {int(validation_summary.get('overall_validation_lock_percent') or 0)}% "
            f"(submission lock={'yes' if validation_summary.get('ready_for_submission_lock') else 'not yet'})."
        )

    lines.extend(["", "## Cohort Manifest", ""])
    lines.extend(sections["cohort_lines"] or ["- Cohort manifest unavailable."])

    lines.extend(["", "## Consensus Strategy", ""])
    if sections["consensus_members"]:
        lines.append(f"- Consensus members: {', '.join(sections['consensus_members'])}")
    else:
        lines.append("- No consensus ensemble generated.")

    lines.extend(["", "## Pairwise Deltas", ""])
    lines.extend(sections["pairwise_lines"] or ["- Pairwise bootstrap deltas unavailable."])

    lines.extend(["", "## Artifact Package", ""])
    for label, value in sections["output_paths"].items():
        if value:
            lines.append(f"- {label}: {value}")

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Este dossie resume desempenho interno, validacao externa, comparacoes bootstrap, freeze de coortes reais e a forca da alegacao cientifica.",
            "- As conclusoes devem ser acompanhadas de curadoria dos datasets e revisao biologica especializada antes de uso clinico.",
        ]
    )
    return "\n".join(lines)


def build_study_scientific_dossier_html(results: dict, report_context: Dict[str, Any] | None = None) -> str:
    markdown = build_study_scientific_dossier_markdown(results, report_context=report_context)
    paragraphs = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            paragraphs.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            paragraphs.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            paragraphs.append(f"<ul>{items}</ul>")
            continue
        paragraphs.append(f"<p>{html.escape(stripped)}</p>")

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Scientific Dossier</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f1e8;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2.2rem;margin-bottom:0.4rem;}h2{margin-top:2rem;color:#2d6f73;}"
        "ul{background:#fff;border:1px solid #e8ddcc;border-radius:18px;padding:18px 24px;}"
        "p{background:#fffdf8;padding:14px 18px;border-left:4px solid #b84d2f;border-radius:12px;}"
        "</style></head><body>"
        + "".join(paragraphs)
        + "</body></html>"
    )


def export_study_scientific_dossier(
    results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    markdown = build_study_scientific_dossier_markdown(results, report_context=report_context)
    html_report = build_study_scientific_dossier_html(results, report_context=report_context)
    manifest = {
        "generated_at": _now_utc(),
        "report_context": dict(report_context or {}),
        "study_summary_report_path": results.get("study_summary_report_path"),
        "training_metrics_path": results.get("training_metrics_path"),
        "external_evaluation_path": results.get("external_evaluation_path"),
    }

    markdown_path = output_root / "study_scientific_dossier.md"
    html_path = output_root / "study_scientific_dossier.html"
    manifest_path = output_root / "study_scientific_dossier_manifest.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "scientific_dossier_markdown_path": str(markdown_path),
        "scientific_dossier_html_path": str(html_path),
        "scientific_dossier_manifest_path": str(manifest_path),
    }
