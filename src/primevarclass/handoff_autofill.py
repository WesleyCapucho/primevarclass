from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from .handoff_reconciliation import COMPLETE_STATUSES, FILE_TASK_TYPES, TRACKER_COLUMNS


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


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


def _tokenize(value: Any) -> List[str]:
    return [token for token in re.split(r"[^a-z0-9]+", _normalize_token(value)) if token]


def _looks_like_demo_path(path_value: str | None) -> bool:
    token = _normalize_token(path_value)
    return any(marker in token for marker in ["example", "demo", "sample", "like_brca"])


def _load_tracker_rows(tasks_df: pd.DataFrame, tracker_path: str | None) -> pd.DataFrame:
    existing_df = pd.DataFrame(columns=TRACKER_COLUMNS)
    if tracker_path:
        tracker_file = Path(tracker_path).resolve()
        if tracker_file.exists():
            existing_df = pd.read_csv(tracker_file)
    if not existing_df.empty and "task_id" in existing_df.columns:
        existing_df = existing_df.drop_duplicates(subset=["task_id"], keep="last")

    existing_by_task = {
        str(row.get("task_id") or ""): row
        for row in existing_df.to_dict(orient="records")
        if str(row.get("task_id") or "")
    }
    tracker_rows = []
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


def _scan_delivery_inventory(delivery_dir: Path) -> List[dict]:
    inventory: List[dict] = []
    if not delivery_dir.exists():
        return inventory

    for path in sorted(delivery_dir.rglob("*")):
        if not path.is_file():
            continue
        release_hint = _infer_release_hints(str(path))
        inventory.append(
            {
                "path": str(path.resolve()),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "stem_tokens": _tokenize(path.stem),
                "path_tokens": _tokenize(str(path)),
                "release_version_hint": release_hint.get("release_version") or "",
                "release_date_hint": release_hint.get("release_date") or "",
                "looks_like_demo": _looks_like_demo_path(str(path)),
            }
        )
    return inventory


def _infer_release_hints(text: str) -> dict:
    token = str(text or "")
    release_date = ""
    release_version = ""

    date_match = re.search(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])", token)
    if date_match:
        release_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        release_version = f"{date_match.group(1)}.{date_match.group(2)}"

    if not release_version:
        version_match = re.search(r"(20\d{2})[._-](0[1-9]|1[0-2])", token)
        if version_match:
            release_version = f"{version_match.group(1)}.{version_match.group(2)}"

    urn_match = re.search(r"(urn:mavedb:[a-z0-9._:-]+)", token, flags=re.IGNORECASE)
    if urn_match:
        release_version = urn_match.group(1)

    return {"release_version": release_version, "release_date": release_date}


def _priority_rank(priority: str) -> int:
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return mapping.get(_normalize_token(priority), 9)


def _task_expected_names(row: dict) -> List[str]:
    names: List[str] = []
    for candidate in [row.get("target_path"), row.get("current_path")]:
        path_value = str(candidate or "").strip()
        if not path_value:
            continue
        names.append(Path(path_value).name.lower())
        names.append(Path(path_value).stem.lower())
    return [name for name in dict.fromkeys(name for name in names if name)]


def _task_tokens(row: dict) -> List[str]:
    tokens: List[str] = []
    for value in [
        row.get("cohort_name"),
        row.get("cohort_role"),
        row.get("source_name"),
        row.get("profile_id"),
        row.get("task_type"),
        row.get("current_path"),
        row.get("target_path"),
    ]:
        tokens.extend(_tokenize(value))
    return list(dict.fromkeys(tokens))


def _score_inventory_match(row: dict, item: dict) -> int:
    if item.get("looks_like_demo"):
        return -10_000

    expected_names = _task_expected_names(row)
    item_name = _normalize_token(item.get("name"))
    item_stem = Path(str(item.get("name") or "")).stem.lower()
    score = 0

    if item_name and item_name in expected_names:
        score += 120
    if item_stem and item_stem in expected_names:
        score += 80

    expected_suffix = Path(str(row.get("target_path") or row.get("current_path") or "")).suffix.lower()
    if expected_suffix and item.get("suffix") == expected_suffix:
        score += 25

    tokens = _task_tokens(row)
    path_token_set = set(item.get("path_tokens") or [])
    stem_token_set = set(item.get("stem_tokens") or [])
    for token in tokens:
        if token in stem_token_set:
            score += 10
        elif token in path_token_set:
            score += 4

    if _normalize_token(row.get("source_name")) in _normalize_token(item.get("name")):
        score += 20
    if _normalize_token(row.get("profile_id")) in _normalize_token(item.get("name")):
        score += 12

    return score


def _select_best_match(row: dict, inventory: List[dict], used_paths: set[str]) -> dict | None:
    candidates = []
    for item in inventory:
        if str(item.get("path")) in used_paths:
            continue
        score = _score_inventory_match(row, item)
        if score < 35:
            continue
        candidates.append((score, len(str(item.get("path") or "")), item))
    if not candidates:
        return None
    candidates.sort(key=lambda entry: (-entry[0], entry[1]))
    return dict(candidates[0][2])


def _normalize_completion_status(value: Any) -> str:
    token = _normalize_token(value)
    if not token:
        return "pending"
    if token in COMPLETE_STATUSES or token in {"pending", "blocked", "in_progress"}:
        return token
    return "pending"


def _merge_note(existing_note: str, addition: str) -> str:
    current = str(existing_note or "").strip()
    if not current:
        return addition
    if addition in current:
        return current
    return f"{current}; {addition}"


def build_real_data_handoff_autofill(
    *,
    study_name: str,
    handoff_tasks_path: str,
    delivery_dir: str,
    tracker_path: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    tasks_file = Path(handoff_tasks_path).resolve()
    delivery_root = Path(delivery_dir).resolve()
    if not tasks_file.exists():
        raise ValueError("Arquivo de tarefas do handoff nao encontrado para autofill.")
    if not delivery_root.exists():
        raise ValueError("Diretorio de entrega de dados reais nao encontrado.")

    tasks_df = pd.read_csv(tasks_file)
    tracker_df = _load_tracker_rows(tasks_df, tracker_path)
    tracker_by_task = {
        str(row.get("task_id") or ""): row
        for row in tracker_df.to_dict(orient="records")
        if str(row.get("task_id") or "")
    }
    inventory = _scan_delivery_inventory(delivery_root)

    used_paths: set[str] = set()
    matched_release_hints: Dict[str, dict] = {}
    proposed_tracker_rows: List[dict] = []
    match_rows: List[dict] = []

    sortable_tasks = tasks_df.copy()
    if not sortable_tasks.empty:
        sortable_tasks = sortable_tasks.sort_values(
            by=["priority", "cohort_name", "source_name"],
            key=lambda col: col.map(_priority_rank) if col.name == "priority" else col,
        ).reset_index(drop=True)

    for row in sortable_tasks.to_dict(orient="records"):
        task_id = str(row.get("task_id") or "")
        tracker_row = dict(tracker_by_task.get(task_id, {}))
        tracker_row = {
            "task_id": task_id,
            "completion_status": tracker_row.get("completion_status") or "pending",
            "provided_path": tracker_row.get("provided_path") or "",
            "release_version": tracker_row.get("release_version") or "",
            "release_date": tracker_row.get("release_date") or "",
            "notes": tracker_row.get("notes") or "",
        }
        completion_status = _normalize_completion_status(tracker_row.get("completion_status"))
        tracker_row["completion_status"] = completion_status
        task_type = str(row.get("task_type") or "")

        match_state = "pending"
        match_reason = "Task ainda nao foi relacionada a um arquivo de entrega."
        matched_path = ""
        match_score = 0

        existing_complete = (
            completion_status in COMPLETE_STATUSES
            and str(tracker_row.get("provided_path") or "").strip()
            and Path(str(tracker_row.get("provided_path"))).resolve().exists()
            and not _looks_like_demo_path(str(tracker_row.get("provided_path")))
        )
        if existing_complete:
            matched_path = str(Path(str(tracker_row.get("provided_path"))).resolve())
            used_paths.add(matched_path)
            match_state = "preserved_existing"
            match_reason = "Tracker ja continha um caminho completo e valido."
            release_hint = _infer_release_hints(matched_path)
            matched_release_hints[str(row.get("source_name") or "")] = release_hint
            if not tracker_row.get("release_version") and release_hint.get("release_version"):
                tracker_row["release_version"] = release_hint["release_version"]
            if not tracker_row.get("release_date") and release_hint.get("release_date"):
                tracker_row["release_date"] = release_hint["release_date"]
        elif task_type in FILE_TASK_TYPES:
            best_match = _select_best_match(row, inventory, used_paths)
            if best_match:
                matched_path = str(best_match.get("path") or "")
                match_score = _safe_int(_score_inventory_match(row, best_match))
                tracker_row["completion_status"] = "completed"
                tracker_row["provided_path"] = matched_path
                tracker_row["notes"] = _merge_note(
                    str(tracker_row.get("notes") or ""),
                    f"autofilled_from_delivery:{Path(matched_path).name}",
                )
                if not tracker_row.get("release_version") and best_match.get("release_version_hint"):
                    tracker_row["release_version"] = best_match["release_version_hint"]
                if not tracker_row.get("release_date") and best_match.get("release_date_hint"):
                    tracker_row["release_date"] = best_match["release_date_hint"]
                used_paths.add(matched_path)
                match_state = "autofilled"
                match_reason = "Arquivo da entrega associado automaticamente ao bloqueio desta fonte."
                matched_release_hints[str(row.get("source_name") or "")] = {
                    "release_version": tracker_row.get("release_version") or "",
                    "release_date": tracker_row.get("release_date") or "",
                }
            else:
                match_state = "unmatched"
                match_reason = "Nenhum arquivo compativel foi encontrado no diretorio de entrega."
        elif task_type == "lock_public_release_metadata":
            source_name = str(row.get("source_name") or "")
            release_hint = matched_release_hints.get(source_name) or {}
            if not tracker_row.get("release_version") and release_hint.get("release_version"):
                tracker_row["release_version"] = release_hint["release_version"]
            if not tracker_row.get("release_date") and release_hint.get("release_date"):
                tracker_row["release_date"] = release_hint["release_date"]
            if tracker_row.get("release_version") or tracker_row.get("release_date"):
                tracker_row["completion_status"] = "completed"
                tracker_row["notes"] = _merge_note(
                    str(tracker_row.get("notes") or ""),
                    "release_metadata_inferred_from_delivery",
                )
                match_state = "autofilled_release"
                match_reason = "Metadados de release inferidos a partir dos arquivos entregues."
            else:
                match_state = "needs_manual_release_lock"
                match_reason = "Nao foi possivel inferir release_version/release_date automaticamente."

        proposed_tracker_rows.append(tracker_row)
        match_rows.append(
            {
                "task_id": task_id,
                "priority": row.get("priority"),
                "cohort_name": row.get("cohort_name"),
                "cohort_role": row.get("cohort_role"),
                "source_name": row.get("source_name"),
                "profile_id": row.get("profile_id"),
                "task_type": task_type,
                "match_state": match_state,
                "match_score": match_score,
                "matched_path": matched_path,
                "completion_status_after_autofill": tracker_row.get("completion_status"),
                "release_version_after_autofill": tracker_row.get("release_version"),
                "release_date_after_autofill": tracker_row.get("release_date"),
                "match_reason": match_reason,
                "recommended_action": row.get("recommended_action"),
            }
        )

    proposed_tracker_df = pd.DataFrame(proposed_tracker_rows, columns=TRACKER_COLUMNS)
    match_df = pd.DataFrame(match_rows)
    inventory_df = pd.DataFrame(inventory)

    n_tasks = int(len(match_df))
    n_file_tasks = int(match_df["task_type"].astype(str).isin(FILE_TASK_TYPES).sum()) if not match_df.empty else 0
    n_autofilled = int(match_df["match_state"].astype(str).isin(["autofilled", "autofilled_release"]).sum()) if not match_df.empty else 0
    n_preserved = int((match_df["match_state"].astype(str) == "preserved_existing").sum()) if not match_df.empty else 0
    n_unmatched = int((match_df["match_state"].astype(str) == "unmatched").sum()) if not match_df.empty else 0
    n_manual_release = int((match_df["match_state"].astype(str) == "needs_manual_release_lock").sum()) if not match_df.empty else 0
    n_completed_after_autofill = int(
        proposed_tracker_df["completion_status"].astype(str).str.lower().isin(COMPLETE_STATUSES).sum()
    ) if not proposed_tracker_df.empty else 0
    completion_percent = int(round((n_completed_after_autofill / n_tasks) * 100)) if n_tasks else 100

    recommended_actions = (
        match_df.loc[
            ~match_df["match_state"].astype(str).isin(["autofilled", "autofilled_release", "preserved_existing"]),
            "recommended_action",
        ]
        .dropna()
        .astype(str)
        .tolist()
        if not match_df.empty
        else []
    )
    recommended_actions = list(dict.fromkeys(item for item in recommended_actions if item.strip()))
    if not recommended_actions and n_tasks:
        recommended_actions = ["Tracker autofill concluido; rerrode a reconciliacao para validar os novos caminhos."]

    summary = {
        "generated_at": _now_utc(),
        "study_name": study_name,
        "delivery_dir": str(delivery_root),
        "overall_handoff_autofill_percent": completion_percent,
        "overall_status": _status_from_percent(completion_percent),
        "n_tasks": n_tasks,
        "n_file_tasks": n_file_tasks,
        "n_delivery_files_scanned": int(len(inventory_df)),
        "n_autofilled_tasks": n_autofilled,
        "n_preserved_completed_tasks": n_preserved,
        "n_unmatched_tasks": n_unmatched,
        "n_manual_release_lock_tasks": n_manual_release,
        "n_completed_tasks_after_autofill": n_completed_after_autofill,
        "ready_for_reconciliation_rerun": bool(n_tasks == 0 or (n_unmatched == 0 and n_manual_release == 0)),
    }

    markdown_lines = [
        f"# {study_name} - Real-data Handoff Autofill",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Delivery dir: {summary['delivery_dir']}",
        f"- Autofill completeness: {summary['overall_handoff_autofill_percent']}%",
        f"- Tasks: {summary['n_tasks']} total | autofilled={summary['n_autofilled_tasks']} | preserved={summary['n_preserved_completed_tasks']} | unmatched={summary['n_unmatched_tasks']}",
        f"- Files scanned: {summary['n_delivery_files_scanned']}",
        f"- Ready for reconciliation rerun: {'yes' if summary['ready_for_reconciliation_rerun'] else 'not yet'}",
        "",
        "## Match Board",
        "",
    ]
    if match_df.empty:
        markdown_lines.append("- No handoff tasks available.")
    else:
        for row in match_df.to_dict(orient="records"):
            markdown_lines.append(
                f"- [{row['match_state']}] {row['cohort_name']} / {row['source_name']} -> "
                f"{row['matched_path'] or '-'} | {row['match_reason']}"
            )

    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "recommended_actions": recommended_actions,
        "tracker_rows": proposed_tracker_rows,
        "match_rows": match_rows,
        "inventory_rows": inventory,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_real_data_handoff_autofill_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Real-data Handoff Autofill</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1a2832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #e7dccb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_real_data_handoff_autofill(
    *,
    study_name: str,
    handoff_tasks_path: str,
    delivery_dir: str,
    output_dir: str,
    tracker_path: str | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_real_data_handoff_autofill(
        study_name=study_name,
        handoff_tasks_path=handoff_tasks_path,
        delivery_dir=delivery_dir,
        tracker_path=tracker_path,
        report_context=report_context,
    )

    tracker_output_path = root / "study_real_data_handoff_tracker_autofilled.csv"
    matches_path = root / "study_real_data_handoff_autofill_matches.csv"
    inventory_path = root / "study_real_data_handoff_autofill_inventory.csv"
    markdown_path = root / "study_real_data_handoff_autofill.md"
    html_path = root / "study_real_data_handoff_autofill.html"
    manifest_path = root / "study_real_data_handoff_autofill_manifest.json"

    pd.DataFrame(bundle.get("tracker_rows") or []).to_csv(tracker_output_path, index=False)
    pd.DataFrame(bundle.get("match_rows") or []).to_csv(matches_path, index=False)
    pd.DataFrame(bundle.get("inventory_rows") or []).to_csv(inventory_path, index=False)
    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_real_data_handoff_autofill_html(bundle), encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "tracker_path": str(tracker_output_path),
        "matches_path": str(matches_path),
        "inventory_path": str(inventory_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "delivery_dir": str(Path(delivery_dir).resolve()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_real_data_handoff_autofill": bundle,
        "study_real_data_handoff_autofill_summary": bundle.get("summary") or {},
        "study_real_data_handoff_autofill_tracker_path": str(tracker_output_path),
        "study_real_data_handoff_autofill_matches_path": str(matches_path),
        "study_real_data_handoff_autofill_inventory_path": str(inventory_path),
        "study_real_data_handoff_autofill_markdown_path": str(markdown_path),
        "study_real_data_handoff_autofill_html_path": str(html_path),
        "study_real_data_handoff_autofill_manifest_path": str(manifest_path),
    }
