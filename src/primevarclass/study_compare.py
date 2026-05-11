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


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Artefato nao encontrado: {path}")
    return pd.read_csv(path)


def load_study_result_bundle(result_dir: str) -> dict:
    root = Path(result_dir).resolve()
    training_metrics_path = root / "study_training_metrics.csv"
    external_evaluation_path = root / "study_external_evaluation.csv"
    pairwise_path = root / "study_external_pairwise.csv"
    summary_path = root / "study_summary_report.txt"
    return {
        "result_dir": str(root),
        "training_metrics_path": str(training_metrics_path),
        "external_evaluation_path": str(external_evaluation_path),
        "external_pairwise_path": str(pairwise_path),
        "study_summary_report_path": str(summary_path),
        "training_metrics": _load_csv(training_metrics_path),
        "external_evaluation": _load_csv(external_evaluation_path),
        "external_pairwise": pd.read_csv(pairwise_path) if pairwise_path.exists() else pd.DataFrame(),
        "study_summary_text": summary_path.read_text(encoding="utf-8") if summary_path.exists() else "",
    }


def summarize_best_internal(metrics_df: pd.DataFrame, primary_metric: str = "auc_roc") -> dict:
    if metrics_df.empty:
        return {
            "experiment": None,
            "feature_set": None,
            "model_family": None,
            "primary_metric_name": primary_metric,
            "primary_metric_value": np.nan,
            "auc_roc": np.nan,
            "auc_pr": np.nan,
            "mcc": np.nan,
        }
    metric_name = primary_metric if primary_metric in metrics_df.columns else "auc_roc"
    ranked = metrics_df.sort_values(
        [metric_name, "auc_pr", "mcc", "is_primary_experiment", "experiment"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    best_row = ranked.iloc[0]
    return {
        "experiment": str(best_row.get("experiment")),
        "feature_set": best_row.get("feature_set"),
        "model_family": best_row.get("model_family"),
        "primary_metric_name": metric_name,
        "primary_metric_value": _metric_value(best_row.get(metric_name)),
        "auc_roc": _metric_value(best_row.get("auc_roc")),
        "auc_pr": _metric_value(best_row.get("auc_pr")),
        "mcc": _metric_value(best_row.get("mcc")),
    }


def summarize_external_best(metrics_df: pd.DataFrame, primary_metric: str = "auc_roc") -> pd.DataFrame:
    if metrics_df.empty:
        return pd.DataFrame(
            columns=[
                "cohort",
                "experiment",
                "feature_set",
                "model_family",
                "primary_metric_name",
                "primary_metric_value",
                "auc_roc",
                "auc_pr",
                "mcc",
            ]
        )
    metric_name = primary_metric if primary_metric in metrics_df.columns else "auc_roc"
    subset = metrics_df.loc[metrics_df["evaluation_group"].astype(str) == "combined"].copy()
    if subset.empty:
        subset = metrics_df.copy()
    ranked = subset.sort_values(
        ["cohort", metric_name, "auc_pr", "mcc", "experiment"],
        ascending=[True, False, False, False, True],
    )
    top_rows = ranked.groupby("cohort", as_index=False).head(1).reset_index(drop=True)
    top_rows["primary_metric_name"] = metric_name
    top_rows["primary_metric_value"] = top_rows[metric_name].astype(float)
    return top_rows[
        ["cohort", "experiment", "feature_set", "model_family", "primary_metric_name", "primary_metric_value", "auc_roc", "auc_pr", "mcc"]
    ].copy()


def build_study_comparison(
    baseline_dir: str,
    candidate_dir: str,
    primary_metric: str = "auc_roc",
    report_title: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    baseline = load_study_result_bundle(baseline_dir)
    candidate = load_study_result_bundle(candidate_dir)

    baseline_internal = summarize_best_internal(baseline["training_metrics"], primary_metric=primary_metric)
    candidate_internal = summarize_best_internal(candidate["training_metrics"], primary_metric=primary_metric)

    internal_comparison = pd.DataFrame(
        [
            {
                "study_label": "baseline",
                "result_dir": baseline["result_dir"],
                **baseline_internal,
            },
            {
                "study_label": "candidate",
                "result_dir": candidate["result_dir"],
                **candidate_internal,
            },
        ]
    )
    internal_delta = {
        "primary_metric_name": candidate_internal["primary_metric_name"],
        "primary_metric_delta": candidate_internal["primary_metric_value"] - baseline_internal["primary_metric_value"],
        "auc_roc_delta": candidate_internal["auc_roc"] - baseline_internal["auc_roc"],
        "auc_pr_delta": candidate_internal["auc_pr"] - baseline_internal["auc_pr"],
        "mcc_delta": candidate_internal["mcc"] - baseline_internal["mcc"],
    }

    baseline_external = summarize_external_best(baseline["external_evaluation"], primary_metric=primary_metric).rename(
        columns={
            "experiment": "baseline_experiment",
            "feature_set": "baseline_feature_set",
            "model_family": "baseline_model_family",
            "primary_metric_value": "baseline_primary_metric_value",
            "auc_roc": "baseline_auc_roc",
            "auc_pr": "baseline_auc_pr",
            "mcc": "baseline_mcc",
        }
    )
    candidate_external = summarize_external_best(candidate["external_evaluation"], primary_metric=primary_metric).rename(
        columns={
            "experiment": "candidate_experiment",
            "feature_set": "candidate_feature_set",
            "model_family": "candidate_model_family",
            "primary_metric_value": "candidate_primary_metric_value",
            "auc_roc": "candidate_auc_roc",
            "auc_pr": "candidate_auc_pr",
            "mcc": "candidate_mcc",
        }
    )
    external_comparison = baseline_external.merge(candidate_external, on=["cohort", "primary_metric_name"], how="outer")
    if not external_comparison.empty:
        external_comparison["primary_metric_delta"] = external_comparison["candidate_primary_metric_value"] - external_comparison["baseline_primary_metric_value"]
        external_comparison["auc_roc_delta"] = external_comparison["candidate_auc_roc"] - external_comparison["baseline_auc_roc"]
        external_comparison["auc_pr_delta"] = external_comparison["candidate_auc_pr"] - external_comparison["baseline_auc_pr"]
        external_comparison["mcc_delta"] = external_comparison["candidate_mcc"] - external_comparison["baseline_mcc"]

    context = dict(report_context or {})
    title = report_title or context.get("report_title") or "PrimeVarClass Study Comparison"
    markdown_report = build_study_comparison_markdown(
        title=title,
        baseline_dir=baseline["result_dir"],
        candidate_dir=candidate["result_dir"],
        internal_comparison=internal_comparison,
        internal_delta=internal_delta,
        external_comparison=external_comparison,
        report_context=context,
    )
    html_report = build_study_comparison_html(markdown_report)
    return {
        "report_title": title,
        "generated_at": _now_utc(),
        "baseline_dir": baseline["result_dir"],
        "candidate_dir": candidate["result_dir"],
        "primary_metric": primary_metric,
        "internal_comparison": internal_comparison,
        "internal_delta": internal_delta,
        "external_comparison": external_comparison,
        "markdown_report": markdown_report,
        "html_report": html_report,
    }


def build_study_comparison_markdown(
    *,
    title: str,
    baseline_dir: str,
    candidate_dir: str,
    internal_comparison: pd.DataFrame,
    internal_delta: Dict[str, Any],
    external_comparison: pd.DataFrame,
    report_context: Dict[str, Any] | None = None,
) -> str:
    context = dict(report_context or {})
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Baseline study: {baseline_dir}",
        f"- Candidate study: {candidate_dir}",
    ]
    for key, label in [
        ("institution", "Institution"),
        ("team_name", "Team"),
        ("operator_name", "Operator"),
        ("comparison_purpose", "Purpose"),
    ]:
        value = context.get(key)
        if value:
            lines.append(f"- {label}: {value}")

    lines.extend(["", "## Internal Comparison", ""])
    for _, row in internal_comparison.iterrows():
        lines.append(
            f"- {row['study_label']}: {row.get('experiment')} "
            f"(primary={_metric_text(row.get('primary_metric_value'))}, "
            f"AUC-ROC={_metric_text(row.get('auc_roc'))}, "
            f"AUC-PR={_metric_text(row.get('auc_pr'))}, "
            f"MCC={_metric_text(row.get('mcc'))})"
        )
    lines.append(
        f"- Internal delta ({internal_delta.get('primary_metric_name')}): {_metric_text(internal_delta.get('primary_metric_delta'))}"
    )

    lines.extend(["", "## External Comparison", ""])
    if external_comparison.empty:
        lines.append("- Nenhuma comparacao externa disponivel.")
    else:
        for _, row in external_comparison.iterrows():
            lines.append(
                f"- {row['cohort']}: candidate={row.get('candidate_experiment')} vs baseline={row.get('baseline_experiment')} "
                f"(delta primary={_metric_text(row.get('primary_metric_delta'))}, "
                f"delta AUC-ROC={_metric_text(row.get('auc_roc_delta'))}, "
                f"delta AUC-PR={_metric_text(row.get('auc_pr_delta'))}, "
                f"delta MCC={_metric_text(row.get('mcc_delta'))})"
            )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Este comparativo resume a melhor configuracao interna e o melhor desempenho combinado por coorte externa em cada estudo.",
            "- Diferencas positivas favorecem o estudo candidato para a metrica considerada.",
        ]
    )
    return "\n".join(lines)


def build_study_comparison_html(markdown_report: str) -> str:
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
        "<title>PrimeVarClass Study Comparison</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6efe4;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#2d6f73;}ul{background:#fff;border:1px solid #e7decd;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(chunks)
        + "</body></html>"
    )


def export_study_comparison(
    comparison: dict,
    output_dir: str,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    internal_path = root / "study_comparison_internal.csv"
    external_path = root / "study_comparison_external.csv"
    markdown_path = root / "study_comparison_report.md"
    html_path = root / "study_comparison_report.html"
    manifest_path = root / "study_comparison_manifest.json"

    comparison["internal_comparison"].to_csv(internal_path, index=False)
    comparison["external_comparison"].to_csv(external_path, index=False)
    markdown_path.write_text(str(comparison["markdown_report"]), encoding="utf-8")
    html_path.write_text(str(comparison["html_report"]), encoding="utf-8")
    manifest = {
        "generated_at": comparison.get("generated_at"),
        "baseline_dir": comparison.get("baseline_dir"),
        "candidate_dir": comparison.get("candidate_dir"),
        "primary_metric": comparison.get("primary_metric"),
        "report_title": comparison.get("report_title"),
        "internal_delta": comparison.get("internal_delta"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "internal_comparison_path": str(internal_path),
        "external_comparison_path": str(external_path),
        "comparison_markdown_path": str(markdown_path),
        "comparison_html_path": str(html_path),
        "comparison_manifest_path": str(manifest_path),
    }
