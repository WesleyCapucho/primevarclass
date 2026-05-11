from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OFFICIAL_ALPHAMISSENSE_HG38_URL = "https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: str | Path | None) -> dict:
    if not path:
        return {}
    resolved = Path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _read_table(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    resolved = Path(path)
    if not resolved.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(resolved, sep="\t" if resolved.suffix.lower() == ".tsv" else ",")
    except Exception:
        return pd.DataFrame()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    return default if math.isnan(numeric) else numeric


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _missing(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "None", "NA", "N/A"])


def _variant_parts(variant: Any, fallback_gene: Any = "") -> tuple[str, str]:
    text = str(variant or "").strip()
    if " " in text:
        gene, hgvs_p = text.split(" ", 1)
        return gene.strip() or str(fallback_gene or ""), hgvs_p.strip()
    return str(fallback_gene or "").strip(), text


def _normalise_variant_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    work = frame.copy()
    if "variant" in work.columns:
        parsed = work.apply(lambda row: _variant_parts(row.get("variant"), row.get("gene", "")), axis=1)
        work["gene"] = [item[0] for item in parsed]
        work["hgvs_p"] = [item[1] for item in parsed]
    else:
        work["gene"] = work.get("gene", "")
        work["hgvs_p"] = work.get("hgvs_p", "")
        work["variant"] = (
            work["gene"].astype(str).str.strip() + " " + work["hgvs_p"].astype(str).str.strip()
        ).str.strip()
    work["gene"] = work["gene"].astype(str).str.upper()
    work["hgvs_p"] = work["hgvs_p"].astype(str).str.strip()
    work["variant_key"] = work["gene"] + "|" + work["hgvs_p"]
    return work


def _parse_gnomad_variant_id(value: Any) -> dict[str, str]:
    text = str(value or "").strip()
    parts = text.split("-")
    if len(parts) < 4:
        return {"chromosome": "", "position_vcf": "", "reference_allele_vcf": "", "alternate_allele_vcf": ""}
    return {
        "chromosome": parts[0] if str(parts[0]).lower().startswith("chr") else f"chr{parts[0]}",
        "position_vcf": parts[1],
        "reference_allele_vcf": parts[2],
        "alternate_allele_vcf": parts[3],
    }


def _metadata_from_study(study_dir: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted((study_dir / "cohorts").glob("*_processed_dataset.csv")):
        frame = _read_table(path)
        if frame.empty or "variant" not in frame.columns:
            continue
        keep = [
            "variant",
            "gene",
            "hgvs_p",
            "variant_id",
            "meta_gnomad_variant_id",
            "meta_gnomad_reference_genome",
            "feature_gnomad_af",
            "feature_mave_score",
            "review_status",
            "source",
        ]
        available = [column for column in keep if column in frame.columns]
        rows.append(frame[available].copy())
    if not rows:
        return pd.DataFrame()
    combined = pd.concat(rows, ignore_index=True)
    combined = _normalise_variant_table(combined)
    combined["_has_coordinate"] = ~_missing(combined.get("meta_gnomad_variant_id", pd.Series("", index=combined.index)))
    combined = combined.sort_values(["variant_key", "_has_coordinate"], ascending=[True, False], kind="stable")
    return combined.drop_duplicates(subset=["variant_key"], keep="first").drop(columns=["_has_coordinate"], errors="ignore")


def _resolve_priority_queue(campaign_root: Path, priority_queue_path: str | None) -> Path:
    if priority_queue_path:
        return Path(priority_queue_path)
    readiness_manifest = _read_json(campaign_root / "competition_readiness" / "competition_readiness_manifest.json")
    manifest_path = readiness_manifest.get("priority_queue_path")
    if manifest_path:
        resolved = Path(manifest_path)
        if resolved.exists():
            return resolved
    return campaign_root / "competition_readiness" / "competition_priority_variant_queue.csv"


def _build_source_config(local_subset_path: Path, target_genes: list[str]) -> str:
    return "\n".join(
        [
            "[ingestion]",
            'deduplicate_on = ["gene", "hgvs_p"]',
            "prefer_annotation_values = true",
            "",
            "[[sources]]",
            'name = "alphamissense_priority_variant_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_display_path(local_subset_path)}"',
            'preset = "alphamissense_table"',
            'join_on = ["gene", "hgvs_p"]',
            f"gene_allowlist = {json.dumps(target_genes)}",
            'release_version = "AlphaMissense_v2023_hg38_priority_subset"',
            "",
        ]
    )


def _render_markdown_html(markdown: str, title: str) -> str:
    blocks: list[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("- "):
            blocks.append("<ul>" + "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines()) + "</ul>")
        else:
            blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;color:#132238;background:#f8fbff}"
        "h1{color:#102a43}h2{color:#2155d9}ul{background:#fff;border:1px solid #d9e2ec;border-radius:14px;padding:16px 24px}</style>"
        "</head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def build_alphamissense_priority_enrichment_package(
    campaign_root: str,
    output_dir: str | None = None,
    priority_queue_path: str | None = None,
    local_alphamissense_subset_path: str = "data/raw/alphamissense/target_gene_alphamissense.tsv",
    max_targets: int = 50,
) -> dict:
    campaign_path = Path(campaign_root).resolve()
    if not campaign_path.exists():
        raise FileNotFoundError(f"Campaign root not found: {campaign_path}")
    output_root = Path(output_dir).resolve() if output_dir else campaign_path / "alphamissense_priority_enrichment"
    output_root.mkdir(parents=True, exist_ok=True)

    priority_path = _resolve_priority_queue(campaign_path, priority_queue_path)
    priority = _normalise_variant_table(_read_table(priority_path)).head(max_targets)
    study_metadata = _metadata_from_study(campaign_path / "brca_real_quick")
    if not study_metadata.empty:
        priority = priority.merge(
            study_metadata.drop(columns=["gene", "hgvs_p", "variant"], errors="ignore"),
            on="variant_key",
            how="left",
            suffixes=("", "_study"),
        )
    if "meta_gnomad_variant_id" not in priority.columns:
        priority["meta_gnomad_variant_id"] = ""
    if "variant_id" not in priority.columns:
        priority["variant_id"] = ""
    parsed_coordinates = priority["meta_gnomad_variant_id"].map(_parse_gnomad_variant_id).apply(pd.Series)
    target_table = pd.concat([priority.reset_index(drop=True), parsed_coordinates.reset_index(drop=True)], axis=1)
    target_table.insert(0, "target_rank", range(1, len(target_table) + 1))
    target_table["meta_genome_build"] = target_table.get("meta_gnomad_reference_genome", "GRCh38").replace("", "GRCh38")
    target_table["coordinate_ready"] = ~_missing(target_table["chromosome"]) & ~_missing(target_table["position_vcf"])

    protein_columns = [
        "target_rank",
        "gene",
        "hgvs_p",
        "variant",
        "variant_key",
        "competition_priority_score",
        "label",
        "cohort",
        "calibration_effect",
        "evidence_gap",
        "recommended_next_action",
    ]
    coordinate_columns = [
        "target_rank",
        "gene",
        "hgvs_p",
        "variant",
        "variant_id",
        "chromosome",
        "position_vcf",
        "reference_allele_vcf",
        "alternate_allele_vcf",
        "meta_genome_build",
        "meta_gnomad_variant_id",
        "competition_priority_score",
        "label",
        "cohort",
    ]
    protein_targets = target_table[[column for column in protein_columns if column in target_table.columns]].copy()
    coordinate_targets = target_table[target_table["coordinate_ready"]][
        [column for column in coordinate_columns if column in target_table.columns]
    ].copy()

    local_subset_path = Path(local_alphamissense_subset_path)
    local_subset = _normalise_variant_table(_read_table(local_subset_path))
    matched = pd.DataFrame()
    if not local_subset.empty and "variant_key" in local_subset.columns:
        selected_alpha_columns = [
            "variant_key",
            "feature_alphamissense_pathogenicity",
            "feature_alphamissense_class",
            "meta_alphamissense_transcript_id",
            "meta_genome_build",
            "meta_uniprot_accession",
        ]
        matched = target_table.merge(
            local_subset[[column for column in selected_alpha_columns if column in local_subset.columns]].drop_duplicates(
                subset=["variant_key"]
            ),
            on="variant_key",
            how="left",
        )
    else:
        matched = target_table.copy()
        matched["feature_alphamissense_pathogenicity"] = ""
        matched["feature_alphamissense_class"] = ""

    alpha_covered = (
        ~_missing(matched.get("feature_alphamissense_pathogenicity", pd.Series("", index=matched.index)))
        if not matched.empty
        else pd.Series(dtype=bool)
    )
    coordinate_ready_percent = round(float(target_table["coordinate_ready"].mean() * 100), 2) if len(target_table) else 0.0
    local_subset_coverage_percent = round(float(alpha_covered.mean() * 100), 2) if len(matched) else 0.0
    target_genes = sorted(set(protein_targets.get("gene", pd.Series(dtype=str)).astype(str).str.upper()) - {""})
    status = (
        "ready_to_benchmark"
        if local_subset_coverage_percent >= 80
        else "ready_to_extract"
        if len(coordinate_targets) > 0
        else "needs_coordinate_resolution"
    )

    protein_targets_path = output_root / "alphamissense_priority_protein_targets.tsv"
    coordinate_targets_path = output_root / "alphamissense_priority_coordinate_targets.csv"
    matched_path = output_root / "alphamissense_priority_matched_coverage.csv"
    missing_path = output_root / "alphamissense_priority_missing_targets.csv"
    source_config_path = output_root / "alphamissense_priority_source_config.toml"
    extractor_script_path = output_root / "extract_priority_alphamissense.ps1"
    report_path = output_root / "alphamissense_priority_enrichment_report.md"
    html_path = output_root / "alphamissense_priority_enrichment_report.html"
    manifest_path = output_root / "alphamissense_priority_enrichment_manifest.json"

    protein_targets.to_csv(protein_targets_path, sep="\t", index=False)
    coordinate_targets.to_csv(coordinate_targets_path, index=False)
    matched.to_csv(matched_path, index=False)
    matched[~alpha_covered].to_csv(missing_path, index=False)
    source_config_path.write_text(_build_source_config(local_subset_path, target_genes), encoding="utf-8")
    extractor_script_path.write_text(
        "\n".join(
            [
                "# Generated by PrimeVarClass. Run only when you want to stream the official AlphaMissense table.",
                "$ErrorActionPreference = 'Stop'",
                "py -3.14 scripts\\extract_alphamissense_subset.py `",
                f"  --alphamissense-input \"{OFFICIAL_ALPHAMISSENSE_HG38_URL}\" `",
                f"  --targets \"{_display_path(coordinate_targets_path)}\" `",
                f"  --output \"{_display_path(local_subset_path)}\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "generated_at": _now_utc(),
        "campaign_root": _display_path(campaign_path),
        "priority_queue_path": _display_path(priority_path),
        "target_count": int(len(target_table)),
        "coordinate_ready_count": int(len(coordinate_targets)),
        "coordinate_ready_percent": coordinate_ready_percent,
        "local_alphamissense_subset_path": _display_path(local_subset_path),
        "local_subset_exists": local_subset_path.exists(),
        "local_subset_coverage_percent": local_subset_coverage_percent,
        "matched_alphamissense_count": int(alpha_covered.sum()) if len(alpha_covered) else 0,
        "missing_alphamissense_count": int((~alpha_covered).sum()) if len(alpha_covered) else int(len(target_table)),
        "target_genes": target_genes,
        "official_alphamissense_hg38_url": OFFICIAL_ALPHAMISSENSE_HG38_URL,
        "status": status,
        "next_action": (
            "Run the generated PowerShell extractor or provide a local AlphaMissense subset, then rerun this package."
            if status != "ready_to_benchmark"
            else "Rerun the BRCA benchmark with the generated AlphaMissense source config."
        ),
    }
    lines = [
        "# AlphaMissense priority enrichment package",
        "",
        f"- Generated at: `{manifest['generated_at']}`",
        f"- Priority targets: `{manifest['target_count']}`",
        f"- Coordinate-ready targets: `{manifest['coordinate_ready_count']}` (`{coordinate_ready_percent}%`)",
        f"- Local AlphaMissense subset exists: `{manifest['local_subset_exists']}`",
        f"- Local subset coverage: `{local_subset_coverage_percent}%`",
        f"- Status: `{status}`",
        "",
        "## Why this matters",
        "",
        "- AlphaMissense is an independent functional predictor and is especially valuable for persistent BRCA1/LOVD errors with missing MAVE evidence.",
        "- This package avoids downloading large files automatically; it creates exact target lists and a streaming extraction command.",
        "- Coordinate-ready targets can be extracted directly from the official hg38 table. Protein-only targets remain useful for manual curation or coordinate resolution.",
        "",
        "## Next action",
        "",
        f"- {manifest['next_action']}",
        "",
        "## Output files",
        "",
        f"- Protein targets: `{_display_path(protein_targets_path)}`",
        f"- Coordinate targets: `{_display_path(coordinate_targets_path)}`",
        f"- Matched coverage: `{_display_path(matched_path)}`",
        f"- Missing targets: `{_display_path(missing_path)}`",
        f"- Source config: `{_display_path(source_config_path)}`",
        f"- Extractor script: `{_display_path(extractor_script_path)}`",
    ]
    report = "\n".join(lines).strip() + "\n"
    report_path.write_text(report, encoding="utf-8")
    html_path.write_text(_render_markdown_html(report, "AlphaMissense Priority Enrichment"), encoding="utf-8")
    manifest.update(
        {
            "protein_targets_path": _display_path(protein_targets_path),
            "coordinate_targets_path": _display_path(coordinate_targets_path),
            "matched_coverage_path": _display_path(matched_path),
            "missing_targets_path": _display_path(missing_path),
            "source_config_path": _display_path(source_config_path),
            "extractor_script_path": _display_path(extractor_script_path),
            "markdown_path": _display_path(report_path),
            "html_path": _display_path(html_path),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "alphamissense_priority_enrichment": manifest,
        "alphamissense_priority_enrichment_manifest_path": str(manifest_path),
        "alphamissense_priority_enrichment_report_markdown_path": str(report_path),
        "alphamissense_priority_enrichment_report_html_path": str(html_path),
        "alphamissense_priority_protein_targets_path": str(protein_targets_path),
        "alphamissense_priority_coordinate_targets_path": str(coordinate_targets_path),
        "alphamissense_priority_matched_coverage_path": str(matched_path),
        "alphamissense_priority_missing_targets_path": str(missing_path),
        "alphamissense_priority_source_config_path": str(source_config_path),
        "alphamissense_priority_extractor_script_path": str(extractor_script_path),
    }


def export_alphamissense_priority_enrichment_package(
    campaign_root: str,
    output_dir: str | None = None,
    priority_queue_path: str | None = None,
    local_alphamissense_subset_path: str = "data/raw/alphamissense/target_gene_alphamissense.tsv",
    max_targets: int = 50,
) -> dict:
    return build_alphamissense_priority_enrichment_package(
        campaign_root=campaign_root,
        output_dir=output_dir,
        priority_queue_path=priority_queue_path,
        local_alphamissense_subset_path=local_alphamissense_subset_path,
        max_targets=max_targets,
    )
