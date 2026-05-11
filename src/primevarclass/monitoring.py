from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .study_compare import load_study_result_bundle


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _metric_value(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _metric_text(value: Any) -> str:
    numeric = _metric_value(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.4f}"


def _load_study_release_row(result_dir: str, primary_metric: str = "auc_roc") -> dict:
    root = Path(result_dir).resolve()
    manifest_path = root / "study_release_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "result_dir": str(root),
            "study_name": payload.get("study_name"),
            "release_id": payload.get("release_id"),
            "generated_at": payload.get("generated_at"),
            "primary_metric": payload.get("primary_metric") or primary_metric,
            "top_internal_experiment": payload.get("top_internal_experiment"),
            "internal_primary_metric": _metric_value(payload.get("internal_primary_metric")),
            "internal_auc_roc": _metric_value(payload.get("internal_auc_roc")),
            "internal_auc_pr": _metric_value(payload.get("internal_auc_pr")),
            "internal_mcc": _metric_value(payload.get("internal_mcc")),
            "top_external_experiment": payload.get("top_external_experiment"),
            "mean_external_primary_metric": _metric_value(payload.get("mean_external_primary_metric")),
            "mean_external_auc_roc": _metric_value(payload.get("mean_external_auc_roc")),
            "mean_external_auc_pr": _metric_value(payload.get("mean_external_auc_pr")),
            "mean_external_mcc": _metric_value(payload.get("mean_external_mcc")),
            "study_summary_report_path": payload.get("study_summary_report_path"),
            "scientific_dossier_markdown_path": payload.get("scientific_dossier_markdown_path"),
            "scientific_dossier_html_path": payload.get("scientific_dossier_html_path"),
        }

    bundle = load_study_result_bundle(str(root))
    training_metrics = bundle["training_metrics"]
    metric_name = primary_metric if primary_metric in training_metrics.columns else "auc_roc"
    if training_metrics.empty:
        internal = {
            "top_internal_experiment": None,
            "internal_primary_metric": np.nan,
            "internal_auc_roc": np.nan,
            "internal_auc_pr": np.nan,
            "internal_mcc": np.nan,
        }
    else:
        best_row = training_metrics.sort_values(
            [metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
            ascending=[False, False, False, False, True],
        ).iloc[0]
        internal = {
            "top_internal_experiment": best_row.get("experiment"),
            "internal_primary_metric": _metric_value(best_row.get(metric_name)),
            "internal_auc_roc": _metric_value(best_row.get("auc_roc")),
            "internal_auc_pr": _metric_value(best_row.get("auc_pr")),
            "internal_mcc": _metric_value(best_row.get("mcc")),
        }

    external = bundle["external_evaluation"]
    if external.empty:
        external_summary = {
            "top_external_experiment": None,
            "mean_external_primary_metric": np.nan,
            "mean_external_auc_roc": np.nan,
            "mean_external_auc_pr": np.nan,
            "mean_external_mcc": np.nan,
        }
    else:
        subset = external.loc[external["evaluation_group"].astype(str) == "combined"].copy()
        if subset.empty:
            subset = external.copy()
        top_per_cohort = subset.sort_values(
            ["cohort", metric_name, "auc_pr", "mcc", "experiment"],
            ascending=[True, False, False, False, True],
        ).groupby("cohort", as_index=False).head(1)
        overall = subset.sort_values([metric_name, "auc_pr", "mcc", "experiment"], ascending=[False, False, False, True]).iloc[0]
        external_summary = {
            "top_external_experiment": overall.get("experiment"),
            "mean_external_primary_metric": float(top_per_cohort[metric_name].mean()),
            "mean_external_auc_roc": float(top_per_cohort["auc_roc"].mean()) if "auc_roc" in top_per_cohort.columns else np.nan,
            "mean_external_auc_pr": float(top_per_cohort["auc_pr"].mean()) if "auc_pr" in top_per_cohort.columns else np.nan,
            "mean_external_mcc": float(top_per_cohort["mcc"].mean()) if "mcc" in top_per_cohort.columns else np.nan,
        }

    return {
        "result_dir": str(root),
        "study_name": root.name,
        "release_id": root.name,
        "generated_at": _now_utc(),
        "primary_metric": metric_name,
        **internal,
        **external_summary,
        "study_summary_report_path": bundle.get("study_summary_report_path"),
        "scientific_dossier_markdown_path": str(root / "study_scientific_dossier.md") if (root / "study_scientific_dossier.md").exists() else None,
        "scientific_dossier_html_path": str(root / "study_scientific_dossier.html") if (root / "study_scientific_dossier.html").exists() else None,
    }


def build_longitudinal_study_monitor(
    study_dirs: List[str],
    primary_metric: str = "auc_roc",
    report_title: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    if not study_dirs:
        raise ValueError("Informe ao menos um diretorio de estudo para monitoramento longitudinal.")
    rows = [_load_study_release_row(result_dir=item, primary_metric=primary_metric) for item in study_dirs]
    timeline = pd.DataFrame(rows)
    timeline = timeline.sort_values(["generated_at", "release_id"], ascending=[True, True]).reset_index(drop=True)
    timeline["internal_primary_metric_delta_vs_previous"] = timeline["internal_primary_metric"].diff()
    timeline["mean_external_primary_metric_delta_vs_previous"] = timeline["mean_external_primary_metric"].diff()
    timeline["version_rank"] = range(1, len(timeline) + 1)

    latest = timeline.iloc[-1].to_dict()
    previous = timeline.iloc[-2].to_dict() if len(timeline) > 1 else None
    summary = {
        "n_versions": int(len(timeline)),
        "latest_release_id": latest.get("release_id"),
        "latest_study_name": latest.get("study_name"),
        "latest_internal_primary_metric": _metric_value(latest.get("internal_primary_metric")),
        "latest_mean_external_primary_metric": _metric_value(latest.get("mean_external_primary_metric")),
        "delta_internal_vs_previous": _metric_value(latest.get("internal_primary_metric_delta_vs_previous")),
        "delta_external_vs_previous": _metric_value(latest.get("mean_external_primary_metric_delta_vs_previous")),
        "previous_release_id": previous.get("release_id") if previous else None,
    }

    context = dict(report_context or {})
    title = report_title or context.get("report_title") or "PrimeVarClass Longitudinal Monitor"
    markdown_report = build_longitudinal_markdown(title=title, timeline=timeline, summary=summary, report_context=context)
    html_report = build_longitudinal_html(markdown_report)
    return {
        "report_title": title,
        "generated_at": _now_utc(),
        "primary_metric": primary_metric,
        "summary": summary,
        "timeline": timeline,
        "markdown_report": markdown_report,
        "html_report": html_report,
    }


def build_longitudinal_markdown(
    *,
    title: str,
    timeline: pd.DataFrame,
    summary: Dict[str, Any],
    report_context: Dict[str, Any] | None = None,
) -> str:
    context = dict(report_context or {})
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_utc()}",
    ]
    for key, label in [
        ("institution", "Institution"),
        ("team_name", "Team"),
        ("operator_name", "Operator"),
        ("monitoring_purpose", "Purpose"),
    ]:
        value = context.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Versions tracked: {summary.get('n_versions')}",
            f"- Latest release: {summary.get('latest_release_id')}",
            f"- Latest internal metric: {_metric_text(summary.get('latest_internal_primary_metric'))}",
            f"- Latest mean external metric: {_metric_text(summary.get('latest_mean_external_primary_metric'))}",
            f"- Delta internal vs previous: {_metric_text(summary.get('delta_internal_vs_previous'))}",
            f"- Delta external vs previous: {_metric_text(summary.get('delta_external_vs_previous'))}",
            "",
            "## Timeline",
            "",
        ]
    )
    for _, row in timeline.iterrows():
        lines.append(
            f"- v{int(row.get('version_rank', 0))} {row.get('release_id')}: "
            f"internal={_metric_text(row.get('internal_primary_metric'))}, "
            f"external={_metric_text(row.get('mean_external_primary_metric'))}, "
            f"top_internal={row.get('top_internal_experiment')}, "
            f"top_external={row.get('top_external_experiment')}"
        )
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Este monitor resume a evolucao das melhores metricas internas e externas entre releases do estudo.",
            "- Deltas positivos sugerem ganho em relacao a versao anterior para a metrica primaria acompanhada.",
        ]
    )
    return "\n".join(lines)


def build_longitudinal_html(markdown_report: str) -> str:
    chunks = []
    for block in markdown_report.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            chunks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            chunks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            chunks.append(f"<ul>{items}</ul>")
            continue
        chunks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Longitudinal Monitor</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f1e8;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#2d6f73;}ul{background:#fff;border:1px solid #e7decd;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(chunks)
        + "</body></html>"
    )


def export_longitudinal_study_monitor(monitor: dict, output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    timeline_path = root / "study_longitudinal_timeline.csv"
    markdown_path = root / "study_longitudinal_report.md"
    html_path = root / "study_longitudinal_report.html"
    manifest_path = root / "study_longitudinal_manifest.json"
    monitor["timeline"].to_csv(timeline_path, index=False)
    markdown_path.write_text(str(monitor["markdown_report"]), encoding="utf-8")
    html_path.write_text(str(monitor["html_report"]), encoding="utf-8")
    manifest = {
        "generated_at": monitor.get("generated_at"),
        "report_title": monitor.get("report_title"),
        "primary_metric": monitor.get("primary_metric"),
        "summary": monitor.get("summary"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "timeline_path": str(timeline_path),
        "longitudinal_markdown_path": str(markdown_path),
        "longitudinal_html_path": str(html_path),
        "longitudinal_manifest_path": str(manifest_path),
    }
