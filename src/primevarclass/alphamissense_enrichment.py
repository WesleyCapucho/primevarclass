from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    roc_auc_score,
)


OFFICIAL_ALPHAMISSENSE_HG38_URL = "https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz"
OFFICIAL_ALPHAMISSENSE_AA_URL = "https://storage.googleapis.com/dm_alphamissense/AlphaMissense_aa_substitutions.tsv.gz"


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


def _json_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except Exception:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, 6)


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


def _label_int(value: Any) -> int | None:
    text = "" if value is None else str(value).strip().lower()
    try:
        numeric = float(text)
        if numeric == 1.0:
            return 1
        if numeric == 0.0:
            return 0
    except Exception:
        pass
    if text in {"1", "pathogenic", "likely pathogenic"}:
        return 1
    if text in {"0", "benign", "likely benign"}:
        return 0
    return None


def _functional_alignment(row: pd.Series) -> str:
    label = _label_int(row.get("label"))
    am_class = str(row.get("feature_alphamissense_class") or "").strip().lower()
    if not am_class:
        return "missing_alphamissense"
    if "ambiguous" in am_class:
        return "ambiguous_functional_signal"
    if label == 1 and "pathogenic" in am_class:
        return "supports_external_label"
    if label == 0 and "benign" in am_class:
        return "supports_external_label"
    if label == 0 and "pathogenic" in am_class:
        return "discordant_am_pathogenic_for_benign_label"
    if label == 1 and "benign" in am_class:
        return "discordant_am_benign_for_pathogenic_label"
    return "unresolved_alignment"


def _functional_interpretation(row: pd.Series) -> str:
    alignment = str(row.get("alphamissense_label_alignment") or "")
    label = _label_int(row.get("label"))
    model_score = _safe_float(row.get("locked_calibrated_score", row.get("raw_score", 0.0)))
    if alignment == "supports_external_label" and label == 0 and model_score >= 0.5:
        return "AlphaMissense supports benign external label; prioritize as model false-positive mechanism."
    if alignment == "supports_external_label" and label == 1 and model_score < 0.5:
        return "AlphaMissense supports pathogenic external label; prioritize as model false-negative mechanism."
    if alignment.startswith("discordant_am_pathogenic"):
        return "AlphaMissense is pathogenic despite benign external label; review curation, isoform and functional assay context."
    if alignment.startswith("discordant_am_benign"):
        return "AlphaMissense is benign despite pathogenic external label; review clinical evidence and mechanism."
    if alignment == "ambiguous_functional_signal":
        return "AlphaMissense is ambiguous; combine with MAVE, gnomAD and structural review."
    return "Use as supporting functional annotation in the next benchmark rerun."


def _binary_score_metrics(
    predictions: pd.DataFrame,
    score_column: str,
    model_name: str,
    threshold: float = 0.5,
) -> dict[str, Any]:
    if predictions.empty or score_column not in predictions.columns:
        return {
            "model": model_name,
            "score_column": score_column,
            "n_evaluated": 0,
            "n_positive": 0,
            "n_negative": 0,
            "auc_roc": None,
            "auc_pr": None,
            "accuracy": None,
            "balanced_accuracy": None,
            "mcc": None,
            "threshold": threshold,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
            "status": "missing_score",
        }

    work = predictions[["label", score_column]].copy()
    work["label"] = work["label"].map(_label_int)
    work[score_column] = pd.to_numeric(work[score_column], errors="coerce")
    work = work.dropna(subset=["label", score_column]).copy()
    if work.empty:
        return {
            "model": model_name,
            "score_column": score_column,
            "n_evaluated": 0,
            "n_positive": 0,
            "n_negative": 0,
            "auc_roc": None,
            "auc_pr": None,
            "accuracy": None,
            "balanced_accuracy": None,
            "mcc": None,
            "threshold": threshold,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
            "status": "no_complete_rows",
        }

    y_true = work["label"].astype(int)
    y_score = work[score_column].astype(float)
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    has_two_classes = int(y_true.nunique()) == 2
    return {
        "model": model_name,
        "score_column": score_column,
        "n_evaluated": int(len(work)),
        "n_positive": int(y_true.sum()),
        "n_negative": int(len(work) - y_true.sum()),
        "auc_roc": _json_float(roc_auc_score(y_true, y_score)) if has_two_classes else None,
        "auc_pr": _json_float(average_precision_score(y_true, y_score)) if has_two_classes else None,
        "accuracy": _json_float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": _json_float(balanced_accuracy_score(y_true, y_pred)) if has_two_classes else None,
        "mcc": _json_float(matthews_corrcoef(y_true, y_pred)) if has_two_classes else None,
        "threshold": threshold,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "status": "evaluated" if has_two_classes else "single_class_only",
    }


def _build_priority_benchmark(functional_overlay: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if functional_overlay.empty:
        metrics = pd.DataFrame(
            [
                _binary_score_metrics(pd.DataFrame(), "feature_alphamissense_pathogenicity", "AlphaMissense priority overlay"),
            ]
        )
        return pd.DataFrame(), metrics, pd.DataFrame(), {
            "status": "missing_overlay",
            "n_variants": 0,
            "n_complete_alphamissense_rows": 0,
            "best_model_by_auc_roc": None,
            "best_auc_roc": None,
            "functional_support_rate_percent": 0.0,
        }

    predictions = functional_overlay.copy()
    predictions["label_int"] = predictions.get("label", pd.Series(index=predictions.index)).map(_label_int)
    predictions["feature_alphamissense_pathogenicity"] = pd.to_numeric(
        predictions.get("feature_alphamissense_pathogenicity"),
        errors="coerce",
    )
    for column in ["locked_calibrated_score", "raw_score", "baseline_score"]:
        if column in predictions.columns:
            predictions[column] = pd.to_numeric(predictions[column], errors="coerce")
    if "locked_calibrated_score" in predictions.columns:
        predictions["simple_mean_locked_alpha"] = predictions[
            ["locked_calibrated_score", "feature_alphamissense_pathogenicity"]
        ].mean(axis=1, skipna=False)
    if "raw_score" in predictions.columns:
        predictions["simple_mean_raw_alpha"] = predictions[
            ["raw_score", "feature_alphamissense_pathogenicity"]
        ].mean(axis=1, skipna=False)

    metric_specs = [
        ("feature_alphamissense_pathogenicity", "AlphaMissense priority overlay"),
        ("locked_calibrated_score", "PrimeVarClass locked calibrated"),
        ("raw_score", "PrimeVarClass raw score"),
        ("baseline_score", "External baseline score"),
        ("simple_mean_locked_alpha", "Simple mean: locked PrimeVarClass + AlphaMissense"),
        ("simple_mean_raw_alpha", "Simple mean: raw PrimeVarClass + AlphaMissense"),
    ]
    metrics = pd.DataFrame(
        [
            _binary_score_metrics(predictions, score_column, model_name)
            for score_column, model_name in metric_specs
            if score_column in predictions.columns
        ]
    )
    discordance = predictions[
        predictions.get("alphamissense_label_alignment", pd.Series("", index=predictions.index))
        .astype(str)
        .ne("supports_external_label")
    ].copy()
    if not discordance.empty:
        discordance["hypothesis_priority"] = discordance.apply(
            lambda row: (
                "highest"
                if str(row.get("alphamissense_label_alignment", "")).startswith("discordant")
                else "high"
                if str(row.get("alphamissense_label_alignment", "")) == "ambiguous_functional_signal"
                else "medium"
            ),
            axis=1,
        )
        priority_order = {"highest": 0, "high": 1, "medium": 2}
        discordance["_hypothesis_priority_rank"] = discordance["hypothesis_priority"].map(priority_order).fillna(9)
        discordance = discordance.sort_values(
            ["_hypothesis_priority_rank", "competition_priority_score", "feature_alphamissense_pathogenicity"],
            ascending=[True, False, False],
            kind="stable",
        ).drop(columns=["_hypothesis_priority_rank"], errors="ignore")

    valid_metric_rows = metrics[metrics["auc_roc"].notna()].copy() if not metrics.empty else pd.DataFrame()
    best_model = None
    best_auc = None
    if not valid_metric_rows.empty:
        best_row = valid_metric_rows.sort_values(["auc_roc", "auc_pr"], ascending=[False, False]).iloc[0]
        best_model = str(best_row["model"])
        best_auc = _json_float(best_row["auc_roc"])
    support_counts = predictions.get("alphamissense_label_alignment", pd.Series(dtype=str)).value_counts().to_dict()
    support_rate = (
        100.0 * float(support_counts.get("supports_external_label", 0)) / max(len(predictions), 1)
        if len(predictions)
        else 0.0
    )
    summary = {
        "status": "priority_overlay_evaluated",
        "n_variants": int(len(predictions)),
        "n_complete_alphamissense_rows": int(predictions["feature_alphamissense_pathogenicity"].notna().sum()),
        "n_positive": int(predictions["label_int"].fillna(0).astype(int).sum()),
        "n_negative": int(predictions["label_int"].notna().sum() - predictions["label_int"].fillna(0).astype(int).sum()),
        "best_model_by_auc_roc": best_model,
        "best_auc_roc": best_auc,
        "functional_support_rate_percent": round(support_rate, 2),
        "functional_alignment_counts": support_counts,
        "discordance_hypothesis_count": int(len(discordance)),
        "competition_claim_scope": (
            "Independent AlphaMissense overlay was evaluated on the locked priority-error queue; "
            "treat as functional hypothesis evidence, not definitive clinical validation."
        ),
    }
    return predictions, metrics, discordance, summary


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
    functional_overlay = matched.copy()
    if not functional_overlay.empty:
        functional_overlay["alphamissense_label_alignment"] = functional_overlay.apply(_functional_alignment, axis=1)
        functional_overlay["functional_interpretation"] = functional_overlay.apply(_functional_interpretation, axis=1)
        functional_overlay["feature_alphamissense_pathogenicity"] = pd.to_numeric(
            functional_overlay.get("feature_alphamissense_pathogenicity"),
            errors="coerce",
        )
        functional_overlay = functional_overlay.sort_values(
            ["alphamissense_label_alignment", "feature_alphamissense_pathogenicity", "competition_priority_score"],
            ascending=[True, False, False],
            kind="stable",
        )
    benchmark_predictions, benchmark_metrics, discordance_hypotheses, benchmark_summary = _build_priority_benchmark(
        functional_overlay
    )
    coordinate_ready_percent = round(float(target_table["coordinate_ready"].mean() * 100), 2) if len(target_table) else 0.0
    local_subset_coverage_percent = round(float(alpha_covered.mean() * 100), 2) if len(matched) else 0.0
    target_genes = sorted(set(protein_targets.get("gene", pd.Series(dtype=str)).astype(str).str.upper()) - {""})
    local_subset_exists = local_subset_path.exists()
    status = (
        "ready_to_benchmark"
        if local_subset_coverage_percent >= 80
        else "needs_identifier_mapping"
        if local_subset_exists and len(target_table) and local_subset_coverage_percent == 0
        else "ready_to_extract"
        if len(coordinate_targets) > 0
        else "needs_coordinate_resolution"
    )

    protein_targets_path = output_root / "alphamissense_priority_protein_targets.tsv"
    coordinate_targets_path = output_root / "alphamissense_priority_coordinate_targets.csv"
    matched_path = output_root / "alphamissense_priority_matched_coverage.csv"
    functional_overlay_path = output_root / "alphamissense_priority_functional_overlay.csv"
    benchmark_predictions_path = output_root / "alphamissense_priority_benchmark_predictions.csv"
    benchmark_metrics_path = output_root / "alphamissense_priority_benchmark_metrics.csv"
    discordance_hypotheses_path = output_root / "alphamissense_priority_discordance_hypotheses.csv"
    missing_path = output_root / "alphamissense_priority_missing_targets.csv"
    source_config_path = output_root / "alphamissense_priority_source_config.toml"
    extractor_script_path = output_root / "extract_priority_alphamissense.ps1"
    aa_extractor_script_path = output_root / "extract_priority_alphamissense_aa.ps1"
    report_path = output_root / "alphamissense_priority_enrichment_report.md"
    html_path = output_root / "alphamissense_priority_enrichment_report.html"
    manifest_path = output_root / "alphamissense_priority_enrichment_manifest.json"
    extraction_attempts_path = output_root / "alphamissense_extraction_attempts.json"

    protein_targets.to_csv(protein_targets_path, sep="\t", index=False)
    coordinate_targets.to_csv(coordinate_targets_path, index=False)
    matched.to_csv(matched_path, index=False)
    functional_overlay.to_csv(functional_overlay_path, index=False)
    benchmark_predictions.to_csv(benchmark_predictions_path, index=False)
    benchmark_metrics.to_csv(benchmark_metrics_path, index=False)
    discordance_hypotheses.to_csv(discordance_hypotheses_path, index=False)
    matched[~alpha_covered].to_csv(missing_path, index=False)
    source_config_path.write_text(_build_source_config(local_subset_path, target_genes), encoding="utf-8")
    extractor_script_path.write_text(
        "\n".join(
            [
                "# Generated by PrimeVarClass. Run only when you want to stream the official AlphaMissense table.",
                "$ErrorActionPreference = 'Stop'",
                "py -3.14 scripts\\extract_alphamissense_subset.py `",
                "  --mode genomic `",
                f"  --alphamissense-input \"{OFFICIAL_ALPHAMISSENSE_HG38_URL}\" `",
                f"  --targets \"{_display_path(coordinate_targets_path)}\" `",
                f"  --output \"{_display_path(local_subset_path)}\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    aa_extractor_script_path.write_text(
        "\n".join(
            [
                "# Generated by PrimeVarClass. Protein-substitution extraction is preferred when VCF coordinates do not align.",
                "$ErrorActionPreference = 'Stop'",
                "py -3.14 scripts\\extract_alphamissense_subset.py `",
                "  --mode aa `",
                f"  --alphamissense-input \"{OFFICIAL_ALPHAMISSENSE_AA_URL}\" `",
                f"  --targets \"{_display_path(protein_targets_path)}\" `",
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
        "local_subset_exists": local_subset_exists,
        "local_subset_coverage_percent": local_subset_coverage_percent,
        "matched_alphamissense_count": int(alpha_covered.sum()) if len(alpha_covered) else 0,
        "missing_alphamissense_count": int((~alpha_covered).sum()) if len(alpha_covered) else int(len(target_table)),
        "functional_alignment_counts": (
            functional_overlay["alphamissense_label_alignment"].value_counts().to_dict()
            if not functional_overlay.empty and "alphamissense_label_alignment" in functional_overlay.columns
            else {}
        ),
        "priority_benchmark": benchmark_summary,
        "target_genes": target_genes,
        "official_alphamissense_hg38_url": OFFICIAL_ALPHAMISSENSE_HG38_URL,
        "official_alphamissense_aa_url": OFFICIAL_ALPHAMISSENSE_AA_URL,
        "status": status,
        "next_action": (
            "Resolve UniProt/transcript/protein-variant harmonization before rerunning extraction; direct genomic and protein matching did not cover the current targets."
            if status == "needs_identifier_mapping"
            else
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
        "- If local coverage remains zero after extraction, treat this as an identifier/transcript harmonization problem rather than as biological absence.",
        "- When local coverage is available, the package also benchmarks AlphaMissense against locked PrimeVarClass scores on the priority queue and exports discordant mechanistic hypotheses.",
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
        f"- Functional overlay: `{_display_path(functional_overlay_path)}`",
        f"- Priority benchmark metrics: `{_display_path(benchmark_metrics_path)}`",
        f"- Priority benchmark predictions: `{_display_path(benchmark_predictions_path)}`",
        f"- Discordance hypotheses: `{_display_path(discordance_hypotheses_path)}`",
        f"- Missing targets: `{_display_path(missing_path)}`",
        f"- Source config: `{_display_path(source_config_path)}`",
        f"- Extractor script: `{_display_path(extractor_script_path)}`",
        f"- Protein extractor script: `{_display_path(aa_extractor_script_path)}`",
    ]
    if extraction_attempts_path.exists():
        lines.append(f"- Extraction attempts audit: `{_display_path(extraction_attempts_path)}`")
    report = "\n".join(lines).strip() + "\n"
    report_path.write_text(report, encoding="utf-8")
    html_path.write_text(_render_markdown_html(report, "AlphaMissense Priority Enrichment"), encoding="utf-8")
    manifest.update(
        {
            "protein_targets_path": _display_path(protein_targets_path),
            "coordinate_targets_path": _display_path(coordinate_targets_path),
            "matched_coverage_path": _display_path(matched_path),
            "functional_overlay_path": _display_path(functional_overlay_path),
            "benchmark_predictions_path": _display_path(benchmark_predictions_path),
            "benchmark_metrics_path": _display_path(benchmark_metrics_path),
            "discordance_hypotheses_path": _display_path(discordance_hypotheses_path),
            "missing_targets_path": _display_path(missing_path),
            "source_config_path": _display_path(source_config_path),
            "extractor_script_path": _display_path(extractor_script_path),
            "aa_extractor_script_path": _display_path(aa_extractor_script_path),
            "extraction_attempts_path": _display_path(extraction_attempts_path) if extraction_attempts_path.exists() else None,
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
        "alphamissense_priority_functional_overlay_path": str(functional_overlay_path),
        "alphamissense_priority_benchmark_predictions_path": str(benchmark_predictions_path),
        "alphamissense_priority_benchmark_metrics_path": str(benchmark_metrics_path),
        "alphamissense_priority_discordance_hypotheses_path": str(discordance_hypotheses_path),
        "alphamissense_priority_missing_targets_path": str(missing_path),
        "alphamissense_priority_source_config_path": str(source_config_path),
        "alphamissense_priority_extractor_script_path": str(extractor_script_path),
        "alphamissense_priority_aa_extractor_script_path": str(aa_extractor_script_path),
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
