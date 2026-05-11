from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _artifact_exists(path: Any) -> bool:
    if not path:
        return False
    try:
        return Path(str(path)).exists()
    except Exception:
        return False


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _criterion(
    criterion_id: str,
    title: str,
    weight: float,
    score_percent: int,
    evidence: str,
    next_step: str,
    critical: bool = False,
) -> dict:
    score = max(0, min(100, int(score_percent)))
    return {
        "criterion_id": criterion_id,
        "title": title,
        "weight": float(weight),
        "score_percent": score,
        "status": _status_from_percent(score),
        "critical": bool(critical),
        "evidence": evidence,
        "next_step": next_step,
    }


def build_study_execution_board(
    *,
    public_resolution: dict,
    preflight_export: dict,
    study_results: dict,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    resolution_summary = dict(public_resolution.get("summary") or {})
    preflight = dict(preflight_export.get("preflight") or {})
    preflight_summary = dict(preflight.get("summary") or {})
    readiness_assessment = dict(study_results.get("publication_readiness_assessment") or {})
    readiness_summary = dict(readiness_assessment.get("summary") or {})
    readiness_criteria = list(readiness_assessment.get("criteria") or [])
    readiness_index = {str(item.get("criterion_id") or ""): dict(item) for item in readiness_criteria}
    independence_summary = dict((study_results.get("cohort_independence_assessment") or {}).get("summary") or {})
    cohort_freeze_summary = dict(study_results.get("study_cohort_freeze_summary") or {})
    claim_summary = dict((study_results.get("claim_strength_assessment") or {}).get("summary") or {})
    validation_summary = dict((study_results.get("study_validation_lock") or {}).get("summary") or {})
    baseline_summary = dict((study_results.get("baseline_coverage_assessment") or {}).get("summary") or {})
    methods_summary = dict(study_results.get("methods_package_summary") or {})
    manuscript_summary = dict(study_results.get("manuscript_package_summary") or {})

    title = str(context.get("report_title") or f"{resolution_summary.get('config_path', 'PrimeVarClass')} - Study Execution Board")

    comparative_strength = int((readiness_index.get("comparative_evidence") or {}).get("score_percent") or 0)
    operational_artifacts = [
        study_results.get("model_paths", {}).get("registry"),
        study_results.get("study_release_manifest_path"),
        study_results.get("scientific_dossier_markdown_path"),
        study_results.get("comparative_evidence_manifest_path"),
        study_results.get("claim_strength_manifest_path"),
        study_results.get("methods_package_manifest_path"),
        study_results.get("manuscript_package_manifest_path"),
        study_results.get("study_validation_lock_manifest_path"),
    ]
    operational_package_score = int(round(sum(1 for item in operational_artifacts if _artifact_exists(item)) / len(operational_artifacts) * 100)) if operational_artifacts else 0

    translational_inputs = [
        operational_package_score,
        int(readiness_summary.get("overall_readiness_percent") or 0),
        int(baseline_summary.get("overall_coverage_percent") or 0),
    ]
    translational_score = int(round(sum(translational_inputs) / len(translational_inputs))) if translational_inputs else 0

    criteria = [
        _criterion(
            "resolved_public_inputs",
            "Resolved public inputs",
            1.15,
            int(resolution_summary.get("overall_resolution_percent") or 0),
            (
                f"{resolution_summary.get('n_ready_cohorts', 0)}/{resolution_summary.get('n_cohorts', 0)} coortes prontas "
                f"e {resolution_summary.get('n_live_public_ready_cohorts', 0)} com fontes publicas totalmente resolvidas. "
                f"Handoff={int(resolution_summary.get('real_data_handoff_percent') or 0)}% com "
                f"{int(resolution_summary.get('n_real_data_tasks') or 0)} tarefa(s) abertas."
            ),
            "Concluir a resolucao das coortes e garantir staging/referencias congeladas para as fontes publicas.",
            critical=True,
        ),
        _criterion(
            "resolved_preflight",
            "Resolved study preflight",
            1.05,
            int(preflight_summary.get("overall_preflight_percent") or 0),
            (
                f"Preflight do estudo resolvido em {preflight_summary.get('overall_preflight_percent', 0)}% "
                f"com {preflight_summary.get('n_critical_gaps', 0)} gaps criticos."
            ),
            "Subir o preflight do estudo resolvido ate um estado sem gaps criticos antes da rodada final.",
            critical=True,
        ),
        _criterion(
            "cohort_independence",
            "Cohort independence",
            1.0,
            int(independence_summary.get("overall_independence_percent") or 0),
            (
                f"Independencia entre coortes em {int(independence_summary.get('overall_independence_percent') or 0)}% "
                f"com max overlap treino/externo de {int(independence_summary.get('max_variant_overlap_percent') or 0)}%."
            ),
            "Garantir independencia forte entre treino e validacao externa antes da rodada final.",
            critical=True,
        ),
        _criterion(
            "real_data_freeze",
            "Real-data cohort freeze",
            1.15,
            int(cohort_freeze_summary.get("overall_real_data_readiness_percent") or 0),
            (
                f"Freeze real em {int(cohort_freeze_summary.get('overall_real_data_readiness_percent') or 0)}% "
                f"com {int(cohort_freeze_summary.get('n_example_blocked_cohorts') or 0)} coorte(s) ainda presas a demo/example."
            ),
            "Congelar as coortes finais com dados reais versionados antes da rodada definitiva.",
            critical=True,
        ),
        _criterion(
            "submission_evidence",
            "Submission evidence package",
            1.35,
            int(readiness_summary.get("overall_readiness_percent") or 0),
            (
                f"Publication readiness em {readiness_summary.get('overall_readiness_percent', 0)}% "
                f"com status {readiness_summary.get('overall_status') or '-'}."
            ),
            "Fechar o publication readiness com resultados em coortes reais e manifests finais de submissao.",
            critical=True,
        ),
        _criterion(
            "comparative_strength",
            "Comparative evidence strength",
            1.3,
            comparative_strength,
            (
                f"O criterio comparative_evidence do publication readiness marcou {comparative_strength}% "
                f"contra o baseline declarado."
            ),
            "Buscar ganho consistente e estatisticamente defendivel contra os baselines em dados reais.",
            critical=True,
        ),
        _criterion(
            "claim_strength",
            "Claim strength",
            1.2,
            int(claim_summary.get("overall_claim_strength_percent") or 0),
            (
                f"Claim tier {claim_summary.get('claim_tier') or '-'} em "
                f"{int(claim_summary.get('overall_claim_strength_percent') or 0)}%."
            ),
            "Elevar a forca da alegacao cientifica antes da rodada final de submissao.",
            critical=True,
        ),
        _criterion(
            "baseline_ablation",
            "Baseline and ablation coverage",
            0.95,
            int(baseline_summary.get("overall_coverage_percent") or 0),
            (
                f"Coverage de baseline/ablation em {baseline_summary.get('overall_coverage_percent', 0)}% "
                f"com melhor experimento primo {baseline_summary.get('best_prime_experiment') or '-'}."
            ),
            "Preservar a comparacao completa de feature sets e baselines no pacote final do paper.",
        ),
        _criterion(
            "operational_package",
            "Operational package completeness",
            0.85,
            operational_package_score,
            (
                f"{operational_package_score}% dos artefatos operacionais centrais estao presentes "
                f"(registry, dossier, methods, manuscript, release manifest)."
            ),
            "Assegurar que o pacote operacional acompanhe cada benchmark final e release de estudo.",
        ),
        _criterion(
            "translational_readiness",
            "Translational readiness",
            0.9,
            translational_score,
            (
                f"Score translacional agregado em {translational_score}% com melhor experimento externo "
                f"{manuscript_summary.get('best_external_experiment') or '-'}."
            ),
            "Usar o benchmark final para sustentar piloto de laboratorio e narrativa de impacto translacional.",
        ),
        _criterion(
            "validation_lock",
            "Validation lock status",
            1.0,
            int(validation_summary.get("overall_validation_lock_percent") or 0),
            (
                f"Validation lock em {int(validation_summary.get('overall_validation_lock_percent') or 0)}% "
                f"com submission lock {'yes' if validation_summary.get('ready_for_submission_lock') else 'not yet'}."
            ),
            "Consolidar os locks cientificos ate um estado pronto para submissao.",
            critical=True,
        ),
    ]

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_execution_percent = int(round(weighted_score / total_weight)) if total_weight else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]

    summary = {
        "title": title,
        "generated_at": _now_utc(),
        "overall_execution_percent": overall_execution_percent,
        "overall_status": _status_from_percent(overall_execution_percent),
        "ready_for_benchmark_lock": bool(
            resolution_summary.get("ready_for_resolved_study")
            and preflight_summary.get("ready_to_run")
            and cohort_freeze_summary.get("ready_for_real_data_study", True)
            and overall_execution_percent >= 80
        ),
        "ready_for_submission_lock": bool(
            readiness_summary.get("ready_for_submission")
            and bool(validation_summary.get("ready_for_submission_lock", True))
            and overall_execution_percent >= 85
            and not critical_gaps
        ),
        "ready_for_translational_pilot": bool(
            overall_execution_percent >= 80
            and bool(validation_summary.get("ready_for_translational_pilot", True))
            and translational_score >= 75
            and operational_package_score >= 80
        ),
        "n_critical_gaps": int(len(critical_gaps)),
        "resolution_percent": int(resolution_summary.get("overall_resolution_percent") or 0),
        "preflight_percent": int(preflight_summary.get("overall_preflight_percent") or 0),
        "publication_readiness_percent": int(readiness_summary.get("overall_readiness_percent") or 0),
        "cohort_independence_percent": int(independence_summary.get("overall_independence_percent") or 0),
        "real_data_readiness_percent": int(cohort_freeze_summary.get("overall_real_data_readiness_percent") or 0),
        "real_data_handoff_percent": int(resolution_summary.get("real_data_handoff_percent") or 0),
        "comparative_evidence_percent": comparative_strength,
        "claim_strength_percent": int(claim_summary.get("overall_claim_strength_percent") or 0),
        "claim_tier": claim_summary.get("claim_tier"),
        "validation_lock_percent": int(validation_summary.get("overall_validation_lock_percent") or 0),
        "translational_readiness_percent": translational_score,
        "methods_best_internal_experiment": methods_summary.get("best_internal_experiment"),
        "manuscript_best_external_experiment": manuscript_summary.get("best_external_experiment"),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Overall execution readiness: {summary['overall_execution_percent']}%",
        f"- Ready for benchmark lock: {'yes' if summary['ready_for_benchmark_lock'] else 'not yet'}",
        f"- Ready for submission lock: {'yes' if summary['ready_for_submission_lock'] else 'not yet'}",
        f"- Ready for translational pilot: {'yes' if summary['ready_for_translational_pilot'] else 'not yet'}",
        "",
        "## Consolidated Progress",
        "",
        f"- Resolution: {summary['resolution_percent']}%",
        f"- Preflight: {summary['preflight_percent']}%",
        f"- Publication readiness: {summary['publication_readiness_percent']}%",
        f"- Cohort independence: {summary['cohort_independence_percent']}%",
        f"- Real-data freeze: {summary['real_data_readiness_percent']}%",
        f"- Real-data handoff package: {summary['real_data_handoff_percent']}%",
        f"- Comparative evidence: {summary['comparative_evidence_percent']}%",
        f"- Claim strength: {summary['claim_strength_percent']}% ({summary['claim_tier'] or '-'})",
        f"- Validation lock: {summary['validation_lock_percent']}%",
        f"- Translational readiness: {summary['translational_readiness_percent']}%",
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

    markdown_lines.extend(["## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- Nenhuma acao adicional prioritaria foi identificada.")

    markdown_lines.extend(["", "## Critical Gaps", ""])
    if critical_gaps:
        for gap in critical_gaps:
            markdown_lines.append(f"- {gap}")
    else:
        markdown_lines.append("- Nenhum gap critico aberto.")

    return {
        "summary": summary,
        "criteria": criteria,
        "recommended_actions": recommended_actions,
        "critical_gaps": critical_gaps,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_study_execution_board_html(board: dict) -> str:
    markdown = str(board.get("markdown_report") or "")
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
        "<title>PrimeVarClass Study Execution Board</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f2ea;color:#162733;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8d4f2f;}h3{margin-top:1.4rem;color:#2b786f;}"
        "ul{background:#fff;border:1px solid #e7dbcb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(chunks)
        + "</body></html>"
    )


def export_study_execution_board(
    *,
    public_resolution: dict,
    preflight_export: dict,
    study_results: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    board = build_study_execution_board(
        public_resolution=public_resolution,
        preflight_export=preflight_export,
        study_results=study_results,
        report_context=report_context,
    )
    markdown_path = root / "study_execution_board.md"
    html_path = root / "study_execution_board.html"
    manifest_path = root / "study_execution_board_manifest.json"
    criteria_path = root / "study_execution_board_criteria.csv"

    markdown_path.write_text(str(board.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_study_execution_board_html(board), encoding="utf-8")
    pd.DataFrame(board.get("criteria") or []).to_csv(criteria_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": board.get("summary") or {},
        "recommended_actions": board.get("recommended_actions") or [],
        "critical_gaps": board.get("critical_gaps") or [],
        "report_context": board.get("report_context") or {},
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "study_execution_board": board,
        "study_execution_board_markdown_path": str(markdown_path),
        "study_execution_board_html_path": str(html_path),
        "study_execution_board_manifest_path": str(manifest_path),
        "study_execution_board_criteria_path": str(criteria_path),
    }
