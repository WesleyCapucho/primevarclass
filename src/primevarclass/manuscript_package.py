from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd


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


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned or "figure"


def _resolve_cohort_table(results: dict) -> pd.DataFrame:
    readiness = dict(results.get("publication_readiness_assessment") or {})
    cohorts = readiness.get("cohorts") or []
    if cohorts:
        frame = pd.DataFrame(cohorts)
        preferred = [
            "cohort_name",
            "role",
            "valid_rows",
            "n_classes",
            "n_source_tables",
            "release_coverage_percent",
            "schema_coverage_percent",
            "public_catalog_readiness_percent",
            "benchmark_readiness_percent",
        ]
        selected = [column for column in preferred if column in frame.columns]
        return frame[selected].copy()
    cohort_manifest = results.get("cohort_manifest")
    return cohort_manifest.copy() if isinstance(cohort_manifest, pd.DataFrame) else pd.DataFrame()


def _resolve_internal_table(results: dict) -> pd.DataFrame:
    leaderboard = results.get("feature_set_leaderboard")
    if isinstance(leaderboard, pd.DataFrame) and not leaderboard.empty:
        preferred = ["feature_set", "experiment", "model_family", "auc_roc", "auc_pr", "mcc", "n_features"]
        selected = [column for column in preferred if column in leaderboard.columns]
        return leaderboard[selected].copy()
    training_metrics = results.get("training_metrics")
    if not isinstance(training_metrics, pd.DataFrame) or training_metrics.empty:
        return pd.DataFrame()
    ranked = training_metrics.sort_values(
        ["auc_roc", "auc_pr", "mcc", "is_primary_experiment", "experiment"],
        ascending=[False, False, False, False, True],
    )
    if "feature_set" in ranked.columns:
        ranked = ranked.groupby("feature_set", as_index=False).head(1)
    preferred = ["feature_set", "experiment", "model_family", "auc_roc", "auc_pr", "mcc", "n_features"]
    selected = [column for column in preferred if column in ranked.columns]
    return ranked[selected].reset_index(drop=True)


def _resolve_external_table(results: dict) -> pd.DataFrame:
    external = results.get("external_evaluation_metrics")
    if not isinstance(external, pd.DataFrame) or external.empty:
        return pd.DataFrame()
    combined = external[external["evaluation_group"].astype(str) == "combined"].copy()
    combined = combined.sort_values(
        ["cohort", "auc_roc", "auc_pr", "mcc", "experiment"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)
    preferred = ["cohort", "cohort_role", "experiment", "feature_set", "model_family", "auc_roc", "auc_pr", "mcc", "n_variants"]
    selected = [column for column in preferred if column in combined.columns]
    return combined[selected].copy()


def _resolve_pairwise_table(results: dict) -> pd.DataFrame:
    pairwise = results.get("external_pairwise_comparisons")
    if not isinstance(pairwise, pd.DataFrame) or pairwise.empty:
        return pd.DataFrame()
    auc_only = pairwise[pairwise["metric"].astype(str) == "auc_roc"].copy()
    auc_only = auc_only.sort_values(
        ["cohort", "delta_mean", "ci_lower_95", "experiment"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)
    preferred = ["cohort", "cohort_role", "experiment", "baseline_experiment", "delta_mean", "ci_lower_95", "ci_upper_95", "n_bootstrap_valid"]
    selected = [column for column in preferred if column in auc_only.columns]
    return auc_only[selected].copy()


def _best_rows_by_group(table: pd.DataFrame, group_column: str, metric_column: str) -> pd.DataFrame:
    if table.empty or group_column not in table.columns or metric_column not in table.columns:
        return pd.DataFrame()
    return (
        table.sort_values([group_column, metric_column], ascending=[True, False])
        .groupby(group_column, as_index=False)
        .head(1)
        .reset_index(drop=True)
    )


def _chart_rows(items: Iterable[dict], label_key: str, value_key: str) -> List[dict]:
    rows = []
    for item in items:
        value = _safe_float(item.get(value_key))
        if np.isnan(value):
            continue
        rows.append({"label": str(item.get(label_key) or "-"), "value": value})
    return rows


def _build_horizontal_bar_chart_svg(title: str, rows: List[dict], value_format: str = ".3f") -> str:
    if not rows:
        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='960' height='160' viewBox='0 0 960 160'>"
            "<rect width='960' height='160' fill='#fbf7ef'/>"
            f"<text x='40' y='60' font-family='Georgia,serif' font-size='28' fill='#213547'>{html.escape(title)}</text>"
            "<text x='40' y='105' font-family='Georgia,serif' font-size='20' fill='#7b3f24'>No data available</text>"
            "</svg>"
        )

    max_value = max(max(item["value"] for item in rows), 1e-6)
    width = 960
    top_margin = 86
    row_height = 34
    chart_left = 280
    chart_width = 560
    height = top_margin + (len(rows) * row_height) + 28

    elements = [
        f"<rect width='{width}' height='{height}' fill='#fbf7ef'/>",
        f"<text x='36' y='48' font-family='Georgia,serif' font-size='28' fill='#213547'>{html.escape(title)}</text>",
    ]

    for index, item in enumerate(rows):
        y = top_margin + (index * row_height)
        bar_width = (item["value"] / max_value) * chart_width
        value_text = format(item["value"], value_format)
        elements.extend(
            [
                f"<text x='36' y='{y + 20}' font-family='Arial,sans-serif' font-size='16' fill='#213547'>{html.escape(item['label'])}</text>",
                f"<rect x='{chart_left}' y='{y + 4}' width='{chart_width}' height='18' rx='9' fill='#e6ddd1'/>",
                f"<rect x='{chart_left}' y='{y + 4}' width='{bar_width:.2f}' height='18' rx='9' fill='#2f7f73'/>",
                f"<text x='{chart_left + chart_width + 18}' y='{y + 19}' font-family='Arial,sans-serif' font-size='15' fill='#7b3f24'>{html.escape(value_text)}</text>",
            ]
        )

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        + "".join(elements)
        + "</svg>"
    )


def build_manuscript_package(results: dict, report_context: Dict[str, Any] | None = None) -> dict:
    context = dict(report_context or {})
    study_design = results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Manuscript Package")
    title = str(context.get("report_title") or f"{study_name} - Manuscript Package")

    cohort_table = _resolve_cohort_table(results)
    internal_table = _resolve_internal_table(results)
    external_table = _resolve_external_table(results)
    pairwise_table = _resolve_pairwise_table(results)
    independence_summary = dict((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    cohort_freeze_summary = dict(results.get("study_cohort_freeze_summary") or {})
    claim_summary = dict((results.get("claim_strength_assessment") or {}).get("summary") or {})

    best_internal = _best_rows_by_group(internal_table, "feature_set", "auc_roc")
    best_external = _best_rows_by_group(external_table, "cohort", "auc_roc")
    best_pairwise = _best_rows_by_group(pairwise_table, "cohort", "delta_mean")

    internal_figure_rows = _chart_rows(best_internal.to_dict(orient="records"), "feature_set", "auc_roc")
    external_figure_rows = _chart_rows(best_external.to_dict(orient="records"), "cohort", "auc_roc")

    summary = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "n_cohorts": int(len(cohort_table)),
        "n_internal_rows": int(len(internal_table)),
        "n_external_rows": int(len(external_table)),
        "n_pairwise_rows": int(len(pairwise_table)),
        "cohort_independence_percent": int(independence_summary.get("overall_independence_percent") or 0),
        "real_data_readiness_percent": int(cohort_freeze_summary.get("overall_real_data_readiness_percent") or 0),
        "claim_strength_percent": int(claim_summary.get("overall_claim_strength_percent") or 0),
        "claim_tier": claim_summary.get("claim_tier"),
        "best_internal_experiment": best_internal.iloc[0]["experiment"] if not best_internal.empty and "experiment" in best_internal.columns else None,
        "best_internal_auc_roc": _safe_float(best_internal.iloc[0]["auc_roc"]) if not best_internal.empty and "auc_roc" in best_internal.columns else float("nan"),
        "best_external_experiment": best_external.iloc[0]["experiment"] if not best_external.empty and "experiment" in best_external.columns else None,
        "best_external_auc_roc": _safe_float(best_external.iloc[0]["auc_roc"]) if not best_external.empty and "auc_roc" in best_external.columns else float("nan"),
        "best_pairwise_experiment": best_pairwise.iloc[0]["experiment"] if not best_pairwise.empty and "experiment" in best_pairwise.columns else None,
        "best_pairwise_delta_auc_roc": _safe_float(best_pairwise.iloc[0]["delta_mean"]) if not best_pairwise.empty and "delta_mean" in best_pairwise.columns else float("nan"),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Study: {summary['study_name']}",
        f"- Cohorts: {summary['n_cohorts']}",
        f"- Best internal experiment: {summary['best_internal_experiment'] or '-'} (AUC-ROC={_fmt_metric(summary['best_internal_auc_roc'])})",
        f"- Best external experiment: {summary['best_external_experiment'] or '-'} (AUC-ROC={_fmt_metric(summary['best_external_auc_roc'])})",
        f"- Best pairwise delta AUC-ROC: {summary['best_pairwise_experiment'] or '-'} ({_fmt_metric(summary['best_pairwise_delta_auc_roc'])})",
        f"- Cohort independence audit: {summary['cohort_independence_percent']}%",
        f"- Real-data cohort freeze: {summary['real_data_readiness_percent']}%",
        f"- Claim strength audit: {summary['claim_strength_percent']}% ({summary['claim_tier'] or '-'})",
        "",
        "## Table Inventory",
        "",
        "- Table 1: cohort design and release coverage",
        "- Table 2: best internal experiment per feature set",
        "- Table 3: combined external evaluation matrix",
        "- Table 4: pairwise external delta AUC-ROC vs baseline",
        "",
        "## Cohort Snapshot",
        "",
    ]

    if cohort_table.empty:
        markdown_lines.append("- No cohort table available.")
    else:
        for _, row in cohort_table.iterrows():
            markdown_lines.append(
                f"- {row.get('cohort_name')}: role={row.get('role')}, n={int(row.get('valid_rows', 0))}, "
                f"release={int(row.get('release_coverage_percent', 0)) if not pd.isna(row.get('release_coverage_percent', np.nan)) else 0}%, "
                f"schema={int(row.get('schema_coverage_percent', 0)) if not pd.isna(row.get('schema_coverage_percent', np.nan)) else 0}%"
            )

    markdown_lines.extend(["", "## Internal Results Snapshot", ""])
    if best_internal.empty:
        markdown_lines.append("- No internal ranking available.")
    else:
        for _, row in best_internal.iterrows():
            markdown_lines.append(
                f"- {row.get('feature_set')}: {row.get('experiment')} "
                f"(AUC-ROC={_fmt_metric(row.get('auc_roc'))}, AUC-PR={_fmt_metric(row.get('auc_pr'))}, MCC={_fmt_metric(row.get('mcc'))})"
            )

    markdown_lines.extend(["", "## External Results Snapshot", ""])
    if best_external.empty:
        markdown_lines.append("- No external evaluation available.")
    else:
        for _, row in best_external.iterrows():
            markdown_lines.append(
                f"- {row.get('cohort')}: {row.get('experiment')} "
                f"(AUC-ROC={_fmt_metric(row.get('auc_roc'))}, AUC-PR={_fmt_metric(row.get('auc_pr'))}, MCC={_fmt_metric(row.get('mcc'))})"
            )

    markdown_lines.extend(["", "## Pairwise Deltas", ""])
    if best_pairwise.empty:
        markdown_lines.append("- No pairwise AUC-ROC deltas available.")
    else:
        for _, row in best_pairwise.iterrows():
            markdown_lines.append(
                f"- {row.get('cohort')}: {row.get('experiment')} vs {row.get('baseline_experiment')} "
                f"=> delta={_fmt_metric(row.get('delta_mean'))} "
                f"[{_fmt_metric(row.get('ci_lower_95'))}, {_fmt_metric(row.get('ci_upper_95'))}]"
            )

    markdown_lines.extend(
        [
            "",
            "## Figure Inventory",
            "",
            "- Figure 1: internal AUC-ROC leaderboard by feature set",
            "- Figure 2: external AUC-ROC leaderboard by cohort",
            "",
            "## Notes",
            "",
            "- Este pacote organiza tabelas e figuras para reaproveitamento direto no manuscrito.",
            f"- A independencia entre coortes foi auditada em {summary['cohort_independence_percent']}%, reforcando a validade da avaliacao externa.",
            f"- A prontidao de dados reais ficou em {summary['real_data_readiness_percent']}%, ajudando a separar infraestrutura de evidencia biologica final.",
            f"- A forca da alegacao comparativa ficou em {summary['claim_strength_percent']}% ({summary['claim_tier'] or '-'}) para orientar a narrativa do artigo.",
            "- Resultados baseados em datasets de exemplo servem para validar infraestrutura, nao para conclusao biologica final.",
        ]
    )

    return {
        "summary": summary,
        "cohort_table": cohort_table,
        "internal_table": internal_table,
        "external_table": external_table,
        "pairwise_table": pairwise_table,
        "best_internal_table": best_internal,
        "best_external_table": best_external,
        "best_pairwise_table": best_pairwise,
        "internal_figure_svg": _build_horizontal_bar_chart_svg("Figure 1. Internal AUC-ROC by feature set", internal_figure_rows),
        "external_figure_svg": _build_horizontal_bar_chart_svg("Figure 2. External AUC-ROC by cohort", external_figure_rows),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_manuscript_package_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Manuscript Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f9f5ef;color:#17242f;max-width:1100px;margin:0 auto;padding:32px;line-height:1.7;}"
        "h1{font-size:2.3rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #eadfce;border-radius:18px;padding:18px 24px;}"
        ".figure{background:#fff;border:1px solid #eadfce;border-radius:18px;padding:18px;margin-top:20px;overflow:auto;}"
        "</style></head><body>"
        + "".join(blocks)
        + f"<div class='figure'>{bundle.get('internal_figure_svg') or ''}</div>"
        + f"<div class='figure'>{bundle.get('external_figure_svg') or ''}</div>"
        + "</body></html>"
    )


def export_manuscript_package(
    results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    bundle = build_manuscript_package(results, report_context=report_context)
    html_report = build_manuscript_package_html(bundle)

    markdown_path = output_root / "manuscript_package.md"
    html_path = output_root / "manuscript_package.html"
    manifest_path = output_root / "manuscript_package_manifest.json"
    cohort_table_path = output_root / "manuscript_table_cohorts.csv"
    internal_table_path = output_root / "manuscript_table_internal.csv"
    external_table_path = output_root / "manuscript_table_external.csv"
    pairwise_table_path = output_root / "manuscript_table_pairwise_auc_roc.csv"
    internal_figure_path = output_root / "manuscript_figure_internal_auc_roc.svg"
    external_figure_path = output_root / "manuscript_figure_external_auc_roc.svg"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    bundle["cohort_table"].to_csv(cohort_table_path, index=False)
    bundle["internal_table"].to_csv(internal_table_path, index=False)
    bundle["external_table"].to_csv(external_table_path, index=False)
    bundle["pairwise_table"].to_csv(pairwise_table_path, index=False)
    internal_figure_path.write_text(str(bundle.get("internal_figure_svg") or ""), encoding="utf-8")
    external_figure_path.write_text(str(bundle.get("external_figure_svg") or ""), encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "cohort_table_path": str(cohort_table_path),
        "internal_table_path": str(internal_table_path),
        "external_table_path": str(external_table_path),
        "pairwise_table_path": str(pairwise_table_path),
        "internal_figure_path": str(internal_figure_path),
        "external_figure_path": str(external_figure_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "manuscript_package_summary": bundle.get("summary"),
        "manuscript_package_markdown_path": str(markdown_path),
        "manuscript_package_html_path": str(html_path),
        "manuscript_package_manifest_path": str(manifest_path),
        "manuscript_table_cohorts_path": str(cohort_table_path),
        "manuscript_table_internal_path": str(internal_table_path),
        "manuscript_table_external_path": str(external_table_path),
        "manuscript_table_pairwise_path": str(pairwise_table_path),
        "manuscript_figure_internal_path": str(internal_figure_path),
        "manuscript_figure_external_path": str(external_figure_path),
    }
