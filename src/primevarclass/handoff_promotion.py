from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
) -> dict:
    normalized = max(0, min(100, int(score_percent)))
    return {
        "criterion_id": criterion_id,
        "title": title,
        "weight": float(weight),
        "score_percent": normalized,
        "status": _status_from_percent(normalized),
        "evidence": evidence,
        "next_step": next_step,
    }


def _priority_rank(priority: str) -> int:
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return mapping.get(str(priority or "").strip().lower(), 9)


def _load_json(path_value: str | None) -> dict:
    if not path_value:
        return {}
    path = Path(path_value).resolve()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_real_data_candidate_promotion(
    *,
    study_name: str,
    candidate_config_path: str,
    handoff_application_manifest_path: str | None = None,
    handoff_reconciliation_tasks_path: str | None = None,
    output_dir_hint: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    application_manifest = _load_json(handoff_application_manifest_path)
    application_summary = dict(application_manifest.get("summary") or {})

    candidate_config_file = Path(candidate_config_path).resolve()
    candidate_config_exists = candidate_config_file.exists()
    tasks_file = Path(handoff_reconciliation_tasks_path).resolve() if handoff_reconciliation_tasks_path else None
    tasks_df = pd.read_csv(tasks_file) if tasks_file and tasks_file.exists() else pd.DataFrame()
    if not tasks_df.empty and "validated" in tasks_df.columns:
        tasks_df["validated"] = tasks_df["validated"].astype(bool)
        pending_df = tasks_df[~tasks_df["validated"]].copy()
        invalid_df = tasks_df[tasks_df["validation_state"].astype(str) == "invalid"].copy() if "validation_state" in tasks_df.columns else pd.DataFrame()
    else:
        pending_df = tasks_df.copy()
        invalid_df = pd.DataFrame()

    n_tasks = _safe_int(application_summary.get("n_tasks") or len(tasks_df))
    n_validated = _safe_int(
        application_summary.get("n_validated_tasks")
        or (tasks_df["validated"].astype(bool).sum() if not tasks_df.empty and "validated" in tasks_df.columns else 0)
    )
    n_applied_changes = _safe_int(application_summary.get("n_applied_changes"))
    application_percent = _safe_int(application_summary.get("overall_handoff_application_percent"))
    ready_for_candidate_resolution = bool(application_summary.get("ready_for_candidate_resolution"))
    ready_for_candidate_public_study = bool(application_summary.get("ready_for_candidate_public_study"))
    n_pending = int(len(pending_df))
    n_invalid = int(len(invalid_df))
    n_critical_pending = int(
        (pending_df["priority"].astype(str).str.lower() == "critical").sum()
    ) if not pending_df.empty and "priority" in pending_df.columns else 0

    candidate_run_dir = (Path(output_dir_hint).resolve() / "candidate_public_study_run") if output_dir_hint else (candidate_config_file.parent / "candidate_public_study_run")
    candidate_public_study_command = (
        f'primevarclass --study-config "{candidate_config_file}" --public-study-run --output-dir "{candidate_run_dir}"'
        if candidate_config_exists
        else ""
    )

    criteria = [
        _criterion_row(
            "candidate_config_materialized",
            "Candidate config materialized",
            0.9,
            100 if candidate_config_exists else 0,
            f"Arquivo candidato {'encontrado' if candidate_config_exists else 'ausente'} em {candidate_config_file}.",
            "Gerar o candidate config a partir do tracker validado antes de tentar promover a coorte.",
        ),
        _criterion_row(
            "validated_changes_applied",
            "Validated changes applied",
            1.05,
            application_percent,
            f"{n_validated}/{n_tasks} tarefa(s) validada(s) e {n_applied_changes} alteracao(oes) aplicada(s) no candidate config.",
            "Continuar fechando e aplicando as tarefas validadas do tracker ate reduzir o gap operacional.",
        ),
        _criterion_row(
            "candidate_resolution_gate",
            "Candidate resolution gate",
            1.0,
            100 if ready_for_candidate_resolution else min(70, application_percent),
            (
                "O candidate config ja tem base minima para rerresolver o estudo."
                if ready_for_candidate_resolution
                else "Ainda nao ha base suficiente para promover a configuracao candidata a uma nova resolucao."
            ),
            "Validar pelo menos uma entrega real no tracker para liberar a promocao do candidate config.",
        ),
        _criterion_row(
            "candidate_public_study_gate",
            "Candidate public-study gate",
            1.2,
            100 if ready_for_candidate_public_study else application_percent,
            (
                "Todas as tarefas de handoff relevantes ja foram validadas para a rerrodada controlada."
                if ready_for_candidate_public_study
                else f"Ainda existem {n_pending} tarefa(s) pendente(s) antes da rerrodada controlada do estudo."
            ),
            "Zerar tarefas pendentes e invalidas no tracker para rerrodar o public-study-run com confianca.",
        ),
    ]
    total_weight = sum(item["weight"] for item in criteria) or 1.0
    overall_percent = int(round(sum(item["weight"] * item["score_percent"] for item in criteria) / total_weight))

    blockers: List[dict] = []
    if not candidate_config_exists:
        blockers.append(
            {
                "blocker_id": "missing_candidate_config",
                "priority": "critical",
                "title": "Candidate config ainda nao foi materializado",
                "status": "open",
                "blocking_reason": "Sem o arquivo candidato nao existe configuracao concreta para promover ao benchmark real.",
                "recommended_action": "Gerar study_real_data_candidate_config.toml a partir do tracker validado.",
            }
        )
    if n_critical_pending > 0:
        blockers.append(
            {
                "blocker_id": "critical_pending_tasks",
                "priority": "critical",
                "title": "Tarefas criticas do tracker continuam abertas",
                "status": "open",
                "blocking_reason": f"Existem {n_critical_pending} tarefa(s) critica(s) ainda pendente(s) no handoff.",
                "recommended_action": "Fechar primeiro as tarefas criticas para reduzir risco na promocao do candidate config.",
            }
        )
    if n_invalid > 0:
        blockers.append(
            {
                "blocker_id": "invalid_tracker_tasks",
                "priority": "high",
                "title": "Existe evidencia invalida no tracker",
                "status": "open",
                "blocking_reason": f"{n_invalid} tarefa(s) foram marcadas como concluidas, mas sem evidencias validas.",
                "recommended_action": "Corrigir caminhos, release metadata ou status dessas tarefas antes de promover a configuracao candidata.",
            }
        )
    if candidate_config_exists and not ready_for_candidate_public_study:
        blockers.append(
            {
                "blocker_id": "candidate_public_study_not_ready",
                "priority": "high",
                "title": "Candidate config ainda nao esta pronto para a rerrodada final",
                "status": "open",
                "blocking_reason": f"A aplicacao do handoff esta em {application_percent}% e ainda ha pendencias abertas.",
                "recommended_action": "Usar o pacote de reconciliacao para fechar as pendencias restantes antes de rerrodar o estudo publico.",
            }
        )

    ready_to_promote_candidate_config = bool(candidate_config_exists and ready_for_candidate_resolution)
    ready_to_run_candidate_public_study = bool(candidate_config_exists and ready_for_candidate_public_study and n_invalid == 0)

    recommended_actions: List[str] = []
    if not ready_to_promote_candidate_config:
        recommended_actions.append("Concluir validacoes suficientes no tracker para liberar a promocao do candidate config.")
    if ready_to_promote_candidate_config and not ready_to_run_candidate_public_study:
        recommended_actions.append("Revisar o candidate config gerado e fechar as tarefas pendentes antes da rerrodada final.")
    if ready_to_run_candidate_public_study and candidate_public_study_command:
        recommended_actions.append(f"Executar a rerrodada controlada com: {candidate_public_study_command}")
    if not recommended_actions:
        recommended_actions.append("Pacote candidato pronto para promocao controlada.")

    if not tasks_df.empty and {"priority", "cohort_name", "source_name"}.issubset(tasks_df.columns):
        pending_df = pending_df.sort_values(
            by=["priority", "cohort_name", "source_name"],
            key=lambda col: col.map(_priority_rank) if col.name == "priority" else col,
        ).reset_index(drop=True)

    summary = {
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_candidate_promotion_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "candidate_config_exists": candidate_config_exists,
        "candidate_config_path": str(candidate_config_file),
        "n_tasks": n_tasks,
        "n_validated_tasks": n_validated,
        "n_pending_tasks": n_pending,
        "n_invalid_tasks": n_invalid,
        "n_critical_pending_tasks": n_critical_pending,
        "n_applied_changes": n_applied_changes,
        "handoff_application_percent": application_percent,
        "ready_for_candidate_resolution": ready_for_candidate_resolution,
        "ready_for_candidate_public_study": ready_for_candidate_public_study,
        "ready_to_promote_candidate_config": ready_to_promote_candidate_config,
        "ready_to_run_candidate_public_study": ready_to_run_candidate_public_study,
        "candidate_public_study_command": candidate_public_study_command,
        "candidate_public_study_output_dir": str(candidate_run_dir),
    }

    markdown_lines = [
        f"# {study_name} - Candidate Promotion Package",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Candidate promotion: {summary['overall_candidate_promotion_percent']}%",
        f"- Candidate config exists: {'yes' if summary['candidate_config_exists'] else 'not yet'}",
        f"- Validated tasks applied: {summary['n_validated_tasks']}/{summary['n_tasks']}",
        f"- Applied changes: {summary['n_applied_changes']}",
        f"- Ready to promote candidate config: {'yes' if summary['ready_to_promote_candidate_config'] else 'not yet'}",
        f"- Ready to run candidate public study: {'yes' if summary['ready_to_run_candidate_public_study'] else 'not yet'}",
        "",
        "## Criteria",
        "",
    ]
    for criterion in criteria:
        markdown_lines.append(
            f"- {criterion['title']}: {criterion['score_percent']}% | {criterion['evidence']} | Next: {criterion['next_step']}"
        )
    markdown_lines.extend(["", "## Blockers", ""])
    if blockers:
        for blocker in blockers:
            markdown_lines.append(
                f"- [{blocker['priority']}] {blocker['title']}: {blocker['blocking_reason']} | Next: {blocker['recommended_action']}"
            )
    else:
        markdown_lines.append("- Nenhum blocker prioritario restante para a promocao candidata.")
    markdown_lines.extend(["", "## Commands", ""])
    if candidate_public_study_command:
        markdown_lines.append(f"- Candidate public study run: `{candidate_public_study_command}`")
    else:
        markdown_lines.append("- Candidate public study run: indisponivel ate o candidate config existir.")
    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "criteria": criteria,
        "blockers": blockers,
        "recommended_actions": recommended_actions,
        "pending_tasks": pending_df.to_dict(orient="records") if not pending_df.empty else [],
        "report_context": context,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def build_real_data_candidate_promotion_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Candidate Promotion Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f5efe6;color:#152431;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#985d2f;}ul{background:#fff;border:1px solid #e3d8c7;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_real_data_candidate_promotion(
    *,
    study_name: str,
    candidate_config_path: str,
    handoff_application_manifest_path: str | None,
    handoff_reconciliation_tasks_path: str | None,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_real_data_candidate_promotion(
        study_name=study_name,
        candidate_config_path=candidate_config_path,
        handoff_application_manifest_path=handoff_application_manifest_path,
        handoff_reconciliation_tasks_path=handoff_reconciliation_tasks_path,
        output_dir_hint=str(root),
        report_context=report_context,
    )

    markdown_path = root / "study_real_data_candidate_promotion.md"
    html_path = root / "study_real_data_candidate_promotion.html"
    manifest_path = root / "study_real_data_candidate_promotion_manifest.json"
    criteria_path = root / "study_real_data_candidate_promotion_criteria.csv"
    blockers_path = root / "study_real_data_candidate_promotion_blockers.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_real_data_candidate_promotion_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("criteria") or []).to_csv(criteria_path, index=False)
    pd.DataFrame(bundle.get("blockers") or []).to_csv(blockers_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "recommended_actions": bundle.get("recommended_actions") or [],
        "report_context": bundle.get("report_context") or {},
        "candidate_config_path": str(Path(candidate_config_path).resolve()),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "blockers_path": str(blockers_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_real_data_candidate_promotion": bundle,
        "study_real_data_candidate_promotion_summary": bundle.get("summary") or {},
        "study_real_data_candidate_promotion_markdown_path": str(markdown_path),
        "study_real_data_candidate_promotion_html_path": str(html_path),
        "study_real_data_candidate_promotion_manifest_path": str(manifest_path),
        "study_real_data_candidate_promotion_criteria_path": str(criteria_path),
        "study_real_data_candidate_promotion_blockers_path": str(blockers_path),
    }
