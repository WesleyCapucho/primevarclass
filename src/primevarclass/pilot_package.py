from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


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


def _pilot_mode(*, ready_for_real_data_study: bool, ready_for_shadow_pilot: bool, ready_for_live_pilot: bool) -> str:
    if ready_for_live_pilot:
        return "live_candidate"
    if ready_for_shadow_pilot:
        return "shadow_mode"
    if ready_for_real_data_study:
        return "internal_validation"
    return "demo_mode"


def build_translational_pilot_package(
    *,
    summary: dict,
    resolution: dict,
    preflight: dict,
    study_results: dict,
    execution_board: dict,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    study_design = study_results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Translational Pilot Package")
    title = str(context.get("report_title") or f"{study_name} - Translational Pilot Package")

    validation_summary = dict((study_results.get("study_validation_lock") or {}).get("summary") or {})
    claim_summary = dict((study_results.get("claim_strength_assessment") or {}).get("summary") or {})
    readiness_summary = dict((study_results.get("publication_readiness_assessment") or {}).get("summary") or {})
    freeze_summary = dict(study_results.get("study_cohort_freeze_summary") or {})
    resolution_summary = dict((resolution or {}).get("summary") or {})
    preflight_summary = dict(((preflight or {}).get("preflight") or {}).get("summary") or {})
    execution_summary = dict(((execution_board or {}).get("study_execution_board") or {}).get("summary") or {})

    package_artifacts = [
        study_results.get("study_release_manifest_path"),
        study_results.get("study_summary_report_path"),
        study_results.get("study_validation_lock_manifest_path"),
        study_results.get("claim_strength_manifest_path"),
        study_results.get("publication_readiness_manifest_path"),
        study_results.get("study_cohort_freeze_manifest_path"),
        resolution.get("study_real_data_handoff_manifest_path"),
        execution_board.get("study_execution_board_manifest_path"),
    ]
    package_artifact_percent = int(round(sum(1 for item in package_artifacts if _artifact_exists(item)) / len(package_artifacts) * 100)) if package_artifacts else 0

    operator_surface_percent = 100
    handoff_percent = _safe_int(summary.get("real_data_handoff_percent"))
    validation_percent = _safe_int(validation_summary.get("overall_validation_lock_percent"))
    claim_percent = _safe_int(claim_summary.get("overall_claim_strength_percent"))
    readiness_percent = _safe_int(readiness_summary.get("overall_readiness_percent"))
    preflight_percent = _safe_int(preflight_summary.get("overall_preflight_percent"))
    execution_percent = _safe_int(execution_summary.get("overall_execution_percent"))

    shadow_pilot_percent = int(round(np.mean([package_artifact_percent, handoff_percent, preflight_percent, execution_percent])))
    live_pilot_percent = int(round(np.mean([validation_percent, claim_percent, readiness_percent, _safe_int(freeze_summary.get("overall_real_data_readiness_percent"))])))

    ready_for_demo_pilot = bool(package_artifact_percent >= 80 and execution_percent >= 60)
    ready_for_shadow_pilot = bool(
        ready_for_demo_pilot
        and handoff_percent >= 80
        and preflight_percent >= 85
    )
    ready_for_live_pilot = bool(
        ready_for_shadow_pilot
        and bool(summary.get("ready_for_real_data_study"))
        and bool(validation_summary.get("ready_for_translational_pilot"))
    )

    criteria = [
        _criterion_row(
            "operator_surface",
            "Operator surface readiness",
            1.0,
            operator_surface_percent,
            "Workbench, API, jobs e manifests ja suportam uso guiado por laboratorio.",
            "Manter a superficie operacional consistente entre releases.",
        ),
        _criterion_row(
            "artifact_package",
            "Pilot artifact package",
            1.1,
            package_artifact_percent,
            f"{package_artifact_percent}% dos artefatos operacionais essenciais do piloto foram materializados.",
            "Garantir que todo piloto venha acompanhado de manifests, relatorios e release final.",
            critical=True,
        ),
        _criterion_row(
            "lab_handoff",
            "Lab handoff readiness",
            1.2,
            handoff_percent,
            (
                f"Handoff de dados reais em {handoff_percent}% com "
                f"{_safe_int(summary.get('n_real_data_tasks'))} tarefa(s) abertas."
            ),
            "Fechar as tarefas do handoff para permitir uma rodada assistida pelo laboratorio.",
            critical=True,
        ),
        _criterion_row(
            "shadow_mode",
            "Shadow-mode pilot readiness",
            1.15,
            shadow_pilot_percent,
            (
                f"Shadow-mode em {shadow_pilot_percent}% com preflight={preflight_percent}% "
                f"e execution board={execution_percent}%."
            ),
            "Usar a workbench e o handoff para rodar o fluxo em paralelo com revisao humana.",
            critical=True,
        ),
        _criterion_row(
            "live_candidate",
            "Live translational candidate",
            1.25,
            live_pilot_percent,
            (
                f"Candidato live em {live_pilot_percent}% com freeze={_safe_int(freeze_summary.get('overall_real_data_readiness_percent'))}% "
                f"e validation lock={validation_percent}%."
            ),
            "Trocar datasets demo por coortes reais e fortalecer claim/validation antes de qualquer piloto live.",
            critical=True,
        ),
    ]

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / total_weight)) if total_weight else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]
    pilot_mode = _pilot_mode(
        ready_for_real_data_study=bool(summary.get("ready_for_real_data_study")),
        ready_for_shadow_pilot=ready_for_shadow_pilot,
        ready_for_live_pilot=ready_for_live_pilot,
    )

    checklist_rows = [
        {
            "check_id": "open_workbench",
            "phase": "operator",
            "status": "ready",
            "action": "Abrir /workbench e carregar o registry de modelos.",
        },
        {
            "check_id": "review_handoff",
            "phase": "data",
            "status": "ready" if handoff_percent >= 85 else "pending",
            "action": "Revisar study_real_data_handoff_tasks.csv e atribuir as tarefas criticas por coorte/fonte.",
        },
        {
            "check_id": "run_preflight",
            "phase": "benchmark",
            "status": "ready" if preflight_percent >= 85 else "pending",
            "action": "Executar preflight do estudo resolvido antes da rodada publica final.",
        },
        {
            "check_id": "shadow_mode",
            "phase": "pilot",
            "status": "ready" if ready_for_shadow_pilot else "pending",
            "action": "Usar a API e a workbench em modo assistido, com validacao humana e sem claims clinicos finais.",
        },
        {
            "check_id": "live_candidate",
            "phase": "pilot",
            "status": "ready" if ready_for_live_pilot else "pending",
            "action": "Permitir piloto live apenas quando freeze real, validation lock e claim strength sustentarem a rodada.",
        },
    ]

    summary_payload = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_pilot_package_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "pilot_mode": pilot_mode,
        "ready_for_demo_pilot": ready_for_demo_pilot,
        "ready_for_shadow_pilot": ready_for_shadow_pilot,
        "ready_for_live_pilot": ready_for_live_pilot,
        "package_artifact_percent": package_artifact_percent,
        "lab_handoff_percent": handoff_percent,
        "shadow_pilot_percent": shadow_pilot_percent,
        "live_pilot_percent": live_pilot_percent,
        "n_critical_gaps": int(len(critical_gaps)),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary_payload['generated_at']}",
        f"- Pilot package readiness: {summary_payload['overall_pilot_package_percent']}%",
        f"- Pilot mode: {summary_payload['pilot_mode']}",
        f"- Ready for demo pilot: {'yes' if summary_payload['ready_for_demo_pilot'] else 'not yet'}",
        f"- Ready for shadow pilot: {'yes' if summary_payload['ready_for_shadow_pilot'] else 'not yet'}",
        f"- Ready for live pilot: {'yes' if summary_payload['ready_for_live_pilot'] else 'not yet'}",
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

    markdown_lines.extend(["## Pilot Checklist", ""])
    for item in checklist_rows:
        markdown_lines.append(f"- [{item['status']}] {item['phase']}: {item['action']}")

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- O pacote piloto parece pronto para execucao assistida.")

    return {
        "summary": summary_payload,
        "criteria": criteria,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "checklist": checklist_rows,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_translational_pilot_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Translational Pilot Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f1e9;color:#192832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4b29;}h3{margin-top:1.35rem;color:#275f66;}"
        "ul{background:#fff;border:1px solid #e7ddcd;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_translational_pilot_package(
    *,
    summary: dict,
    resolution: dict,
    preflight: dict,
    study_results: dict,
    execution_board: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_translational_pilot_package(
        summary=summary,
        resolution=resolution,
        preflight=preflight,
        study_results=study_results,
        execution_board=execution_board,
        report_context=report_context,
    )

    markdown_path = root / "translational_pilot_package.md"
    html_path = root / "translational_pilot_package.html"
    manifest_path = root / "translational_pilot_package_manifest.json"
    criteria_path = root / "translational_pilot_package_criteria.csv"
    checklist_path = root / "translational_pilot_package_checklist.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_translational_pilot_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("criteria") or []).to_csv(criteria_path, index=False)
    pd.DataFrame(bundle.get("checklist") or []).to_csv(checklist_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "critical_gaps": bundle.get("critical_gaps"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "checklist_path": str(checklist_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "translational_pilot_package": bundle,
        "translational_pilot_package_summary": bundle.get("summary") or {},
        "translational_pilot_package_markdown_path": str(markdown_path),
        "translational_pilot_package_html_path": str(html_path),
        "translational_pilot_package_manifest_path": str(manifest_path),
        "translational_pilot_package_criteria_path": str(criteria_path),
        "translational_pilot_package_checklist_path": str(checklist_path),
    }
