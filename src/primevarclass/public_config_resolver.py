from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from .data_sources import DataSourceSpec, SourceCatalog, load_source_catalog
from .handoff_autofill import export_real_data_handoff_autofill
from .handoff_application import export_real_data_handoff_application
from .handoff_promotion import export_real_data_candidate_promotion
from .handoff_reconciliation import export_real_data_handoff_reconciliation
from .public_bootstrap import load_public_source_bootstrap_manifest, load_public_source_sync_history
from .public_sources import build_public_source_catalog_assessment
from .real_data_handoff import export_real_data_handoff_package
from .public_sync import build_public_source_sync_plan
from .study import StudyDesign, load_study_design
from .cohort_freeze import export_study_cohort_freeze


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


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


def _existing_local_path(path_value: str | None, *, config_dir: Path) -> str | None:
    if not path_value:
        return None
    candidate = _resolve_config_path(path_value, config_dir=config_dir)
    return str(candidate) if candidate.exists() else None


def _bundle_index(bundle: dict | None) -> dict[str, dict]:
    return {
        str(item.get("source_name") or ""): dict(item)
        for item in (bundle or {}).get("bundle_items", [])
        if str(item.get("source_name") or "")
    }


def _history_index(history: dict | None) -> dict[str, dict]:
    return {
        str(item.get("source_name") or ""): dict(item)
        for item in (history or {}).get("source_statuses", [])
        if str(item.get("source_name") or "")
    }


def _assessment_index(assessment: dict | None) -> dict[str, dict]:
    return {
        str(item.get("source_name") or ""): dict(item)
        for item in (assessment or {}).get("sources", [])
        if str(item.get("source_name") or "")
    }


def _first_existing_path(paths: Iterable[str], suffixes: Iterable[str] | None = None) -> str | None:
    suffix_tokens = {_normalize_token(item) for item in (suffixes or []) if str(item or "").strip()}
    for raw_path in paths:
        candidate = Path(str(raw_path or "")).resolve()
        if not candidate.exists():
            continue
        if suffix_tokens:
            lowered = _normalize_token(candidate.name)
            if not any(lowered.endswith(token) for token in suffix_tokens):
                continue
        return str(candidate)
    return None


def _source_to_resolution_row(
    spec: DataSourceSpec,
    *,
    assessment_row: dict | None,
    bundle_item: dict | None,
    history_row: dict | None,
    config_dir: Path,
) -> tuple[DataSourceSpec, dict]:
    assessment_row = dict(assessment_row or {})
    bundle_item = dict(bundle_item or {})
    history_row = dict(history_row or {})

    source_type = str(spec.source_type or "file").lower()
    recognized_public = bool(assessment_row.get("recognized_public_source"))
    profile_id = str(assessment_row.get("profile_id") or "")
    existing_local_path = _existing_local_path(spec.path, config_dir=config_dir) if source_type == "file" else None
    execution_status = str(history_row.get("latest_execution_status") or "never_run")
    expected_artifacts = [str(item) for item in (bundle_item.get("expected_artifact_paths") or [])]
    resolved_spec = replace(spec)
    resolution_notes: List[str] = []
    recommended_action = ""
    resolution_status = "unchanged"
    resolution_percent = 0
    ready_for_use = False
    resolved_path = existing_local_path if source_type == "file" else spec.path
    resolved_from_stage = False

    if source_type != "file":
        ready_for_use = True
        resolution_status = "retained_non_file_source"
        resolution_percent = 100
        recommended_action = "Fonte nao baseada em arquivo preservada como configurada."
    elif recognized_public and execution_status == "completed":
        stage_map = {
            "clinvar": ("variant_summary.txt.gz", "tsv", None),
            "gnomad": ("gnomad_brca_subset.tsv", "tsv", None),
            "enigma": ("enigma_curated_import", str(spec.format or "tsv"), None),
        }
        stage_spec = stage_map.get(profile_id)
        if stage_spec is not None:
            suffix_hint, format_name, records_path = stage_spec
            resolved_path = _first_existing_path(expected_artifacts, suffixes=[suffix_hint]) or resolved_path
            if resolved_path and Path(resolved_path).exists():
                resolved_spec.path = str(Path(resolved_path).resolve())
                resolved_spec.format = format_name
                resolved_spec.records_path = records_path
                resolution_status = "resolved_from_staged_artifact"
                resolution_percent = 100
                ready_for_use = True
                resolved_from_stage = True
                recommended_action = "Catalogo apontado para o artefato staged e versionado do bootstrap."
        elif profile_id == "mavedb":
            if existing_local_path:
                resolved_spec.path = str(Path(existing_local_path).resolve())
                resolution_status = "retained_existing_local_source"
                resolution_percent = 88
                ready_for_use = True
                recommended_action = (
                    "Mantido o score table local existente; o bootstrap MaveDB segue util para proveniencia,"
                    " mas ainda nao substitui automaticamente a tabela de treino."
                )
            else:
                resolution_status = "requires_manual_mavedb_transform"
                resolution_percent = 55
                ready_for_use = False
                recommended_action = (
                    "Converter os artefatos staged de MaveDB para uma tabela de scores compativel ou informar um arquivo local pronto."
                )
                resolution_notes.append("Os artefatos MaveDB staged ainda exigem tabularizacao explicita para o pipeline de treino.")

    if not ready_for_use and existing_local_path:
        resolved_spec.path = str(Path(existing_local_path).resolve())
        if recognized_public:
            resolution_status = "retained_existing_local_source"
            resolution_percent = max(82, int(assessment_row.get("readiness_percent", 0) or 0))
            recommended_action = "Fonte local versionada mantida; o bootstrap staged continua recomendado, mas nao e bloqueante."
        else:
            resolution_status = "retained_local_source"
            resolution_percent = 100
            recommended_action = "Fonte local preservada como configurada."
        ready_for_use = True

    if not ready_for_use and source_type == "file":
        if recognized_public:
            resolution_status = "blocked_missing_public_source"
            resolution_percent = min(60, int(assessment_row.get("readiness_percent", 0) or 0))
            recommended_action = assessment_row.get("warnings", ["Executar bootstrap e/ou informar um arquivo local versionado."])[0]
        else:
            resolution_status = "blocked_missing_local_source"
            resolution_percent = 0
            recommended_action = "Ajustar o caminho do arquivo local antes de gerar a coorte."

    if bundle_item and not resolved_from_stage and execution_status == "completed" and profile_id in {"clinvar", "gnomad", "enigma"}:
        resolution_notes.append("Existe bootstrap concluido, mas o artefato staged esperado nao foi localizado para esta fonte.")

    resolution_row = {
        "source_name": spec.name,
        "kind": spec.kind,
        "source_type": spec.source_type,
        "preset": spec.preset,
        "profile_id": assessment_row.get("profile_id"),
        "display_name": assessment_row.get("display_name"),
        "recognized_public_source": recognized_public,
        "release_value": assessment_row.get("release_value"),
        "catalog_readiness_percent": int(assessment_row.get("readiness_percent", 0) or 0),
        "sync_readiness_percent": int(history_row.get("sync_readiness_percent", 0) or 0),
        "resolution_percent": int(resolution_percent),
        "resolution_status": resolution_status,
        "ready_for_use": bool(ready_for_use),
        "resolved_from_stage": bool(resolved_from_stage),
        "latest_execution_status": execution_status,
        "original_path": str(_resolve_config_path(spec.path, config_dir=config_dir)) if spec.path else None,
        "resolved_path": str(Path(resolved_spec.path).resolve()) if resolved_spec.path else None,
        "resolved_format": resolved_spec.format,
        "resolved_records_path": resolved_spec.records_path,
        "expected_artifact_count": int(len(expected_artifacts)),
        "recommended_action": recommended_action,
        "notes": resolution_notes,
    }
    return resolved_spec, resolution_row


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


def build_public_source_resolution(
    *,
    config_path: str,
    bootstrap_output_dir: str,
) -> dict:
    config_file = Path(config_path).resolve()
    config_dir = config_file.parent
    catalog = load_source_catalog(str(config_file))
    assessment = build_public_source_catalog_assessment(
        config_path=str(config_file),
        catalog=catalog,
        source_provenance=[],
    )
    sync_plan = build_public_source_sync_plan(
        config_path=str(config_file),
        public_source_assessment=assessment,
    )
    bundle = load_public_source_bootstrap_manifest(bootstrap_output_dir) or {}
    history = load_public_source_sync_history(
        output_dir=bootstrap_output_dir,
        public_source_assessment=assessment,
        public_source_sync_plan=sync_plan,
    )

    assessment_by_name = _assessment_index(assessment)
    bundle_by_name = _bundle_index(bundle)
    history_by_name = _history_index(history)

    resolved_specs: List[DataSourceSpec] = []
    source_rows: List[dict] = []
    for spec in catalog.sources:
        resolved_spec, row = _source_to_resolution_row(
            spec,
            assessment_row=assessment_by_name.get(spec.name),
            bundle_item=bundle_by_name.get(spec.name),
            history_row=history_by_name.get(spec.name),
            config_dir=config_dir,
        )
        resolved_specs.append(resolved_spec)
        source_rows.append(row)

    source_table = pd.DataFrame(source_rows)
    recognized_table = source_table[source_table["recognized_public_source"] == True].copy() if not source_table.empty else pd.DataFrame()
    blocked_rows = source_table[source_table["ready_for_use"] == False].copy() if not source_table.empty else pd.DataFrame()
    public_resolution_percent = int(round(recognized_table["resolution_percent"].mean())) if not recognized_table.empty else 0
    overall_resolution_percent = int(round(source_table["resolution_percent"].mean())) if not source_table.empty else 0
    summary = {
        "config_path": str(config_file),
        "bootstrap_output_dir": str(Path(bootstrap_output_dir).resolve()),
        "n_sources": int(len(source_rows)),
        "n_recognized_public_sources": int(len(recognized_table)),
        "n_resolved_from_stage": int((source_table["resolved_from_stage"] == True).sum()) if not source_table.empty else 0,
        "n_retained_existing_local_sources": int((source_table["resolution_status"] == "retained_existing_local_source").sum()) if not source_table.empty else 0,
        "n_ready_sources": int((source_table["ready_for_use"] == True).sum()) if not source_table.empty else 0,
        "n_blocked_sources": int(len(blocked_rows)),
        "public_resolution_percent": public_resolution_percent,
        "overall_resolution_percent": overall_resolution_percent,
        "ready_for_resolved_config": bool(not source_table.empty and blocked_rows.empty),
        "ready_for_live_public_sources": bool(
            not recognized_table.empty
            and blocked_rows[blocked_rows["recognized_public_source"] == True].empty
            and int((source_table["resolved_from_stage"] == True).sum()) >= 1
        ),
    }
    recommended_actions = [
        str(item)
        for item in source_table.loc[source_table["ready_for_use"] == False, "recommended_action"].dropna().tolist()
        if str(item).strip()
    ]
    if not recommended_actions and summary["ready_for_resolved_config"]:
        recommended_actions.append("Catalogo pronto para gerar coortes reprodutiveis a partir das fontes resolvidas.")

    markdown_lines = [
        "# Public Source Resolution",
        "",
        f"- Config path: {summary['config_path']}",
        f"- Bootstrap output dir: {summary['bootstrap_output_dir']}",
        f"- Sources: {summary['n_sources']}",
        f"- Recognized public sources: {summary['n_recognized_public_sources']}",
        f"- Resolved from staged artifacts: {summary['n_resolved_from_stage']}",
        f"- Retained existing local sources: {summary['n_retained_existing_local_sources']}",
        f"- Blocked sources: {summary['n_blocked_sources']}",
        f"- Public resolution: {summary['public_resolution_percent']}%",
        f"- Overall resolution: {summary['overall_resolution_percent']}%",
        f"- Ready for resolved config: {'yes' if summary['ready_for_resolved_config'] else 'not yet'}",
        f"- Ready for live public sources: {'yes' if summary['ready_for_live_public_sources'] else 'not yet'}",
        "",
        "## Sources",
        "",
    ]
    for row in source_rows:
        markdown_lines.extend(
            [
                f"### {row['source_name']}",
                "",
                f"- Status: {row['resolution_status']}",
                f"- Ready: {'yes' if row['ready_for_use'] else 'not yet'}",
                f"- Resolution: {row['resolution_percent']}%",
                f"- Original path: {row['original_path'] or '-'}",
                f"- Resolved path: {row['resolved_path'] or '-'}",
                f"- Recommended action: {row['recommended_action'] or '-'}",
                "",
            ]
        )

    resolved_catalog = SourceCatalog(
        sources=resolved_specs,
        deduplicate_on=list(catalog.deduplicate_on or []),
        prefer_annotation_values=bool(catalog.prefer_annotation_values),
    )
    return {
        "generated_at": _now_utc(),
        "summary": summary,
        "recommended_actions": recommended_actions,
        "source_rows": source_rows,
        "source_table": source_table,
        "assessment": assessment,
        "sync_plan": sync_plan,
        "sync_history": history,
        "bootstrap_bundle": bundle,
        "resolved_catalog": resolved_catalog,
        "resolved_catalog_payload": _catalog_to_payload(resolved_catalog),
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def export_public_source_resolution(
    *,
    config_path: str,
    bootstrap_output_dir: str,
    output_dir: str,
) -> dict:
    resolution = build_public_source_resolution(
        config_path=config_path,
        bootstrap_output_dir=bootstrap_output_dir,
    )
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    resolved_config_path = output_root / "resolved_source_config.toml"
    manifest_path = output_root / "public_source_resolution_manifest.json"
    report_path = output_root / "public_source_resolution_report.md"
    sources_path = output_root / "public_source_resolution_sources.csv"

    resolved_config_path.write_text(
        _payload_to_toml(resolution["resolved_catalog_payload"]),
        encoding="utf-8",
    )
    report_path.write_text(str(resolution.get("markdown_report") or ""), encoding="utf-8")
    resolution["source_table"].to_csv(sources_path, index=False)
    manifest = {
        "generated_at": resolution.get("generated_at"),
        "summary": resolution.get("summary") or {},
        "recommended_actions": resolution.get("recommended_actions") or [],
        "resolved_config_path": str(resolved_config_path),
        "sources_path": str(sources_path),
        "bootstrap_output_dir": str(Path(bootstrap_output_dir).resolve()),
        "source_rows": resolution.get("source_rows") or [],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "resolution": resolution,
        "resolved_config_path": str(resolved_config_path),
        "public_source_resolution_manifest_path": str(manifest_path),
        "public_source_resolution_report_markdown_path": str(report_path),
        "public_source_resolution_sources_path": str(sources_path),
    }


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
                f"source_config = {_toml_scalar(cohort_row['resolved_source_config_path'])}",
            ]
        )
        if cohort_row.get("mode_override"):
            lines.append(f"mode = {_toml_scalar(cohort_row['mode_override'])}")
        if cohort_row.get("high_confidence_only_override") is not None:
            lines.append(f"high_confidence_only = {_toml_scalar(cohort_row['high_confidence_only_override'])}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def export_study_public_config_resolution(
    *,
    config_path: str,
    output_dir: str,
    bootstrap_root_dir: str | None = None,
    delivery_dir: str | None = None,
) -> dict:
    study_config_file = Path(config_path).resolve()
    study_config_dir = study_config_file.parent
    study = load_study_design(str(study_config_file))
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_cohort_root = output_root / "resolved_cohorts"
    resolved_cohort_root.mkdir(parents=True, exist_ok=True)

    bootstrap_root = Path(bootstrap_root_dir).resolve() if bootstrap_root_dir else output_root
    cohort_rows: List[dict] = []
    recommended_actions: List[str] = []

    for cohort in study.cohorts or []:
        cohort_slug = "".join(ch if ch.isalnum() else "_" for ch in str(cohort.name).lower()).strip("_") or "cohort"
        cohort_output_dir = resolved_cohort_root / cohort_slug
        cohort_bootstrap_dir = bootstrap_root / "cohorts" / f"{cohort_slug}_ingestion"
        cohort_config_path = _resolve_config_path(cohort.source_config, config_dir=study_config_dir)
        export_paths = export_public_source_resolution(
            config_path=str(cohort_config_path),
            bootstrap_output_dir=str(cohort_bootstrap_dir),
            output_dir=str(cohort_output_dir),
        )
        resolution_summary = (export_paths.get("resolution") or {}).get("summary") or {}
        cohort_rows.append(
            {
                "cohort_name": cohort.name,
                "role": cohort.role,
                "original_source_config": str(cohort_config_path),
                "resolved_source_config_path": export_paths.get("resolved_config_path"),
                "bootstrap_output_dir": str(cohort_bootstrap_dir),
                "n_public_sources": resolution_summary.get("n_recognized_public_sources", 0),
                "n_blocked_sources": resolution_summary.get("n_blocked_sources", 0),
                "public_resolution_percent": resolution_summary.get("public_resolution_percent", 0),
                "overall_resolution_percent": resolution_summary.get("overall_resolution_percent", 0),
                "ready_for_resolved_config": resolution_summary.get("ready_for_resolved_config", False),
                "ready_for_live_public_sources": resolution_summary.get("ready_for_live_public_sources", False),
                "mode_override": cohort.mode,
                "high_confidence_only_override": cohort.high_confidence_only,
                "public_source_resolution_manifest_path": export_paths.get("public_source_resolution_manifest_path"),
            }
        )
        recommended_actions.extend((export_paths.get("resolution") or {}).get("recommended_actions") or [])

    cohort_table = pd.DataFrame(cohort_rows)
    ready_mask = cohort_table["ready_for_resolved_config"] == True if not cohort_table.empty else pd.Series(dtype=bool)
    ready_live_mask = cohort_table["ready_for_live_public_sources"] == True if not cohort_table.empty else pd.Series(dtype=bool)
    summary = {
        "config_path": str(study_config_file),
        "bootstrap_root_dir": str(bootstrap_root),
        "delivery_dir": str(Path(delivery_dir).resolve()) if delivery_dir else "",
        "n_cohorts": int(len(cohort_rows)),
        "n_ready_cohorts": int(ready_mask.sum()) if not cohort_table.empty else 0,
        "n_live_public_ready_cohorts": int(ready_live_mask.sum()) if not cohort_table.empty else 0,
        "overall_resolution_percent": int(round(cohort_table["overall_resolution_percent"].mean())) if not cohort_table.empty else 0,
        "public_resolution_percent": int(round(cohort_table["public_resolution_percent"].mean())) if not cohort_table.empty else 0,
        "ready_for_resolved_study": bool(not cohort_table.empty and bool(ready_mask.all())),
        "ready_for_live_public_study": bool(not cohort_table.empty and bool(ready_live_mask.all())),
    }
    if summary["ready_for_resolved_study"] and not recommended_actions:
        recommended_actions.append("Estudo publico resolvido e pronto para ser usado como configuracao congelada de benchmark.")

    resolved_study_config_path = output_root / "resolved_study_config.toml"
    resolved_study_config_path.write_text(_study_to_payload(study, cohort_rows), encoding="utf-8")
    cohort_freeze = export_study_cohort_freeze(
        config_path=str(resolved_study_config_path),
        output_dir=str(output_root),
    )
    freeze_summary = cohort_freeze.get("study_cohort_freeze_summary") or {}
    summary["real_data_readiness_percent"] = int(freeze_summary.get("overall_real_data_readiness_percent") or 0)
    summary["ready_for_real_data_study"] = bool(freeze_summary.get("ready_for_real_data_study"))
    summary["n_real_data_ready_cohorts"] = int(freeze_summary.get("n_ready_cohorts") or 0)
    summary["n_example_blocked_cohorts"] = int(freeze_summary.get("n_example_blocked_cohorts") or 0)
    summary["n_placeholder_release_blocked_cohorts"] = int(freeze_summary.get("n_placeholder_release_blocked_cohorts") or 0)
    recommended_actions.extend(cohort_freeze.get("study_cohort_freeze", {}).get("recommended_actions") or [])
    real_data_handoff = export_real_data_handoff_package(
        study_name=study.name,
        resolution_summary=summary,
        cohort_rows=cohort_rows,
        freeze_summary=freeze_summary,
        freeze_cohorts_path=str(cohort_freeze.get("study_cohort_freeze_cohorts_path")),
        freeze_sources_path=str(cohort_freeze.get("study_cohort_freeze_sources_path")),
        output_dir=str(output_root),
    )
    handoff_summary = real_data_handoff.get("study_real_data_handoff_summary") or {}
    summary["real_data_handoff_percent"] = int(handoff_summary.get("real_data_handoff_percent") or 0)
    summary["ready_for_lab_handoff"] = bool(handoff_summary.get("ready_for_lab_handoff"))
    summary["n_real_data_tasks"] = int(handoff_summary.get("n_tasks") or 0)
    summary["n_critical_real_data_tasks"] = int(handoff_summary.get("n_critical_tasks") or 0)
    recommended_actions.extend(real_data_handoff.get("study_real_data_handoff", {}).get("recommended_actions") or [])
    handoff_autofill: dict[str, Any] = {}
    handoff_tracker_path = None
    if delivery_dir:
        handoff_autofill = export_real_data_handoff_autofill(
            study_name=study.name,
            handoff_tasks_path=str(real_data_handoff.get("study_real_data_handoff_tasks_path")),
            tracker_path=str(output_root / "study_real_data_handoff_tracker.csv"),
            delivery_dir=delivery_dir,
            output_dir=str(output_root),
        )
        autofill_summary = handoff_autofill.get("study_real_data_handoff_autofill_summary") or {}
        summary["real_data_handoff_autofill_percent"] = int(autofill_summary.get("overall_handoff_autofill_percent") or 0)
        summary["n_handoff_autofilled_tasks"] = int(autofill_summary.get("n_autofilled_tasks") or 0)
        summary["n_handoff_preserved_completed_tasks"] = int(autofill_summary.get("n_preserved_completed_tasks") or 0)
        summary["n_handoff_unmatched_tasks"] = int(autofill_summary.get("n_unmatched_tasks") or 0)
        summary["ready_for_reconciliation_rerun_from_autofill"] = bool(
            autofill_summary.get("ready_for_reconciliation_rerun")
        )
        handoff_tracker_path = str(handoff_autofill.get("study_real_data_handoff_autofill_tracker_path"))
        recommended_actions.extend(
            handoff_autofill.get("study_real_data_handoff_autofill", {}).get("recommended_actions") or []
        )
    else:
        summary["real_data_handoff_autofill_percent"] = 0
        summary["n_handoff_autofilled_tasks"] = 0
        summary["n_handoff_preserved_completed_tasks"] = 0
        summary["n_handoff_unmatched_tasks"] = summary["n_real_data_tasks"]
        summary["ready_for_reconciliation_rerun_from_autofill"] = False
    handoff_reconciliation = export_real_data_handoff_reconciliation(
        study_name=study.name,
        handoff_tasks_path=str(real_data_handoff.get("study_real_data_handoff_tasks_path")),
        output_dir=str(output_root),
        tracker_path=handoff_tracker_path,
    )
    reconciliation_summary = handoff_reconciliation.get("study_real_data_handoff_reconciliation_summary") or {}
    summary["real_data_handoff_reconciliation_percent"] = int(reconciliation_summary.get("overall_handoff_reconciliation_percent") or 0)
    summary["n_handoff_validated_tasks"] = int(reconciliation_summary.get("n_validated_tasks") or 0)
    summary["n_handoff_pending_tasks"] = int(reconciliation_summary.get("n_pending_tasks") or 0)
    summary["n_handoff_invalid_tasks"] = int(reconciliation_summary.get("n_invalid_tasks") or 0)
    summary["ready_to_rerun_resolution_from_handoff"] = bool(reconciliation_summary.get("ready_to_rerun_resolution"))
    summary["ready_to_rerun_public_study_from_handoff"] = bool(reconciliation_summary.get("ready_to_rerun_public_study"))
    recommended_actions.extend(
        handoff_reconciliation.get("study_real_data_handoff_reconciliation", {}).get("recommended_actions") or []
    )
    handoff_application = export_real_data_handoff_application(
        study_config_path=str(study_config_file),
        cohort_rows=cohort_rows,
        handoff_reconciliation_tasks_path=str(
            handoff_reconciliation.get("study_real_data_handoff_reconciliation_tasks_path")
        ),
        output_dir=str(output_root),
    )
    application_summary = handoff_application.get("study_real_data_handoff_application_summary") or {}
    summary["real_data_handoff_application_percent"] = int(application_summary.get("overall_handoff_application_percent") or 0)
    summary["n_handoff_applied_changes"] = int(application_summary.get("n_applied_changes") or 0)
    summary["ready_for_candidate_resolution_from_handoff"] = bool(application_summary.get("ready_for_candidate_resolution"))
    summary["ready_for_candidate_public_study_from_handoff"] = bool(application_summary.get("ready_for_candidate_public_study"))
    recommended_actions.extend(
        handoff_application.get("study_real_data_handoff_application", {}).get("recommended_actions") or []
    )
    candidate_promotion = export_real_data_candidate_promotion(
        study_name=study.name,
        candidate_config_path=str(handoff_application.get("study_real_data_candidate_config_path")),
        handoff_application_manifest_path=str(handoff_application.get("study_real_data_handoff_application_manifest_path")),
        handoff_reconciliation_tasks_path=str(
            handoff_reconciliation.get("study_real_data_handoff_reconciliation_tasks_path")
        ),
        output_dir=str(output_root),
    )
    promotion_summary = candidate_promotion.get("study_real_data_candidate_promotion_summary") or {}
    summary["real_data_candidate_promotion_percent"] = int(promotion_summary.get("overall_candidate_promotion_percent") or 0)
    summary["ready_to_promote_candidate_config"] = bool(promotion_summary.get("ready_to_promote_candidate_config"))
    summary["ready_to_run_candidate_public_study"] = bool(promotion_summary.get("ready_to_run_candidate_public_study"))
    recommended_actions.extend(
        candidate_promotion.get("study_real_data_candidate_promotion", {}).get("recommended_actions") or []
    )

    manifest_path = output_root / "study_public_config_resolution_manifest.json"
    report_path = output_root / "study_public_config_resolution_report.md"
    cohorts_path = output_root / "study_public_config_resolution_cohorts.csv"
    cohort_table.to_csv(cohorts_path, index=False)

    markdown_lines = [
        "# Study Public Config Resolution",
        "",
        f"- Study config: {summary['config_path']}",
        f"- Bootstrap root dir: {summary['bootstrap_root_dir']}",
        f"- Cohorts: {summary['n_cohorts']}",
        f"- Ready cohorts: {summary['n_ready_cohorts']}",
        f"- Live-public-ready cohorts: {summary['n_live_public_ready_cohorts']}",
        f"- Overall resolution: {summary['overall_resolution_percent']}%",
        f"- Public resolution: {summary['public_resolution_percent']}%",
        f"- Real-data readiness: {summary['real_data_readiness_percent']}%",
        f"- Real-data handoff: {summary['real_data_handoff_percent']}%",
        f"- Handoff autofill: {summary['real_data_handoff_autofill_percent']}%",
        f"- Handoff reconciliation: {summary['real_data_handoff_reconciliation_percent']}%",
        f"- Handoff application: {summary['real_data_handoff_application_percent']}%",
        f"- Candidate promotion: {summary['real_data_candidate_promotion_percent']}%",
        f"- Ready for resolved study: {'yes' if summary['ready_for_resolved_study'] else 'not yet'}",
        f"- Ready for live public study: {'yes' if summary['ready_for_live_public_study'] else 'not yet'}",
        f"- Ready for real-data study: {'yes' if summary['ready_for_real_data_study'] else 'not yet'}",
        f"- Ready for lab handoff: {'yes' if summary['ready_for_lab_handoff'] else 'not yet'}",
        f"- Ready for reconciliation rerun from autofill: {'yes' if summary['ready_for_reconciliation_rerun_from_autofill'] else 'not yet'}",
        f"- Ready to rerun resolution from handoff: {'yes' if summary['ready_to_rerun_resolution_from_handoff'] else 'not yet'}",
        f"- Ready to rerun public study from handoff: {'yes' if summary['ready_to_rerun_public_study_from_handoff'] else 'not yet'}",
        f"- Ready for candidate resolution from handoff: {'yes' if summary['ready_for_candidate_resolution_from_handoff'] else 'not yet'}",
        f"- Ready for candidate public study from handoff: {'yes' if summary['ready_for_candidate_public_study_from_handoff'] else 'not yet'}",
        f"- Ready to promote candidate config: {'yes' if summary['ready_to_promote_candidate_config'] else 'not yet'}",
        f"- Ready to run candidate public study: {'yes' if summary['ready_to_run_candidate_public_study'] else 'not yet'}",
        "",
        "## Cohorts",
        "",
    ]
    for row in cohort_rows:
        markdown_lines.extend(
            [
                f"### {row['cohort_name']}",
                "",
                f"- Role: {row['role']}",
                f"- Overall resolution: {row['overall_resolution_percent']}%",
                f"- Public resolution: {row['public_resolution_percent']}%",
                f"- Ready for resolved config: {'yes' if row['ready_for_resolved_config'] else 'not yet'}",
                f"- Ready for live public sources: {'yes' if row['ready_for_live_public_sources'] else 'not yet'}",
                f"- Resolved source config: {row['resolved_source_config_path']}",
                "",
            ]
        )
    report_path.write_text("\n".join(markdown_lines).strip(), encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "summary": summary,
        "recommended_actions": recommended_actions,
        "resolved_study_config_path": str(resolved_study_config_path),
        "cohorts_path": str(cohorts_path),
        "cohorts": cohort_rows,
        "study_cohort_freeze_manifest_path": cohort_freeze.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_markdown_path": cohort_freeze.get("study_cohort_freeze_markdown_path"),
        "study_cohort_freeze_cohorts_path": cohort_freeze.get("study_cohort_freeze_cohorts_path"),
        "study_cohort_freeze_sources_path": cohort_freeze.get("study_cohort_freeze_sources_path"),
        "study_real_data_handoff_manifest_path": real_data_handoff.get("study_real_data_handoff_manifest_path"),
        "study_real_data_handoff_markdown_path": real_data_handoff.get("study_real_data_handoff_markdown_path"),
        "study_real_data_handoff_html_path": real_data_handoff.get("study_real_data_handoff_html_path"),
        "study_real_data_handoff_cohorts_path": real_data_handoff.get("study_real_data_handoff_cohorts_path"),
        "study_real_data_handoff_tasks_path": real_data_handoff.get("study_real_data_handoff_tasks_path"),
        "study_real_data_handoff_autofill_manifest_path": handoff_autofill.get("study_real_data_handoff_autofill_manifest_path"),
        "study_real_data_handoff_autofill_markdown_path": handoff_autofill.get("study_real_data_handoff_autofill_markdown_path"),
        "study_real_data_handoff_autofill_html_path": handoff_autofill.get("study_real_data_handoff_autofill_html_path"),
        "study_real_data_handoff_autofill_tracker_path": handoff_autofill.get("study_real_data_handoff_autofill_tracker_path"),
        "study_real_data_handoff_autofill_matches_path": handoff_autofill.get("study_real_data_handoff_autofill_matches_path"),
        "study_real_data_handoff_autofill_inventory_path": handoff_autofill.get("study_real_data_handoff_autofill_inventory_path"),
        "study_real_data_handoff_tracker_path": handoff_reconciliation.get("study_real_data_handoff_tracker_path"),
        "study_real_data_handoff_reconciliation_manifest_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_manifest_path"),
        "study_real_data_handoff_reconciliation_markdown_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_markdown_path"),
        "study_real_data_handoff_reconciliation_html_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_html_path"),
        "study_real_data_handoff_reconciliation_tasks_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_tasks_path"),
        "study_real_data_candidate_config_path": handoff_application.get("study_real_data_candidate_config_path"),
        "study_real_data_handoff_application_manifest_path": handoff_application.get("study_real_data_handoff_application_manifest_path"),
        "study_real_data_handoff_application_markdown_path": handoff_application.get("study_real_data_handoff_application_markdown_path"),
        "study_real_data_handoff_application_html_path": handoff_application.get("study_real_data_handoff_application_html_path"),
        "study_real_data_handoff_application_sources_path": handoff_application.get("study_real_data_handoff_application_sources_path"),
        "study_real_data_handoff_application_cohorts_path": handoff_application.get("study_real_data_handoff_application_cohorts_path"),
        "study_real_data_candidate_promotion_manifest_path": candidate_promotion.get("study_real_data_candidate_promotion_manifest_path"),
        "study_real_data_candidate_promotion_markdown_path": candidate_promotion.get("study_real_data_candidate_promotion_markdown_path"),
        "study_real_data_candidate_promotion_html_path": candidate_promotion.get("study_real_data_candidate_promotion_html_path"),
        "study_real_data_candidate_promotion_criteria_path": candidate_promotion.get("study_real_data_candidate_promotion_criteria_path"),
        "study_real_data_candidate_promotion_blockers_path": candidate_promotion.get("study_real_data_candidate_promotion_blockers_path"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "summary": summary,
        "recommended_actions": list(dict.fromkeys(recommended_actions)),
        "resolved_study_config_path": str(resolved_study_config_path),
        "study_public_config_resolution_manifest_path": str(manifest_path),
        "study_public_config_resolution_report_markdown_path": str(report_path),
        "study_public_config_resolution_cohorts_path": str(cohorts_path),
        "study_cohort_freeze_manifest_path": cohort_freeze.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_markdown_path": cohort_freeze.get("study_cohort_freeze_markdown_path"),
        "study_cohort_freeze_cohorts_path": cohort_freeze.get("study_cohort_freeze_cohorts_path"),
        "study_cohort_freeze_sources_path": cohort_freeze.get("study_cohort_freeze_sources_path"),
        "study_real_data_handoff_manifest_path": real_data_handoff.get("study_real_data_handoff_manifest_path"),
        "study_real_data_handoff_markdown_path": real_data_handoff.get("study_real_data_handoff_markdown_path"),
        "study_real_data_handoff_html_path": real_data_handoff.get("study_real_data_handoff_html_path"),
        "study_real_data_handoff_cohorts_path": real_data_handoff.get("study_real_data_handoff_cohorts_path"),
        "study_real_data_handoff_tasks_path": real_data_handoff.get("study_real_data_handoff_tasks_path"),
        "study_real_data_handoff_autofill_manifest_path": handoff_autofill.get("study_real_data_handoff_autofill_manifest_path"),
        "study_real_data_handoff_autofill_markdown_path": handoff_autofill.get("study_real_data_handoff_autofill_markdown_path"),
        "study_real_data_handoff_autofill_html_path": handoff_autofill.get("study_real_data_handoff_autofill_html_path"),
        "study_real_data_handoff_autofill_tracker_path": handoff_autofill.get("study_real_data_handoff_autofill_tracker_path"),
        "study_real_data_handoff_autofill_matches_path": handoff_autofill.get("study_real_data_handoff_autofill_matches_path"),
        "study_real_data_handoff_autofill_inventory_path": handoff_autofill.get("study_real_data_handoff_autofill_inventory_path"),
        "study_real_data_handoff_tracker_path": handoff_reconciliation.get("study_real_data_handoff_tracker_path"),
        "study_real_data_handoff_reconciliation_manifest_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_manifest_path"),
        "study_real_data_handoff_reconciliation_markdown_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_markdown_path"),
        "study_real_data_handoff_reconciliation_html_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_html_path"),
        "study_real_data_handoff_reconciliation_tasks_path": handoff_reconciliation.get("study_real_data_handoff_reconciliation_tasks_path"),
        "study_real_data_candidate_config_path": handoff_application.get("study_real_data_candidate_config_path"),
        "study_real_data_handoff_application_manifest_path": handoff_application.get("study_real_data_handoff_application_manifest_path"),
        "study_real_data_handoff_application_markdown_path": handoff_application.get("study_real_data_handoff_application_markdown_path"),
        "study_real_data_handoff_application_html_path": handoff_application.get("study_real_data_handoff_application_html_path"),
        "study_real_data_handoff_application_sources_path": handoff_application.get("study_real_data_handoff_application_sources_path"),
        "study_real_data_handoff_application_cohorts_path": handoff_application.get("study_real_data_handoff_application_cohorts_path"),
        "study_real_data_candidate_promotion_manifest_path": candidate_promotion.get("study_real_data_candidate_promotion_manifest_path"),
        "study_real_data_candidate_promotion_markdown_path": candidate_promotion.get("study_real_data_candidate_promotion_markdown_path"),
        "study_real_data_candidate_promotion_html_path": candidate_promotion.get("study_real_data_candidate_promotion_html_path"),
        "study_real_data_candidate_promotion_criteria_path": candidate_promotion.get("study_real_data_candidate_promotion_criteria_path"),
        "study_real_data_candidate_promotion_blockers_path": candidate_promotion.get("study_real_data_candidate_promotion_blockers_path"),
    }
