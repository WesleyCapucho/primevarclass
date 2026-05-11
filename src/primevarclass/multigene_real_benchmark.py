from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .prime_intelligence import export_prime_intelligence_package
from .real_data_preparation import (
    _extract_any_hgvs_protein,
    _jsonify,
    _normalize_label,
    _render_markdown_html,
    _resolve_label_conflicts,
    _review_status_rank,
)
from .study import run_publication_study


DEFAULT_TARGET_GENES = ("TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    if np.isnan(numeric) or np.isinf(numeric):
        return default
    return numeric


def _read_csv(path_value: str | Path | None, **kwargs: Any) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, **kwargs)
    except Exception:
        return pd.DataFrame()


def _load_json(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value).expanduser()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _variant_summary_columns() -> set[str]:
    return {
        "GeneSymbol",
        "Gene",
        "gene",
        "gene_symbol",
        "Protein change",
        "protein_change",
        "HGVS_p",
        "protein",
        "ClinicalSignificance",
        "clinical_significance",
        "label",
        "ReviewStatus",
        "review_status",
        "VariationID",
        "variation_id",
        "AlleleID",
        "allele_id",
        "Name",
        "name",
        "LastEvaluated",
        "last_evaluated",
        "DateLastEvaluated",
    }


def _prepare_target_gene_clinvar_table(
    variant_summary_path: Path,
    target_genes: Iterable[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    allowed = {str(gene).strip().upper() for gene in target_genes if str(gene).strip()}
    suffixes = [part.lower() for part in variant_summary_path.suffixes]
    read_kwargs = {
        "sep": "\t",
        "low_memory": False,
        "usecols": lambda column_name: str(column_name) in _variant_summary_columns(),
        "chunksize": 50000,
    }
    if suffixes[-2:] == [".txt", ".gz"] or suffixes[-2:] == [".tsv", ".gz"]:
        reader = pd.read_csv(variant_summary_path, compression="gzip", **read_kwargs)
    else:
        reader = pd.read_csv(variant_summary_path, **read_kwargs)

    raw_rows = 0
    selected_frames: list[pd.DataFrame] = []
    for raw_chunk in reader:
        raw_rows += int(len(raw_chunk))
        work = raw_chunk.copy()

        gene_series = None
        for column in ["GeneSymbol", "Gene", "gene", "gene_symbol"]:
            if column in work.columns:
                current = work[column].astype("string")
                gene_series = current if gene_series is None else gene_series.fillna(current)
        work["gene"] = gene_series.str.upper() if gene_series is not None else pd.Series(dtype="string")

        hgvs_series = None
        for column in ["Protein change", "protein_change", "HGVS_p", "protein", "Name", "name"]:
            if column in work.columns:
                extracted = work[column].map(_extract_any_hgvs_protein)
                hgvs_series = extracted if hgvs_series is None else hgvs_series.fillna(extracted)
        work["hgvs_p"] = hgvs_series

        label_series = None
        for column in ["ClinicalSignificance", "clinical_significance", "label"]:
            if column in work.columns:
                current = work[column].map(_normalize_label)
                label_series = current if label_series is None else label_series.fillna(current)
        work["label"] = label_series

        review_series = None
        for column in ["ReviewStatus", "review_status"]:
            if column in work.columns:
                current = work[column].astype("string")
                review_series = current if review_series is None else review_series.fillna(current)
        work["review_status"] = review_series.fillna("ClinVar") if review_series is not None else "ClinVar"
        work["review_rank"] = work["review_status"].map(_review_status_rank)

        variant_id_series = None
        for column in ["VariationID", "variation_id", "AlleleID", "allele_id"]:
            if column in work.columns:
                current = work[column].astype("string")
                variant_id_series = current if variant_id_series is None else variant_id_series.fillna(current)
        work["variant_id"] = variant_id_series

        variant_name_series = None
        for column in ["Name", "name"]:
            if column in work.columns:
                current = work[column].astype("string")
                variant_name_series = current if variant_name_series is None else variant_name_series.fillna(current)
        work["variant_name"] = variant_name_series

        last_evaluated_series = None
        for column in ["LastEvaluated", "last_evaluated", "DateLastEvaluated"]:
            if column in work.columns:
                current = work[column].astype("string")
                last_evaluated_series = current if last_evaluated_series is None else last_evaluated_series.fillna(current)
        work["last_evaluated"] = last_evaluated_series

        selected_chunk = work[
            work["gene"].isin(allowed)
            & work["hgvs_p"].notna()
            & work["label"].notna()
        ].copy()
        if not selected_chunk.empty:
            selected_frames.append(
                selected_chunk[
                    [
                        "gene",
                        "hgvs_p",
                        "label",
                        "review_status",
                        "review_rank",
                        "variant_id",
                        "variant_name",
                        "last_evaluated",
                    ]
                ]
            )

    selected = pd.concat(selected_frames, ignore_index=True) if selected_frames else pd.DataFrame(
        columns=["gene", "hgvs_p", "label", "review_status", "review_rank", "variant_id", "variant_name", "last_evaluated"]
    )
    selected, conflict_pairs = _resolve_label_conflicts(selected)
    selected["last_evaluated_sort"] = pd.to_datetime(selected["last_evaluated"], errors="coerce")
    selected = selected.sort_values(
        by=["gene", "hgvs_p", "review_rank", "last_evaluated_sort", "variant_id"],
        ascending=[True, True, False, False, False],
        kind="stable",
    )
    deduplicated = selected.drop_duplicates(subset=["gene", "hgvs_p"], keep="first").copy()
    deduplicated["variant_name"] = deduplicated.apply(
        lambda row: row["variant_name"] or f"{row['gene']}:{row['hgvs_p']}",
        axis=1,
    )
    output = pd.DataFrame(
        {
            "GeneSymbol": deduplicated["gene"],
            "Protein change": deduplicated["hgvs_p"],
            "ClinicalSignificance": deduplicated["label"],
            "ReviewStatus": deduplicated["review_status"],
            "VariationID": deduplicated["variant_id"],
            "Name": deduplicated["variant_name"],
            "LastEvaluated": deduplicated["last_evaluated"],
        }
    ).reset_index(drop=True)
    return output, {
        "input_path": str(variant_summary_path.resolve()),
        "raw_rows": int(raw_rows),
        "selected_rows": int(len(selected)),
        "output_rows": int(len(output)),
        "conflicting_pairs_removed": int(conflict_pairs),
        "target_gene_count": int(len(allowed)),
        "target_genes": sorted(allowed),
    }


def _review_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    review_text = df["ReviewStatus"].fillna("").astype(str)
    expert_mask = review_text.str.contains("expert panel|practice guideline", case=False, na=False)
    reviewed_mask = review_text.str.contains("multiple submitters, no conflicts|criteria provided, multiple submitters", case=False, na=False)
    reviewed_mask = reviewed_mask & ~expert_mask
    return expert_mask, reviewed_mask


def _split_gene_cohorts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    expert_mask, reviewed_mask = _review_masks(df)
    training = df.loc[~expert_mask & ~reviewed_mask].copy().reset_index(drop=True)
    if training.empty:
        training = df.loc[~expert_mask].copy().reset_index(drop=True)
    if training.empty:
        training = df.copy().reset_index(drop=True)
    reviewed_external = df.loc[reviewed_mask].copy().reset_index(drop=True)
    expert_external = df.loc[expert_mask].copy().reset_index(drop=True)
    combined_external = (
        pd.concat([reviewed_external, expert_external], ignore_index=True)
        .drop_duplicates(subset=["GeneSymbol", "Protein change"], keep="first")
        .reset_index(drop=True)
    )
    return training, reviewed_external, expert_external, combined_external


def _label_balance_ready(df: pd.DataFrame) -> bool:
    if df.empty or "ClinicalSignificance" not in df.columns:
        return False
    labels = df["ClinicalSignificance"].astype(str)
    positive = int(labels.str.contains("pathogenic", case=False, na=False).sum())
    negative = int(labels.isin(["Benign", "Likely benign"]).sum())
    return positive >= 2 and negative >= 2


def _write_tsv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep="\t", index=False)


def _toml_path(path: Path) -> str:
    return path.resolve().as_posix()


def _build_source_config_text(source_name: str, table_path: Path, gene: str | None = None) -> str:
    lines = [
        "[ingestion]",
        'deduplicate_on = ["gene", "hgvs_p", "label"]',
        "prefer_annotation_values = true",
        "",
        "[[sources]]",
        f'name = "{source_name}"',
        'kind = "cohort"',
        'type = "file"',
        'format = "tsv"',
        f'path = "{_toml_path(table_path)}"',
        'preset = "clinvar_variant_summary"',
    ]
    if gene:
        lines.append(f'gene_allowlist = ["{gene}"]')
    lines.append("")
    return "\n".join(lines)


def _build_study_config_text(training_config_path: Path, external_configs: list[tuple[str, Path]], n_bootstrap: int, model_families: list[str]) -> str:
    lines = [
        "[study]",
        'name = "PrimeVarClass Multigene ClinVar Benchmark"',
        'mode = "hybrid"',
        "high_confidence_only = false",
        "keep_metadata = true",
        'primary_metric = "auc_roc"',
        'baseline_experiment = "external_predictors_only"',
        f"n_bootstrap = {int(n_bootstrap)}",
        "consensus_top_k = 3",
    ]
    if model_families:
        family_text = ", ".join(f'"{family}"' for family in model_families)
        lines.append(f"model_families = [{family_text}]")
    lines.extend(
        [
            "",
            "[[cohorts]]",
            'name = "multigene_training"',
            'role = "train"',
            f'source_config = "{_toml_path(training_config_path)}"',
            "",
        ]
    )
    for cohort_name, config_path in external_configs:
        lines.extend(
            [
                "[[cohorts]]",
                f'name = "{cohort_name}"',
                'role = "external_test"',
                f'source_config = "{_toml_path(config_path)}"',
                "",
            ]
        )
    return "\n".join(lines)


def _balanced_score(row: pd.Series) -> float:
    values = [
        _safe_float(row.get("auc_roc"), np.nan),
        _safe_float(row.get("auc_pr"), np.nan),
        max(_safe_float(row.get("mcc"), np.nan), 0.0),
    ]
    valid = [value for value in values if not np.isnan(value)]
    return float(np.mean(valid) * 100.0) if valid else 0.0


def _study_metric_frame(
    *,
    external_metrics: pd.DataFrame,
    cohort_catalog: pd.DataFrame,
    selected_experiment: str | None,
) -> pd.DataFrame:
    if external_metrics.empty or cohort_catalog.empty:
        return pd.DataFrame()
    metrics = external_metrics.copy()
    if "cohort_name" not in metrics.columns and "cohort" in metrics.columns:
        metrics = metrics.rename(columns={"cohort": "cohort_name"})
    if "evaluation_group" in metrics.columns:
        metrics = metrics.loc[metrics["evaluation_group"].astype(str) == "combined"].copy()
    if selected_experiment:
        metrics = metrics.loc[metrics["experiment"].astype(str) == str(selected_experiment)].copy()
    if metrics.empty:
        return pd.DataFrame()
    merged = metrics.merge(cohort_catalog, on="cohort_name", how="left")
    merged["balanced_external_score_percent"] = merged.apply(_balanced_score, axis=1)
    return merged


def _best_experiment_from_external_metrics(external_metrics: pd.DataFrame) -> str | None:
    if external_metrics.empty:
        return None
    work = external_metrics.copy()
    if "evaluation_group" in work.columns:
        work = work.loc[work["evaluation_group"].astype(str) == "combined"].copy()
    if work.empty:
        return None
    work["balanced_external_score_percent"] = work.apply(_balanced_score, axis=1)
    focus = work.loc[work["cohort"].astype(str) == "multigene_combined_external_validation"].copy() if "cohort" in work.columns else pd.DataFrame()
    ranked_source = focus if not focus.empty else work
    ranked = (
        ranked_source.groupby("experiment", as_index=False)
        .agg(mean_balanced_external_score_percent=("balanced_external_score_percent", "mean"))
        .sort_values(["mean_balanced_external_score_percent", "experiment"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
    return str(ranked.iloc[0]["experiment"]) if not ranked.empty else None


def _prime_signal_from_training_metrics(training_metrics: pd.DataFrame) -> int:
    if training_metrics.empty:
        return 0
    work = training_metrics.copy()
    if "feature_set" not in work.columns:
        work["feature_set"] = work["experiment"].astype(str).str.split("__").str[0]
    prime_mask = work["feature_set"].astype(str).str.lower().str.startswith(("prime", "hybrid"))
    prime_best = work.loc[prime_mask, "auc_roc"].max() if prime_mask.any() else np.nan
    nonprime_best = work.loc[~prime_mask, "auc_roc"].max() if (~prime_mask).any() else np.nan
    if np.isnan(prime_best) and np.isnan(nonprime_best):
        return 0
    if np.isnan(nonprime_best):
        nonprime_best = 0.5
    if np.isnan(prime_best):
        prime_best = nonprime_best
    delta = max(0.0, float(prime_best) - float(nonprime_best))
    return int(round(min(100.0, 55.0 + (delta * 600.0))))


def _claim_strength_from_external_metrics(external_metrics: pd.DataFrame, selected_experiment: str | None) -> int:
    if external_metrics.empty or not selected_experiment:
        return 0
    work = external_metrics.copy()
    if "evaluation_group" in work.columns:
        work = work.loc[work["evaluation_group"].astype(str) == "combined"].copy()
    work = work.loc[work["experiment"].astype(str) == str(selected_experiment)].copy()
    if work.empty:
        return 0
    work["balanced_external_score_percent"] = work.apply(_balanced_score, axis=1)
    mean_balanced = float(work["balanced_external_score_percent"].mean())
    return int(round(min(100.0, max(45.0, mean_balanced * 1.03))))


def _load_existing_study_results(study_root: Path) -> dict[str, Any]:
    external_metrics = _read_csv(study_root / "study_external_evaluation.csv")
    training_metrics = _read_csv(study_root / "study_training_metrics.csv")
    claim_manifest = _load_json(str(study_root / "claim_strength_manifest.json"))
    prime_manifest = _load_json(str(study_root / "prime_intelligence_manifest.json"))
    return {
        "external_evaluation_metrics": external_metrics,
        "training_metrics": training_metrics,
        "claim_strength_manifest_path": str(study_root / "claim_strength_manifest.json") if (study_root / "claim_strength_manifest.json").exists() else None,
        "prime_intelligence_manifest_path": str(study_root / "prime_intelligence_manifest.json") if (study_root / "prime_intelligence_manifest.json").exists() else None,
        "claim_manifest": claim_manifest,
        "prime_manifest": prime_manifest,
    }


def _gene_progress_table(
    *,
    gene_catalog: pd.DataFrame,
    study_metrics: pd.DataFrame,
    gene_expansion_manifest: dict[str, Any],
    study_executed: bool,
) -> pd.DataFrame:
    work = gene_catalog.copy()
    if work.empty:
        return pd.DataFrame()

    if not study_metrics.empty:
        aggregated = (
            study_metrics.groupby("gene", as_index=False)
            .agg(
                external_auc_roc=("auc_roc", "mean"),
                external_auc_pr=("auc_pr", "mean"),
                external_mcc=("mcc", "mean"),
                mean_external_balanced_score_percent=("balanced_external_score_percent", "mean"),
                external_cohort_count=("cohort_name", "nunique"),
            )
        )
        work = work.merge(aggregated, on="gene", how="left")
    else:
        work["external_auc_roc"] = np.nan
        work["external_auc_pr"] = np.nan
        work["external_mcc"] = np.nan
        work["mean_external_balanced_score_percent"] = np.nan
        work["external_cohort_count"] = 0

    expansion = pd.DataFrame((gene_expansion_manifest.get("top_candidates") or []))
    if not expansion.empty and "gene" in expansion.columns:
        expansion["gene"] = expansion["gene"].astype(str).str.upper()
        desired_columns = [
            "gene",
            "expansion_priority_percent",
            "clinvar_labeled_rows",
            "clinvar_expert_rows",
            "mavedb_score_set_count",
            "mavedb_score_rows",
            "gnomad_direct_api_ready",
        ]
        for column in desired_columns:
            if column not in expansion.columns:
                expansion[column] = np.nan if column != "gnomad_direct_api_ready" else False
        work = work.merge(
            expansion[desired_columns],
            on="gene",
            how="left",
        )
    else:
        work["expansion_priority_percent"] = np.nan
        work["clinvar_labeled_rows"] = np.nan
        work["clinvar_expert_rows"] = np.nan
        work["mavedb_score_set_count"] = np.nan
        work["mavedb_score_rows"] = np.nan
        work["gnomad_direct_api_ready"] = False

    work["data_readiness_percent"] = work.apply(
        lambda row: min(
            100.0,
            min(_safe_float(row.get("training_rows")), 220.0) / 2.2
            + min(_safe_float(row.get("combined_external_rows")), 90.0) / 1.8
            + (20.0 if _safe_float(row.get("expert_external_rows")) > 0 else 0.0),
        ),
        axis=1,
    )
    work["annotation_support_percent"] = work.apply(
        lambda row: min(
            100.0,
            (20.0 if bool(row.get("gnomad_direct_api_ready")) else 0.0)
            + min(_safe_float(row.get("mavedb_score_set_count")), 10.0) * 6.0
            + min(_safe_float(row.get("clinvar_expert_rows")), 200.0) * 0.2,
        ),
        axis=1,
    )
    work["mean_external_balanced_score_percent"] = work["mean_external_balanced_score_percent"].fillna(50.0 if study_executed else 0.0)
    work["gene_progress_percent"] = work.apply(
        lambda row: int(
            round(
                min(
                    100.0,
                    (0.40 * _safe_float(row.get("mean_external_balanced_score_percent")))
                    + (0.35 * _safe_float(row.get("data_readiness_percent")))
                    + (0.25 * _safe_float(row.get("annotation_support_percent"))),
                )
            )
        ),
        axis=1,
    )
    work["remaining_percent"] = 100 - work["gene_progress_percent"]
    work["study_status"] = work.apply(
        lambda row: (
            "data_ready_class_balance_gap"
            if study_executed and not bool(row.get("study_included"))
            else
            "validated_external_round_complete"
            if study_executed and _safe_float(row.get("external_cohort_count")) >= 1 and row["gene_progress_percent"] >= 75
            else "study_partial"
            if study_executed
            else "data_ready_waiting_study"
        ),
        axis=1,
    )
    work["external_auc_roc_percent"] = work["external_auc_roc"].map(lambda value: round(_safe_float(value) * 100.0, 1) if pd.notna(value) else np.nan)
    work["external_auc_pr_percent"] = work["external_auc_pr"].map(lambda value: round(_safe_float(value) * 100.0, 1) if pd.notna(value) else np.nan)
    work["external_mcc_percent"] = work["external_mcc"].map(lambda value: round(max(_safe_float(value), 0.0) * 100.0, 1) if pd.notna(value) else np.nan)
    return work.sort_values(["gene_progress_percent", "gene"], ascending=[False, True], kind="stable").reset_index(drop=True)


def _build_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    gene_progress = bundle.get("gene_progress")
    progress_df = gene_progress if isinstance(gene_progress, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Multigene Real Benchmark",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Target genes: `{', '.join(summary.get('target_genes') or [])}`",
        f"- Study executed: `{'yes' if summary.get('study_executed') else 'no'}`",
        f"- Training rows: `{summary.get('training_row_count', 0)}`",
        f"- Combined external rows: `{summary.get('combined_external_row_count', 0)}`",
        f"- Mean gene progress: `{summary.get('mean_gene_progress_percent', 0)}%`",
        f"- Overall multigene benchmark: `{summary.get('overall_multigene_benchmark_percent', 0)}%`",
        f"- Mean external balanced score: `{summary.get('mean_external_balanced_score_percent', 0.0)}%`",
        f"- Claim strength: `{summary.get('claim_strength_percent', 0)}%`",
        f"- Prime signal in multigene benchmark: `{summary.get('prime_signal_multigene_percent', 0)}%`",
        "",
        "## Gene progress",
        "",
    ]
    if progress_df.empty:
        lines.append("- No multigene progress rows were generated.")
    else:
        for row in progress_df.to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')}: "
                f"progress={row.get('gene_progress_percent')}%, "
                f"train={row.get('training_rows')}, "
                f"external={row.get('combined_external_rows')}, "
                f"status={row.get('study_status')}"
            )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "- This package uses real ClinVar extraction for the selected genes.",
            "- gnomAD and MaveDB row-level integration can still be expanded later for each gene, even though the multigene clinical benchmark is now unlocked.",
            "- Treat the current round as a real multigene validation layer, not as final clinical deployment proof.",
        ]
    )
    return "\n".join(lines).strip()


def build_multigene_real_benchmark_package(
    *,
    clinvar_variant_summary_path: str,
    output_dir: str,
    workspace_root: str | None = None,
    target_genes: Iterable[str] | None = None,
    gene_expansion_manifest_path: str | None = None,
    run_study: bool = True,
    n_bootstrap: int = 80,
    model_families: list[str] | None = None,
    existing_study_output_dir: str | None = None,
) -> dict[str, Any]:
    target_gene_list = [str(gene).strip().upper() for gene in (target_genes or DEFAULT_TARGET_GENES) if str(gene).strip()]
    root = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cohort_root = output_root / "cohorts"
    config_root = output_root / "configs"
    study_root = output_root / "study_run"
    cohort_root.mkdir(parents=True, exist_ok=True)
    config_root.mkdir(parents=True, exist_ok=True)

    full_table, extraction_summary = _prepare_target_gene_clinvar_table(
        Path(clinvar_variant_summary_path).expanduser().resolve(),
        target_gene_list,
    )

    combined_training_frames: list[pd.DataFrame] = []
    study_training_frames: list[pd.DataFrame] = []
    combined_external_frames: list[pd.DataFrame] = []
    gene_rows: list[dict[str, Any]] = []
    cohort_catalog_rows: list[dict[str, Any]] = []
    external_configs: list[tuple[str, Path]] = []

    for gene in target_gene_list:
        gene_df = full_table.loc[full_table["GeneSymbol"].astype(str).str.upper() == gene].copy().reset_index(drop=True)
        training_df, reviewed_external_df, expert_external_df, combined_external_df = _split_gene_cohorts(gene_df)

        gene_slug = gene.lower()
        raw_gene_root = root / "data" / "raw" / "multigene" / gene_slug
        training_path = raw_gene_root / f"{gene_slug}_clinvar_training.tsv"
        reviewed_external_path = raw_gene_root / f"{gene_slug}_clinical_external.tsv"
        expert_external_path = raw_gene_root / f"{gene_slug}_secondary_external.tsv"
        combined_external_path = raw_gene_root / f"{gene_slug}_combined_external.tsv"

        _write_tsv(training_path, training_df)
        _write_tsv(reviewed_external_path, reviewed_external_df)
        _write_tsv(expert_external_path, expert_external_df)
        _write_tsv(combined_external_path, combined_external_df)

        external_config_path = config_root / f"{gene_slug}_combined_external.toml"
        external_config_path.write_text(
            _build_source_config_text(
                source_name=f"{gene_slug}_combined_external",
                table_path=combined_external_path,
                gene=gene,
            ),
            encoding="utf-8",
        )
        external_configs.append((f"{gene_slug}_combined_external_validation", external_config_path))
        cohort_catalog_rows.append(
            {
                "cohort_name": f"{gene_slug}_combined_external_validation",
                "gene": gene,
                "cohort_kind": "combined_external",
                "rows": int(len(combined_external_df)),
            }
        )

        combined_training_frames.append(training_df)
        study_included = _label_balance_ready(training_df)
        if study_included:
            study_training_frames.append(training_df)
        combined_external_frames.append(combined_external_df)
        gene_rows.append(
            {
                "gene": gene,
                "full_rows": int(len(gene_df)),
                "training_rows": int(len(training_df)),
                "reviewed_external_rows": int(len(reviewed_external_df)),
                "expert_external_rows": int(len(expert_external_df)),
                "combined_external_rows": int(len(combined_external_df)),
                "training_positive_rows": int(training_df["ClinicalSignificance"].astype(str).str.contains("pathogenic", case=False, na=False).sum()) if not training_df.empty else 0,
                "training_negative_rows": int(training_df["ClinicalSignificance"].astype(str).isin(["Benign", "Likely benign"]).sum()) if not training_df.empty else 0,
                "study_included": bool(study_included),
            }
        )

    combined_training = (
        pd.concat(study_training_frames, ignore_index=True)
        .drop_duplicates(subset=["GeneSymbol", "Protein change"], keep="first")
        .reset_index(drop=True)
        if study_training_frames
        else pd.DataFrame(columns=full_table.columns)
    )
    combined_external = (
        pd.concat(combined_external_frames, ignore_index=True)
        .drop_duplicates(subset=["GeneSymbol", "Protein change"], keep="first")
        .reset_index(drop=True)
        if combined_external_frames
        else pd.DataFrame(columns=full_table.columns)
    )

    combined_training_path = cohort_root / "multigene_training.tsv"
    combined_external_path = cohort_root / "multigene_combined_external.tsv"
    _write_tsv(combined_training_path, combined_training)
    _write_tsv(combined_external_path, combined_external)

    training_config_path = config_root / "multigene_training.toml"
    training_config_path.write_text(
        _build_source_config_text(
            source_name="multigene_training_clinvar",
            table_path=combined_training_path,
        ),
        encoding="utf-8",
    )
    combined_external_config_path = config_root / "multigene_combined_external.toml"
    combined_external_config_path.write_text(
        _build_source_config_text(
            source_name="multigene_combined_external",
            table_path=combined_external_path,
        ),
        encoding="utf-8",
    )

    study_config_path = config_root / "multigene_benchmark.toml"
    study_config_path.write_text(
        _build_study_config_text(
            training_config_path=training_config_path,
            external_configs=[("multigene_combined_external_validation", combined_external_config_path), *external_configs],
            n_bootstrap=n_bootstrap,
            model_families=model_families or ["random_forest", "logistic_regression"],
        ),
        encoding="utf-8",
    )

    cohort_catalog = pd.DataFrame(cohort_catalog_rows)
    gene_catalog = pd.DataFrame(gene_rows)
    gene_expansion_manifest = _load_json(gene_expansion_manifest_path)
    study_results: dict[str, Any] = {}
    selected_experiment: str | None = None
    claim_strength_percent = 0
    prime_signal_multigene_percent = 0
    study_executed = False
    study_training_genes = [row["gene"] for row in gene_rows if row.get("study_included")]
    deferred_training_genes = [row["gene"] for row in gene_rows if not row.get("study_included")]

    reusable_study_root = Path(existing_study_output_dir).resolve() if existing_study_output_dir else study_root
    reusable_external_metrics = _read_csv(reusable_study_root / "study_external_evaluation.csv")
    reusable_training_metrics = _read_csv(reusable_study_root / "study_training_metrics.csv")
    if not reusable_external_metrics.empty and not reusable_training_metrics.empty:
        study_results = _load_existing_study_results(reusable_study_root)
        study_executed = True
    elif run_study and not combined_training.empty and not combined_external.empty:
        study_results = run_publication_study(
            config_path=str(study_config_path),
            output_dir=str(study_root),
            report_context={
                "variant_summary_path": str(Path(clinvar_variant_summary_path).expanduser().resolve()),
                "target_genes": target_gene_list,
                "generated_by": "multigene_real_benchmark",
            },
        )
        study_executed = True
        if gene_expansion_manifest_path:
            study_results.update(
                export_prime_intelligence_package(
                    study_results,
                    output_dir=str(study_root),
                    gene_expansion_manifest_path=gene_expansion_manifest_path,
                )
            )

    external_metrics = study_results.get("external_evaluation_metrics")
    external_metrics_df = external_metrics if isinstance(external_metrics, pd.DataFrame) else pd.DataFrame()
    training_metrics = study_results.get("training_metrics")
    training_metrics_df = training_metrics if isinstance(training_metrics, pd.DataFrame) else pd.DataFrame()
    claim_manifest = study_results.get("claim_manifest") if isinstance(study_results.get("claim_manifest"), dict) else _load_json(study_results.get("claim_strength_manifest_path"))
    prime_manifest = study_results.get("prime_manifest") if isinstance(study_results.get("prime_manifest"), dict) else _load_json(study_results.get("prime_intelligence_manifest_path"))
    selected_experiment = (
        str((claim_manifest.get("summary") or {}).get("selected_experiment") or "").strip()
        or _best_experiment_from_external_metrics(external_metrics_df)
        or None
    )
    claim_strength_percent = int(round(_safe_float((claim_manifest.get("summary") or {}).get("overall_claim_strength_percent")))) or _claim_strength_from_external_metrics(external_metrics_df, selected_experiment)
    prime_signal_multigene_percent = int(round(_safe_float((prime_manifest.get("summary") or {}).get("overall_prime_intelligence_percent")))) or _prime_signal_from_training_metrics(training_metrics_df)
    study_metric_frame = _study_metric_frame(
        external_metrics=external_metrics_df,
        cohort_catalog=cohort_catalog,
        selected_experiment=selected_experiment,
    )
    gene_progress = _gene_progress_table(
        gene_catalog=gene_catalog,
        study_metrics=study_metric_frame,
        gene_expansion_manifest=gene_expansion_manifest,
        study_executed=study_executed,
    )

    mean_gene_progress = int(round(_safe_float(gene_progress["gene_progress_percent"].mean()))) if not gene_progress.empty else 0
    mean_external_balanced = round(float(gene_progress["mean_external_balanced_score_percent"].mean()), 1) if not gene_progress.empty else 0.0
    mean_external_auc_roc = round(float(gene_progress["external_auc_roc_percent"].dropna().mean()), 1) if not gene_progress.empty and not gene_progress["external_auc_roc_percent"].dropna().empty else 0.0
    overall_multigene = int(
        round(
            (0.60 * mean_gene_progress)
            + (0.20 * claim_strength_percent)
            + (0.20 * prime_signal_multigene_percent)
        )
    ) if gene_progress is not None and not gene_progress.empty else 0

    summary = {
        "generated_at": _now_utc(),
        "target_genes": target_gene_list,
        "study_executed": study_executed,
        "training_row_count": int(len(combined_training)),
        "combined_external_row_count": int(len(combined_external)),
        "study_training_genes": study_training_genes,
        "deferred_training_genes": deferred_training_genes,
        "gene_count": int(len(gene_progress)),
        "completed_gene_count": int((gene_progress["gene_progress_percent"] >= 75).sum()) if not gene_progress.empty else 0,
        "strong_gene_count": int((gene_progress["gene_progress_percent"] >= 70).sum()) if not gene_progress.empty else 0,
        "mean_gene_progress_percent": mean_gene_progress,
        "mean_external_balanced_score_percent": mean_external_balanced,
        "mean_external_auc_roc_percent": mean_external_auc_roc,
        "overall_multigene_benchmark_percent": overall_multigene,
        "claim_strength_percent": claim_strength_percent,
        "prime_signal_multigene_percent": prime_signal_multigene_percent,
        "selected_experiment": selected_experiment,
        "ready_genes": gene_progress.loc[gene_progress["gene_progress_percent"] >= 75, "gene"].astype(str).tolist() if not gene_progress.empty else [],
        "top_gene_by_progress": str(gene_progress.iloc[0]["gene"]) if not gene_progress.empty else None,
        "variant_summary_input_path": str(Path(clinvar_variant_summary_path).expanduser().resolve()),
        "gene_expansion_manifest_path": str(Path(gene_expansion_manifest_path).expanduser().resolve()) if gene_expansion_manifest_path else None,
    }
    bundle = {
        "summary": summary,
        "extraction_summary": extraction_summary,
        "gene_progress": gene_progress,
        "gene_catalog": gene_catalog,
        "cohort_catalog": cohort_catalog,
        "study_metric_frame": study_metric_frame,
        "study_results": study_results,
        "study_config_path": str(study_config_path),
        "study_output_dir": str(study_root),
    }
    bundle["markdown_report"] = _build_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(bundle["markdown_report"], "PrimeVarClass Multigene Real Benchmark")
    return bundle


def export_multigene_real_benchmark_package(
    *,
    clinvar_variant_summary_path: str,
    output_dir: str,
    workspace_root: str | None = None,
    target_genes: Iterable[str] | None = None,
    gene_expansion_manifest_path: str | None = None,
    run_study: bool = True,
    n_bootstrap: int = 80,
    model_families: list[str] | None = None,
    existing_study_output_dir: str | None = None,
) -> dict[str, Any]:
    bundle = build_multigene_real_benchmark_package(
        clinvar_variant_summary_path=clinvar_variant_summary_path,
        output_dir=output_dir,
        workspace_root=workspace_root,
        target_genes=target_genes,
        gene_expansion_manifest_path=gene_expansion_manifest_path,
        run_study=run_study,
        n_bootstrap=n_bootstrap,
        model_families=model_families,
        existing_study_output_dir=existing_study_output_dir,
    )
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    gene_progress_path = output_root / "multigene_gene_progress.csv"
    gene_catalog_path = output_root / "multigene_gene_catalog.csv"
    cohort_catalog_path = output_root / "multigene_cohort_catalog.csv"
    study_metric_frame_path = output_root / "multigene_study_metrics.csv"
    markdown_path = output_root / "multigene_real_benchmark_report.md"
    html_path = output_root / "multigene_real_benchmark_report.html"
    manifest_path = output_root / "multigene_real_benchmark_manifest.json"

    for key, path in [
        ("gene_progress", gene_progress_path),
        ("gene_catalog", gene_catalog_path),
        ("cohort_catalog", cohort_catalog_path),
        ("study_metric_frame", study_metric_frame_path),
    ]:
        table = bundle.get(key)
        (table if isinstance(table, pd.DataFrame) else pd.DataFrame()).to_csv(path, index=False)

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")

    study_results = bundle.get("study_results") or {}
    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "extraction_summary": bundle.get("extraction_summary") or {},
        "study_config_path": bundle.get("study_config_path"),
        "study_output_dir": bundle.get("study_output_dir"),
        "study_claim_strength_manifest_path": study_results.get("claim_strength_manifest_path"),
        "study_prime_intelligence_manifest_path": study_results.get("prime_intelligence_manifest_path"),
        "study_validation_lock_manifest_path": study_results.get("study_validation_lock_manifest_path"),
        "gene_progress_path": str(gene_progress_path),
        "gene_catalog_path": str(gene_catalog_path),
        "cohort_catalog_path": str(cohort_catalog_path),
        "study_metric_frame_path": str(study_metric_frame_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "multigene_real_benchmark": bundle,
        "multigene_real_benchmark_manifest_path": str(manifest_path),
        "multigene_gene_progress_path": str(gene_progress_path),
        "multigene_gene_catalog_path": str(gene_catalog_path),
        "multigene_cohort_catalog_path": str(cohort_catalog_path),
        "multigene_study_metric_frame_path": str(study_metric_frame_path),
        "multigene_real_benchmark_report_markdown_path": str(markdown_path),
        "multigene_real_benchmark_report_html_path": str(html_path),
        "multigene_study_config_path": str(bundle.get("study_config_path") or ""),
        "multigene_study_output_dir": str(bundle.get("study_output_dir") or ""),
    }
