from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


TRACKER_COLUMNS = [
    "task_id",
    "completion_status",
    "provided_path",
    "release_version",
    "release_date",
    "notes",
]

FILE_TASK_TYPES = {
    "replace_example_source",
    "provide_local_dataset",
    "materialize_training_table",
    "promote_raw_staging_to_resolved_input",
}
COMPLETE_STATUSES = {"done", "completed", "validated"}


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


def _priority_rank(priority: str) -> int:
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return mapping.get(str(priority or "").strip().lower(), 9)


def _normalize_status(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "pending"
    if token in COMPLETE_STATUSES:
        return token
    if token in {"pending", "blocked", "in_progress"}:
        return token
    return "pending"


def _looks_like_demo_path(path_value: str | None) -> bool:
    token = str(path_value or "").strip().lower()
    return any(marker in token for marker in ["example", "demo", "sample", "like_brca"])


def _build_tracker_template(tasks_df: pd.DataFrame, existing_tracker: pd.DataFrame | None = None) -> pd.DataFrame:
    existing_tracker = existing_tracker.copy() if isinstance(existing_tracker, pd.DataFrame) else pd.DataFrame(columns=TRACKER_COLUMNS)
    if not existing_tracker.empty and "task_id" in existing_tracker.columns:
        existing_tracker = existing_tracker.drop_duplicates(subset=["task_id"], keep="last")
    tracker_rows = []
    existing_by_task = {
        str(row.get("task_id") or ""): row
        for row in existing_tracker.to_dict(orient="records")
        if str(row.get("task_id") or "")
    }
    for row in tasks_df.to_dict(orient="records"):
        task_id = str(row.get("task_id") or "")
        existing = existing_by_task.get(task_id, {})
        tracker_rows.append(
            {
                "task_id": task_id,
                "completion_status": existing.get("completion_status") or "pending",
                "provided_path": existing.get("provided_path") or "",
                "release_version": existing.get("release_version") or "",
                "release_date": existing.get("release_date") or "",
                "notes": existing.get("notes") or "",
            }
        )
    return pd.DataFrame(tracker_rows, columns=TRACKER_COLUMNS)


def _validate_tracker_row(row: dict) -> dict:
    task_type = str(row.get("task_type") or "")
    completion_status = _normalize_status(row.get("completion_status"))
    claimed_complete = completion_status in COMPLETE_STATUSES
    provided_path = str(row.get("provided_path") or "").strip()
    release_version = str(row.get("release_version") or "").strip()
    release_date = str(row.get("release_date") or "").strip()
    notes = str(row.get("notes") or "").strip()

    validation_state = "pending"
    validation_reason = "Task still pending in tracker."
    validated = False

    if claimed_complete:
        if task_type in FILE_TASK_TYPES:
            if not provided_path:
                validation_state = "invalid"
                validation_reason = "Tracker marked task as complete, but no provided_path was informed."
            elif not Path(provided_path).expanduser().resolve().exists():
                validation_state = "invalid"
                validation_reason = "Tracker marked task as complete, but the provided_path does not exist."
            elif task_type == "replace_example_source" and _looks_like_demo_path(provided_path):
                validation_state = "invalid"
                validation_reason = "Provided path still appears to point to demo/example content."
            else:
                validation_state = "validated"
                validation_reason = "Filesystem evidence confirms the provided_path for this task."
                validated = True
        elif task_type == "lock_public_release_metadata":
            if release_version or release_date:
                validation_state = "validated"
                validation_reason = "Release metadata was supplied in the tracker."
                validated = True
            else:
                validation_state = "invalid"
                validation_reason = "Task requires release_version and/or release_date before it can be validated."
        else:
            if provided_path or notes:
                validation_state = "validated"
                validation_reason = "Tracker contains explicit completion evidence for this task."
                validated = True
            else:
                validation_state = "invalid"
                validation_reason = "Task was marked complete without evidence in provided_path or notes."
    elif completion_status == "in_progress":
        validation_state = "in_progress"
        validation_reason = "Task is being worked on but not yet validated."
    elif completion_status == "blocked":
        validation_state = "blocked"
        validation_reason = "Task remains blocked and needs manual follow-up."

    return {
        "completion_status_normalized": completion_status,
        "claimed_complete": claimed_complete,
        "validation_state": validation_state,
        "validation_reason": validation_reason,
        "validated": validated,
    }


def build_real_data_handoff_reconciliation(
    *,
    study_name: str,
    handoff_tasks_path: str,
    tracker_path: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    tasks_file = Path(handoff_tasks_path).resolve()
    tracker_file = Path(tracker_path).resolve()

    tasks_df = pd.read_csv(tasks_file) if tasks_file.exists() else pd.DataFrame()
    existing_tracker_df = pd.read_csv(tracker_file) if tracker_file.exists() else pd.DataFrame(columns=TRACKER_COLUMNS)
    tracker_df = _build_tracker_template(tasks_df, existing_tracker_df)

    merged_df = tasks_df.copy()
    if merged_df.empty:
        merged_df = pd.DataFrame(columns=["task_id"])
    merged_df = merged_df.merge(tracker_df, on="task_id", how="left")

    validation_rows = []
    for row in merged_df.to_dict(orient="records"):
        validation_rows.append({**row, **_validate_tracker_row(row)})
    validation_df = pd.DataFrame(validation_rows)

    if not validation_df.empty:
        validation_df = validation_df.sort_values(
            by=["priority", "cohort_name", "source_name"],
            key=lambda col: col.map(_priority_rank) if col.name == "priority" else col,
        ).reset_index(drop=True)

    n_tasks = int(len(validation_df))
    n_validated = int(validation_df["validated"].astype(bool).sum()) if not validation_df.empty else 0
    n_claimed_complete = int(validation_df["claimed_complete"].astype(bool).sum()) if not validation_df.empty else 0
    n_invalid = int((validation_df["validation_state"].astype(str) == "invalid").sum()) if not validation_df.empty else 0
    n_in_progress = int((validation_df["validation_state"].astype(str) == "in_progress").sum()) if not validation_df.empty else 0
    n_pending = int((validation_df["validation_state"].astype(str) == "pending").sum()) if not validation_df.empty else 0
    n_blocked = int((validation_df["validation_state"].astype(str) == "blocked").sum()) if not validation_df.empty else 0
    n_critical_pending = int(
        ((validation_df["priority"].astype(str) == "critical") & (~validation_df["validated"].astype(bool))).sum()
    ) if not validation_df.empty else 0
    n_high_pending = int(
        ((validation_df["priority"].astype(str) == "high") & (~validation_df["validated"].astype(bool))).sum()
    ) if not validation_df.empty else 0

    overall_percent = int(round((n_validated / n_tasks) * 100)) if n_tasks else 100
    ready_to_rerun_resolution = bool(n_critical_pending == 0 and n_invalid == 0)
    ready_to_rerun_public_study = bool(n_tasks == 0 or (n_validated == n_tasks and n_invalid == 0))

    recommended_actions = validation_df.loc[
        ~validation_df["validated"].astype(bool), "recommended_action"
    ].dropna().astype(str).tolist() if not validation_df.empty else []
    recommended_actions = list(dict.fromkeys(item for item in recommended_actions if item.strip()))
    if not recommended_actions and ready_to_rerun_public_study:
        recommended_actions = ["Tracker reconciliado; o estudo pode ser rerrodado com as evidencias atuais."]

    summary = {
        "generated_at": _now_utc(),
        "study_name": study_name,
        "overall_handoff_reconciliation_percent": overall_percent,
        "overall_status": _status_from_percent(overall_percent),
        "n_tasks": n_tasks,
        "n_validated_tasks": n_validated,
        "n_claimed_complete_tasks": n_claimed_complete,
        "n_pending_tasks": n_pending,
        "n_in_progress_tasks": n_in_progress,
        "n_blocked_tasks": n_blocked,
        "n_invalid_tasks": n_invalid,
        "n_critical_pending_tasks": n_critical_pending,
        "n_high_pending_tasks": n_high_pending,
        "ready_to_rerun_resolution": ready_to_rerun_resolution,
        "ready_to_rerun_public_study": ready_to_rerun_public_study,
    }

    markdown_lines = [
        f"# {study_name} - Real-data Handoff Reconciliation",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Reconciliation progress: {summary['overall_handoff_reconciliation_percent']}%",
        f"- Validated tasks: {summary['n_validated_tasks']}/{summary['n_tasks']}",
        f"- Pending tasks: {summary['n_pending_tasks']} | in progress={summary['n_in_progress_tasks']} | blocked={summary['n_blocked_tasks']} | invalid={summary['n_invalid_tasks']}",
        f"- Ready to rerun resolution: {'yes' if summary['ready_to_rerun_resolution'] else 'not yet'}",
        f"- Ready to rerun public study: {'yes' if summary['ready_to_rerun_public_study'] else 'not yet'}",
        "",
        "## Task Validation",
        "",
    ]
    if validation_df.empty:
        markdown_lines.append("- No handoff tasks available.")
    else:
        for row in validation_df.to_dict(orient="records"):
            markdown_lines.append(
                f"- [{row.get('priority')}] {row.get('cohort_name')} / {row.get('source_name')} -> "
                f"{row.get('validation_state')} | {row.get('validation_reason')}"
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "recommended_actions": recommended_actions,
        "tracker_rows": tracker_df.to_dict(orient="records"),
        "task_validation_rows": validation_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_real_data_handoff_reconciliation_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Real-data Handoff Reconciliation</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1a2832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #e7dccb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_real_data_handoff_reconciliation(
    *,
    study_name: str,
    handoff_tasks_path: str,
    output_dir: str,
    tracker_path: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    resolved_tracker_path = Path(tracker_path).resolve() if tracker_path else (root / "study_real_data_handoff_tracker.csv")
    if not resolved_tracker_path.exists():
        tasks_df = pd.read_csv(handoff_tasks_path) if Path(handoff_tasks_path).exists() else pd.DataFrame(columns=["task_id"])
        tracker_template = _build_tracker_template(tasks_df)
        tracker_template.to_csv(resolved_tracker_path, index=False)

    bundle = build_real_data_handoff_reconciliation(
        study_name=study_name,
        handoff_tasks_path=handoff_tasks_path,
        tracker_path=str(resolved_tracker_path),
        report_context=report_context,
    )

    tracker_df = pd.DataFrame(bundle.get("tracker_rows") or [])
    tracker_df.to_csv(resolved_tracker_path, index=False)

    markdown_path = root / "study_real_data_handoff_reconciliation.md"
    html_path = root / "study_real_data_handoff_reconciliation.html"
    manifest_path = root / "study_real_data_handoff_reconciliation_manifest.json"
    validation_rows_path = root / "study_real_data_handoff_reconciliation_tasks.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_real_data_handoff_reconciliation_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("task_validation_rows") or []).to_csv(validation_rows_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "tracker_path": str(resolved_tracker_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "validation_rows_path": str(validation_rows_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_real_data_handoff_reconciliation": bundle,
        "study_real_data_handoff_reconciliation_summary": bundle.get("summary") or {},
        "study_real_data_handoff_tracker_path": str(resolved_tracker_path),
        "study_real_data_handoff_reconciliation_markdown_path": str(markdown_path),
        "study_real_data_handoff_reconciliation_html_path": str(html_path),
        "study_real_data_handoff_reconciliation_manifest_path": str(manifest_path),
        "study_real_data_handoff_reconciliation_tasks_path": str(validation_rows_path),
    }
