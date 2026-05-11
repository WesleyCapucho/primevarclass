from __future__ import annotations

import csv
import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

SYNC_REGISTRY_COLUMNS = [
    "run_id",
    "run_started_at",
    "run_finished_at",
    "dry_run",
    "config_path",
    "output_dir",
    "source_name",
    "profile_id",
    "display_name",
    "automation_level",
    "can_execute_from_script",
    "execution_status",
    "selected",
    "release_value",
    "target_dir",
    "n_expected_artifacts",
    "n_present_artifacts",
    "artifact_coverage_percent",
    "error_message",
    "run_manifest_path",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _windows_path(path: Path) -> str:
    return str(path.resolve())


def _ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


def _ps_mkdir_command(path: str) -> str:
    return f"New-Item -ItemType Directory -Force -Path {_ps_quote(path)} | Out-Null"


def _ps_download_command(url: str, output_path: str) -> str:
    return f"Invoke-WebRequest -Uri {_ps_quote(url)} -OutFile {_ps_quote(output_path)}"


def _plan_to_commands(plan: Iterable[dict]) -> List[str]:
    commands: List[str] = []
    for step in plan:
        step_type = str(step.get("step_type") or "")
        if step_type == "mkdir":
            commands.append(_ps_mkdir_command(str(step.get("path") or "")))
        elif step_type == "download":
            commands.append(_ps_download_command(str(step.get("url") or ""), str(step.get("output_path") or "")))
        elif step_type == "filter_variant_table":
            commands.extend(
                [
                    f"# PrimeVarClass runner step: filter local table {_ps_quote(str(step.get('input_path') or ''))}",
                    f"# Output subset: {_ps_quote(str(step.get('output_path') or ''))}",
                    f"# Output manifest: {_ps_quote(str(step.get('manifest_path') or ''))}",
                    f"# Genes: {', '.join(str(item) for item in (step.get('gene_allowlist') or []))}",
                ]
            )
        elif step_type == "stage_local_file":
            commands.extend(
                [
                    f"# PrimeVarClass runner step: stage curated local file {_ps_quote(str(step.get('input_path') or ''))}",
                    f"# Output staged file: {_ps_quote(str(step.get('output_path') or ''))}",
                    f"# Output manifest: {_ps_quote(str(step.get('manifest_path') or ''))}",
                ]
            )
    return commands


def _clinvar_execution_plan(target_dir: Path) -> List[dict]:
    data_path = target_dir / "variant_summary.txt.gz"
    md5_path = target_dir / "variant_summary.txt.gz.md5"
    return [
        {
            "step_type": "mkdir",
            "path": _windows_path(target_dir),
            "label": "Create ClinVar staging directory",
        },
        {
            "step_type": "download",
            "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
            "output_path": _windows_path(data_path),
            "label": "Download ClinVar variant summary",
        },
        {
            "step_type": "download",
            "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5",
            "output_path": _windows_path(md5_path),
            "label": "Download ClinVar checksum",
        },
    ]


def _mavedb_execution_plan(target_dir: Path, urn: str) -> List[dict]:
    encoded_urn = urllib.parse.quote(str(urn), safe="")
    metadata_path = target_dir / "score_set_metadata.json"
    mapped_variants_path = target_dir / "mapped_variants.json"
    return [
        {
            "step_type": "mkdir",
            "path": _windows_path(target_dir),
            "label": "Create MaveDB staging directory",
        },
        {
            "step_type": "download",
            "url": f"https://api.mavedb.org/api/v1/score-sets/{encoded_urn}",
            "output_path": _windows_path(metadata_path),
            "label": "Download MaveDB score set metadata",
        },
        {
            "step_type": "download",
            "url": f"https://api.mavedb.org/api/v1/score-sets/{encoded_urn}/mapped-variants",
            "output_path": _windows_path(mapped_variants_path),
            "label": "Download MaveDB mapped variants",
        },
    ]


def _resolve_tabular_format(source_path: str, source_format: str | None = None) -> str:
    explicit = str(source_format or "").strip().lower()
    if explicit in {"csv", "tsv"}:
        return explicit
    suffix = Path(source_path).suffix.lower()
    if suffix in {".tsv", ".txt"}:
        return "tsv"
    return "csv"


def _gnomad_execution_plan(
    target_dir: Path,
    *,
    source_path: str,
    source_format: str | None,
    gene_allowlist: List[str] | None = None,
) -> List[dict]:
    subset_path = target_dir / "gnomad_brca_subset.tsv"
    manifest_path = target_dir / "gnomad_brca_subset_manifest.json"
    return [
        {
            "step_type": "mkdir",
            "path": _windows_path(target_dir),
            "label": "Create gnomAD staging directory",
        },
        {
            "step_type": "filter_variant_table",
            "input_path": str(Path(source_path).resolve()),
            "input_format": _resolve_tabular_format(source_path, source_format),
            "output_path": _windows_path(subset_path),
            "manifest_path": _windows_path(manifest_path),
            "gene_allowlist": list(gene_allowlist or ["BRCA1", "BRCA2"]),
            "gene_column_candidates": ["gene", "gene_symbol", "Gene", "symbol"],
            "label": "Filter gnomAD variant table to BRCA subset",
        },
    ]


def _enigma_execution_plan(target_dir: Path, *, source_path: str) -> List[dict]:
    source_file = Path(source_path)
    staged_path = target_dir / f"enigma_curated_import{source_file.suffix or '.tsv'}"
    manifest_path = target_dir / "enigma_curated_import_manifest.json"
    return [
        {
            "step_type": "mkdir",
            "path": _windows_path(target_dir),
            "label": "Create ENIGMA staging directory",
        },
        {
            "step_type": "stage_local_file",
            "input_path": str(source_file.resolve()),
            "output_path": _windows_path(staged_path),
            "manifest_path": _windows_path(manifest_path),
            "label": "Stage curated ENIGMA import",
        },
    ]


def _comment_block(lines: List[str]) -> List[str]:
    return [f"# {line}" if line else "#" for line in lines]


def _bundle_paths(output_root: Path) -> dict:
    return {
        "manifest_path": output_root / "public_source_bootstrap_manifest.json",
        "guide_markdown_path": output_root / "public_source_bootstrap_guide.md",
        "powershell_script_path": output_root / "bootstrap_public_sources.ps1",
        "sync_runs_root": output_root / "sync_runs",
        "sync_registry_path": output_root / "public_source_sync_registry.csv",
    }


def _expected_artifact_paths(
    profile_id: str,
    target_dir: Path,
    *,
    resolved_mavedb_urn: str | None = None,
    local_source_available: bool = False,
    local_source_suffix: str | None = None,
) -> List[str]:
    if profile_id == "clinvar":
        return [
            _windows_path(target_dir / "variant_summary.txt.gz"),
            _windows_path(target_dir / "variant_summary.txt.gz.md5"),
        ]
    if profile_id == "gnomad" and local_source_available:
        return [
            _windows_path(target_dir / "gnomad_brca_subset.tsv"),
            _windows_path(target_dir / "gnomad_brca_subset_manifest.json"),
        ]
    if profile_id == "enigma" and local_source_available:
        suffix = local_source_suffix or ".tsv"
        return [
            _windows_path(target_dir / f"enigma_curated_import{suffix}"),
            _windows_path(target_dir / "enigma_curated_import_manifest.json"),
        ]
    if profile_id == "mavedb" and resolved_mavedb_urn:
        return [
            _windows_path(target_dir / "score_set_metadata.json"),
            _windows_path(target_dir / "mapped_variants.json"),
        ]
    return []


def _collect_artifact_state(item: dict) -> dict:
    expected_paths = [str(path) for path in (item.get("expected_artifact_paths") or [])]
    artifacts = []
    present = 0
    for artifact_path in expected_paths:
        path = Path(artifact_path)
        exists = path.exists()
        if exists:
            present += 1
        artifacts.append(
            {
                "path": str(path.resolve()),
                "exists": exists,
                "size_bytes": int(path.stat().st_size) if exists else 0,
            }
        )
    expected = len(expected_paths)
    coverage = int(round((present / expected) * 100)) if expected else 0
    return {
        "expected_artifacts": artifacts,
        "n_expected_artifacts": expected,
        "n_present_artifacts": present,
        "artifact_coverage_percent": coverage,
    }


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_public_source_bootstrap_manifest(output_dir: str) -> dict | None:
    output_root = Path(output_dir).resolve()
    return _read_json(_bundle_paths(output_root)["manifest_path"])


def _load_registry_rows(registry_path: Path) -> List[dict]:
    if not registry_path.exists():
        return []
    try:
        with registry_path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except Exception:
        return []


def _append_registry_rows(registry_path: Path, rows: Iterable[dict]) -> None:
    rows = [dict(row) for row in rows]
    if not rows:
        return
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not registry_path.exists()
    with registry_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SYNC_REGISTRY_COLUMNS)
        if write_header:
            writer.writeheader()
        for row in rows:
            normalized = {column: row.get(column, "") for column in SYNC_REGISTRY_COLUMNS}
            writer.writerow(normalized)


def _selected_source(item: dict, selected_sources: List[str] | None) -> bool:
    if not selected_sources:
        return True
    selected_tokens = {_normalize_token(value) for value in selected_sources if str(value or "").strip()}
    item_tokens = {
        _normalize_token(item.get("source_name")),
        _normalize_token(item.get("profile_id")),
        _normalize_token(item.get("display_name")),
    }
    item_tokens.discard("")
    return bool(selected_tokens & item_tokens)


def _execute_step(step: dict, *, timeout_seconds: int = 180) -> dict:
    step_type = str(step.get("step_type") or "")
    if step_type == "mkdir":
        path = Path(str(step.get("path") or "")).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return {
            "step_type": step_type,
            "status": "completed",
            "path": str(path),
        }

    if step_type == "download":
        output_path = Path(str(step.get("output_path") or "")).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            str(step.get("url") or ""),
            headers={"User-Agent": "PrimeVarClass/0.2.0"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            output_path.write_bytes(response.read())
            status_code = getattr(response, "status", 200)
        return {
            "step_type": step_type,
            "status": "completed",
            "url": str(step.get("url") or ""),
            "output_path": str(output_path),
            "http_status": int(status_code),
        }

    if step_type == "filter_variant_table":
        input_path = Path(str(step.get("input_path") or "")).resolve()
        if not input_path.exists():
            raise ValueError(f"Arquivo de entrada nao encontrado para filtro: {input_path}")
        input_format = _resolve_tabular_format(str(input_path), str(step.get("input_format") or ""))
        sep = "\t" if input_format == "tsv" else ","
        dataframe = pd.read_csv(input_path, sep=sep)
        gene_column = None
        for candidate in step.get("gene_column_candidates") or []:
            if candidate in dataframe.columns:
                gene_column = candidate
                break
        if gene_column is None:
            raise ValueError(f"Nao foi encontrada uma coluna de gene em {input_path}.")
        allowlist = {str(gene).strip().upper() for gene in (step.get("gene_allowlist") or []) if str(gene).strip()}
        if not allowlist:
            raise ValueError("A etapa de filtro gnomAD precisa de pelo menos um gene na allowlist.")

        filtered = dataframe.loc[dataframe[gene_column].astype(str).str.upper().isin(allowlist)].copy()
        output_path = Path(str(step.get("output_path") or "")).resolve()
        manifest_path = Path(str(step.get("manifest_path") or "")).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        filtered.to_csv(output_path, sep="\t", index=False)

        filter_manifest = {
            "input_path": str(input_path),
            "input_format": input_format,
            "input_size_bytes": int(os.path.getsize(input_path)),
            "output_path": str(output_path),
            "gene_column": gene_column,
            "gene_allowlist": sorted(allowlist),
            "rows_input": int(len(dataframe)),
            "rows_output": int(len(filtered)),
            "columns": [str(column) for column in filtered.columns],
        }
        manifest_path.write_text(json.dumps(filter_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "step_type": step_type,
            "status": "completed",
            "input_path": str(input_path),
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "rows_input": int(len(dataframe)),
            "rows_output": int(len(filtered)),
            "gene_column": gene_column,
        }

    if step_type == "stage_local_file":
        input_path = Path(str(step.get("input_path") or "")).resolve()
        if not input_path.exists():
            raise ValueError(f"Arquivo de entrada nao encontrado para staging: {input_path}")
        output_path = Path(str(step.get("output_path") or "")).resolve()
        manifest_path = Path(str(step.get("manifest_path") or "")).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, output_path)
        stage_manifest = {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "input_size_bytes": int(os.path.getsize(input_path)),
            "output_size_bytes": int(os.path.getsize(output_path)),
            "staging_mode": "curated_local_import",
        }
        manifest_path.write_text(json.dumps(stage_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "step_type": step_type,
            "status": "completed",
            "input_path": str(input_path),
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
        }

    raise ValueError(f"Tipo de passo nao suportado: {step_type}")


def build_public_source_bootstrap_bundle(
    *,
    config_path: str,
    public_source_assessment: dict | None = None,
    public_source_sync_plan: dict | None = None,
    output_dir: str,
) -> dict:
    assessment = dict(public_source_assessment or {})
    sync_plan = dict(public_source_sync_plan or {})
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle_paths = _bundle_paths(output_root)
    bundle_paths["sync_runs_root"].mkdir(parents=True, exist_ok=True)

    sync_items = list(sync_plan.get("sync_items") or [])
    bundle_items = []
    script_lines = [
        "# PrimeVarClass public-source bootstrap bundle",
        "# Generated automatically to help stage official public datasets locally.",
        "# Review comments for semi-automatable and manual-assisted sources before execution.",
        "",
        "$ErrorActionPreference = 'Stop'",
        "",
    ]

    guide_lines = [
        "# PrimeVarClass Public Source Bootstrap Guide",
        "",
        f"- Config path: {Path(config_path).resolve()}",
        f"- Output root: {output_root}",
        "",
        "## Sources",
        "",
    ]

    for item in sync_items:
        profile_id = str(item.get("profile_id") or "public")
        source_name = str(item.get("source_name") or profile_id)
        target_dir = output_root / profile_id / source_name
        automation_level = str(item.get("automation_level") or "manual_assisted")
        entrypoints = list(item.get("official_entrypoints") or [])
        recommended_artifacts = list(item.get("recommended_artifacts") or [])
        execution_plan: List[dict] = []
        source_path = str(item.get("source_path") or "").strip() or None
        source_format = str(item.get("source_format") or "").strip() or None
        gene_allowlist = list(item.get("gene_allowlist") or [])
        local_source_exists = bool(item.get("local_source_exists"))
        local_source_suffix = Path(source_path).suffix if source_path else None
        resolved_mavedb_urn = str(item.get("resolved_mavedb_urn") or "").strip() or None
        if profile_id == "clinvar":
            execution_plan = _clinvar_execution_plan(target_dir)
        elif profile_id == "gnomad" and source_path and local_source_exists:
            execution_plan = _gnomad_execution_plan(
                target_dir,
                source_path=source_path,
                source_format=source_format,
                gene_allowlist=gene_allowlist,
            )
        elif profile_id == "enigma" and source_path and local_source_exists:
            execution_plan = _enigma_execution_plan(target_dir, source_path=source_path)
        elif profile_id == "mavedb" and resolved_mavedb_urn:
            execution_plan = _mavedb_execution_plan(target_dir, resolved_mavedb_urn)

        expected_artifact_paths = _expected_artifact_paths(
            profile_id,
            target_dir,
            local_source_available=bool(profile_id in {"gnomad", "enigma"} and source_path and local_source_exists),
            local_source_suffix=local_source_suffix,
            resolved_mavedb_urn=resolved_mavedb_urn,
        )
        commands: List[str]
        if execution_plan:
            commands = _plan_to_commands(execution_plan)
        elif profile_id == "gnomad":
            commands = [
                _ps_mkdir_command(_windows_path(target_dir)),
                "# TODO: forneca um caminho local de tabela gnomAD exportada para habilitar recorte BRCA controlado.",
            ]
        elif profile_id == "enigma":
            commands = [
                _ps_mkdir_command(_windows_path(target_dir)),
                "# TODO: forneca um arquivo local curado ENIGMA para habilitar staging auditavel da importacao.",
            ]
        elif profile_id == "mavedb":
            commands = [
                _ps_mkdir_command(_windows_path(target_dir)),
                "# TODO: defina release_version = 'urn:mavedb:...' no catalogo para habilitar sync automatico do score set.",
            ]
        elif automation_level == "automatable":
            commands = [
                _ps_mkdir_command(_windows_path(target_dir)),
                f"# TODO: conectar download automatico para {profile_id} com os entrypoints oficiais abaixo.",
            ]
        else:
            commands = [f"# TODO: sincronizacao {automation_level} para {profile_id}. Use os entrypoints oficiais abaixo."]

        bundle_item = {
            "source_name": source_name,
            "profile_id": profile_id,
            "display_name": item.get("display_name"),
            "release_value": item.get("release_value"),
            "automation_level": automation_level,
            "target_dir": _windows_path(target_dir),
            "can_execute_from_script": bool(execution_plan),
            "official_entrypoints": entrypoints,
            "recommended_artifacts": recommended_artifacts,
            "expected_artifact_paths": expected_artifact_paths,
            "next_action": item.get("next_action"),
            "source_path": source_path,
            "source_format": source_format,
            "gene_allowlist": gene_allowlist,
            "local_source_exists": local_source_exists,
            "resolved_mavedb_urn": resolved_mavedb_urn,
            "execution_plan": execution_plan,
            "bootstrap_commands": commands,
        }
        bundle_item.update(_collect_artifact_state(bundle_item))
        bundle_items.append(bundle_item)

        script_lines.extend(
            _comment_block(
                [
                    f"Source: {item.get('display_name') or source_name} ({source_name})",
                    f"Release: {item.get('release_value') or '-'}",
                    f"Automation level: {automation_level}",
                    f"Next action: {item.get('next_action') or '-'}",
                    f"Local source path: {source_path or '-'}" if profile_id == "gnomad" else "",
                    f"Local source available: {'yes' if local_source_exists else 'no'}" if profile_id == "gnomad" else "",
                    f"Curated source path: {source_path or '-'}" if profile_id == "enigma" else "",
                    f"Curated source available: {'yes' if local_source_exists else 'no'}" if profile_id == "enigma" else "",
                    f"MaveDB URN: {resolved_mavedb_urn or '-'}" if profile_id == "mavedb" else "",
                    *[f"Official entrypoint: {entry.get('label')} -> {entry.get('url')}" for entry in entrypoints],
                    *[f"Expected artifact: {artifact}" for artifact in recommended_artifacts],
                ]
            )
        )
        script_lines.extend(commands)
        script_lines.extend(["", ""])

        guide_lines.extend(
            [
                f"### {item.get('display_name') or source_name} - {source_name}",
                "",
                f"- Release: {item.get('release_value') or '-'}",
                f"- Automation level: {automation_level}",
                f"- Target dir: {_windows_path(target_dir)}",
                f"- Script-executable: {'yes' if execution_plan else 'no'}",
                f"- Next action: {item.get('next_action') or '-'}",
            ]
        )
        if profile_id == "gnomad":
            guide_lines.append(f"- Local source path: {source_path or '-'}")
            guide_lines.append(f"- Local source available: {'yes' if local_source_exists else 'no'}")
            guide_lines.append(f"- Gene allowlist: {', '.join(gene_allowlist) if gene_allowlist else 'BRCA1, BRCA2'}")
        if profile_id == "enigma":
            guide_lines.append(f"- Curated source path: {source_path or '-'}")
            guide_lines.append(f"- Curated source available: {'yes' if local_source_exists else 'no'}")
        if profile_id == "mavedb":
            guide_lines.append(f"- Resolved URN: {resolved_mavedb_urn or '-'}")
        for entry in entrypoints:
            guide_lines.append(f"- Official entrypoint: [{entry.get('label')}]({entry.get('url')})")
            if entry.get("notes"):
                guide_lines.append(f"- Notes: {entry.get('notes')}")
        for artifact in recommended_artifacts:
            guide_lines.append(f"- Expected artifact: {artifact}")
        guide_lines.append("")

    summary = {
        "config_path": str(Path(config_path).resolve()),
        "output_dir": str(output_root),
        "n_bundle_items": int(len(bundle_items)),
        "n_script_executable_items": int(sum(1 for item in bundle_items if item.get("can_execute_from_script"))),
        "n_manual_followups": int(sum(1 for item in bundle_items if not item.get("can_execute_from_script"))),
    }

    manifest = {
        "summary": summary,
        "assessment_summary": assessment.get("summary") or {},
        "sync_summary": sync_plan.get("summary") or {},
        "bundle_items": bundle_items,
    }

    bundle_paths["manifest_path"].write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    bundle_paths["guide_markdown_path"].write_text("\n".join(guide_lines).strip(), encoding="utf-8")
    bundle_paths["powershell_script_path"].write_text("\n".join(script_lines).strip() + "\n", encoding="utf-8")

    return {
        "summary": summary,
        "manifest_path": str(bundle_paths["manifest_path"]),
        "guide_markdown_path": str(bundle_paths["guide_markdown_path"]),
        "powershell_script_path": str(bundle_paths["powershell_script_path"]),
        "sync_registry_path": str(bundle_paths["sync_registry_path"]),
        "sync_runs_root": str(bundle_paths["sync_runs_root"]),
        "bundle_items": bundle_items,
    }


def build_public_benchmark_readiness(
    *,
    public_source_assessment: dict | None = None,
    public_source_sync_plan: dict | None = None,
    sync_history: dict | None = None,
    bootstrap_bundle: dict | None = None,
) -> dict:
    assessment = dict(public_source_assessment or {})
    sync_plan = dict(public_source_sync_plan or {})
    history = dict(sync_history or {})
    bundle = dict(bootstrap_bundle or {})

    recognized_sources = [item for item in (assessment.get("sources") or []) if item.get("recognized_public_source")]
    source_status_index = {
        str(item.get("source_name") or ""): dict(item)
        for item in (history.get("source_statuses") or [])
    }
    bundle_index = {
        str(item.get("source_name") or ""): dict(item)
        for item in (bundle.get("bundle_items") or [])
    }

    source_readiness = []
    for source in recognized_sources:
        source_name = str(source.get("source_name") or "")
        history_status = source_status_index.get(source_name, {})
        sync_percent = int(history_status.get("sync_readiness_percent", 0) or 0)
        blended = int(round((int(source.get("readiness_percent", 0) or 0) + sync_percent) / 2))
        source_readiness.append(
            {
                "source_name": source_name,
                "display_name": source.get("display_name"),
                "catalog_readiness_percent": int(source.get("readiness_percent", 0) or 0),
                "sync_readiness_percent": sync_percent,
                "benchmark_readiness_percent": blended,
                "latest_execution_status": history_status.get("latest_execution_status"),
                "has_execution_ready_bundle": bool(bundle_index.get(source_name, {}).get("can_execute_from_script")),
            }
        )

    execution_ready_sources = [
        item
        for item in (bundle.get("bundle_items") or [])
        if item.get("can_execute_from_script")
    ]
    execution_ready_names = {str(item.get("source_name") or "") for item in execution_ready_sources}
    completed_execution_ready = sum(
        1
        for name in execution_ready_names
        if str((source_status_index.get(name) or {}).get("latest_execution_status") or "") == "completed"
    )
    catalog_ready = bool((assessment.get("summary") or {}).get("ready_for_public_benchmark"))
    sync_history_percent = int(history.get("summary", {}).get("sync_readiness_percent", 0) or 0)
    catalog_percent = int((assessment.get("summary") or {}).get("overall_readiness_percent", 0) or 0)
    benchmark_percent = int(round((catalog_percent + sync_history_percent) / 2)) if recognized_sources else 0
    ready_for_live_public_benchmark = bool(
        recognized_sources
        and catalog_ready
        and (not execution_ready_sources or completed_execution_ready == len(execution_ready_sources))
    )

    markdown_lines = [
        "# Public Benchmark Readiness",
        "",
        f"- Catalog readiness: {catalog_percent}%",
        f"- Sync readiness: {sync_history_percent}%",
        f"- Benchmark readiness: {benchmark_percent}%",
        f"- Execution-ready sources completed: {completed_execution_ready}/{len(execution_ready_sources)}",
        f"- Ready for live public benchmark: {'yes' if ready_for_live_public_benchmark else 'not yet'}",
        "",
        "## Source Readiness",
        "",
    ]
    for item in source_readiness:
        markdown_lines.extend(
            [
                f"### {item.get('display_name') or item.get('source_name')}",
                "",
                f"- Catalog readiness: {item.get('catalog_readiness_percent', 0)}%",
                f"- Sync readiness: {item.get('sync_readiness_percent', 0)}%",
                f"- Benchmark readiness: {item.get('benchmark_readiness_percent', 0)}%",
                f"- Latest execution status: {item.get('latest_execution_status') or 'never_run'}",
                "",
            ]
        )

    return {
        "summary": {
            "n_recognized_sources": int(len(recognized_sources)),
            "catalog_readiness_percent": catalog_percent,
            "sync_readiness_percent": sync_history_percent,
            "benchmark_readiness_percent": benchmark_percent,
            "n_execution_ready_sources": int(len(execution_ready_sources)),
            "n_completed_execution_ready_sources": int(completed_execution_ready),
            "ready_for_live_public_benchmark": ready_for_live_public_benchmark,
        },
        "sources": source_readiness,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def load_public_source_sync_history(
    *,
    output_dir: str,
    public_source_assessment: dict | None = None,
    public_source_sync_plan: dict | None = None,
    limit: int = 50,
) -> dict:
    output_root = Path(output_dir).resolve()
    bundle = load_public_source_bootstrap_manifest(str(output_root)) or {}
    registry_path = _bundle_paths(output_root)["sync_registry_path"]
    rows = _load_registry_rows(registry_path)
    rows.sort(key=lambda item: str(item.get("run_started_at") or ""), reverse=True)
    limited_rows = rows[: max(1, int(limit))]

    latest_by_source: Dict[str, dict] = {}
    for row in rows:
        source_name = str(row.get("source_name") or "")
        if source_name and source_name not in latest_by_source:
            latest_by_source[source_name] = row

    bundle_index = {
        str(item.get("source_name") or ""): dict(item)
        for item in (bundle.get("bundle_items") or [])
    }
    assessment_sources = [
        source
        for source in (public_source_assessment or {}).get("sources", [])
        if source.get("recognized_public_source")
    ]
    if not assessment_sources:
        assessment_sources = [
            {
                "source_name": row.get("source_name"),
                "profile_id": row.get("profile_id"),
                "display_name": row.get("display_name"),
                "readiness_percent": 0,
                "recognized_public_source": True,
            }
            for row in latest_by_source.values()
        ]

    source_statuses = []
    for source in assessment_sources:
        source_name = str(source.get("source_name") or "")
        latest = latest_by_source.get(source_name, {})
        latest_status = str(latest.get("execution_status") or "never_run")
        artifact_coverage = int(latest.get("artifact_coverage_percent") or 0) if latest else 0
        sync_readiness_percent = {
            "completed": max(80, artifact_coverage or 80),
            "dry_run": 65,
            "manual_followup": 35,
            "not_selected": 15,
            "failed": 10,
            "never_run": 0,
        }.get(latest_status, 0)
        source_statuses.append(
            {
                "source_name": source_name,
                "profile_id": source.get("profile_id"),
                "display_name": source.get("display_name"),
                "latest_execution_status": latest_status,
                "latest_run_id": latest.get("run_id"),
                "latest_run_started_at": latest.get("run_started_at"),
                "artifact_coverage_percent": artifact_coverage,
                "sync_readiness_percent": sync_readiness_percent,
                "has_execution_ready_bundle": bool(bundle_index.get(source_name, {}).get("can_execute_from_script")),
            }
        )

    sync_readiness_percent = int(round(sum(item["sync_readiness_percent"] for item in source_statuses) / len(source_statuses))) if source_statuses else 0
    summary = {
        "output_dir": str(output_root),
        "registry_path": str(registry_path),
        "n_runs": int(len(rows)),
        "n_recent_rows": int(len(limited_rows)),
        "n_sources_with_sync_history": int(len(source_statuses)),
        "n_completed_rows": int(sum(1 for row in rows if str(row.get("execution_status") or "") == "completed")),
        "n_dry_run_rows": int(sum(1 for row in rows if str(row.get("execution_status") or "") == "dry_run")),
        "n_failed_rows": int(sum(1 for row in rows if str(row.get("execution_status") or "") == "failed")),
        "latest_run_at": rows[0].get("run_started_at") if rows else None,
        "sync_readiness_percent": sync_readiness_percent,
    }

    markdown_lines = [
        "# Public Source Sync History",
        "",
        f"- Output dir: {summary['output_dir']}",
        f"- Total sync rows: {summary['n_runs']}",
        f"- Sources with sync history: {summary['n_sources_with_sync_history']}",
        f"- Completed rows: {summary['n_completed_rows']}",
        f"- Dry-run rows: {summary['n_dry_run_rows']}",
        f"- Failed rows: {summary['n_failed_rows']}",
        f"- Sync readiness: {summary['sync_readiness_percent']}%",
        "",
        "## Latest Source Status",
        "",
    ]
    for item in source_statuses:
        markdown_lines.extend(
            [
                f"### {item.get('display_name') or item.get('source_name')}",
                "",
                f"- Latest execution status: {item.get('latest_execution_status')}",
                f"- Latest run: {item.get('latest_run_id') or '-'}",
                f"- Latest timestamp: {item.get('latest_run_started_at') or '-'}",
                f"- Artifact coverage: {item.get('artifact_coverage_percent', 0)}%",
                f"- Sync readiness: {item.get('sync_readiness_percent', 0)}%",
                "",
            ]
        )

    benchmark_readiness = build_public_benchmark_readiness(
        public_source_assessment=public_source_assessment,
        public_source_sync_plan=public_source_sync_plan,
        sync_history={
            "summary": summary,
            "source_statuses": source_statuses,
        },
        bootstrap_bundle=bundle,
    )
    return {
        "summary": summary,
        "recent_rows": limited_rows,
        "source_statuses": source_statuses,
        "benchmark_readiness": benchmark_readiness,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }


def execute_public_source_bootstrap_bundle(
    *,
    config_path: str,
    public_source_assessment: dict | None = None,
    public_source_sync_plan: dict | None = None,
    output_dir: str,
    dry_run: bool = True,
    selected_sources: List[str] | None = None,
) -> dict:
    bundle = build_public_source_bootstrap_bundle(
        config_path=config_path,
        public_source_assessment=public_source_assessment,
        public_source_sync_plan=public_source_sync_plan,
        output_dir=output_dir,
    )
    output_root = Path(output_dir).resolve()
    bundle_paths = _bundle_paths(output_root)
    bundle_paths["sync_runs_root"].mkdir(parents=True, exist_ok=True)

    run_id = f"public-sync-{uuid.uuid4().hex[:12]}"
    run_dir = bundle_paths["sync_runs_root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_started_at = _now_utc()

    execution_items = []
    registry_rows = []
    for bundle_item in bundle.get("bundle_items", []):
        item = dict(bundle_item)
        source_name = str(item.get("source_name") or "")
        selected = _selected_source(item, selected_sources)
        before_state = _collect_artifact_state(item)
        execution_status = "not_selected"
        error_message = ""
        step_results: List[dict] = []

        if selected:
            if not item.get("can_execute_from_script"):
                execution_status = "manual_followup"
            elif dry_run:
                execution_status = "dry_run"
            else:
                try:
                    for step in item.get("execution_plan") or []:
                        step_results.append(_execute_step(step))
                    execution_status = "completed"
                except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
                    execution_status = "failed"
                    error_message = str(exc)

        after_state = _collect_artifact_state(item)
        execution_item = {
            "run_id": run_id,
            "run_started_at": run_started_at,
            "source_name": source_name,
            "profile_id": item.get("profile_id"),
            "display_name": item.get("display_name"),
            "release_value": item.get("release_value"),
            "automation_level": item.get("automation_level"),
            "selected": selected,
            "can_execute_from_script": bool(item.get("can_execute_from_script")),
            "execution_status": execution_status,
            "dry_run": bool(dry_run),
            "target_dir": item.get("target_dir"),
            "artifact_state_before": before_state,
            "artifact_state_after": after_state,
            "step_results": step_results,
            "error_message": error_message,
        }
        execution_items.append(execution_item)
        registry_rows.append(
            {
                "run_id": run_id,
                "run_started_at": run_started_at,
                "run_finished_at": "",
                "dry_run": str(bool(dry_run)).lower(),
                "config_path": str(Path(config_path).resolve()),
                "output_dir": str(output_root),
                "source_name": source_name,
                "profile_id": item.get("profile_id"),
                "display_name": item.get("display_name"),
                "automation_level": item.get("automation_level"),
                "can_execute_from_script": str(bool(item.get("can_execute_from_script"))).lower(),
                "execution_status": execution_status,
                "selected": str(bool(selected)).lower(),
                "release_value": item.get("release_value") or "",
                "target_dir": item.get("target_dir") or "",
                "n_expected_artifacts": after_state.get("n_expected_artifacts", 0),
                "n_present_artifacts": after_state.get("n_present_artifacts", 0),
                "artifact_coverage_percent": after_state.get("artifact_coverage_percent", 0),
                "error_message": error_message,
                "run_manifest_path": "",
            }
        )

    run_finished_at = _now_utc()
    summary = {
        "config_path": str(Path(config_path).resolve()),
        "output_dir": str(output_root),
        "run_id": run_id,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "dry_run": bool(dry_run),
        "n_items": int(len(execution_items)),
        "n_selected_items": int(sum(1 for item in execution_items if item.get("selected"))),
        "n_completed_items": int(sum(1 for item in execution_items if item.get("execution_status") == "completed")),
        "n_dry_run_items": int(sum(1 for item in execution_items if item.get("execution_status") == "dry_run")),
        "n_failed_items": int(sum(1 for item in execution_items if item.get("execution_status") == "failed")),
        "n_manual_followups": int(sum(1 for item in execution_items if item.get("execution_status") == "manual_followup")),
    }

    run_manifest = {
        "summary": summary,
        "bundle_summary": bundle.get("summary") or {},
        "assessment_summary": (public_source_assessment or {}).get("summary") or {},
        "sync_summary": (public_source_sync_plan or {}).get("summary") or {},
        "execution_items": execution_items,
    }
    run_manifest_path = run_dir / "public_source_sync_run_manifest.json"
    run_manifest_path.write_text(json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    for row in registry_rows:
        row["run_finished_at"] = run_finished_at
        row["run_manifest_path"] = str(run_manifest_path)
    _append_registry_rows(bundle_paths["sync_registry_path"], registry_rows)

    history = load_public_source_sync_history(
        output_dir=str(output_root),
        public_source_assessment=public_source_assessment,
        public_source_sync_plan=public_source_sync_plan,
    )
    benchmark_readiness = history.get("benchmark_readiness") or {}
    run_manifest["sync_history_summary"] = history.get("summary") or {}
    run_manifest["benchmark_readiness"] = benchmark_readiness
    run_manifest_path.write_text(json.dumps(run_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "summary": summary,
        "run_manifest_path": str(run_manifest_path),
        "sync_registry_path": str(bundle_paths["sync_registry_path"]),
        "bundle": bundle,
        "execution_items": execution_items,
        "sync_history": history,
        "benchmark_readiness": benchmark_readiness,
    }
