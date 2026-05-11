from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd


SESSION_COLUMNS = [
    "session_id",
    "study_name",
    "pilot_mode",
    "site_name",
    "institution",
    "team_name",
    "operator_name",
    "status",
    "cases_reviewed",
    "variants_flagged",
    "started_at",
    "completed_at",
    "outcome_summary",
    "notes",
    "created_at",
    "updated_at",
]

FEEDBACK_COLUMNS = [
    "feedback_id",
    "session_id",
    "study_name",
    "operator_name",
    "role",
    "confidence_score",
    "actionability_score",
    "time_saved_minutes",
    "adoption_recommendation",
    "incident_level",
    "notes",
    "created_at",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _mean_percent(values: Iterable[float], scale: float = 1.0) -> int:
    values = [float(item) for item in values if item is not None]
    if not values:
        return 0
    return int(round((sum(values) / len(values)) * scale))


def _artifact_exists(path_value: Any) -> bool:
    if not path_value:
        return False
    try:
        return Path(str(path_value)).exists()
    except Exception:
        return False


def _normalize_mode(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"demo_mode", "internal_validation", "shadow_mode", "live_candidate"}:
        return token
    return "shadow_mode"


def _normalize_status(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"planned", "running", "completed", "cancelled"}:
        return token
    return "planned"


def _recommendation_score(value: Any) -> int:
    token = str(value or "").strip().lower()
    if token in {"yes", "strong_yes", "recommended"}:
        return 100
    if token in {"conditional", "maybe"}:
        return 70
    if token in {"no", "not_recommended"}:
        return 20
    return 0


def _incident_penalty(value: Any) -> int:
    token = str(value or "").strip().lower()
    if token in {"critical", "high"}:
        return 50
    if token == "medium":
        return 25
    if token == "low":
        return 10
    return 0


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


class PrimeVarClassPilotOpsStore:
    def __init__(self, root_dir: str | Path | None = None):
        self.root_dir = Path(root_dir or (Path.cwd() / "primevarclass_translational_ops")).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sessions_path(self) -> Path:
        return self.root_dir / "pilot_sessions.csv"

    @property
    def feedback_path(self) -> Path:
        return self.root_dir / "pilot_feedback.csv"

    def _read_csv(self, path: Path, columns: list[str]) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame(columns=columns)
        frame = pd.read_csv(path)
        for column in columns:
            if column not in frame.columns:
                frame[column] = ""
        return frame[columns].copy()

    def list_sessions(self, study_name: str | None = None) -> list[dict]:
        frame = self._read_csv(self.sessions_path, SESSION_COLUMNS)
        if study_name:
            frame = frame[frame["study_name"].astype(str) == str(study_name)]
        if not frame.empty:
            frame = frame.sort_values(by=["updated_at", "session_id"], ascending=[False, True], na_position="last")
        return frame.to_dict(orient="records")

    def list_feedback(self, study_name: str | None = None, session_id: str | None = None) -> list[dict]:
        frame = self._read_csv(self.feedback_path, FEEDBACK_COLUMNS)
        if study_name:
            frame = frame[frame["study_name"].astype(str) == str(study_name)]
        if session_id:
            frame = frame[frame["session_id"].astype(str) == str(session_id)]
        if not frame.empty:
            frame = frame.sort_values(by=["created_at", "feedback_id"], ascending=[False, True], na_position="last")
        return frame.to_dict(orient="records")

    def upsert_session(self, payload: Dict[str, Any]) -> dict:
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            raise ValueError("session_id e obrigatorio.")
        frame = self._read_csv(self.sessions_path, SESSION_COLUMNS)
        now = _now_utc()
        row = {
            "session_id": session_id,
            "study_name": str(payload.get("study_name") or "").strip(),
            "pilot_mode": _normalize_mode(payload.get("pilot_mode")),
            "site_name": str(payload.get("site_name") or "").strip(),
            "institution": str(payload.get("institution") or "").strip(),
            "team_name": str(payload.get("team_name") or "").strip(),
            "operator_name": str(payload.get("operator_name") or "").strip(),
            "status": _normalize_status(payload.get("status")),
            "cases_reviewed": _safe_int(payload.get("cases_reviewed")),
            "variants_flagged": _safe_int(payload.get("variants_flagged")),
            "started_at": str(payload.get("started_at") or "").strip(),
            "completed_at": str(payload.get("completed_at") or "").strip(),
            "outcome_summary": str(payload.get("outcome_summary") or "").strip(),
            "notes": str(payload.get("notes") or "").strip(),
            "created_at": now,
            "updated_at": now,
        }
        existing_mask = frame["session_id"].astype(str) == session_id
        if existing_mask.any():
            existing = frame.loc[existing_mask].iloc[0].to_dict()
            row["created_at"] = str(existing.get("created_at") or now)
            frame = frame.loc[~existing_mask].copy()
        frame = pd.concat([frame, pd.DataFrame([row], columns=SESSION_COLUMNS)], ignore_index=True)
        frame.to_csv(self.sessions_path, index=False)
        return row

    def add_feedback(self, payload: Dict[str, Any]) -> dict:
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            raise ValueError("session_id e obrigatorio para feedback.")
        study_name = str(payload.get("study_name") or "").strip()
        feedback_id = str(payload.get("feedback_id") or "").strip() or f"{session_id}::{_now_utc()}"
        row = {
            "feedback_id": feedback_id,
            "session_id": session_id,
            "study_name": study_name,
            "operator_name": str(payload.get("operator_name") or "").strip(),
            "role": str(payload.get("role") or "").strip(),
            "confidence_score": max(0, min(5, _safe_int(payload.get("confidence_score")))),
            "actionability_score": max(0, min(5, _safe_int(payload.get("actionability_score")))),
            "time_saved_minutes": max(0, _safe_int(payload.get("time_saved_minutes"))),
            "adoption_recommendation": str(payload.get("adoption_recommendation") or "").strip(),
            "incident_level": str(payload.get("incident_level") or "none").strip().lower() or "none",
            "notes": str(payload.get("notes") or "").strip(),
            "created_at": _now_utc(),
        }
        frame = self._read_csv(self.feedback_path, FEEDBACK_COLUMNS)
        frame = pd.concat([frame, pd.DataFrame([row], columns=FEEDBACK_COLUMNS)], ignore_index=True)
        frame.to_csv(self.feedback_path, index=False)
        return row


def build_translational_impact_dashboard(
    *,
    session_rows: List[dict],
    feedback_rows: List[dict],
    study_name: str | None = None,
) -> dict:
    sessions_df = pd.DataFrame(session_rows or [], columns=SESSION_COLUMNS)
    feedback_df = pd.DataFrame(feedback_rows or [], columns=FEEDBACK_COLUMNS)
    if study_name and not sessions_df.empty:
        sessions_df = sessions_df[sessions_df["study_name"].astype(str) == str(study_name)].copy()
    if study_name and not feedback_df.empty:
        feedback_df = feedback_df[feedback_df["study_name"].astype(str) == str(study_name)].copy()

    n_sessions = int(len(sessions_df))
    n_completed_sessions = int((sessions_df["status"].astype(str) == "completed").sum()) if not sessions_df.empty else 0
    n_shadow_sessions = int((sessions_df["pilot_mode"].astype(str) == "shadow_mode").sum()) if not sessions_df.empty else 0
    n_live_sessions = int((sessions_df["pilot_mode"].astype(str) == "live_candidate").sum()) if not sessions_df.empty else 0
    cases_reviewed_total = int(sessions_df["cases_reviewed"].fillna(0).astype(int).sum()) if not sessions_df.empty else 0
    variants_flagged_total = int(sessions_df["variants_flagged"].fillna(0).astype(int).sum()) if not sessions_df.empty else 0
    n_feedback = int(len(feedback_df))
    avg_confidence_percent = _mean_percent(feedback_df["confidence_score"].fillna(0).astype(float).tolist(), scale=20.0) if not feedback_df.empty else 0
    avg_actionability_percent = _mean_percent(feedback_df["actionability_score"].fillna(0).astype(float).tolist(), scale=20.0) if not feedback_df.empty else 0
    adoption_percent = _mean_percent([_recommendation_score(item) for item in feedback_df["adoption_recommendation"].tolist()]) if not feedback_df.empty else 0
    incident_penalty = max((_incident_penalty(item) for item in feedback_df["incident_level"].tolist()), default=0)
    feedback_coverage_percent = int(round((n_feedback / max(n_completed_sessions, 1)) * 100)) if n_completed_sessions else 0
    total_time_saved_minutes = int(feedback_df["time_saved_minutes"].fillna(0).astype(int).sum()) if not feedback_df.empty else 0
    operator_satisfaction_percent = int(round((avg_confidence_percent + avg_actionability_percent + adoption_percent) / 3)) if n_feedback else 0
    rollout_signal_percent = max(0, int(round((feedback_coverage_percent + operator_satisfaction_percent) / 2)) - incident_penalty)

    summary = {
        "study_name": study_name or "",
        "n_sessions": n_sessions,
        "n_completed_sessions": n_completed_sessions,
        "n_shadow_sessions": n_shadow_sessions,
        "n_live_sessions": n_live_sessions,
        "cases_reviewed_total": cases_reviewed_total,
        "variants_flagged_total": variants_flagged_total,
        "n_feedback_entries": n_feedback,
        "feedback_coverage_percent": feedback_coverage_percent,
        "operator_satisfaction_percent": operator_satisfaction_percent,
        "rollout_signal_percent": rollout_signal_percent,
        "avg_confidence_percent": avg_confidence_percent,
        "avg_actionability_percent": avg_actionability_percent,
        "adoption_percent": adoption_percent,
        "incident_penalty": incident_penalty,
        "time_saved_minutes_total": total_time_saved_minutes,
    }
    return {
        "summary": summary,
        "sessions": sessions_df.to_dict(orient="records"),
        "feedback": feedback_df.to_dict(orient="records"),
    }


def build_translational_impact_package(
    *,
    summary: dict,
    pilot_package: dict,
    final_mile_package: dict,
    candidate_promotion_summary: dict | None = None,
    session_rows: List[dict] | None = None,
    feedback_rows: List[dict] | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    pilot_summary = dict(pilot_package.get("translational_pilot_package_summary") or {})
    final_summary = dict(final_mile_package.get("final_mile_package_summary") or {})
    candidate_summary = dict(candidate_promotion_summary or {})
    study_name = str(pilot_summary.get("study_name") or summary.get("study_name") or context.get("study_name") or "PrimeVarClass Translational Impact")
    title = str(context.get("report_title") or f"{study_name} - Translational Impact Package")

    dashboard = build_translational_impact_dashboard(
        session_rows=session_rows or [],
        feedback_rows=feedback_rows or [],
        study_name=study_name if study_name else None,
    )
    dashboard_summary = dict(dashboard.get("summary") or {})

    pilot_package_percent = _safe_int(summary.get("pilot_package_percent") or pilot_summary.get("overall_pilot_package_percent"))
    final_mile_percent = _safe_int(summary.get("final_mile_percent") or final_summary.get("overall_final_mile_percent"))
    candidate_promotion_percent = _safe_int(summary.get("real_data_candidate_promotion_percent") or candidate_summary.get("overall_candidate_promotion_percent"))
    package_artifacts = [
        pilot_package.get("translational_pilot_package_manifest_path"),
        final_mile_package.get("final_mile_package_manifest_path"),
        summary.get("study_real_data_candidate_promotion_manifest_path"),
        summary.get("study_execution_board_manifest_path"),
        summary.get("public_study_run_manifest_path"),
    ]
    package_integrity_percent = int(round(sum(1 for item in package_artifacts if _artifact_exists(item)) / len(package_artifacts) * 100)) if package_artifacts else 0
    execution_signal_percent = int(round((pilot_package_percent + max(0, 100 - _safe_int(summary.get("n_final_mile_critical_blockers")) * 20)) / 2))
    feedback_signal_percent = dashboard_summary.get("rollout_signal_percent", 0)
    adoption_signal_percent = dashboard_summary.get("operator_satisfaction_percent", 0)
    institutional_rollout_percent = int(
        round(
            (
                execution_signal_percent
                + candidate_promotion_percent
                + feedback_signal_percent
                + package_integrity_percent
            ) / 4
        )
    )

    ready_for_assisted_pilot_ops = bool(pilot_summary.get("ready_for_demo_pilot") and package_integrity_percent >= 80)
    ready_for_shadow_rollout = bool(
        pilot_summary.get("ready_for_shadow_pilot")
        and dashboard_summary.get("n_completed_sessions", 0) >= 1
        and feedback_signal_percent >= 60
    )
    ready_for_institutional_rollout = bool(
        ready_for_shadow_rollout
        and dashboard_summary.get("n_completed_sessions", 0) >= 2
        and dashboard_summary.get("operator_satisfaction_percent", 0) >= 75
        and dashboard_summary.get("incident_penalty", 0) == 0
        and final_mile_percent >= 70
    )

    criteria = [
        _criterion_row(
            "platform_enablement",
            "Platform enablement",
            1.0,
            package_integrity_percent,
            f"{package_integrity_percent}% dos artefatos translacionais e manifests foram materializados.",
            "Garantir que cada rodada publica mantenha os manifests operacionais de piloto, candidate promotion e closeout.",
        ),
        _criterion_row(
            "pilot_operability",
            "Pilot operability",
            1.2,
            pilot_package_percent,
            f"Pacote translacional em {pilot_package_percent}% e pilot_mode={pilot_summary.get('pilot_mode') or '-'}.",
            "Usar a workbench e a API como superficie principal do piloto assistido.",
        ),
        _criterion_row(
            "candidate_transition",
            "Candidate transition",
            1.15,
            candidate_promotion_percent,
            f"Candidate promotion em {candidate_promotion_percent}% com rerrodada controlada explicitada no pacote.",
            "Promover o candidate config apenas quando o tracker estiver validado e auditado.",
        ),
        _criterion_row(
            "field_feedback",
            "Field feedback signal",
            1.2,
            feedback_signal_percent,
            (
                f"Feedback coverage={dashboard_summary.get('feedback_coverage_percent', 0)}%, "
                f"satisfacao={dashboard_summary.get('operator_satisfaction_percent', 0)}% "
                f"e incident penalty={dashboard_summary.get('incident_penalty', 0)}."
            ),
            "Registrar sessoes, feedback e tempo economizado para tornar o impacto medido e nao apenas estimado.",
        ),
        _criterion_row(
            "institutional_rollout",
            "Institutional rollout signal",
            1.25,
            institutional_rollout_percent,
            (
                f"Rollout em {institutional_rollout_percent}% com {dashboard_summary.get('n_completed_sessions', 0)} sessao(oes) concluida(s)."
            ),
            "Consolidar pelo menos duas sessoes concluidas com feedback positivo e sem incidentes altos.",
        ),
    ]
    total_weight = sum(item["weight"] for item in criteria) or 1.0
    overall_percent = int(round(sum(item["weight"] * item["score_percent"] for item in criteria) / total_weight))

    recommended_actions = [item["next_step"] for item in criteria if item["score_percent"] < 85]
    if not recommended_actions:
        recommended_actions.append("Camada translacional pronta para operacao recorrente e institucional.")

    summary_payload = {
        "title": title,
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_translational_impact_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "package_integrity_percent": package_integrity_percent,
        "pilot_operability_percent": pilot_package_percent,
        "candidate_transition_percent": candidate_promotion_percent,
        "field_feedback_percent": feedback_signal_percent,
        "institutional_rollout_percent": institutional_rollout_percent,
        "ready_for_assisted_pilot_ops": ready_for_assisted_pilot_ops,
        "ready_for_shadow_rollout": ready_for_shadow_rollout,
        "ready_for_institutional_rollout": ready_for_institutional_rollout,
        "n_sessions": dashboard_summary.get("n_sessions", 0),
        "n_completed_sessions": dashboard_summary.get("n_completed_sessions", 0),
        "n_feedback_entries": dashboard_summary.get("n_feedback_entries", 0),
    }

    markdown_lines = [
        f"# {title}",
        "",
        f"- Generated at: {summary_payload['generated_at']}",
        f"- Translational impact package: {summary_payload['overall_translational_impact_percent']}%",
        f"- Ready for assisted pilot ops: {'yes' if summary_payload['ready_for_assisted_pilot_ops'] else 'not yet'}",
        f"- Ready for shadow rollout: {'yes' if summary_payload['ready_for_shadow_rollout'] else 'not yet'}",
        f"- Ready for institutional rollout: {'yes' if summary_payload['ready_for_institutional_rollout'] else 'not yet'}",
        "",
        "## Criteria",
        "",
    ]
    for item in criteria:
        markdown_lines.append(
            f"- {item['title']}: {item['score_percent']}% | {item['evidence']} | Next: {item['next_step']}"
        )
    markdown_lines.extend(["", "## Pilot Operations", ""])
    markdown_lines.extend(
        [
            f"- Sessions: {dashboard_summary.get('n_sessions', 0)} total / {dashboard_summary.get('n_completed_sessions', 0)} completed",
            f"- Feedback entries: {dashboard_summary.get('n_feedback_entries', 0)}",
            f"- Cases reviewed: {dashboard_summary.get('cases_reviewed_total', 0)}",
            f"- Time saved: {dashboard_summary.get('time_saved_minutes_total', 0)} minutes",
        ]
    )
    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary_payload,
        "criteria": criteria,
        "dashboard": dashboard,
        "recommended_actions": recommended_actions,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_translational_impact_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Translational Impact Package</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f4efe5;color:#17303c;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#9a5d2d;}ul{background:#fff;border:1px solid #e5dac9;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_translational_impact_package(
    *,
    summary: dict,
    pilot_package: dict,
    final_mile_package: dict,
    candidate_promotion_summary: dict | None = None,
    session_rows: List[dict] | None = None,
    feedback_rows: List[dict] | None = None,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_translational_impact_package(
        summary=summary,
        pilot_package=pilot_package,
        final_mile_package=final_mile_package,
        candidate_promotion_summary=candidate_promotion_summary,
        session_rows=session_rows,
        feedback_rows=feedback_rows,
        report_context=report_context,
    )

    markdown_path = root / "translational_impact_package.md"
    html_path = root / "translational_impact_package.html"
    manifest_path = root / "translational_impact_package_manifest.json"
    criteria_path = root / "translational_impact_package_criteria.csv"
    sessions_path = root / "translational_impact_sessions.csv"
    feedback_path = root / "translational_impact_feedback.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_translational_impact_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("criteria") or []).to_csv(criteria_path, index=False)
    pd.DataFrame((bundle.get("dashboard") or {}).get("sessions") or []).to_csv(sessions_path, index=False)
    pd.DataFrame((bundle.get("dashboard") or {}).get("feedback") or []).to_csv(feedback_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "recommended_actions": bundle.get("recommended_actions") or [],
        "report_context": bundle.get("report_context") or {},
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "criteria_path": str(criteria_path),
        "sessions_path": str(sessions_path),
        "feedback_path": str(feedback_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "translational_impact_package": bundle,
        "translational_impact_package_summary": bundle.get("summary") or {},
        "translational_impact_package_markdown_path": str(markdown_path),
        "translational_impact_package_html_path": str(html_path),
        "translational_impact_package_manifest_path": str(manifest_path),
        "translational_impact_package_criteria_path": str(criteria_path),
        "translational_impact_sessions_path": str(sessions_path),
        "translational_impact_feedback_path": str(feedback_path),
    }
