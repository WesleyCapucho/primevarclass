from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .audit import PrimeVarClassAuditLogger
from .jobs import PrimeVarClassJobManager


def _filter_jobs_for_team(jobs: List[dict], team_id: str) -> List[dict]:
    return [
        job
        for job in jobs
        if str((job.get("submitted_for_team") or {}).get("team_id") or "") == str(team_id)
    ]


def _filter_events_for_team(events: List[dict], team_id: str) -> List[dict]:
    filtered = []
    for event in events:
        metadata = dict(event.get("metadata") or {})
        if str(metadata.get("team_id") or "") == str(team_id):
            filtered.append(event)
    return filtered


def _build_dashboard_markdown(team: dict, summary: dict, top_event_types: List[dict], recent_jobs: List[dict]) -> str:
    lines = [
        f"# Team Dashboard - {team.get('display_name')}",
        "",
        f"- Team ID: {team.get('team_id')}",
        f"- Institution: {team.get('institution')}",
        f"- Member role: {team.get('member_role')}",
        "",
        "## Operational Summary",
        "",
        f"- Total jobs: {summary.get('total_jobs', 0)}",
        f"- Completed jobs: {summary.get('completed_jobs', 0)}",
        f"- Running jobs: {summary.get('running_jobs', 0)}",
        f"- Failed jobs: {summary.get('failed_jobs', 0)}",
        f"- Study jobs: {summary.get('study_jobs', 0)}",
        f"- Training jobs: {summary.get('training_jobs', 0)}",
        f"- Audit events: {summary.get('audit_events', 0)}",
    ]
    lines.extend(["", "## Activity Hotspots", ""])
    for item in top_event_types:
        lines.append(f"- {item['event_type']}: {item['count']}")
    lines.extend(["", "## Recent Jobs", ""])
    for job in recent_jobs:
        lines.append(
            f"- {job.get('job_id')}: {job.get('job_type')} / {job.get('status')} "
            f"(created={job.get('created_at')}, finished={job.get('finished_at')})"
        )
    if not recent_jobs:
        lines.append("- Nenhum job encontrado para o time.")
    return "\n".join(lines)


def build_team_dashboard(
    *,
    team: dict,
    job_manager: PrimeVarClassJobManager,
    audit_logger: PrimeVarClassAuditLogger,
    recent_limit: int = 10,
    audit_limit: int = 500,
) -> dict:
    team_id = str(team.get("team_id") or "")
    jobs = _filter_jobs_for_team(job_manager.list_jobs(limit=1000), team_id=team_id)
    events = _filter_events_for_team(audit_logger.list_events(limit=audit_limit), team_id=team_id)

    status_counts = Counter(str(job.get("status") or "unknown") for job in jobs)
    job_type_counts = Counter(str(job.get("job_type") or "unknown") for job in jobs)
    event_type_counts = Counter(str(event.get("event_type") or "unknown") for event in events)

    recent_jobs = jobs[:recent_limit]
    recent_events = events[:recent_limit]
    top_event_types = [
        {"event_type": event_type, "count": count}
        for event_type, count in event_type_counts.most_common(10)
    ]

    scientific_outputs = []
    for job in jobs:
        if str(job.get("status")) != "completed":
            continue
        result = dict(job.get("result") or {})
        for key in [
            "scientific_dossier_markdown_path",
            "scientific_dossier_html_path",
            "study_summary_report_path",
            "model_registry_path",
        ]:
            if result.get(key):
                scientific_outputs.append(
                    {
                        "job_id": job.get("job_id"),
                        "job_type": job.get("job_type"),
                        "artifact_type": key,
                        "path": result.get(key),
                    }
                )

    summary = {
        "total_jobs": len(jobs),
        "completed_jobs": int(status_counts.get("completed", 0)),
        "running_jobs": int(status_counts.get("running", 0)),
        "queued_jobs": int(status_counts.get("queued", 0)),
        "failed_jobs": int(status_counts.get("failed", 0)),
        "interrupted_jobs": int(status_counts.get("interrupted", 0)),
        "study_jobs": int(job_type_counts.get("study_run", 0)),
        "training_jobs": int(job_type_counts.get("train_source_config", 0)),
        "audit_events": len(events),
        "unique_event_types": len(event_type_counts),
    }
    markdown_report = _build_dashboard_markdown(team, summary, top_event_types, recent_jobs)
    return {
        "team": team,
        "summary": summary,
        "status_counts": dict(status_counts),
        "job_type_counts": dict(job_type_counts),
        "top_event_types": top_event_types,
        "recent_jobs": recent_jobs,
        "recent_events": recent_events,
        "scientific_outputs": scientific_outputs[:recent_limit],
        "markdown_report": markdown_report,
    }
