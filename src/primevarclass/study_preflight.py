from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .cohort_validation import build_cohort_independence_assessment
from .core import prepare_training_dataframe
from .data_sources import ingest_sources_from_config
from .study import StudyDesign, load_study_design


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


def _fmt_percent(value: Any) -> str:
    numeric = _safe_float(value)
    if np.isnan(numeric):
        return "-"
    return f"{numeric:.0f}%"


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _resolve_source_config_path(study_config_path: str, source_config: str) -> Path:
    candidate = Path(source_config)
    if candidate.is_absolute():
        return candidate.resolve()
    root_relative = (Path.cwd() / candidate).resolve()
    if root_relative.exists():
        return root_relative
    return (Path(study_config_path).resolve().parent / candidate).resolve()


def _resolve_cohort_mode(study: StudyDesign, cohort: Any) -> str:
    return str(getattr(cohort, "mode", None) or study.mode)


def _resolve_cohort_high_confidence(study: StudyDesign, cohort: Any) -> bool:
    cohort_value = getattr(cohort, "high_confidence_only", None)
    return bool(study.high_confidence_only if cohort_value is None else cohort_value)


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


def build_study_preflight(
    config_path: str,
    output_dir: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    study = load_study_design(config_path)
    context = dict(report_context or {})
    title = str(context.get("report_title") or f"{study.name} - Study Preflight")

    train_count = sum(1 for cohort in study.cohorts or [] if cohort.role == "train")
    external_count = sum(1 for cohort in study.cohorts or [] if cohort.role != "train")

    cohort_rows: List[dict] = []
    cohort_tables_for_validation: List[dict] = []
    warnings: List[str] = []

    output_root = Path(output_dir).resolve() if output_dir else None
    if output_root is not None:
        output_root.mkdir(parents=True, exist_ok=True)

    for cohort in study.cohorts or []:
        resolved_source_config = _resolve_source_config_path(config_path, cohort.source_config)
        source_config_exists = resolved_source_config.exists()

        if not source_config_exists:
            warnings.append(f"Coorte {cohort.name}: source_config nao encontrado em {resolved_source_config}.")
            cohort_rows.append(
                {
                    "cohort_name": cohort.name,
                    "role": cohort.role,
                    "source_config": cohort.source_config,
                    "resolved_source_config": str(resolved_source_config),
                    "source_config_exists": False,
                    "integrated_rows": 0,
                    "valid_rows": 0,
                    "n_classes": 0,
                    "public_catalog_readiness_percent": 0,
                    "release_coverage_percent": 0,
                    "schema_coverage_percent": 0,
                    "sync_candidates": 0,
                    "automatable_sources": 0,
                    "semi_automatable_sources": 0,
                    "manual_sources": 0,
                    "cohort_ready": False,
                    "warning": "source_config_not_found",
                }
            )
            continue

        ingestion_output_dir = None
        if output_root is not None:
            ingestion_output_dir = output_root / "cohorts" / f"{cohort.name.lower().replace(' ', '_')}_preflight"

        ingestion = ingest_sources_from_config(
            config_path=str(resolved_source_config),
            output_dir=str(ingestion_output_dir) if ingestion_output_dir is not None else None,
        )
        built_df, build_report = prepare_training_dataframe(
            raw_df=ingestion["integrated_dataframe"],
            mode=_resolve_cohort_mode(study, cohort),
            keep_metadata=study.keep_metadata,
            high_confidence_only=_resolve_cohort_high_confidence(study, cohort),
        )

        public_summary = dict((ingestion.get("public_source_assessment") or {}).get("summary") or {})
        sync_summary = dict((ingestion.get("public_source_sync_plan") or {}).get("summary") or {})
        n_classes = int(built_df["label"].nunique()) if "label" in built_df.columns and not built_df.empty else 0
        cohort_ready = bool(build_report.valid_rows > 0 and n_classes >= 2)
        if not cohort_ready:
            warnings.append(f"Coorte {cohort.name}: dataset curado sem diversidade de classes suficiente ou sem linhas validas.")

        cohort_tables_for_validation.append(
            {
                "cohort_name": cohort.name,
                "role": cohort.role,
                "dataframe": built_df,
            }
        )

        cohort_rows.append(
            {
                "cohort_name": cohort.name,
                "role": cohort.role,
                "source_config": cohort.source_config,
                "resolved_source_config": str(resolved_source_config),
                "source_config_exists": True,
                "integrated_rows": int(len(ingestion["integrated_dataframe"])),
                "valid_rows": int(build_report.valid_rows),
                "n_classes": n_classes,
                "prime_mode": _resolve_cohort_mode(study, cohort),
                "public_catalog_readiness_percent": int(public_summary.get("overall_readiness_percent", 0) or 0),
                "release_coverage_percent": int(public_summary.get("release_coverage_percent", 0) or 0),
                "schema_coverage_percent": int(public_summary.get("schema_coverage_percent", 0) or 0),
                "sync_candidates": int(sync_summary.get("n_sync_candidates", 0) or 0),
                "automatable_sources": int(sync_summary.get("n_automatable_sources", 0) or 0),
                "semi_automatable_sources": int(sync_summary.get("n_semi_automatable_sources", 0) or 0),
                "manual_sources": int(sync_summary.get("n_manual_sources", 0) or 0),
                "cohort_ready": cohort_ready,
                "warning": "",
            }
        )

    cohorts_df = pd.DataFrame(cohort_rows)
    independence_assessment = build_cohort_independence_assessment(cohort_tables_for_validation)
    independence_summary = dict(independence_assessment.get("summary") or {})
    for gap in independence_assessment.get("critical_gaps") or []:
        warnings.append(f"Independencia entre coortes: {gap}.")

    source_configs_ready = int(round(cohorts_df["source_config_exists"].mean() * 100)) if not cohorts_df.empty else 0
    cohort_validity_ready = int(round(cohorts_df["valid_rows"].gt(0).mean() * 100)) if not cohorts_df.empty else 0
    class_diversity_ready = int(round(cohorts_df["n_classes"].ge(2).mean() * 100)) if not cohorts_df.empty else 0
    public_catalog_ready = int(round(cohorts_df["public_catalog_readiness_percent"].mean())) if not cohorts_df.empty else 0

    automation_scores = []
    for _, row in cohorts_df.iterrows():
        total = int(row.get("sync_candidates", 0) or 0)
        if total <= 0:
            automation_scores.append(0)
            continue
        automatable = int(row.get("automatable_sources", 0) or 0)
        semi = int(row.get("semi_automatable_sources", 0) or 0)
        manual = int(row.get("manual_sources", 0) or 0)
        score = ((automatable * 100) + (semi * 60) + (manual * 30)) / total
        automation_scores.append(score)
    sync_automation_ready = int(round(float(np.mean(automation_scores)))) if automation_scores else 0

    design_ready = int(round(np.mean([
        100 if train_count == 1 else 0,
        100 if external_count >= 1 else 0,
    ])))

    criteria = [
        _criterion_row(
            "study_design",
            "Study design structure",
            1.1,
            design_ready,
            f"{train_count} coorte(s) de treino e {external_count} coorte(s) externas declaradas.",
            "Garantir exatamente uma coorte train e pelo menos uma coorte externa.",
            critical=True,
        ),
        _criterion_row(
            "source_configs",
            "Source config resolution",
            1.0,
            source_configs_ready,
            f"{source_configs_ready}% das coortes tiveram source_config resolvido com sucesso.",
            "Corrigir caminhos TOML e padronizar referencias relativas das coortes.",
            critical=True,
        ),
        _criterion_row(
            "cohort_validity",
            "Curated cohort validity",
            1.0,
            cohort_validity_ready,
            f"{cohort_validity_ready}% das coortes produziram linhas validas apos curadoria.",
            "Revisar filtros, colunas obrigatorias e labels das coortes com zero linhas validas.",
            critical=True,
        ),
        _criterion_row(
            "class_diversity",
            "Label diversity",
            0.95,
            class_diversity_ready,
            f"{class_diversity_ready}% das coortes ficaram com pelo menos duas classes apos curadoria.",
            "Assegurar rotulos positivos e negativos suficientes para treino e validacao.",
            critical=True,
        ),
        _criterion_row(
            "cohort_independence",
            "Cohort independence",
            1.2,
            int(independence_summary.get("overall_independence_percent") or 0),
            (
                f"Max overlap treino/externo={int(independence_summary.get('max_variant_overlap_percent') or 0)}% e "
                f"label-conflict pairs={int(independence_summary.get('label_conflict_pair_rate_percent') or 0)}%."
            ),
            "Remover sobreposicoes entre treino e validacao externa antes da rodada final.",
            critical=True,
        ),
        _criterion_row(
            "public_traceability",
            "Public-source traceability",
            1.15,
            public_catalog_ready,
            f"Readiness media de catalogo publico = {public_catalog_ready}%.",
            "Elevar release/schema coverage dos catalogos publicos usados no estudo.",
            critical=True,
        ),
        _criterion_row(
            "sync_automation",
            "Sync automation readiness",
            0.85,
            sync_automation_ready,
            f"Readiness media de automacao/sync = {sync_automation_ready}%.",
            "Aumentar staging automatizado das fontes mais criticas antes da rodada final.",
        ),
    ]

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_preflight_percent = int(round(weighted_score / total_weight)) if total_weight else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]
    ready_to_run = bool(overall_preflight_percent >= 80 and not critical_gaps)

    summary = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study.name,
        "overall_preflight_percent": overall_preflight_percent,
        "overall_status": _status_from_percent(overall_preflight_percent),
        "ready_to_run": ready_to_run,
        "n_cohorts": int(len(cohorts_df)),
        "n_train_cohorts": int(train_count),
        "n_external_cohorts": int(external_count),
        "cohort_independence_percent": int(independence_summary.get("overall_independence_percent") or 0),
        "n_critical_gaps": int(len(critical_gaps)),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Overall preflight: {summary['overall_preflight_percent']}%",
        f"- Ready to run benchmark: {'yes' if ready_to_run else 'not yet'}",
        f"- Cohorts: {summary['n_cohorts']} total / {summary['n_train_cohorts']} train / {summary['n_external_cohorts']} external",
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
                f"- Critical: {'yes' if item['critical'] else 'no'}",
                f"- Evidence: {item['evidence']}",
                f"- Next step: {item['next_step']}",
                "",
            ]
        )

    markdown_lines.extend(["## Cohort Diagnostics", ""])
    if cohorts_df.empty:
        markdown_lines.append("- Nenhuma coorte foi avaliada no preflight.")
    else:
        for _, row in cohorts_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort_name']} ({row['role']}): valid_rows={int(row['valid_rows'])}, "
                f"classes={int(row['n_classes'])}, public={int(row['public_catalog_readiness_percent'])}%, "
                f"sync={int(row['automatable_sources'])}/{int(row['sync_candidates'])} automatable."
            )

    markdown_lines.extend(["", "## Warnings", ""])
    if warnings:
        for warning in sorted(set(warnings)):
            markdown_lines.append(f"- {warning}")
    else:
        markdown_lines.append("- Nenhum alerta critico identificado no preflight.")

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- O estudo parece pronto para a execucao benchmark.")

    return {
        "summary": summary,
        "criteria": criteria,
        "cohorts": cohorts_df.to_dict(orient="records"),
        "cohort_independence": independence_assessment,
        "warnings": sorted(set(warnings)),
        "recommended_actions": recommended_actions,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_study_preflight_html(preflight: dict) -> str:
    markdown = str(preflight.get("markdown_report") or "")
    chunks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            chunks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            chunks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            chunks.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            chunks.append(f"<ul>{items}</ul>")
            continue
        chunks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Study Preflight</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f3eb;color:#17242f;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8b4b2a;}h3{margin-top:1.4rem;color:#2d6f73;}"
        "ul{background:#fff;border:1px solid #eadfcf;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(chunks)
        + "</body></html>"
    )


def export_study_preflight(
    config_path: str,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    preflight = build_study_preflight(config_path=config_path, output_dir=str(root), report_context=report_context)
    html_report = build_study_preflight_html(preflight)
    criteria_df = pd.DataFrame(preflight.get("criteria") or [])
    cohorts_df = pd.DataFrame(preflight.get("cohorts") or [])
    independence_pairs_df = pd.DataFrame((preflight.get("cohort_independence") or {}).get("pairwise_audit") or [])

    markdown_path = root / "study_preflight_report.md"
    html_path = root / "study_preflight_report.html"
    manifest_path = root / "study_preflight_manifest.json"
    criteria_path = root / "study_preflight_criteria.csv"
    cohorts_path = root / "study_preflight_cohorts.csv"
    independence_pairs_path = root / "study_preflight_independence_pairs.csv"

    markdown_path.write_text(str(preflight.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(html_report, encoding="utf-8")
    criteria_df.to_csv(criteria_path, index=False)
    cohorts_df.to_csv(cohorts_path, index=False)
    independence_pairs_df.to_csv(independence_pairs_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": preflight.get("summary"),
        "warnings": preflight.get("warnings"),
        "recommended_actions": preflight.get("recommended_actions"),
        "report_context": preflight.get("report_context"),
        "cohort_independence_summary": (preflight.get("cohort_independence") or {}).get("summary"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "cohorts_path": str(cohorts_path),
        "independence_pairs_path": str(independence_pairs_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "preflight": preflight,
        "study_preflight_report_markdown_path": str(markdown_path),
        "study_preflight_report_html_path": str(html_path),
        "study_preflight_manifest_path": str(manifest_path),
        "study_preflight_criteria_path": str(criteria_path),
        "study_preflight_cohorts_path": str(cohorts_path),
        "study_preflight_independence_pairs_path": str(independence_pairs_path),
    }
