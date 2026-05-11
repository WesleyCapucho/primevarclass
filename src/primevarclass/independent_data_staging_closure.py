from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .independent_data_expansion import (
    DEFAULT_EXPANSION_GENES,
    build_independent_data_expansion_package,
)


SIGNIFICANT_FILE_BYTES = 512

SOURCE_FALLBACK_PATTERNS: dict[str, tuple[str, ...]] = {
    "clinvar": (
        "data/raw/clinvar/variant_summary.txt",
        "data/raw/clinvar/variant_summary.txt.gz",
        "data/raw/clinvar/*variant_summary*.tsv",
        "data/raw/multigene/*/*clinvar_training.tsv",
    ),
    "clingen_erepo": ("data/raw/clingen_erepo/**/*",),
    "brca_exchange_enigma": ("data/raw/brca_exchange/*.tsv",),
    "gnomad": ("data/raw/gnomad/*_missense_annotations.tsv", "data/raw/gnomad/*gene_subset*.tsv", "external_data/gnomad/**/*"),
    "mavedb": ("data/raw/mavedb/*_function_scores.csv", "external_data/mavedb/**/*"),
    "alphamissense": ("data/raw/alphamissense/**/*", "external_data/alphamissense/**/*"),
    "uniprot": ("data/raw/uniprot/**/*", "external_data/uniprot/**/*"),
    "alphafold_db": ("data/raw/alphafold/**/*", "external_data/alphafold/**/*"),
    "pdb": ("data/raw/pdb/**/*", "external_data/pdb/**/*"),
    "civic": ("data/raw/civic/**/*", "external_data/civic/**/*"),
    "cbioportal": ("data/raw/cbioportal/**/*", "external_data/cbioportal/**/*"),
    "gdc": ("data/raw/gdc/**/*", "external_data/gdc/**/*"),
    "gwas_catalog": ("data/raw/gwas_catalog/**/*", "external_data/gwas_catalog/**/*"),
    "opentargets": ("data/raw/opentargets/**/*", "external_data/opentargets/**/*"),
    "pharmgkb": ("data/raw/pharmgkb/**/*", "external_data/pharmgkb/**/*"),
    "lovd": ("data/raw/lovd/**/*", "data/raw/brca_exchange/*lovd*.tsv", "external_data/lovd/**/*"),
}

SOURCE_TARGET_SCOPE: dict[str, tuple[str, ...] | None] = {
    "brca_exchange_enigma": ("BRCA1", "BRCA2"),
    "lovd": ("BRCA1", "BRCA2"),
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonify(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonify(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _safe_int(value: Any) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return 0


def _normalize_genes(target_genes: Iterable[str] | None) -> list[str]:
    genes: list[str] = []
    seen: set[str] = set()
    for value in target_genes or DEFAULT_EXPANSION_GENES:
        gene = str(value or "").strip().upper()
        if gene and gene not in seen:
            seen.add(gene)
            genes.append(gene)
    return genes or list(DEFAULT_EXPANSION_GENES)


def _file_fingerprint(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size_bytes": int(stat.st_size),
        "sha256": digest.hexdigest(),
        "modified_at_epoch": float(stat.st_mtime),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _render_markdown_html(markdown_text: str, *, title: str) -> str:
    blocks: list[str] = []
    for chunk in str(markdown_text or "").split("\n\n"):
        stripped = chunk.strip()
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
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f7f2e8;color:#17242f;max-width:1080px;margin:0 auto;padding:32px;line-height:1.65;}"
        "h1{font-size:2.2rem;}h2{margin-top:2rem;color:#2d6f73;}ul{background:#fff;border:1px solid #e6ddcf;border-radius:16px;padding:18px 24px;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def _load_expansion_manifest(path: str | Path | None, target_genes: Iterable[str] | None) -> dict:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    package = build_independent_data_expansion_package(target_genes=target_genes)
    return {
        "generated_at": package["generated_at"],
        "summary": package["summary"],
        "registry": package["registry"],
        "training_validation_plan": package["training_validation_plan"],
    }


def _iter_pattern_matches(root: Path, pattern: str) -> list[Path]:
    candidates = [root / pattern]
    matches: list[Path] = []
    for candidate in candidates:
        if any(char in pattern for char in "*?[]"):
            matches.extend([path for path in root.glob(pattern) if path.is_file()])
        elif candidate.exists() and candidate.is_file():
            matches.append(candidate)
    return matches


def _collect_source_files(root: Path, source: dict) -> list[Path]:
    source_id = str(source.get("source_id") or "")
    paths: list[Path] = []
    configured = str(source.get("local_stage_path") or "").strip()
    if configured:
        configured_path = root / configured
        if configured_path.exists() and configured_path.is_file():
            paths.append(configured_path)
    for pattern in SOURCE_FALLBACK_PATTERNS.get(source_id, (f"data/raw/{source_id}/**/*",)):
        paths.extend(_iter_pattern_matches(root, pattern))
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return sorted(unique, key=lambda item: item.stat().st_size if item.exists() else 0, reverse=True)


def _target_scope(source: dict, target_genes: list[str]) -> list[str]:
    source_id = str(source.get("source_id") or "")
    scoped = SOURCE_TARGET_SCOPE.get(source_id)
    if scoped is None:
        return list(target_genes)
    return [gene for gene in target_genes if gene in set(scoped)] or list(scoped)


def _scan_gene_column(path: Path, scope: list[str], *, max_lines: int = 50000) -> set[str]:
    if path.suffix.lower() == ".gz" or path.stat().st_size > 50 * 1024 * 1024:
        return set()
    scope_set = set(scope)
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            sample = handle.readline()
            if not sample:
                return set()
            delimiter = "\t" if sample.count("\t") >= sample.count(",") else ","
            header = [item.strip() for item in sample.rstrip("\n\r").split(delimiter)]
            gene_index = None
            for candidate in ("gene", "Gene", "GeneSymbol", "gene_symbol", "symbol", "Hugo_Symbol"):
                if candidate in header:
                    gene_index = header.index(candidate)
                    break
            if gene_index is None:
                return set()
            covered: set[str] = set()
            for line_number, line in enumerate(handle, start=1):
                if line_number > max_lines:
                    break
                parts = line.rstrip("\n\r").split(delimiter)
                if gene_index >= len(parts):
                    continue
                gene = parts[gene_index].strip().upper()
                if gene in scope_set:
                    covered.add(gene)
                if len(covered) == len(scope_set):
                    break
            return covered
    except Exception:
        return set()


def _gene_coverage_from_files(source_id: str, files: list[Path], target_genes: list[str]) -> dict:
    scope = _target_scope({"source_id": source_id}, target_genes)
    if not scope:
        return {"covered_genes": [], "target_gene_count": 0, "gene_coverage_percent": 100}

    covered: set[str] = set()
    for file_path in files:
        name = file_path.name.lower()
        if file_path.stat().st_size < SIGNIFICANT_FILE_BYTES:
            continue
        if "brca" in name:
            covered.update(gene for gene in scope if gene in {"BRCA1", "BRCA2"})
        for gene in scope:
            if gene.lower() in name:
                covered.add(gene)
        if source_id == "clinvar" and ("variant_summary" in name or "clinvar" in name):
            covered.update(scope)
        covered.update(_scan_gene_column(file_path, scope))
    percent = int(round((len(covered) / max(len(scope), 1)) * 100))
    return {
        "covered_genes": sorted(covered),
        "target_gene_count": int(len(scope)),
        "gene_coverage_percent": percent,
    }


def _source_score(source: dict, files: list[Path], target_genes: list[str]) -> dict:
    source_id = str(source.get("source_id") or "")
    significant_files = [path for path in files if path.stat().st_size >= SIGNIFICANT_FILE_BYTES]
    total_bytes = sum(path.stat().st_size for path in files)
    significant_bytes = sum(path.stat().st_size for path in significant_files)
    coverage = _gene_coverage_from_files(source_id, files, target_genes)

    if significant_files:
        raw_score = 100
        state = "ready"
    elif files:
        raw_score = 45
        state = "partial"
    else:
        raw_score = 0
        state = "missing"

    gene_coverage_percent = int(coverage["gene_coverage_percent"])
    if source_id in {"gnomad", "mavedb", "brca_exchange_enigma", "lovd", "clinvar"}:
        score = int(round(raw_score * (0.45 + 0.55 * (gene_coverage_percent / 100))))
    else:
        score = raw_score

    status = "ready" if score >= 85 else "partial" if score >= 40 else "missing"
    if state == "ready" and status == "partial":
        state = "partial"

    best_file = significant_files[0] if significant_files else files[0] if files else None
    return {
        "source_id": source_id,
        "display_name": source.get("display_name"),
        "priority": source.get("priority"),
        "evidence_lane": source.get("evidence_lane"),
        "recommended_use": source.get("recommended_use"),
        "source_kind": source.get("source_kind"),
        "preset": source.get("preset"),
        "format": source.get("format"),
        "join_on": source.get("join_on"),
        "automation_level": source.get("automation_level"),
        "official_url": source.get("official_url"),
        "download_url_hint": source.get("download_url_hint"),
        "local_stage_path": source.get("local_stage_path"),
        "staging_state": state,
        "staging_status": status,
        "staging_score_percent": int(score),
        "file_count": int(len(files)),
        "significant_file_count": int(len(significant_files)),
        "total_size_bytes": int(total_bytes),
        "significant_size_bytes": int(significant_bytes),
        "best_local_path": str(best_file.resolve()) if best_file else "",
        "target_gene_count": coverage["target_gene_count"],
        "covered_genes": ";".join(coverage["covered_genes"]),
        "gene_coverage_percent": gene_coverage_percent,
        "next_action": _next_action(source, state=state, gene_coverage_percent=gene_coverage_percent),
    }


def _next_action(source: dict, *, state: str, gene_coverage_percent: int) -> str:
    source_id = str(source.get("source_id") or "")
    if state == "ready" and gene_coverage_percent >= 85:
        return "Freeze file hash, row count, schema, and release before benchmark use."
    if source_id == "clinvar":
        return "Refresh or reuse local variant_summary, then freeze train/expert/prospective splits."
    if source_id == "gnomad":
        return "Stage gene-filtered gnomAD tables for all target genes or use the existing resumable gnomAD sync runner."
    if source_id == "mavedb":
        return "Stage score sets for all target genes with MaveDB URNs, assay metadata, and mapped variant tables."
    if source_id == "clingen_erepo":
        return "Export gene-filtered ClinGen ERepo classifications and keep them as an independent expert holdout."
    if source_id == "brca_exchange_enigma":
        return "Keep BRCA Exchange/ENIGMA as BRCA-specific expert validation and document redistribution terms."
    return f"Stage this source from {source.get('official_url') or source.get('download_url_hint')} and lock provenance."


def _build_ready_source_config(inventory_rows: list[dict[str, Any]], target_genes: list[str]) -> str:
    ready_rows = [row for row in inventory_rows if row.get("best_local_path") and row.get("staging_score_percent", 0) >= 40]
    lines = [
        "# PrimeVarClass staged independent source config",
        "# Generated from local inventory. Review every source before publication-grade training.",
        "",
        "[ingestion]",
        'deduplicate_on = ["gene", "hgvs_p", "label"]',
        "prefer_annotation_values = true",
        "",
    ]
    for row in ready_rows:
        join_on = [item.strip() for item in str(row.get("join_on") or "gene,hgvs_p").split(",") if item.strip()]
        local_path = str(row["best_local_path"]).replace("\\", "/")
        lines.extend(
            [
                "[[sources]]",
                f'name = "{row["source_id"]}_local_staged"',
                f'kind = "{row["source_kind"]}"',
                'type = "file"',
                f'format = "{row["format"]}"',
                f'path = "{local_path}"',
                f'preset = "{row["preset"]}"',
                "gene_allowlist = [" + ", ".join(json.dumps(gene) for gene in target_genes) + "]",
                "join_on = [" + ", ".join(json.dumps(key) for key in join_on) + "]",
                f'# staging_score_percent = {row["staging_score_percent"]}',
                f'# evidence_lane = "{row["evidence_lane"]}"',
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_stage_runner(inventory_rows: list[dict[str, Any]]) -> str:
    missing_rows = [row for row in inventory_rows if row.get("staging_status") != "ready"]
    lines = [
        "# PrimeVarClass independent data staging handoff",
        "# Review source licenses/terms before running any download command.",
        "$ErrorActionPreference = \"Stop\"",
        "",
        "New-Item -ItemType Directory -Force -Path \"data/raw\" | Out-Null",
        "",
    ]
    for row in missing_rows:
        source_id = str(row.get("source_id") or "")
        local_stage = str(row.get("local_stage_path") or f"data/raw/{source_id}/staged_source.tsv")
        directory = str(Path(local_stage).parent).replace("/", "\\")
        lines.extend(
            [
                f"# {row.get('display_name')} ({source_id})",
                f"New-Item -ItemType Directory -Force -Path \"{directory}\" | Out-Null",
                f"# Official: {row.get('official_url') or ''}",
                f"# Hint: {row.get('download_url_hint') or ''}",
            ]
        )
        if source_id == "clinvar":
            lines.append('Invoke-WebRequest -Uri "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz" -OutFile "data/raw/clinvar/variant_summary.txt.gz"')
        else:
            lines.append(f"# TODO: stage file at {local_stage}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_markdown_report(summary: dict, inventory_rows: list[dict[str, Any]]) -> str:
    ready = [row for row in inventory_rows if row.get("staging_status") == "ready"]
    missing = [row for row in inventory_rows if row.get("staging_status") == "missing"]
    partial = [row for row in inventory_rows if row.get("staging_status") == "partial"]
    lines = [
        "# Independent Data Staging Closure",
        "",
        f"- Staging closure: {summary['independent_data_staging_closure_percent']}%",
        f"- Line-level execution: {summary['line_level_real_data_execution_percent']}%",
        f"- Ready sources: {summary['ready_source_count']}/{summary['database_count']}",
        f"- Partial sources: {summary['partial_source_count']}",
        f"- Missing sources: {summary['missing_source_count']}",
        f"- Ready for next training round: {summary['ready_for_next_training_round']}",
        f"- Ready for full independent retraining: {summary['ready_for_full_independent_retraining']}",
        "",
        "## Ready now",
        "",
    ]
    lines.append("- " + ("; ".join(str(row.get("display_name")) for row in ready) if ready else "None"))
    lines.extend(["", "## Partial", ""])
    lines.append("- " + ("; ".join(str(row.get("display_name")) for row in partial) if partial else "None"))
    lines.extend(["", "## Missing", ""])
    lines.append("- " + ("; ".join(str(row.get("display_name")) for row in missing) if missing else "None"))
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This closure package identifies which independent data sources are locally staged and which still require download, curation, or licensing review. It strengthens operational credibility, but strong scientific claims still require frozen independent benchmarks and functional or structural confirmation.",
        ]
    )
    return "\n".join(lines)


def build_independent_data_staging_closure_package(
    *,
    independent_data_expansion_manifest_path: str | None = None,
    workspace_root: str | Path | None = None,
    target_genes: Iterable[str] | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(workspace_root or Path.cwd()).resolve()
    expansion_manifest = _load_expansion_manifest(independent_data_expansion_manifest_path, target_genes)
    genes = _normalize_genes(target_genes or (expansion_manifest.get("summary") or {}).get("target_genes"))
    registry = [dict(item) for item in expansion_manifest.get("registry") or []]

    inventory_rows: list[dict[str, Any]] = []
    fingerprints: dict[str, list[dict]] = {}
    for source in registry:
        files = _collect_source_files(root, source)
        row = _source_score(source, files, genes)
        inventory_rows.append(row)
        fingerprints[row["source_id"]] = [_file_fingerprint(path) for path in files[:5] if path.exists()]

    ready_count = sum(1 for row in inventory_rows if row.get("staging_status") == "ready")
    partial_count = sum(1 for row in inventory_rows if row.get("staging_status") == "partial")
    missing_count = sum(1 for row in inventory_rows if row.get("staging_status") == "missing")
    critical_rows = [row for row in inventory_rows if row.get("priority") == "critical"]
    critical_ready = sum(1 for row in critical_rows if row.get("staging_status") == "ready")
    score_sum = sum(_safe_int(row.get("staging_score_percent")) for row in inventory_rows)
    line_level_percent = int(round(score_sum / max(len(inventory_rows), 1)))
    closure_percent = int(round((line_level_percent * 0.7) + 30))
    core_ready_ids = {row["source_id"] for row in inventory_rows if row.get("staging_status") in {"ready", "partial"}}
    ready_for_next_training_round = {"clinvar", "gnomad", "mavedb", "brca_exchange_enigma"}.issubset(core_ready_ids)
    ready_for_full_independent_retraining = ready_count >= max(12, int(round(len(inventory_rows) * 0.75))) and critical_ready == len(critical_rows)

    summary = {
        "workspace_root": str(root),
        "target_genes": genes,
        "database_count": int(len(inventory_rows)),
        "ready_source_count": int(ready_count),
        "partial_source_count": int(partial_count),
        "missing_source_count": int(missing_count),
        "critical_source_count": int(len(critical_rows)),
        "critical_ready_source_count": int(critical_ready),
        "significant_file_count": int(sum(_safe_int(row.get("significant_file_count")) for row in inventory_rows)),
        "total_size_bytes": int(sum(_safe_int(row.get("total_size_bytes")) for row in inventory_rows)),
        "line_level_real_data_execution_percent": int(line_level_percent),
        "independent_data_staging_closure_percent": max(0, min(100, closure_percent)),
        "ready_for_next_training_round": bool(ready_for_next_training_round),
        "ready_for_full_independent_retraining": bool(ready_for_full_independent_retraining),
    }
    return {
        "generated_at": _now_utc(),
        "summary": summary,
        "inventory": inventory_rows,
        "source_fingerprints": fingerprints,
        "ready_source_config_toml": _build_ready_source_config(inventory_rows, genes),
        "stage_runner_powershell": _build_stage_runner(inventory_rows),
        "report_context": dict(report_context or {}),
    }


def export_independent_data_staging_closure_package(
    *,
    output_dir: str,
    independent_data_expansion_manifest_path: str | None = None,
    workspace_root: str | Path | None = None,
    target_genes: Iterable[str] | None = None,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    package = build_independent_data_staging_closure_package(
        independent_data_expansion_manifest_path=independent_data_expansion_manifest_path,
        workspace_root=workspace_root,
        target_genes=target_genes,
        report_context=report_context,
    )

    manifest_path = output_root / "independent_data_staging_closure_manifest.json"
    inventory_path = output_root / "independent_data_staging_inventory.csv"
    gap_plan_path = output_root / "independent_data_staging_gap_plan.csv"
    ready_config_path = output_root / "independent_ready_source_config.toml"
    runner_path = output_root / "independent_data_stage_runner.ps1"
    markdown_path = output_root / "independent_data_staging_closure_report.md"
    html_path = output_root / "independent_data_staging_closure_report.html"

    inventory_rows = list(package["inventory"])
    gap_rows = [row for row in inventory_rows if row.get("staging_status") != "ready"]
    _write_csv(inventory_path, inventory_rows)
    _write_csv(gap_plan_path, gap_rows)
    ready_config_path.write_text(str(package["ready_source_config_toml"]), encoding="utf-8")
    runner_path.write_text(str(package["stage_runner_powershell"]), encoding="utf-8")
    markdown = _build_markdown_report(dict(package["summary"]), inventory_rows)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, title="Independent Data Staging Closure"), encoding="utf-8")

    manifest = {
        "generated_at": package["generated_at"],
        "summary": package["summary"],
        "artifact_paths": {
            "inventory_csv": str(inventory_path),
            "gap_plan_csv": str(gap_plan_path),
            "ready_source_config_toml": str(ready_config_path),
            "stage_runner_powershell": str(runner_path),
            "markdown_report": str(markdown_path),
            "html_report": str(html_path),
        },
        "inventory": inventory_rows,
        "source_fingerprints": package["source_fingerprints"],
        "report_context": package["report_context"],
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "independent_data_staging_closure_manifest_path": str(manifest_path),
        "independent_data_staging_inventory_path": str(inventory_path),
        "independent_data_staging_gap_plan_path": str(gap_plan_path),
        "independent_ready_source_config_path": str(ready_config_path),
        "independent_data_stage_runner_path": str(runner_path),
        "independent_data_staging_closure_report_markdown_path": str(markdown_path),
        "independent_data_staging_closure_report_html_path": str(html_path),
        "summary": package["summary"],
    }
