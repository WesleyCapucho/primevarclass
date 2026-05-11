from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .final_mile_package import export_final_mile_package
from .pilot_package import export_translational_pilot_package
from .platform_completion import export_platform_completion_assessment
from .public_config_resolver import export_study_public_config_resolution
from .roadmap import build_roadmap_progress
from .study import run_publication_study
from .study_execution_board import export_study_execution_board
from .study_preflight import export_study_preflight
from .translational_impact import PrimeVarClassPilotOpsStore, export_translational_impact_package


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_public_study_run_report(summary: dict, recommended_actions: list[str]) -> str:
    lines = [
        "# PrimeVarClass Public Study Run",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Original config: {summary.get('original_config_path')}",
        f"- Resolved config: {summary.get('resolved_study_config_path')}",
        f"- Resolution: {summary.get('resolution_percent', 0)}%",
        f"- Real-data readiness: {summary.get('real_data_readiness_percent', 0)}%",
        f"- Real-data handoff package: {summary.get('real_data_handoff_percent', 0)}%",
        f"- Handoff reconciliation: {summary.get('real_data_handoff_reconciliation_percent', 0)}%",
        f"- Handoff candidate application: {summary.get('real_data_handoff_application_percent', 0)}%",
        f"- Candidate promotion: {summary.get('real_data_candidate_promotion_percent', 0)}%",
        f"- Ready for lab handoff: {'yes' if summary.get('ready_for_lab_handoff') else 'not yet'}",
        f"- Real-data tasks: {summary.get('n_real_data_tasks', 0)} total / {summary.get('n_critical_real_data_tasks', 0)} critical",
        f"- Handoff validated tasks: {summary.get('n_handoff_validated_tasks', 0)} | pending={summary.get('n_handoff_pending_tasks', 0)} | invalid={summary.get('n_handoff_invalid_tasks', 0)}",
        f"- Handoff applied changes: {summary.get('n_handoff_applied_changes', 0)}",
        f"- Ready to promote candidate config: {'yes' if summary.get('ready_to_promote_candidate_config') else 'not yet'}",
        f"- Ready to run candidate public study: {'yes' if summary.get('ready_to_run_candidate_public_study') else 'not yet'}",
        f"- Preflight: {summary.get('preflight_percent', 0)}%",
        f"- Cohort independence: {summary.get('cohort_independence_percent', 0)}%",
        f"- Comparative evidence: {summary.get('comparative_evidence_percent', 0)}%",
        f"- Claim strength: {summary.get('claim_strength_percent', 0)}% ({summary.get('claim_tier') or '-'})",
        f"- Publication readiness: {summary.get('publication_readiness_percent', 0)}%",
        f"- Validation lock: {summary.get('validation_lock_percent', 0)}%",
        f"- Execution board: {summary.get('execution_board_percent', 0)}%",
        f"- Translational pilot package: {summary.get('pilot_package_percent', 0)}%",
        f"- Pilot mode: {summary.get('pilot_mode') or '-'}",
        f"- Ready for demo pilot: {'yes' if summary.get('ready_for_demo_pilot') else 'not yet'}",
        f"- Ready for shadow pilot: {'yes' if summary.get('ready_for_shadow_pilot') else 'not yet'}",
        f"- Ready for live pilot: {'yes' if summary.get('ready_for_live_pilot') else 'not yet'}",
        f"- Translational impact package: {summary.get('translational_impact_percent', 0)}%",
        f"- Ready for assisted pilot ops: {'yes' if summary.get('ready_for_assisted_pilot_ops') else 'not yet'}",
        f"- Ready for institutional rollout: {'yes' if summary.get('ready_for_institutional_rollout') else 'not yet'}",
        f"- Final mile package: {summary.get('final_mile_percent', 0)}%",
        f"- Ready for final evidence round: {'yes' if summary.get('ready_for_final_evidence_round') else 'not yet'}",
        f"- Ready for submission closeout: {'yes' if summary.get('ready_for_submission_closeout') else 'not yet'}",
        f"- Ready for live transition: {'yes' if summary.get('ready_for_live_transition') else 'not yet'}",
        f"- Ready for benchmark lock: {'yes' if summary.get('ready_for_benchmark_lock') else 'not yet'}",
        f"- Ready for submission lock: {'yes' if summary.get('ready_for_submission_lock') else 'not yet'}",
        f"- Ready for translational pilot: {'yes' if summary.get('ready_for_translational_pilot') else 'not yet'}",
        "",
        "## Recommended Actions",
        "",
    ]
    if recommended_actions:
        for action in recommended_actions:
            lines.append(f"- {action}")
    else:
        lines.append("- Nenhuma acao adicional prioritaria foi identificada.")
    return "\n".join(lines).strip()


def run_public_benchmark_pipeline(
    *,
    config_path: str,
    output_dir: str = "primevarclass_public_study_run",
    bootstrap_root_dir: str | None = None,
    delivery_dir: str | None = None,
    report_context: Dict[str, Any] | None = None,
    require_live_public_ready: bool = False,
) -> dict:
    context = dict(report_context or {})
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    resolution_dir = output_root / "resolved_inputs"
    preflight_dir = output_root / "resolved_preflight"
    study_dir = output_root / "resolved_study_run"

    resolution = export_study_public_config_resolution(
        config_path=config_path,
        output_dir=str(resolution_dir),
        bootstrap_root_dir=bootstrap_root_dir,
        delivery_dir=delivery_dir,
    )
    resolution_summary = dict(resolution.get("summary") or {})
    if require_live_public_ready and not resolution_summary.get("ready_for_live_public_study"):
        raise ValueError("O estudo publico ainda nao esta pronto para live public benchmark; conclua a resolucao das fontes.")

    resolved_config_path = str(resolution.get("resolved_study_config_path"))
    preflight = export_study_preflight(
        config_path=resolved_config_path,
        output_dir=str(preflight_dir),
        report_context=context,
    )
    preflight_summary = dict((preflight.get("preflight") or {}).get("summary") or {})

    study_results = run_publication_study(
        config_path=resolved_config_path,
        output_dir=str(study_dir),
        report_context=context,
    )

    execution_board = export_study_execution_board(
        public_resolution=resolution,
        preflight_export=preflight,
        study_results=study_results,
        output_dir=str(output_root),
        report_context=context,
    )
    execution_summary = dict((execution_board.get("study_execution_board") or {}).get("summary") or {})

    summary = {
        "generated_at": _now_utc(),
        "original_config_path": str(Path(config_path).resolve()),
        "resolved_study_config_path": resolved_config_path,
        "bootstrap_root_dir": str(Path(bootstrap_root_dir).resolve()) if bootstrap_root_dir else str(output_root),
        "resolution_percent": int(resolution_summary.get("overall_resolution_percent") or 0),
        "real_data_readiness_percent": int(resolution_summary.get("real_data_readiness_percent") or 0),
        "real_data_handoff_percent": int(resolution_summary.get("real_data_handoff_percent") or 0),
        "real_data_handoff_autofill_percent": int(resolution_summary.get("real_data_handoff_autofill_percent") or 0),
        "real_data_handoff_reconciliation_percent": int(resolution_summary.get("real_data_handoff_reconciliation_percent") or 0),
        "real_data_handoff_application_percent": int(resolution_summary.get("real_data_handoff_application_percent") or 0),
        "real_data_candidate_promotion_percent": int(resolution_summary.get("real_data_candidate_promotion_percent") or 0),
        "ready_for_real_data_study": bool(resolution_summary.get("ready_for_real_data_study")),
        "ready_for_lab_handoff": bool(resolution_summary.get("ready_for_lab_handoff")),
        "n_real_data_tasks": int(resolution_summary.get("n_real_data_tasks") or 0),
        "n_critical_real_data_tasks": int(resolution_summary.get("n_critical_real_data_tasks") or 0),
        "n_handoff_autofilled_tasks": int(resolution_summary.get("n_handoff_autofilled_tasks") or 0),
        "n_handoff_preserved_completed_tasks": int(resolution_summary.get("n_handoff_preserved_completed_tasks") or 0),
        "n_handoff_unmatched_tasks": int(resolution_summary.get("n_handoff_unmatched_tasks") or 0),
        "n_handoff_validated_tasks": int(resolution_summary.get("n_handoff_validated_tasks") or 0),
        "n_handoff_pending_tasks": int(resolution_summary.get("n_handoff_pending_tasks") or 0),
        "n_handoff_invalid_tasks": int(resolution_summary.get("n_handoff_invalid_tasks") or 0),
        "ready_for_reconciliation_rerun_from_autofill": bool(
            resolution_summary.get("ready_for_reconciliation_rerun_from_autofill")
        ),
        "n_handoff_applied_changes": int(resolution_summary.get("n_handoff_applied_changes") or 0),
        "ready_to_rerun_resolution_from_handoff": bool(resolution_summary.get("ready_to_rerun_resolution_from_handoff")),
        "ready_to_rerun_public_study_from_handoff": bool(resolution_summary.get("ready_to_rerun_public_study_from_handoff")),
        "ready_for_candidate_resolution_from_handoff": bool(resolution_summary.get("ready_for_candidate_resolution_from_handoff")),
        "ready_for_candidate_public_study_from_handoff": bool(resolution_summary.get("ready_for_candidate_public_study_from_handoff")),
        "ready_to_promote_candidate_config": bool(resolution_summary.get("ready_to_promote_candidate_config")),
        "ready_to_run_candidate_public_study": bool(resolution_summary.get("ready_to_run_candidate_public_study")),
        "preflight_percent": int(preflight_summary.get("overall_preflight_percent") or 0),
        "cohort_independence_percent": int(((study_results.get("cohort_independence_assessment") or {}).get("summary") or {}).get("overall_independence_percent") or 0),
        "comparative_evidence_percent": int(((study_results.get("comparative_evidence_assessment") or {}).get("summary") or {}).get("overall_comparative_strength_percent") or 0),
        "claim_strength_percent": int(((study_results.get("claim_strength_assessment") or {}).get("summary") or {}).get("overall_claim_strength_percent") or 0),
        "claim_tier": ((study_results.get("claim_strength_assessment") or {}).get("summary") or {}).get("claim_tier"),
        "publication_readiness_percent": int(((study_results.get("publication_readiness_assessment") or {}).get("summary") or {}).get("overall_readiness_percent") or 0),
        "validation_lock_percent": int(((study_results.get("study_validation_lock") or {}).get("summary") or {}).get("overall_validation_lock_percent") or 0),
        "execution_board_percent": int(execution_summary.get("overall_execution_percent") or 0),
        "ready_for_benchmark_lock": bool(execution_summary.get("ready_for_benchmark_lock")),
        "ready_for_submission_lock": bool(execution_summary.get("ready_for_submission_lock")),
        "ready_for_translational_pilot": bool(execution_summary.get("ready_for_translational_pilot")),
    }
    pilot_package = export_translational_pilot_package(
        summary=summary,
        resolution=resolution,
        preflight=preflight,
        study_results=study_results,
        execution_board=execution_board,
        output_dir=str(output_root),
        report_context=context,
    )
    pilot_summary = dict(pilot_package.get("translational_pilot_package_summary") or {})
    final_mile_package = export_final_mile_package(
        summary=summary,
        resolution=resolution,
        preflight=preflight,
        study_results=study_results,
        execution_board=execution_board,
        pilot_package=pilot_package,
        output_dir=str(output_root),
        report_context=context,
    )
    final_mile_summary = dict(final_mile_package.get("final_mile_package_summary") or {})

    recommended_actions = []
    recommended_actions.extend(list(resolution.get("recommended_actions") or []))
    recommended_actions.extend(list((preflight.get("preflight") or {}).get("recommended_actions") or []))
    recommended_actions.extend(list((execution_board.get("study_execution_board") or {}).get("recommended_actions") or []))
    recommended_actions.extend(list((pilot_package.get("translational_pilot_package") or {}).get("recommended_actions") or []))
    recommended_actions.extend(list((final_mile_package.get("final_mile_package") or {}).get("recommended_actions") or []))
    summary["pilot_package_percent"] = int(pilot_summary.get("overall_pilot_package_percent") or 0)
    summary["pilot_mode"] = pilot_summary.get("pilot_mode")
    summary["ready_for_demo_pilot"] = bool(pilot_summary.get("ready_for_demo_pilot"))
    summary["ready_for_shadow_pilot"] = bool(pilot_summary.get("ready_for_shadow_pilot"))
    summary["ready_for_live_pilot"] = bool(pilot_summary.get("ready_for_live_pilot"))
    summary["final_mile_percent"] = int(final_mile_summary.get("overall_final_mile_percent") or 0)
    summary["ready_for_real_data_execution"] = bool(final_mile_summary.get("ready_for_real_data_execution"))
    summary["ready_for_final_evidence_round"] = bool(final_mile_summary.get("ready_for_final_evidence_round"))
    summary["ready_for_submission_closeout"] = bool(final_mile_summary.get("ready_for_submission_closeout"))
    summary["ready_for_live_transition"] = bool(final_mile_summary.get("ready_for_live_transition"))
    summary["n_final_mile_blockers"] = int(final_mile_summary.get("n_blockers") or 0)
    summary["n_final_mile_critical_blockers"] = int(final_mile_summary.get("n_critical_blockers") or 0)
    summary["top_final_mile_blocker_phase"] = final_mile_summary.get("top_blocker_phase")
    summary["top_final_mile_blocker_title"] = final_mile_summary.get("top_blocker_title")
    pilot_store = PrimeVarClassPilotOpsStore(root_dir=output_root / "translational_ops")
    candidate_promotion_summary = {
        "overall_candidate_promotion_percent": summary.get("real_data_candidate_promotion_percent"),
    }
    translational_impact = export_translational_impact_package(
        summary={
            **summary,
            "study_execution_board_manifest_path": execution_board.get("study_execution_board_manifest_path"),
            "public_study_run_manifest_path": str(output_root / "public_study_run_manifest.json"),
            "study_real_data_candidate_promotion_manifest_path": resolution.get("study_real_data_candidate_promotion_manifest_path"),
        },
        pilot_package=pilot_package,
        final_mile_package=final_mile_package,
        candidate_promotion_summary=candidate_promotion_summary,
        session_rows=pilot_store.list_sessions(study_name=study_results.get("study_design").name if study_results.get("study_design") else None),
        feedback_rows=pilot_store.list_feedback(study_name=study_results.get("study_design").name if study_results.get("study_design") else None),
        output_dir=str(output_root),
        report_context=context,
    )
    translational_summary = dict(translational_impact.get("translational_impact_package_summary") or {})
    summary["translational_impact_percent"] = int(translational_summary.get("overall_translational_impact_percent") or 0)
    summary["ready_for_assisted_pilot_ops"] = bool(translational_summary.get("ready_for_assisted_pilot_ops"))
    summary["ready_for_shadow_rollout"] = bool(translational_summary.get("ready_for_shadow_rollout"))
    summary["ready_for_institutional_rollout"] = bool(translational_summary.get("ready_for_institutional_rollout"))
    recommended_actions.extend(list((translational_impact.get("translational_impact_package") or {}).get("recommended_actions") or []))
    roadmap = build_roadmap_progress()
    platform_completion = export_platform_completion_assessment(
        roadmap=roadmap,
        evidence_summary=summary,
        output_dir=str(output_root),
        report_context=context,
    )
    platform_completion_summary = dict(platform_completion.get("platform_completion_summary") or {})
    summary["platform_completion_percent"] = int(platform_completion_summary.get("overall_platform_completion_percent") or 0)
    summary["development_complete"] = bool(platform_completion_summary.get("development_complete"))
    summary["scientific_validation_pending"] = bool(platform_completion_summary.get("scientific_validation_pending"))
    summary["evidence_execution_percent"] = int(platform_completion_summary.get("evidence_execution_percent") or 0)
    recommended_actions.extend(list((platform_completion.get("platform_completion") or {}).get("recommended_actions") or []))

    manifest = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "report_context": context,
        "resolution_manifest_path": resolution.get("study_public_config_resolution_manifest_path"),
        "resolution_report_markdown_path": resolution.get("study_public_config_resolution_report_markdown_path"),
        "cohort_freeze_manifest_path": study_results.get("study_cohort_freeze_manifest_path") or resolution.get("study_cohort_freeze_manifest_path"),
        "cohort_freeze_markdown_path": study_results.get("study_cohort_freeze_markdown_path") or resolution.get("study_cohort_freeze_markdown_path"),
        "real_data_handoff_manifest_path": resolution.get("study_real_data_handoff_manifest_path"),
        "real_data_handoff_markdown_path": resolution.get("study_real_data_handoff_markdown_path"),
        "real_data_handoff_html_path": resolution.get("study_real_data_handoff_html_path"),
        "real_data_handoff_autofill_manifest_path": resolution.get("study_real_data_handoff_autofill_manifest_path"),
        "real_data_handoff_autofill_markdown_path": resolution.get("study_real_data_handoff_autofill_markdown_path"),
        "real_data_handoff_autofill_html_path": resolution.get("study_real_data_handoff_autofill_html_path"),
        "real_data_handoff_autofill_tracker_path": resolution.get("study_real_data_handoff_autofill_tracker_path"),
        "real_data_handoff_autofill_matches_path": resolution.get("study_real_data_handoff_autofill_matches_path"),
        "real_data_handoff_autofill_inventory_path": resolution.get("study_real_data_handoff_autofill_inventory_path"),
        "real_data_handoff_tracker_path": resolution.get("study_real_data_handoff_tracker_path"),
        "real_data_handoff_reconciliation_manifest_path": resolution.get("study_real_data_handoff_reconciliation_manifest_path"),
        "real_data_handoff_reconciliation_markdown_path": resolution.get("study_real_data_handoff_reconciliation_markdown_path"),
        "real_data_handoff_reconciliation_html_path": resolution.get("study_real_data_handoff_reconciliation_html_path"),
        "real_data_handoff_reconciliation_tasks_path": resolution.get("study_real_data_handoff_reconciliation_tasks_path"),
        "real_data_candidate_config_path": resolution.get("study_real_data_candidate_config_path"),
        "real_data_handoff_application_manifest_path": resolution.get("study_real_data_handoff_application_manifest_path"),
        "real_data_handoff_application_markdown_path": resolution.get("study_real_data_handoff_application_markdown_path"),
        "real_data_handoff_application_html_path": resolution.get("study_real_data_handoff_application_html_path"),
        "real_data_handoff_application_sources_path": resolution.get("study_real_data_handoff_application_sources_path"),
        "real_data_candidate_promotion_manifest_path": resolution.get("study_real_data_candidate_promotion_manifest_path"),
        "real_data_candidate_promotion_markdown_path": resolution.get("study_real_data_candidate_promotion_markdown_path"),
        "real_data_candidate_promotion_html_path": resolution.get("study_real_data_candidate_promotion_html_path"),
        "real_data_candidate_promotion_criteria_path": resolution.get("study_real_data_candidate_promotion_criteria_path"),
        "real_data_candidate_promotion_blockers_path": resolution.get("study_real_data_candidate_promotion_blockers_path"),
        "preflight_manifest_path": preflight.get("study_preflight_manifest_path"),
        "preflight_report_markdown_path": preflight.get("study_preflight_report_markdown_path"),
        "study_release_manifest_path": study_results.get("study_release_manifest_path"),
        "study_summary_report_path": study_results.get("study_summary_report_path"),
        "cohort_independence_manifest_path": study_results.get("cohort_independence_manifest_path"),
        "cohort_independence_report_markdown_path": study_results.get("cohort_independence_report_markdown_path"),
        "comparative_evidence_manifest_path": study_results.get("comparative_evidence_manifest_path"),
        "comparative_evidence_report_markdown_path": study_results.get("comparative_evidence_report_markdown_path"),
        "claim_strength_manifest_path": study_results.get("claim_strength_manifest_path"),
        "claim_strength_report_markdown_path": study_results.get("claim_strength_report_markdown_path"),
        "publication_readiness_manifest_path": study_results.get("publication_readiness_manifest_path"),
        "study_validation_lock_manifest_path": study_results.get("study_validation_lock_manifest_path"),
        "study_validation_lock_markdown_path": study_results.get("study_validation_lock_markdown_path"),
        "execution_board_manifest_path": execution_board.get("study_execution_board_manifest_path"),
        "execution_board_markdown_path": execution_board.get("study_execution_board_markdown_path"),
        "translational_pilot_package_manifest_path": pilot_package.get("translational_pilot_package_manifest_path"),
        "translational_pilot_package_markdown_path": pilot_package.get("translational_pilot_package_markdown_path"),
        "translational_pilot_package_html_path": pilot_package.get("translational_pilot_package_html_path"),
        "translational_pilot_package_criteria_path": pilot_package.get("translational_pilot_package_criteria_path"),
        "translational_pilot_package_checklist_path": pilot_package.get("translational_pilot_package_checklist_path"),
        "translational_impact_package_manifest_path": translational_impact.get("translational_impact_package_manifest_path"),
        "translational_impact_package_markdown_path": translational_impact.get("translational_impact_package_markdown_path"),
        "translational_impact_package_html_path": translational_impact.get("translational_impact_package_html_path"),
        "translational_impact_package_criteria_path": translational_impact.get("translational_impact_package_criteria_path"),
        "translational_impact_sessions_path": translational_impact.get("translational_impact_sessions_path"),
        "translational_impact_feedback_path": translational_impact.get("translational_impact_feedback_path"),
        "platform_completion_manifest_path": platform_completion.get("platform_completion_manifest_path"),
        "platform_completion_markdown_path": platform_completion.get("platform_completion_markdown_path"),
        "platform_completion_html_path": platform_completion.get("platform_completion_html_path"),
        "final_mile_package_manifest_path": final_mile_package.get("final_mile_package_manifest_path"),
        "final_mile_package_markdown_path": final_mile_package.get("final_mile_package_markdown_path"),
        "final_mile_package_html_path": final_mile_package.get("final_mile_package_html_path"),
        "final_mile_package_criteria_path": final_mile_package.get("final_mile_package_criteria_path"),
        "final_mile_package_blockers_path": final_mile_package.get("final_mile_package_blockers_path"),
        "final_mile_package_checklist_path": final_mile_package.get("final_mile_package_checklist_path"),
        "recommended_actions": recommended_actions,
    }

    manifest_path = output_root / "public_study_run_manifest.json"
    report_path = output_root / "public_study_run_report.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(_build_public_study_run_report(summary, recommended_actions), encoding="utf-8")

    return {
        "output_dir": str(output_root),
        "summary": summary,
        "recommended_actions": recommended_actions,
        "resolved_study_config_path": resolved_config_path,
        "study_public_config_resolution_manifest_path": resolution.get("study_public_config_resolution_manifest_path"),
        "study_public_config_resolution_report_markdown_path": resolution.get("study_public_config_resolution_report_markdown_path"),
        "study_cohort_freeze_manifest_path": study_results.get("study_cohort_freeze_manifest_path") or resolution.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_markdown_path": study_results.get("study_cohort_freeze_markdown_path") or resolution.get("study_cohort_freeze_markdown_path"),
        "study_real_data_handoff_manifest_path": resolution.get("study_real_data_handoff_manifest_path"),
        "study_real_data_handoff_markdown_path": resolution.get("study_real_data_handoff_markdown_path"),
        "study_real_data_handoff_html_path": resolution.get("study_real_data_handoff_html_path"),
        "study_real_data_handoff_autofill_manifest_path": resolution.get("study_real_data_handoff_autofill_manifest_path"),
        "study_real_data_handoff_autofill_markdown_path": resolution.get("study_real_data_handoff_autofill_markdown_path"),
        "study_real_data_handoff_autofill_html_path": resolution.get("study_real_data_handoff_autofill_html_path"),
        "study_real_data_handoff_autofill_tracker_path": resolution.get("study_real_data_handoff_autofill_tracker_path"),
        "study_real_data_handoff_autofill_matches_path": resolution.get("study_real_data_handoff_autofill_matches_path"),
        "study_real_data_handoff_autofill_inventory_path": resolution.get("study_real_data_handoff_autofill_inventory_path"),
        "study_real_data_handoff_tracker_path": resolution.get("study_real_data_handoff_tracker_path"),
        "study_real_data_handoff_reconciliation_manifest_path": resolution.get("study_real_data_handoff_reconciliation_manifest_path"),
        "study_real_data_handoff_reconciliation_markdown_path": resolution.get("study_real_data_handoff_reconciliation_markdown_path"),
        "study_real_data_handoff_reconciliation_html_path": resolution.get("study_real_data_handoff_reconciliation_html_path"),
        "study_real_data_handoff_reconciliation_tasks_path": resolution.get("study_real_data_handoff_reconciliation_tasks_path"),
        "study_real_data_candidate_config_path": resolution.get("study_real_data_candidate_config_path"),
        "study_real_data_handoff_application_manifest_path": resolution.get("study_real_data_handoff_application_manifest_path"),
        "study_real_data_handoff_application_markdown_path": resolution.get("study_real_data_handoff_application_markdown_path"),
        "study_real_data_handoff_application_html_path": resolution.get("study_real_data_handoff_application_html_path"),
        "study_real_data_handoff_application_sources_path": resolution.get("study_real_data_handoff_application_sources_path"),
        "study_real_data_candidate_promotion_manifest_path": resolution.get("study_real_data_candidate_promotion_manifest_path"),
        "study_real_data_candidate_promotion_markdown_path": resolution.get("study_real_data_candidate_promotion_markdown_path"),
        "study_real_data_candidate_promotion_html_path": resolution.get("study_real_data_candidate_promotion_html_path"),
        "study_real_data_candidate_promotion_criteria_path": resolution.get("study_real_data_candidate_promotion_criteria_path"),
        "study_real_data_candidate_promotion_blockers_path": resolution.get("study_real_data_candidate_promotion_blockers_path"),
        "study_preflight_manifest_path": preflight.get("study_preflight_manifest_path"),
        "study_preflight_report_markdown_path": preflight.get("study_preflight_report_markdown_path"),
        "study_output_dir": str(study_dir),
        "study_release_manifest_path": study_results.get("study_release_manifest_path"),
        "cohort_independence_manifest_path": study_results.get("cohort_independence_manifest_path"),
        "cohort_independence_report_markdown_path": study_results.get("cohort_independence_report_markdown_path"),
        "comparative_evidence_manifest_path": study_results.get("comparative_evidence_manifest_path"),
        "comparative_evidence_report_markdown_path": study_results.get("comparative_evidence_report_markdown_path"),
        "claim_strength_manifest_path": study_results.get("claim_strength_manifest_path"),
        "claim_strength_report_markdown_path": study_results.get("claim_strength_report_markdown_path"),
        "publication_readiness_manifest_path": study_results.get("publication_readiness_manifest_path"),
        "study_validation_lock_manifest_path": study_results.get("study_validation_lock_manifest_path"),
        "study_validation_lock_markdown_path": study_results.get("study_validation_lock_markdown_path"),
        "study_execution_board_manifest_path": execution_board.get("study_execution_board_manifest_path"),
        "study_execution_board_markdown_path": execution_board.get("study_execution_board_markdown_path"),
        "study_execution_board_html_path": execution_board.get("study_execution_board_html_path"),
        "translational_pilot_package_manifest_path": pilot_package.get("translational_pilot_package_manifest_path"),
        "translational_pilot_package_markdown_path": pilot_package.get("translational_pilot_package_markdown_path"),
        "translational_pilot_package_html_path": pilot_package.get("translational_pilot_package_html_path"),
        "translational_pilot_package_criteria_path": pilot_package.get("translational_pilot_package_criteria_path"),
        "translational_pilot_package_checklist_path": pilot_package.get("translational_pilot_package_checklist_path"),
        "translational_impact_package_manifest_path": translational_impact.get("translational_impact_package_manifest_path"),
        "translational_impact_package_markdown_path": translational_impact.get("translational_impact_package_markdown_path"),
        "translational_impact_package_html_path": translational_impact.get("translational_impact_package_html_path"),
        "translational_impact_package_criteria_path": translational_impact.get("translational_impact_package_criteria_path"),
        "translational_impact_sessions_path": translational_impact.get("translational_impact_sessions_path"),
        "translational_impact_feedback_path": translational_impact.get("translational_impact_feedback_path"),
        "platform_completion_manifest_path": platform_completion.get("platform_completion_manifest_path"),
        "platform_completion_markdown_path": platform_completion.get("platform_completion_markdown_path"),
        "platform_completion_html_path": platform_completion.get("platform_completion_html_path"),
        "final_mile_package_manifest_path": final_mile_package.get("final_mile_package_manifest_path"),
        "final_mile_package_markdown_path": final_mile_package.get("final_mile_package_markdown_path"),
        "final_mile_package_html_path": final_mile_package.get("final_mile_package_html_path"),
        "final_mile_package_criteria_path": final_mile_package.get("final_mile_package_criteria_path"),
        "final_mile_package_blockers_path": final_mile_package.get("final_mile_package_blockers_path"),
        "final_mile_package_checklist_path": final_mile_package.get("final_mile_package_checklist_path"),
        "public_study_run_manifest_path": str(manifest_path),
        "public_study_run_report_markdown_path": str(report_path),
        "study_results": study_results,
        "resolution": resolution,
        "preflight": preflight,
        "execution_board": execution_board,
        "pilot_package": pilot_package,
        "translational_impact_package": translational_impact,
        "platform_completion": platform_completion,
        "final_mile_package": final_mile_package,
    }
