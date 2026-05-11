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


def _blocker_row(
    blocker_id: str,
    phase: str,
    priority: str,
    title: str,
    status: str,
    score_percent: int,
    blocking_reason: str,
    recommended_action: str,
    evidence_path: str | None = None,
) -> dict:
    return {
        "blocker_id": blocker_id,
        "phase": phase,
        "priority": priority,
        "title": title,
        "status": status,
        "score_percent": int(max(0, min(100, score_percent))),
        "blocking_reason": blocking_reason,
        "recommended_action": recommended_action,
        "evidence_path": evidence_path or "",
    }


def _priority_rank(priority: str) -> int:
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return mapping.get(str(priority or "").strip().lower(), 9)


def build_final_mile_package(
    *,
    summary: dict,
    resolution: dict,
    preflight: dict,
    study_results: dict,
    execution_board: dict,
    pilot_package: dict,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    study_design = study_results.get("study_design")
    study_name = getattr(study_design, "name", "PrimeVarClass Final Mile Package")
    title = str(context.get("report_title") or f"{study_name} - Final Mile Package")

    publication_summary = dict((study_results.get("publication_readiness_assessment") or {}).get("summary") or {})
    claim_summary = dict((study_results.get("claim_strength_assessment") or {}).get("summary") or {})
    validation_summary = dict((study_results.get("study_validation_lock") or {}).get("summary") or {})
    comparative_summary = dict((study_results.get("comparative_evidence_assessment") or {}).get("summary") or {})
    freeze_summary = dict(study_results.get("study_cohort_freeze_summary") or {})
    pilot_summary = dict(pilot_package.get("translational_pilot_package_summary") or {})

    real_data_readiness_percent = _safe_int(summary.get("real_data_readiness_percent") or freeze_summary.get("overall_real_data_readiness_percent"))
    real_data_handoff_percent = _safe_int(summary.get("real_data_handoff_percent"))
    real_data_handoff_reconciliation_percent = _safe_int(summary.get("real_data_handoff_reconciliation_percent"))
    real_data_handoff_application_percent = _safe_int(summary.get("real_data_handoff_application_percent"))
    n_real_data_tasks = _safe_int(summary.get("n_real_data_tasks"))
    n_critical_real_data_tasks = _safe_int(summary.get("n_critical_real_data_tasks"))
    comparative_evidence_percent = _safe_int(summary.get("comparative_evidence_percent") or comparative_summary.get("overall_comparative_strength_percent"))
    claim_strength_percent = _safe_int(summary.get("claim_strength_percent") or claim_summary.get("overall_claim_strength_percent"))
    publication_readiness_percent = _safe_int(summary.get("publication_readiness_percent") or publication_summary.get("overall_readiness_percent"))
    validation_lock_percent = _safe_int(summary.get("validation_lock_percent") or validation_summary.get("overall_validation_lock_percent"))
    pilot_package_percent = _safe_int(summary.get("pilot_package_percent") or pilot_summary.get("overall_pilot_package_percent"))

    handoff_penalty = min(40, (n_critical_real_data_tasks * 5) + (n_real_data_tasks * 2))
    handoff_closure_percent = max(0, real_data_handoff_percent - handoff_penalty)
    evidence_round_percent = int(round(np.mean([comparative_evidence_percent, claim_strength_percent])))
    submission_closeout_percent = int(round(np.mean([publication_readiness_percent, validation_lock_percent])))
    translational_transition_percent = int(round(np.mean([
        pilot_package_percent,
        100 if pilot_summary.get("ready_for_shadow_pilot") else 0,
        100 if pilot_summary.get("ready_for_live_pilot") else 0,
    ])))

    criteria = [
        _criterion_row(
            "real_data_lock",
            "Real-data cohort lock",
            1.25,
            real_data_readiness_percent,
            (
                f"Real-data readiness em {real_data_readiness_percent}% "
                f"com {n_critical_real_data_tasks} tarefa(s) critica(s) abertas."
            ),
            "Substituir todas as fontes demo/example por coortes publicas finais e versionadas.",
            critical=True,
        ),
        _criterion_row(
            "handoff_closure",
            "Operational handoff closure",
            1.0,
            handoff_closure_percent,
            (
                f"Handoff operacional em {real_data_handoff_percent}%, mas com "
                f"{n_real_data_tasks} tarefa(s) abertas, reconciliacao em {real_data_handoff_reconciliation_percent}% "
                f"e aplicacao candidata em {real_data_handoff_application_percent}% "
                f"e penalizacao operacional de {handoff_penalty} ponto(s)."
            ),
            "Executar e fechar as tarefas do handoff antes da rodada cientifica final.",
            critical=True,
        ),
        _criterion_row(
            "final_evidence_round",
            "Final comparative evidence round",
            1.3,
            evidence_round_percent,
            (
                f"Comparative evidence em {comparative_evidence_percent}% e claim strength em {claim_strength_percent}%."
            ),
            "Rerrodar o benchmark final em coortes reais ate consolidar comparative evidence e claim strength.",
            critical=True,
        ),
        _criterion_row(
            "submission_closeout",
            "Submission closeout",
            1.15,
            submission_closeout_percent,
            (
                f"Publication readiness em {publication_readiness_percent}% e validation lock em {validation_lock_percent}%."
            ),
            "Fechar o pacote estatistico e editorial para submission lock.",
            critical=True,
        ),
        _criterion_row(
            "translational_transition",
            "Translational transition",
            0.9,
            translational_transition_percent,
            (
                f"Pilot package em {pilot_package_percent}% com modo {pilot_summary.get('pilot_mode') or '-'}."
            ),
            "Usar shadow mode para consolidar operacao enquanto a rodada cientifica final e fechada.",
        ),
    ]

    blockers: List[dict] = []
    if real_data_readiness_percent < 85:
        blockers.append(
            _blocker_row(
                "real_data_lock",
                "data",
                "critical",
                "Coortes reais finais ainda nao estao congeladas",
                "open",
                real_data_readiness_percent,
                "O estudo ainda depende de fontes demo/example ou release placeholders.",
                "Substituir os arquivos de exemplo pelas coortes publicas finais e rerresolver o estudo.",
                resolution.get("study_cohort_freeze_markdown_path") or study_results.get("study_cohort_freeze_markdown_path"),
            )
        )
    if n_critical_real_data_tasks > 0:
        blockers.append(
            _blocker_row(
                "handoff_tasks",
                "operations",
                "critical",
                "Tarefas criticas do handoff continuam abertas",
                "open",
                handoff_closure_percent,
                f"Existem {n_critical_real_data_tasks} tarefa(s) critica(s) e {n_real_data_tasks} no total para concluir.",
                "Executar study_real_data_handoff_tasks.csv ate zerar os bloqueios criticos.",
                resolution.get("study_real_data_handoff_markdown_path"),
            )
        )
    if comparative_evidence_percent < 60:
        blockers.append(
            _blocker_row(
                "comparative_evidence",
                "science",
                "critical",
                "Comparative evidence ainda insuficiente",
                "open",
                comparative_evidence_percent,
                "O ganho contra baseline ainda nao esta forte o suficiente para sustentar a tese final.",
                "Rodar o benchmark definitivo nas coortes reais e reforcar a comparacao head-to-head.",
                study_results.get("comparative_evidence_report_markdown_path"),
            )
        )
    if claim_strength_percent < 55:
        blockers.append(
            _blocker_row(
                "claim_strength",
                "science",
                "critical",
                "Claim strength abaixo do minimo desejado",
                "open",
                claim_strength_percent,
                f"O claim tier atual e {claim_summary.get('claim_tier') or '-'} e ainda nao sustenta submission forte.",
                "Elevar a evidencia ate pelo menos um claim tier moderado com coortes reais finais.",
                study_results.get("claim_strength_report_markdown_path"),
            )
        )
    if submission_closeout_percent < 85:
        blockers.append(
            _blocker_row(
                "submission_closeout",
                "submission",
                "high",
                "Submission closeout ainda incompleto",
                "open",
                submission_closeout_percent,
                "O pacote de publication readiness e validation lock ainda tem lacunas para submission final.",
                "Fechar os criterios restantes do publication readiness e do validation lock.",
                study_results.get("publication_readiness_report_markdown_path"),
            )
        )
    if not pilot_summary.get("ready_for_live_pilot"):
        blockers.append(
            _blocker_row(
                "live_transition",
                "translation",
                "medium",
                "Transicao live ainda bloqueada",
                "open",
                translational_transition_percent,
                "A plataforma ja suporta demo/shadow mode, mas ainda nao deve entrar em piloto live.",
                "Manter a adocao em shadow mode ate os bloqueios cientificos centrais serem resolvidos.",
                pilot_package.get("translational_pilot_package_markdown_path"),
            )
        )

    if not blockers:
        blockers.append(
            _blocker_row(
                "final_mile_clear",
                "closeout",
                "low",
                "Final mile sem bloqueios relevantes",
                "closed",
                100,
                "Nenhum bloqueio critico foi identificado na rodada atual.",
                "Prosseguir para a release final do estudo e documentar a submissao.",
            )
        )

    blockers_df = pd.DataFrame(blockers)
    blockers_df = blockers_df.sort_values(
        by=["priority", "phase", "title"],
        key=lambda col: col.map(_priority_rank) if col.name == "priority" else col,
    ).reset_index(drop=True)

    total_weight = sum(float(item["weight"]) for item in criteria)
    weighted_score = sum(float(item["weight"]) * float(item["score_percent"]) for item in criteria)
    overall_percent = int(round(weighted_score / total_weight)) if total_weight else 0
    critical_gaps = [item["title"] for item in criteria if item["critical"] and item["score_percent"] < 70]
    recommended_actions = blockers_df["recommended_action"].dropna().astype(str).tolist() if not blockers_df.empty else []
    recommended_actions = list(dict.fromkeys(item for item in recommended_actions if item.strip()))

    checklist = [
        {
            "check_id": "close_critical_handoff",
            "phase": "data",
            "status": "ready" if n_critical_real_data_tasks == 0 else "pending",
            "action": "Fechar todas as tarefas criticas do handoff de dados reais.",
        },
        {
            "check_id": "rerun_real_data_benchmark",
            "phase": "science",
            "status": "ready" if real_data_readiness_percent >= 85 else "pending",
            "action": "Rerrodar o benchmark publico com coortes reais congeladas.",
        },
        {
            "check_id": "strengthen_evidence",
            "phase": "science",
            "status": "ready" if comparative_evidence_percent >= 60 and claim_strength_percent >= 55 else "pending",
            "action": "Elevar comparative evidence e claim strength para o minimo de submissao.",
        },
        {
            "check_id": "close_submission_lock",
            "phase": "submission",
            "status": "ready" if publication_readiness_percent >= 85 and validation_lock_percent >= 80 else "pending",
            "action": "Fechar publication readiness e validation lock para submission closeout.",
        },
        {
            "check_id": "shadow_before_live",
            "phase": "translation",
            "status": "ready" if pilot_summary.get("ready_for_shadow_pilot") else "pending",
            "action": "Usar shadow mode como etapa transicional antes de qualquer piloto live.",
        },
    ]

    ready_for_real_data_execution = bool(real_data_readiness_percent >= 85 and n_critical_real_data_tasks == 0)
    ready_for_final_evidence_round = bool(
        ready_for_real_data_execution
        and comparative_evidence_percent >= 60
        and claim_strength_percent >= 55
    )
    ready_for_submission_closeout = bool(
        ready_for_final_evidence_round
        and publication_readiness_percent >= 85
        and validation_lock_percent >= 80
    )
    ready_for_live_transition = bool(
        ready_for_submission_closeout and pilot_summary.get("ready_for_live_pilot")
    )

    summary_payload = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_final_mile_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "ready_for_real_data_execution": ready_for_real_data_execution,
        "ready_for_final_evidence_round": ready_for_final_evidence_round,
        "ready_for_submission_closeout": ready_for_submission_closeout,
        "ready_for_live_transition": ready_for_live_transition,
        "n_blockers": int(len(blockers_df)),
        "n_critical_blockers": int((blockers_df["priority"].astype(str) == "critical").sum()) if not blockers_df.empty else 0,
        "top_blocker_phase": str(blockers_df.iloc[0]["phase"]) if not blockers_df.empty else "",
        "top_blocker_title": str(blockers_df.iloc[0]["title"]) if not blockers_df.empty else "",
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary_payload['generated_at']}",
        f"- Final mile readiness: {summary_payload['overall_final_mile_percent']}%",
        f"- Ready for real-data execution: {'yes' if summary_payload['ready_for_real_data_execution'] else 'not yet'}",
        f"- Ready for final evidence round: {'yes' if summary_payload['ready_for_final_evidence_round'] else 'not yet'}",
        f"- Ready for submission closeout: {'yes' if summary_payload['ready_for_submission_closeout'] else 'not yet'}",
        f"- Ready for live transition: {'yes' if summary_payload['ready_for_live_transition'] else 'not yet'}",
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

    markdown_lines.extend(["## Blockers", ""])
    for item in blockers_df.to_dict(orient="records"):
        markdown_lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Priority: {item['priority']}",
                f"- Phase: {item['phase']}",
                f"- Score: {item['score_percent']}%",
                f"- Reason: {item['blocking_reason']}",
                f"- Action: {item['recommended_action']}",
                f"- Evidence path: {item['evidence_path'] or '-'}",
                "",
            ]
        )

    markdown_lines.extend(["## Final Checklist", ""])
    for item in checklist:
        markdown_lines.append(f"- [{item['status']}] {item['phase']}: {item['action']}")

    markdown_lines.extend(["", "## Recommended Actions", ""])
    if recommended_actions:
        for action in recommended_actions:
            markdown_lines.append(f"- {action}")
    else:
        markdown_lines.append("- Nenhuma acao adicional prioritaria foi identificada.")

    return {
        "summary": summary_payload,
        "criteria": criteria,
        "blockers": blockers_df.to_dict(orient="records"),
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "checklist": checklist,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_final_mile_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Final Mile Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f6f1e9;color:#192832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4b29;}h3{margin-top:1.35rem;color:#275f66;}"
        "ul{background:#fff;border:1px solid #e7ddcd;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_final_mile_package(
    *,
    summary: dict,
    resolution: dict,
    preflight: dict,
    study_results: dict,
    execution_board: dict,
    pilot_package: dict,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_final_mile_package(
        summary=summary,
        resolution=resolution,
        preflight=preflight,
        study_results=study_results,
        execution_board=execution_board,
        pilot_package=pilot_package,
        report_context=report_context,
    )

    markdown_path = root / "final_mile_package.md"
    html_path = root / "final_mile_package.html"
    manifest_path = root / "final_mile_package_manifest.json"
    criteria_path = root / "final_mile_package_criteria.csv"
    blockers_path = root / "final_mile_package_blockers.csv"
    checklist_path = root / "final_mile_package_checklist.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_final_mile_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("criteria") or []).to_csv(criteria_path, index=False)
    pd.DataFrame(bundle.get("blockers") or []).to_csv(blockers_path, index=False)
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
        "blockers_path": str(blockers_path),
        "checklist_path": str(checklist_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "final_mile_package": bundle,
        "final_mile_package_summary": bundle.get("summary") or {},
        "final_mile_package_markdown_path": str(markdown_path),
        "final_mile_package_html_path": str(html_path),
        "final_mile_package_manifest_path": str(manifest_path),
        "final_mile_package_criteria_path": str(criteria_path),
        "final_mile_package_blockers_path": str(blockers_path),
        "final_mile_package_checklist_path": str(checklist_path),
    }
