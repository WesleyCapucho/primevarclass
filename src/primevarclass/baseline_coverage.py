from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


CORE_ABLATION_FEATURE_SETS = [
    "prime_only",
    "biochemical_only",
    "hybrid",
    "hybrid_plus_conservation",
    "hybrid_plus_conservation_structure",
    "hybrid_plus_external",
    "external_predictors_only",
]


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


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


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
        "status": _status_from_percent(normalized),
        "critical": bool(critical),
        "evidence": evidence,
        "next_step": next_step,
    }


def _feature_set_name(row: pd.Series) -> str:
    return str(row.get("feature_set") or row.get("experiment") or "")


def _is_prime_signal_feature(feature_set: str) -> bool:
    token = str(feature_set or "").strip().lower()
    return token.startswith("prime") or token.startswith("hybrid")


def build_baseline_coverage_assessment(results: dict) -> dict:
    study_design = results.get("study_design")
    baseline_experiment = str(getattr(study_design, "baseline_experiment", "external_predictors_only") or "external_predictors_only")
    training_metrics = results.get("training_metrics")
    external_pairwise = results.get("external_pairwise_comparisons")
    external_metrics = results.get("external_evaluation_metrics")

    training_df = training_metrics.copy() if isinstance(training_metrics, pd.DataFrame) else pd.DataFrame()
    pairwise_df = external_pairwise.copy() if isinstance(external_pairwise, pd.DataFrame) else pd.DataFrame()
    external_df = external_metrics.copy() if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()

    feature_rows: List[dict] = []
    feature_set_names = sorted({_feature_set_name(row) for _, row in training_df.iterrows() if _feature_set_name(row)})
    present_set = set(feature_set_names)
    for feature_set in CORE_ABLATION_FEATURE_SETS:
        feature_rows.append(
            {
                "feature_set": feature_set,
                "present_in_training": feature_set in present_set,
                "coverage_role": "core_ablation",
            }
        )
    for feature_set in feature_set_names:
        if feature_set not in CORE_ABLATION_FEATURE_SETS:
            feature_rows.append(
                {
                    "feature_set": feature_set,
                    "present_in_training": True,
                    "coverage_role": "additional",
                }
            )
    feature_coverage_df = pd.DataFrame(feature_rows)

    core_present = int(sum(1 for item in CORE_ABLATION_FEATURE_SETS if item in present_set))
    core_coverage_percent = int(round((core_present / len(CORE_ABLATION_FEATURE_SETS)) * 100)) if CORE_ABLATION_FEATURE_SETS else 0

    baseline_present_in_training = baseline_experiment in set(training_df["experiment"].astype(str)) if not training_df.empty and "experiment" in training_df.columns else False
    baseline_present_in_external = False
    if not pairwise_df.empty and "baseline_experiment" in pairwise_df.columns:
        baseline_present_in_external = baseline_experiment in set(pairwise_df["baseline_experiment"].astype(str))

    pairwise_auc_df = pairwise_df[pairwise_df["metric"].astype(str) == "auc_roc"].copy() if not pairwise_df.empty and "metric" in pairwise_df.columns else pd.DataFrame()
    pairwise_coverage_percent = 0
    if not external_df.empty and "cohort" in external_df.columns:
        external_cohorts = sorted(set(external_df["cohort"].astype(str)))
        pairwise_cohorts = sorted(set(pairwise_auc_df["cohort"].astype(str))) if not pairwise_auc_df.empty else []
        pairwise_coverage_percent = int(round((len(pairwise_cohorts) / len(external_cohorts)) * 100)) if external_cohorts else 0

    best_prime_delta = float("nan")
    best_prime_experiment = None
    supported_prime_delta = False
    prime_vs_baseline_rows = []
    if not pairwise_auc_df.empty:
        ranked = pairwise_auc_df.sort_values(
            ["cohort", "delta_mean", "ci_lower_95", "experiment"],
            ascending=[True, False, False, True],
        )
        for _, row in ranked.iterrows():
            experiment_name = str(row.get("experiment") or "")
            feature_set = experiment_name.split("__", 1)[0] if "__" in experiment_name else experiment_name
            if not _is_prime_signal_feature(feature_set):
                continue
            prime_vs_baseline_rows.append(
                {
                    "cohort": row.get("cohort"),
                    "experiment": experiment_name,
                    "baseline_experiment": row.get("baseline_experiment"),
                    "feature_set": feature_set,
                    "delta_mean": _safe_float(row.get("delta_mean")),
                    "ci_lower_95": _safe_float(row.get("ci_lower_95")),
                    "ci_upper_95": _safe_float(row.get("ci_upper_95")),
                    "supported_gain": bool(_safe_float(row.get("ci_lower_95")) > 0),
                }
            )
        if prime_vs_baseline_rows:
            prime_df = pd.DataFrame(prime_vs_baseline_rows).sort_values(
                ["delta_mean", "ci_lower_95", "experiment"],
                ascending=[False, False, True],
            )
            best_row = prime_df.iloc[0]
            best_prime_delta = _safe_float(best_row.get("delta_mean"))
            best_prime_experiment = str(best_row.get("experiment") or "")
            supported_prime_delta = bool(best_row.get("supported_gain"))
    prime_vs_baseline_df = pd.DataFrame(prime_vs_baseline_rows)

    criteria = [
        _criterion_row(
            "baseline_presence",
            "Declared baseline presence",
            1.2,
            int(round(np.mean([
                100 if baseline_present_in_training else 0,
                100 if baseline_present_in_external else 0,
            ]))),
            f"Baseline '{baseline_experiment}' {'esta' if baseline_present_in_training else 'nao esta'} no ranking interno e {'esta' if baseline_present_in_external else 'nao esta'} nas comparacoes externas.",
            "Garantir que o baseline declarado esteja presente no treino e nas comparacoes externas.",
            critical=True,
        ),
        _criterion_row(
            "core_ablation_coverage",
            "Core ablation coverage",
            1.1,
            core_coverage_percent,
            f"{core_present}/{len(CORE_ABLATION_FEATURE_SETS)} feature sets centrais de ablation estao presentes.",
            "Completar os feature sets centrais para sustentar a narrativa de ablation.",
            critical=True,
        ),
        _criterion_row(
            "pairwise_external_coverage",
            "Pairwise external coverage",
            1.0,
            pairwise_coverage_percent,
            f"{pairwise_coverage_percent}% das coortes externas possuem comparacao pareada AUC-ROC.",
            "Materializar comparacao pareada para todas as coortes externas do estudo.",
            critical=True,
        ),
        _criterion_row(
            "prime_signal_against_baseline",
            "Prime-signal vs baseline",
            1.3,
            100 if supported_prime_delta else (70 if not np.isnan(best_prime_delta) and best_prime_delta > 0 else 25),
            f"Melhor experimento com sinal primo/hibrido: {best_prime_experiment or '-'} com delta AUC-ROC={_fmt_metric(best_prime_delta)}.",
            "Buscar ganho consistente do bloco primo/hibrido contra o baseline declarado em dados reais.",
            critical=True,
        ),
    ]

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / total_weight)) if total_weight else 0

    markdown_lines = [
        "# Baseline and Ablation Coverage",
        "",
        f"- Generated at: {_now_utc()}",
        f"- Declared baseline: {baseline_experiment}",
        f"- Overall coverage: {overall_percent}%",
        "",
        "## Criteria",
        "",
    ]
    for item in criteria:
        markdown_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Score: {item['score_percent']}%",
                f"- Status: {item['status']}",
                f"- Evidence: {item['evidence']}",
                f"- Next step: {item['next_step']}",
                "",
            ]
        )

    markdown_lines.extend(["## Feature-set Coverage", ""])
    for _, row in feature_coverage_df.iterrows():
        markdown_lines.append(
            f"- {row['feature_set']}: {'present' if row['present_in_training'] else 'missing'} ({row['coverage_role']})"
        )

    markdown_lines.extend(["", "## Prime vs Baseline", ""])
    if prime_vs_baseline_df.empty:
        markdown_lines.append("- Nenhuma comparacao prime/hibrido vs baseline disponivel.")
    else:
        for _, row in prime_vs_baseline_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort']}: {row['experiment']} vs {row['baseline_experiment']} "
                f"=> delta={_fmt_metric(row['delta_mean'])} [{_fmt_metric(row['ci_lower_95'])}, {_fmt_metric(row['ci_upper_95'])}]"
            )

    return {
        "summary": {
            "generated_at": _now_utc(),
            "baseline_experiment": baseline_experiment,
            "overall_coverage_percent": overall_percent,
            "overall_status": _status_from_percent(overall_percent),
            "core_ablation_coverage_percent": core_coverage_percent,
            "pairwise_external_coverage_percent": pairwise_coverage_percent,
            "best_prime_experiment": best_prime_experiment,
            "best_prime_delta_auc_roc": best_prime_delta,
            "supported_prime_delta": supported_prime_delta,
        },
        "criteria": criteria,
        "feature_coverage": feature_coverage_df.to_dict(orient="records"),
        "prime_vs_baseline": prime_vs_baseline_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_baseline_coverage_html(assessment: dict) -> str:
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
        "<title>PrimeVarClass Baseline Coverage</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f0e7;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}h3{margin-top:1.3rem;color:#2d6f73;}ul{background:#fff;border:1px solid #eadfce;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_baseline_coverage_assessment(results: dict, output_dir: str) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    assessment = build_baseline_coverage_assessment(results)
    html_report = build_baseline_coverage_html(assessment)

    criteria_df = pd.DataFrame(assessment.get("criteria") or [])
    feature_df = pd.DataFrame(assessment.get("feature_coverage") or [])
    prime_df = pd.DataFrame(assessment.get("prime_vs_baseline") or [])

    markdown_path = root / "baseline_coverage_report.md"
    html_path = root / "baseline_coverage_report.html"
    manifest_path = root / "baseline_coverage_manifest.json"
    criteria_path = root / "baseline_coverage_criteria.csv"
    feature_path = root / "baseline_coverage_feature_sets.csv"
    prime_path = root / "baseline_coverage_prime_vs_baseline.csv"

    markdown_path.write_text(str(assessment.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    feature_df.to_csv(feature_path, index=False)
    prime_df.to_csv(prime_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": assessment.get("summary"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "feature_path": str(feature_path),
        "prime_path": str(prime_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "baseline_coverage_assessment": assessment,
        "baseline_coverage_report_markdown_path": str(markdown_path),
        "baseline_coverage_report_html_path": str(html_path),
        "baseline_coverage_manifest_path": str(manifest_path),
        "baseline_coverage_criteria_path": str(criteria_path),
        "baseline_coverage_feature_sets_path": str(feature_path),
        "baseline_coverage_prime_vs_baseline_path": str(prime_path),
    }
