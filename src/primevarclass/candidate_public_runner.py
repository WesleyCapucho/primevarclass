from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .public_study_runner import run_public_benchmark_pipeline


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def run_candidate_public_benchmark_pipeline(
    *,
    candidate_config_path: str,
    output_dir: str = "primevarclass_candidate_public_study_run",
    candidate_promotion_manifest_path: str | None = None,
    require_candidate_ready: bool = True,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    candidate_config_file = Path(candidate_config_path).resolve()
    if not candidate_config_file.exists():
        raise ValueError("Candidate config nao encontrado.")

    promotion_manifest = _load_json(candidate_promotion_manifest_path)
    promotion_summary = dict(promotion_manifest.get("summary") or {})
    ready_to_run = bool(promotion_summary.get("ready_to_run_candidate_public_study"))
    if require_candidate_ready and candidate_promotion_manifest_path and not ready_to_run:
        raise ValueError("Candidate public study ainda nao esta pronto; conclua as pendencias do pacote de promocao.")

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    run_results = run_public_benchmark_pipeline(
        config_path=str(candidate_config_file),
        output_dir=str(output_root),
        bootstrap_root_dir=str(candidate_config_file.parent),
        report_context=context,
        require_live_public_ready=False,
    )
    run_summary = dict(run_results.get("summary") or {})

    promotion_percent = int(promotion_summary.get("overall_candidate_promotion_percent") or 0)
    launch_percent = int(round((promotion_percent + int(run_summary.get("resolution_percent") or 0) + int(run_summary.get("preflight_percent") or 0)) / 3))
    summary = {
        "generated_at": _now_utc(),
        "candidate_config_path": str(candidate_config_file),
        "candidate_promotion_percent": promotion_percent,
        "candidate_ready_before_launch": ready_to_run,
        "candidate_launch_percent": launch_percent,
        "candidate_run_output_dir": run_results.get("output_dir"),
        "publication_readiness_percent": run_summary.get("publication_readiness_percent"),
        "comparative_evidence_percent": run_summary.get("comparative_evidence_percent"),
        "claim_strength_percent": run_summary.get("claim_strength_percent"),
        "real_data_readiness_percent": run_summary.get("real_data_readiness_percent"),
        "ready_for_submission_lock": run_summary.get("ready_for_submission_lock"),
        "ready_for_shadow_rollout": run_summary.get("ready_for_shadow_rollout"),
    }

    recommended_actions = []
    if not ready_to_run and candidate_promotion_manifest_path:
        recommended_actions.append("Fechar as pendencias do pacote de promocao candidata antes da rodada final controlada.")
    recommended_actions.extend(list(run_results.get("recommended_actions") or []))
    if not recommended_actions:
        recommended_actions.append("Candidate public study concluido sem acoes adicionais prioritarias.")

    report_lines = [
        "# PrimeVarClass Candidate Public Study Run",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Candidate config: {summary['candidate_config_path']}",
        f"- Candidate promotion: {summary['candidate_promotion_percent']}%",
        f"- Candidate launch readiness: {summary['candidate_launch_percent']}%",
        f"- Candidate ready before launch: {'yes' if summary['candidate_ready_before_launch'] else 'not yet'}",
        f"- Real-data readiness: {summary['real_data_readiness_percent'] or 0}%",
        f"- Comparative evidence: {summary['comparative_evidence_percent'] or 0}%",
        f"- Claim strength: {summary['claim_strength_percent'] or 0}%",
        f"- Publication readiness: {summary['publication_readiness_percent'] or 0}%",
        f"- Ready for submission lock: {'yes' if summary['ready_for_submission_lock'] else 'not yet'}",
        "",
        "## Recommended Actions",
        "",
    ]
    for action in recommended_actions:
        report_lines.append(f"- {action}")

    manifest = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "report_context": context,
        "candidate_promotion_manifest_path": str(Path(candidate_promotion_manifest_path).resolve()) if candidate_promotion_manifest_path else None,
        "candidate_public_run_report_markdown_path": str(output_root / "candidate_public_run_report.md"),
        "candidate_public_run_manifest_path": str(output_root / "candidate_public_run_manifest.json"),
        "public_study_run_manifest_path": run_results.get("public_study_run_manifest_path"),
        "public_study_run_report_markdown_path": run_results.get("public_study_run_report_markdown_path"),
        "recommended_actions": recommended_actions,
    }

    report_path = output_root / "candidate_public_run_report.md"
    manifest_path = output_root / "candidate_public_run_manifest.json"
    report_path.write_text("\n".join(report_lines).strip(), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        **run_results,
        "candidate_public_run_summary": summary,
        "candidate_public_run_manifest_path": str(manifest_path),
        "candidate_public_run_report_markdown_path": str(report_path),
    }
