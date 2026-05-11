from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .versioning import load_release_manifest


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    token = str(value or "").strip().lower()
    return token in {"true", "1", "yes", "y"}


def _priority_rank(priority: str) -> int:
    ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return ranks.get(str(priority or "").strip().lower(), 9)


def _safe_load_manifest(path: str | None) -> dict:
    if not path:
        return {}
    candidate = Path(path).resolve()
    if not candidate.exists():
        return {}
    try:
        return load_release_manifest(str(candidate))
    except Exception:
        return {}


def _determine_task(row: dict) -> dict | None:
    source_name = str(row.get("source_name") or "-")
    profile_id = str(row.get("profile_id") or row.get("preset") or "local")
    resolved_path = row.get("resolved_path") or row.get("current_path") or row.get("original_path")
    expected_target_path = row.get("expected_target_path") or resolved_path
    resolution_status = str(row.get("resolution_status") or "")

    if _safe_bool(row.get("uses_example_path")):
        return {
            "task_type": "replace_example_source",
            "priority": "critical",
            "owner_hint": "data_curation",
            "blocking_reason": "Source still points to demo/example input.",
            "recommended_action": row.get("recommended_action") or "Substituir o arquivo de exemplo por um dataset publico real e versionado.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    if _safe_bool(row.get("has_placeholder_release")):
        return {
            "task_type": "lock_public_release_metadata",
            "priority": "critical",
            "owner_hint": "release_governance",
            "blocking_reason": "Public source still uses placeholder release metadata.",
            "recommended_action": row.get("recommended_action") or "Preencher release_version/release_date reais para a fonte publica.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    if not _safe_bool(row.get("path_exists")):
        return {
            "task_type": "provide_local_dataset",
            "priority": "high",
            "owner_hint": "data_engineering",
            "blocking_reason": "Expected local dataset path does not exist yet.",
            "recommended_action": row.get("recommended_action") or "Informar um arquivo local existente para esta fonte.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    if resolution_status == "requires_manual_mavedb_transform":
        return {
            "task_type": "materialize_training_table",
            "priority": "high",
            "owner_hint": "bioinformatics_pipeline",
            "blocking_reason": "Staged MaveDB artifacts still need transformation into a training-ready table.",
            "recommended_action": row.get("recommended_action") or "Converter os artefatos staged em uma tabela tabular pronta para treino.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    if _safe_bool(row.get("uses_raw_data_path")) and not _safe_bool(row.get("ready_for_real_data_source")):
        return {
            "task_type": "promote_raw_staging_to_resolved_input",
            "priority": "medium",
            "owner_hint": "data_engineering",
            "blocking_reason": "Source is still pointing to raw-data staging instead of a frozen resolved artifact.",
            "recommended_action": row.get("recommended_action") or "Promover a fonte de data/raw para um artefato resolvido e versionado.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    if not _safe_bool(row.get("ready_for_real_data_source")):
        return {
            "task_type": "resolve_source_readiness",
            "priority": "medium",
            "owner_hint": "study_ops",
            "blocking_reason": "Source is not yet ready for real-data lock.",
            "recommended_action": row.get("recommended_action") or "Resolver o bloqueio desta fonte antes do benchmark final.",
            "target_path": expected_target_path,
            "source_name": source_name,
            "profile_id": profile_id,
            "resolution_status": resolution_status,
        }
    return None


def build_real_data_handoff_package(
    *,
    study_name: str,
    resolution_summary: dict,
    cohort_rows: List[dict],
    freeze_summary: dict,
    freeze_cohorts_path: str,
    freeze_sources_path: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    freeze_cohorts_df = pd.read_csv(freeze_cohorts_path) if Path(freeze_cohorts_path).exists() else pd.DataFrame()
    freeze_sources_df = pd.read_csv(freeze_sources_path) if Path(freeze_sources_path).exists() else pd.DataFrame()

    resolution_by_cohort = {
        str(item.get("cohort_name") or ""): dict(item)
        for item in cohort_rows
        if str(item.get("cohort_name") or "")
    }

    source_resolution_rows: List[dict] = []
    for cohort_row in cohort_rows:
        manifest = _safe_load_manifest(cohort_row.get("public_source_resolution_manifest_path"))
        for source_row in manifest.get("source_rows") or []:
            source_resolution_rows.append(
                {
                    "cohort_name": cohort_row.get("cohort_name"),
                    "cohort_role": cohort_row.get("role"),
                    **dict(source_row),
                }
            )
    source_resolution_df = pd.DataFrame(source_resolution_rows)

    merged_df = freeze_sources_df.copy()
    if not merged_df.empty and not source_resolution_df.empty:
        merged_df = merged_df.merge(
            source_resolution_df,
            on=["cohort_name", "source_name"],
            how="left",
            suffixes=("", "_resolution"),
        )
    elif merged_df.empty:
        merged_df = source_resolution_df.copy()

    if merged_df.empty:
        task_df = pd.DataFrame(
            columns=[
                "task_id",
                "priority",
                "cohort_name",
                "cohort_role",
                "source_name",
                "profile_id",
                "task_type",
                "owner_hint",
                "blocking_reason",
                "recommended_action",
                "current_path",
                "target_path",
                "release_value",
                "resolution_status",
            ]
        )
    else:
        task_rows = []
        for _, series in merged_df.iterrows():
            row = series.to_dict()
            task = _determine_task(row)
            if not task:
                continue
            task_rows.append(
                {
                    "task_id": f"{row.get('cohort_name') or 'cohort'}::{row.get('source_name') or 'source'}::{task['task_type']}",
                    "priority": task["priority"],
                    "cohort_name": row.get("cohort_name"),
                    "cohort_role": row.get("cohort_role"),
                    "source_name": row.get("source_name"),
                    "profile_id": task["profile_id"],
                    "task_type": task["task_type"],
                    "owner_hint": task["owner_hint"],
                    "blocking_reason": task["blocking_reason"],
                    "recommended_action": task["recommended_action"],
                    "current_path": row.get("resolved_path") or row.get("current_path") or row.get("original_path"),
                    "target_path": task["target_path"],
                    "release_value": row.get("release_value"),
                    "resolution_status": task["resolution_status"],
                }
            )
        task_df = pd.DataFrame(task_rows)
        if not task_df.empty:
            task_df = task_df.sort_values(
                by=["priority", "cohort_name", "source_name"],
                key=lambda col: col.map(_priority_rank) if col.name == "priority" else col,
            ).reset_index(drop=True)

    cohort_task_summary: List[dict] = []
    if not freeze_cohorts_df.empty:
        for _, row in freeze_cohorts_df.iterrows():
            cohort_name = str(row.get("cohort_name") or "")
            resolution_row = resolution_by_cohort.get(cohort_name, {})
            subset = task_df[task_df["cohort_name"].astype(str) == cohort_name].copy() if not task_df.empty else pd.DataFrame()
            cohort_task_summary.append(
                {
                    "cohort_name": cohort_name,
                    "cohort_role": row.get("cohort_role"),
                    "real_data_readiness_percent": _safe_int(row.get("overall_real_data_readiness_percent")),
                    "ready_for_real_data_lock": _safe_bool(row.get("ready_for_real_data_lock")),
                    "n_tasks": int(len(subset)),
                    "n_critical_tasks": int((subset["priority"].astype(str) == "critical").sum()) if not subset.empty else 0,
                    "n_high_tasks": int((subset["priority"].astype(str) == "high").sum()) if not subset.empty else 0,
                    "n_example_sources": _safe_int(row.get("n_example_sources")),
                    "n_placeholder_release_sources": _safe_int(row.get("n_placeholder_release_sources")),
                    "overall_resolution_percent": _safe_int(resolution_row.get("overall_resolution_percent")),
                    "ready_for_resolved_config": _safe_bool(resolution_row.get("ready_for_resolved_config")),
                }
            )
    cohort_task_df = pd.DataFrame(cohort_task_summary)

    blocked_source_count = int((merged_df["ready_for_real_data_source"].astype(str).str.lower().isin(["false", "0"])).sum()) if not merged_df.empty and "ready_for_real_data_source" in merged_df.columns else int(len(task_df))
    mapped_blockers_percent = int(round(len(task_df) / blocked_source_count * 100)) if blocked_source_count else 100
    inventory_percent = 100 if cohort_rows and not freeze_sources_df.empty else 0
    owner_percent = int(round(task_df["owner_hint"].astype(str).str.len().gt(0).mean() * 100)) if not task_df.empty else 100
    action_percent = int(round(task_df["recommended_action"].astype(str).str.len().gt(0).mean() * 100)) if not task_df.empty else 100
    target_percent = int(round(task_df["target_path"].astype(str).str.len().gt(0).mean() * 100)) if not task_df.empty else 100
    handoff_percent = int(round(sum([inventory_percent, mapped_blockers_percent, owner_percent, action_percent, target_percent]) / 5))

    critical_tasks = int((task_df["priority"].astype(str) == "critical").sum()) if not task_df.empty else 0
    high_tasks = int((task_df["priority"].astype(str) == "high").sum()) if not task_df.empty else 0
    recommended_actions = task_df["recommended_action"].dropna().astype(str).tolist() if not task_df.empty else []
    recommended_actions = list(dict.fromkeys(item for item in recommended_actions if item.strip()))
    if not recommended_actions and _safe_bool(freeze_summary.get("ready_for_real_data_study")):
        recommended_actions = ["Coortes prontas para handoff de laboratorio e rodada final com dados reais."]

    summary = {
        "generated_at": _now_utc(),
        "study_name": study_name,
        "real_data_readiness_percent": _safe_int(freeze_summary.get("overall_real_data_readiness_percent")),
        "real_data_handoff_percent": handoff_percent,
        "overall_status": _status_from_percent(handoff_percent),
        "ready_for_lab_handoff": bool(handoff_percent >= 85),
        "ready_for_real_data_study": _safe_bool(freeze_summary.get("ready_for_real_data_study")),
        "n_cohorts": int(len(cohort_rows)),
        "n_blocked_cohorts": int((cohort_task_df["n_tasks"] > 0).sum()) if not cohort_task_df.empty else 0,
        "n_tasks": int(len(task_df)),
        "n_critical_tasks": critical_tasks,
        "n_high_tasks": high_tasks,
        "n_example_blocked_cohorts": _safe_int(freeze_summary.get("n_example_blocked_cohorts")),
        "n_placeholder_release_blocked_cohorts": _safe_int(freeze_summary.get("n_placeholder_release_blocked_cohorts")),
        "resolution_percent": _safe_int(resolution_summary.get("overall_resolution_percent")),
    }

    markdown_lines = [
        f"# {study_name} - Real-data Handoff",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Study real-data readiness: {summary['real_data_readiness_percent']}%",
        f"- Handoff package completeness: {summary['real_data_handoff_percent']}%",
        f"- Ready for lab handoff: {'yes' if summary['ready_for_lab_handoff'] else 'not yet'}",
        f"- Ready for real-data study: {'yes' if summary['ready_for_real_data_study'] else 'not yet'}",
        f"- Blocking tasks: {summary['n_tasks']} total | critical={summary['n_critical_tasks']} | high={summary['n_high_tasks']}",
        "",
        "## Cohort Action Board",
        "",
    ]
    if cohort_task_df.empty:
        markdown_lines.append("- No cohort handoff rows available.")
    else:
        for _, row in cohort_task_df.iterrows():
            markdown_lines.append(
                f"- {row['cohort_name']} ({row['cohort_role']}): readiness={int(row['real_data_readiness_percent'])}% | "
                f"tasks={int(row['n_tasks'])} | critical={int(row['n_critical_tasks'])} | "
                f"example={int(row['n_example_sources'])} | placeholder_release={int(row['n_placeholder_release_sources'])}"
            )

    markdown_lines.extend(["", "## Priority Tasks", ""])
    if task_df.empty:
        markdown_lines.append("- No blocking tasks remain.")
    else:
        for _, row in task_df.iterrows():
            markdown_lines.append(
                f"- [{row['priority']}] {row['cohort_name']} / {row['source_name']} -> {row['task_type']} | "
                f"owner={row['owner_hint']} | action={row['recommended_action']}"
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "recommended_actions": recommended_actions,
        "cohorts": cohort_task_df.to_dict(orient="records"),
        "tasks": task_df.to_dict(orient="records"),
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_real_data_handoff_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Real-data Handoff</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1a2832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #e7dccb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_real_data_handoff_package(
    *,
    study_name: str,
    resolution_summary: dict,
    cohort_rows: List[dict],
    freeze_summary: dict,
    freeze_cohorts_path: str,
    freeze_sources_path: str,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_real_data_handoff_package(
        study_name=study_name,
        resolution_summary=resolution_summary,
        cohort_rows=cohort_rows,
        freeze_summary=freeze_summary,
        freeze_cohorts_path=freeze_cohorts_path,
        freeze_sources_path=freeze_sources_path,
        report_context=report_context,
    )

    markdown_path = root / "study_real_data_handoff.md"
    html_path = root / "study_real_data_handoff.html"
    manifest_path = root / "study_real_data_handoff_manifest.json"
    cohorts_path = root / "study_real_data_handoff_cohorts.csv"
    tasks_path = root / "study_real_data_handoff_tasks.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_real_data_handoff_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("cohorts") or []).to_csv(cohorts_path, index=False)
    pd.DataFrame(bundle.get("tasks") or []).to_csv(tasks_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "cohorts_path": str(cohorts_path),
        "tasks_path": str(tasks_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_real_data_handoff": bundle,
        "study_real_data_handoff_summary": bundle.get("summary") or {},
        "study_real_data_handoff_markdown_path": str(markdown_path),
        "study_real_data_handoff_html_path": str(html_path),
        "study_real_data_handoff_manifest_path": str(manifest_path),
        "study_real_data_handoff_cohorts_path": str(cohorts_path),
        "study_real_data_handoff_tasks_path": str(tasks_path),
    }
