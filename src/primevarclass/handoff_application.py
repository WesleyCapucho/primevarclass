from __future__ import annotations

from dataclasses import replace
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from .data_sources import DataSourceSpec, SourceCatalog, load_source_catalog
from .study import StudyDesign, load_study_design


FILE_TASK_TYPES = {
    "replace_example_source",
    "provide_local_dataset",
    "materialize_training_table",
    "promote_raw_staging_to_resolved_input",
}


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


def _resolve_config_path(path_value: str, *, config_dir: Path) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        cwd_candidate = candidate.resolve()
        config_candidate = (config_dir / candidate).resolve()
        if cwd_candidate.exists():
            return cwd_candidate
        if config_candidate.exists():
            return config_candidate
        return config_candidate
    return candidate.resolve()


def _infer_format(path_value: str, fallback: str) -> str:
    suffix = Path(path_value).suffix.lower()
    if suffix in {".tsv", ".txt"}:
        return "tsv"
    if suffix == ".csv":
        return "csv"
    return str(fallback or "csv")


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _toml_inline_list(values: Iterable[Any]) -> str:
    return "[" + ", ".join(_toml_scalar(item) for item in values) + "]"


def _toml_inline_table(payload: Dict[str, Any]) -> str:
    parts = []
    for key, value in payload.items():
        if isinstance(value, dict):
            rendered = _toml_inline_table(value)
        elif isinstance(value, list):
            rendered = _toml_inline_list(value)
        else:
            rendered = _toml_scalar(value)
        parts.append(f"{key} = {rendered}")
    return "{ " + ", ".join(parts) + " }"


def _catalog_to_payload(catalog: SourceCatalog) -> dict:
    return {
        "ingestion": {
            "deduplicate_on": list(catalog.deduplicate_on or []),
            "prefer_annotation_values": bool(catalog.prefer_annotation_values),
        },
        "sources": [
            {
                "name": spec.name,
                "kind": spec.kind,
                "type": spec.source_type,
                "format": spec.format,
                "path": spec.path,
                "url": spec.url,
                "query": spec.query,
                "table": spec.table,
                "delimiter": spec.delimiter,
                "encoding": spec.encoding,
                "timeout_seconds": int(spec.timeout_seconds),
                "http_method": spec.http_method,
                "body_json": dict(spec.body_json or {}),
                "column_map": dict(spec.column_map or {}),
                "static_fields": dict(spec.static_fields or {}),
                "headers": dict(spec.headers or {}),
                "params": dict(spec.params or {}),
                "select_columns": list(spec.select_columns or []),
                "join_on": list(spec.join_on or []),
                "gene_allowlist": list(spec.gene_allowlist or []),
                "preset": spec.preset,
                "records_path": spec.records_path,
                "release_version": spec.release_version,
                "release_date": spec.release_date,
            }
            for spec in catalog.sources
        ],
    }


def _payload_to_toml(payload: dict) -> str:
    lines = [
        "[ingestion]",
        f"deduplicate_on = {_toml_inline_list(payload.get('ingestion', {}).get('deduplicate_on', []))}",
        f"prefer_annotation_values = {_toml_scalar(payload.get('ingestion', {}).get('prefer_annotation_values', True))}",
        "",
    ]
    ordered_fields = [
        "name",
        "kind",
        "type",
        "format",
        "path",
        "url",
        "query",
        "table",
        "delimiter",
        "encoding",
        "timeout_seconds",
        "http_method",
        "body_json",
        "column_map",
        "static_fields",
        "headers",
        "params",
        "select_columns",
        "join_on",
        "gene_allowlist",
        "preset",
        "records_path",
        "release_version",
        "release_date",
    ]
    for source in payload.get("sources", []):
        lines.append("[[sources]]")
        for field_name in ordered_fields:
            value = source.get(field_name)
            if value is None or value == "" or value == [] or value == {}:
                continue
            if isinstance(value, dict):
                rendered = _toml_inline_table(value)
            elif isinstance(value, list):
                rendered = _toml_inline_list(value)
            else:
                rendered = _toml_scalar(value)
            lines.append(f"{field_name} = {rendered}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _study_to_payload(study: StudyDesign, cohort_rows: List[dict]) -> str:
    lines = [
        "[study]",
        f"name = {_toml_scalar(study.name)}",
        f"mode = {_toml_scalar(study.mode)}",
        f"keep_metadata = {_toml_scalar(study.keep_metadata)}",
        f"high_confidence_only = {_toml_scalar(study.high_confidence_only)}",
        f"primary_metric = {_toml_scalar(study.primary_metric)}",
        f"baseline_experiment = {_toml_scalar(study.baseline_experiment)}",
        f"n_bootstrap = {_toml_scalar(study.n_bootstrap)}",
        f"consensus_top_k = {_toml_scalar(study.consensus_top_k)}",
    ]
    if study.model_families:
        lines.append(f"model_families = {_toml_inline_list(study.model_families)}")
    lines.append("")
    for cohort_row in cohort_rows:
        lines.extend(
            [
                "[[cohorts]]",
                f"name = {_toml_scalar(cohort_row['cohort_name'])}",
                f"role = {_toml_scalar(cohort_row['role'])}",
                f"source_config = {_toml_scalar(cohort_row['candidate_source_config_path'])}",
            ]
        )
        if cohort_row.get("mode_override"):
            lines.append(f"mode = {_toml_scalar(cohort_row['mode_override'])}")
        if cohort_row.get("high_confidence_only_override") is not None:
            lines.append(f"high_confidence_only = {_toml_scalar(cohort_row['high_confidence_only_override'])}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _apply_validated_tasks_to_spec(spec: DataSourceSpec, task_rows: List[dict]) -> tuple[DataSourceSpec, List[str], int]:
    updated_spec = replace(spec)
    notes: List[str] = []
    applied = 0
    for task in task_rows:
        task_type = str(task.get("task_type") or "")
        provided_path = str(task.get("provided_path") or "").strip()
        release_version = str(task.get("release_version") or "").strip()
        release_date = str(task.get("release_date") or "").strip()
        if task_type in FILE_TASK_TYPES and provided_path:
            updated_spec.path = Path(provided_path).resolve().as_posix()
            updated_spec.format = _infer_format(provided_path, updated_spec.format)
            notes.append(f"path override aplicado via tracker: {updated_spec.path}")
            applied += 1
        if task_type == "lock_public_release_metadata":
            if release_version:
                updated_spec.release_version = release_version
                notes.append(f"release_version aplicado via tracker: {release_version}")
                applied += 1
            if release_date:
                updated_spec.release_date = release_date
                notes.append(f"release_date aplicado via tracker: {release_date}")
                applied += 1
        else:
            if release_version:
                updated_spec.release_version = release_version
            if release_date:
                updated_spec.release_date = release_date
    return updated_spec, notes, applied


def build_real_data_handoff_application(
    *,
    study_config_path: str,
    cohort_rows: List[dict],
    handoff_reconciliation_tasks_path: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    context = dict(report_context or {})
    study_config_file = Path(study_config_path).resolve()
    study = load_study_design(str(study_config_file))
    validation_df = pd.read_csv(handoff_reconciliation_tasks_path) if Path(handoff_reconciliation_tasks_path).exists() else pd.DataFrame()
    if validation_df.empty:
        validation_df = pd.DataFrame(columns=["cohort_name", "source_name", "validated", "priority"])

    validated_df = validation_df[validation_df.get("validated", False).astype(bool)].copy() if "validated" in validation_df.columns else pd.DataFrame()
    cohort_candidate_rows: List[dict] = []
    source_application_rows: List[dict] = []

    for cohort_row in cohort_rows:
        cohort_name = str(cohort_row.get("cohort_name") or "")
        source_config_path = str(cohort_row.get("original_source_config") or "")
        source_config_file = Path(source_config_path).resolve()
        catalog = load_source_catalog(str(source_config_file))
        candidate_sources: List[DataSourceSpec] = []
        applied_for_cohort = 0
        ready_for_candidate = True

        for spec in catalog.sources:
            matching_tasks_df = validated_df[
                (validated_df["cohort_name"].astype(str) == cohort_name)
                & (validated_df["source_name"].astype(str) == spec.name)
            ].copy() if not validated_df.empty else pd.DataFrame()
            matching_tasks = matching_tasks_df.to_dict(orient="records")
            updated_spec, notes, applied_count = _apply_validated_tasks_to_spec(spec, matching_tasks)
            candidate_sources.append(updated_spec)
            applied_for_cohort += applied_count

            all_tasks_for_source = validation_df[
                (validation_df["cohort_name"].astype(str) == cohort_name)
                & (validation_df["source_name"].astype(str) == spec.name)
            ].copy() if not validation_df.empty else pd.DataFrame()
            source_ready = True
            if not all_tasks_for_source.empty:
                source_ready = bool(all_tasks_for_source["validated"].astype(bool).all())
            if not source_ready:
                ready_for_candidate = False

            source_application_rows.append(
                {
                    "cohort_name": cohort_name,
                    "source_name": spec.name,
                    "original_path": spec.path,
                    "candidate_path": updated_spec.path,
                    "original_release_version": spec.release_version,
                    "candidate_release_version": updated_spec.release_version,
                    "original_release_date": spec.release_date,
                    "candidate_release_date": updated_spec.release_date,
                    "n_applied_changes": applied_count,
                    "ready_for_candidate": source_ready,
                    "notes": " | ".join(notes),
                }
            )

        candidate_catalog = SourceCatalog(
            sources=candidate_sources,
            deduplicate_on=list(catalog.deduplicate_on or []),
            prefer_annotation_values=bool(catalog.prefer_annotation_values),
        )
        cohort_candidate_rows.append(
            {
                "cohort_name": cohort_name,
                "role": cohort_row.get("role"),
                "mode_override": cohort_row.get("mode_override"),
                "high_confidence_only_override": cohort_row.get("high_confidence_only_override"),
                "original_source_config": source_config_path,
                "candidate_catalog": candidate_catalog,
                "n_applied_changes": applied_for_cohort,
                "ready_for_candidate": ready_for_candidate,
            }
        )

    candidate_source_rows = []
    for row in cohort_candidate_rows:
        source_table = pd.DataFrame(
            [source for source in source_application_rows if source["cohort_name"] == row["cohort_name"]]
        )
        candidate_source_rows.append(
            {
                "cohort_name": row["cohort_name"],
                "role": row["role"],
                "n_applied_changes": int(row["n_applied_changes"]),
                "n_ready_sources": int(source_table["ready_for_candidate"].astype(bool).sum()) if not source_table.empty else 0,
                "n_sources": int(len(source_table)),
                "ready_for_candidate": bool(row["ready_for_candidate"]),
            }
        )

    summary = {
        "generated_at": _now_utc(),
        "study_name": study.name,
        "n_validated_tasks": int(validated_df["validated"].astype(bool).sum()) if not validated_df.empty else 0,
        "n_tasks": int(len(validation_df)),
        "n_candidate_cohorts": int(len(candidate_source_rows)),
        "n_ready_candidate_cohorts": int(sum(1 for row in candidate_source_rows if row["ready_for_candidate"])),
        "n_applied_changes": int(sum(row["n_applied_changes"] for row in candidate_source_rows)),
    }
    summary["overall_handoff_application_percent"] = int(
        round((summary["n_validated_tasks"] / summary["n_tasks"]) * 100)
    ) if summary["n_tasks"] else 100
    summary["overall_status"] = _status_from_percent(summary["overall_handoff_application_percent"])
    summary["ready_for_candidate_resolution"] = bool(summary["n_validated_tasks"] > 0)
    summary["ready_for_candidate_public_study"] = bool(
        summary["n_tasks"] > 0 and summary["n_validated_tasks"] == summary["n_tasks"]
    )

    recommended_actions = []
    if not summary["ready_for_candidate_public_study"]:
        pending_actions = validation_df.loc[
            ~validation_df.get("validated", False).astype(bool), "recommended_action"
        ].dropna().astype(str).tolist() if not validation_df.empty else []
        recommended_actions.extend(pending_actions)
    if not recommended_actions:
        recommended_actions.append("Configuracao candidata pronta para revisao e rerrodada controlada.")
    recommended_actions = list(dict.fromkeys(item for item in recommended_actions if item.strip()))

    markdown_lines = [
        f"# {study.name} - Handoff Candidate Application",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Handoff application: {summary['overall_handoff_application_percent']}%",
        f"- Validated tasks applied: {summary['n_validated_tasks']}/{summary['n_tasks']}",
        f"- Candidate cohorts ready: {summary['n_ready_candidate_cohorts']}/{summary['n_candidate_cohorts']}",
        f"- Ready for candidate resolution: {'yes' if summary['ready_for_candidate_resolution'] else 'not yet'}",
        f"- Ready for candidate public study: {'yes' if summary['ready_for_candidate_public_study'] else 'not yet'}",
        "",
        "## Candidate Cohorts",
        "",
    ]
    for row in candidate_source_rows:
        markdown_lines.append(
            f"- {row['cohort_name']} ({row['role']}): changes={row['n_applied_changes']} | "
            f"ready={row['ready_for_candidate']} | sources={row['n_ready_sources']}/{row['n_sources']}"
        )
    markdown_lines.extend(["", "## Recommended Actions", ""])
    for action in recommended_actions:
        markdown_lines.append(f"- {action}")

    return {
        "summary": summary,
        "recommended_actions": recommended_actions,
        "candidate_cohorts": cohort_candidate_rows,
        "candidate_source_rows": source_application_rows,
        "markdown_report": "\n".join(markdown_lines).strip(),
        "report_context": context,
    }


def build_real_data_handoff_application_html(bundle: dict) -> str:
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
        "<title>PrimeVarClass Handoff Candidate Application</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2ea;color:#1a2832;max-width:980px;margin:0 auto;padding:32px;line-height:1.68;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#8c4f2d;}ul{background:#fff;border:1px solid #e7dccb;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_real_data_handoff_application(
    *,
    study_config_path: str,
    cohort_rows: List[dict],
    handoff_reconciliation_tasks_path: str,
    output_dir: str,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_real_data_handoff_application(
        study_config_path=study_config_path,
        cohort_rows=cohort_rows,
        handoff_reconciliation_tasks_path=handoff_reconciliation_tasks_path,
        report_context=report_context,
    )

    candidate_cohort_rows = []
    for row in bundle.get("candidate_cohorts") or []:
        cohort_name = str(row.get("cohort_name") or "cohort")
        candidate_source_config_path = root / f"{cohort_name}_candidate_source_config.toml"
        catalog = row.get("candidate_catalog")
        if isinstance(catalog, SourceCatalog):
            candidate_source_config_path.write_text(
                _payload_to_toml(_catalog_to_payload(catalog)),
                encoding="utf-8",
            )
        candidate_cohort_rows.append(
            {
                "cohort_name": cohort_name,
                "role": row.get("role"),
                "candidate_source_config_path": str(candidate_source_config_path),
                "mode_override": row.get("mode_override"),
                "high_confidence_only_override": row.get("high_confidence_only_override"),
                "n_applied_changes": row.get("n_applied_changes"),
                "ready_for_candidate": row.get("ready_for_candidate"),
            }
        )

    study = load_study_design(study_config_path)
    candidate_study_config_path = root / "study_real_data_candidate_config.toml"
    candidate_study_config_path.write_text(_study_to_payload(study, candidate_cohort_rows), encoding="utf-8")

    markdown_path = root / "study_real_data_handoff_application.md"
    html_path = root / "study_real_data_handoff_application.html"
    manifest_path = root / "study_real_data_handoff_application_manifest.json"
    source_rows_path = root / "study_real_data_handoff_application_sources.csv"
    cohorts_path = root / "study_real_data_handoff_application_cohorts.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_real_data_handoff_application_html(bundle), encoding="utf-8")
    pd.DataFrame(bundle.get("candidate_source_rows") or []).to_csv(source_rows_path, index=False)
    pd.DataFrame(candidate_cohort_rows).to_csv(cohorts_path, index=False)

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "candidate_study_config_path": str(candidate_study_config_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "source_rows_path": str(source_rows_path),
        "cohorts_path": str(cohorts_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "study_real_data_handoff_application": bundle,
        "study_real_data_handoff_application_summary": bundle.get("summary") or {},
        "study_real_data_candidate_config_path": str(candidate_study_config_path),
        "study_real_data_handoff_application_markdown_path": str(markdown_path),
        "study_real_data_handoff_application_html_path": str(html_path),
        "study_real_data_handoff_application_manifest_path": str(manifest_path),
        "study_real_data_handoff_application_sources_path": str(source_rows_path),
        "study_real_data_handoff_application_cohorts_path": str(cohorts_path),
    }
