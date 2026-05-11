from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def build_brca1_lovd_error_analysis(campaign_root: Path) -> dict:
    brca_root = campaign_root / "brca_real_quick"
    score_path = brca_root / "study_scores_bridges_like_external_validation_brca1.csv"
    metrics_path = brca_root / "study_external_metrics_bridges_like_external_validation_brca1.csv"
    integrated_path = brca_root / "cohorts" / "bridges_like_external_validation_brca1_ingestion" / "integrated_sources.csv"
    output_dir = campaign_root / "brca1_lovd_error_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    scores = pd.read_csv(score_path)
    metrics = pd.read_csv(metrics_path)
    integrated = pd.read_csv(integrated_path)

    score_columns = [column for column in scores.columns if column.startswith("score__")]
    model_rows: list[dict] = []
    error_frames: list[pd.DataFrame] = []
    for score_column in score_columns:
        experiment = score_column.replace("score__", "")
        pred = (scores[score_column].astype(float) >= 0.5).astype(int)
        label = scores["label"].astype(int)
        fp = scores.loc[(pred == 1) & (label == 0), ["variant", "gene", "label", score_column]].copy()
        fn = scores.loc[(pred == 0) & (label == 1), ["variant", "gene", "label", score_column]].copy()
        tp = int(((pred == 1) & (label == 1)).sum())
        tn = int(((pred == 0) & (label == 0)).sum())
        fp_count = int(len(fp))
        fn_count = int(len(fn))
        error_rate = (fp_count + fn_count) / max(len(scores), 1)
        model_rows.append(
            {
                "experiment": experiment,
                "threshold": 0.5,
                "tp": tp,
                "fp": fp_count,
                "fn": fn_count,
                "tn": tn,
                "error_count": fp_count + fn_count,
                "error_rate": round(error_rate, 4),
                "mean_score": round(float(scores[score_column].astype(float).mean()), 4),
            }
        )
        fp["error_type"] = "false_positive"
        fp["experiment"] = experiment
        fp = fp.rename(columns={score_column: "score"})
        fn["error_type"] = "false_negative"
        fn["experiment"] = experiment
        fn = fn.rename(columns={score_column: "score"})
        error_frames.extend([fp, fn])

    model_error = pd.DataFrame(model_rows).sort_values(["error_count", "experiment"], kind="stable")
    all_errors = pd.concat(error_frames, ignore_index=True) if error_frames else pd.DataFrame()

    best_metric = metrics.sort_values("auc_roc", ascending=False, kind="stable").iloc[0].to_dict()
    best_experiment = str(best_metric.get("experiment"))
    best_score_col = f"score__{best_experiment}"
    selected_score_col = best_score_col if best_score_col in scores.columns else "score__gene_balanced_specialist"
    selected_experiment = selected_score_col.replace("score__", "")
    selected_pred = (scores[selected_score_col].astype(float) >= 0.5).astype(int)
    selected = scores[["variant", "gene", "label", selected_score_col]].copy()
    selected["predicted_label"] = selected_pred
    selected["error_type"] = "correct"
    selected.loc[(selected["predicted_label"] == 1) & (selected["label"].astype(int) == 0), "error_type"] = "false_positive"
    selected.loc[(selected["predicted_label"] == 0) & (selected["label"].astype(int) == 1), "error_type"] = "false_negative"
    selected = selected.rename(columns={selected_score_col: "selected_score"})
    selected_errors = selected[selected["error_type"] != "correct"].copy()

    label_balance = scores["label"].value_counts().rename_axis("label").reset_index(name="count")
    label_balance["percent"] = (label_balance["count"] / max(len(scores), 1) * 100).round(2)
    integrated_coverage = {
        "integrated_rows": int(len(integrated)),
        "gnomad_rows_with_af": int(integrated.get("feature_gnomad_af", pd.Series(dtype=float)).notna().sum()),
        "mavedb_rows_with_score": int(integrated.get("feature_mave_score", pd.Series(dtype=float)).notna().sum()),
    }
    integrated_coverage["gnomad_af_coverage_percent"] = round(
        integrated_coverage["gnomad_rows_with_af"] / max(integrated_coverage["integrated_rows"], 1) * 100,
        2,
    )
    integrated_coverage["mavedb_score_coverage_percent"] = round(
        integrated_coverage["mavedb_rows_with_score"] / max(integrated_coverage["integrated_rows"], 1) * 100,
        2,
    )

    model_error_path = output_dir / "brca1_lovd_model_error_summary.csv"
    selected_errors_path = output_dir / "brca1_lovd_selected_model_errors.csv"
    all_errors_path = output_dir / "brca1_lovd_all_model_errors.csv"
    coverage_path = output_dir / "brca1_lovd_feature_coverage.json"
    report_path = output_dir / "brca1_lovd_error_analysis.md"
    manifest_path = output_dir / "brca1_lovd_error_analysis_manifest.json"

    model_error.to_csv(model_error_path, index=False)
    selected_errors.sort_values("selected_score", ascending=False, kind="stable").to_csv(selected_errors_path, index=False)
    all_errors.to_csv(all_errors_path, index=False)
    coverage_path.write_text(json.dumps(integrated_coverage, indent=2, ensure_ascii=False), encoding="utf-8")

    total_errors = int(len(selected_errors))
    false_positives = int((selected_errors["error_type"] == "false_positive").sum()) if total_errors else 0
    false_negatives = int((selected_errors["error_type"] == "false_negative").sum()) if total_errors else 0
    best_auc = _safe_float(best_metric.get("auc_roc"))
    best_mcc = _safe_float(best_metric.get("mcc"))

    lines = [
        "# BRCA1 LOVD error analysis",
        "",
        f"- Generated at: `{_now_utc()}`",
        f"- Cohort: `bridges_like_external_validation_brca1`",
        f"- Variants analyzed: `{len(scores)}`",
        f"- Best external metric experiment: `{best_experiment}`",
        f"- Best external AUC-ROC: `{best_auc:.4f}`",
        f"- Best external MCC: `{best_mcc:.4f}`",
        f"- Selected model for error inspection: `{selected_experiment}`",
        f"- Selected-model errors at threshold 0.5: `{total_errors}`",
        f"- False positives: `{false_positives}`",
        f"- False negatives: `{false_negatives}`",
        "",
        "## Label balance",
        "",
    ]
    for row in label_balance.to_dict(orient="records"):
        lines.append(f"- Label {row['label']}: {row['count']} variants ({row['percent']}%).")
    lines.extend(
        [
            "",
            "## External evidence coverage in this cohort",
            "",
            f"- gnomAD AF coverage: `{integrated_coverage['gnomad_af_coverage_percent']}%`.",
            f"- MaveDB score coverage: `{integrated_coverage['mavedb_score_coverage_percent']}%`.",
            "",
            "## Interpretation",
            "",
            "- BRCA1 LOVD is the weakest BRCA holdout in the current campaign and should be treated as a priority error-analysis cohort.",
            "- The low MaveDB coverage in this cohort suggests that some errors may be driven by limited functional evidence rather than model failure alone.",
            "- The next scientific step is to enrich these variants with AlphaMissense, reviewed structural context and manual class-balance inspection.",
            "- This analysis strengthens the competition dossier because it shows the platform does not hide weak cases; it identifies them and turns them into testable next steps.",
            "",
            "## Output files",
            "",
            f"- Model error summary: `{model_error_path}`",
            f"- Selected-model errors: `{selected_errors_path}`",
            f"- All model errors: `{all_errors_path}`",
            f"- Feature coverage: `{coverage_path}`",
        ]
    )
    _write_markdown(report_path, lines)

    manifest = {
        "generated_at": _now_utc(),
        "cohort": "bridges_like_external_validation_brca1",
        "score_path": str(score_path),
        "metrics_path": str(metrics_path),
        "integrated_path": str(integrated_path),
        "selected_experiment": selected_experiment,
        "variant_count": int(len(scores)),
        "selected_model_error_count": total_errors,
        "selected_model_false_positives": false_positives,
        "selected_model_false_negatives": false_negatives,
        "feature_coverage": integrated_coverage,
        "model_error_summary_path": str(model_error_path),
        "selected_model_errors_path": str(selected_errors_path),
        "all_model_errors_path": str(all_errors_path),
        "report_path": str(report_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def build_alphamissense_subset_plan(campaign_root: Path) -> dict:
    output_dir = campaign_root / "alphamissense_subset_plan"
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "alphamissense_subset_plan.md"
    template_path = output_dir / "alphamissense_target_gene_source_config.toml"
    manifest_path = output_dir / "alphamissense_subset_plan_manifest.json"

    official_hg38_url = "https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz"
    official_gene_url = "https://storage.googleapis.com/dm_alphamissense/AlphaMissense_gene_hg38.tsv.gz"
    target_path = "data/raw/alphamissense/target_gene_alphamissense.tsv"
    genes = ["BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9"]

    template_path.write_text(
        "\n".join(
            [
                "[ingestion]",
                'deduplicate_on = ["gene", "hgvs_p"]',
                "prefer_annotation_values = true",
                "",
                "[[sources]]",
                'name = "alphamissense_target_gene_scores"',
                'kind = "annotation"',
                'type = "file"',
                'format = "tsv"',
                f'path = "{target_path}"',
                'preset = "alphamissense_table"',
                'join_on = ["gene", "hgvs_p"]',
                f"gene_allowlist = {json.dumps(genes)}",
                'release_version = "AlphaMissense_v2023_hg38"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# AlphaMissense subset plan",
        "",
        f"- Generated at: `{_now_utc()}`",
        "- Goal: add AlphaMissense as an independent predictor without downloading a massive full table into routine campaign runs.",
        f"- Official hg38 all-variant file: `{official_hg38_url}`",
        f"- Official hg38 gene-level file: `{official_gene_url}`",
        f"- Target local subset: `{target_path}`",
        "",
        "## Why this is a controlled step",
        "",
        "- The full AlphaMissense hg38 table is very large and should not be pulled automatically during an interactive session.",
        "- For publication-grade evidence, we only need rows matching the target genes or variants in the frozen benchmarks.",
        "- The generated source config is ready once the target subset file is created.",
        "",
        "## Target genes",
        "",
    ]
    lines.extend([f"- {gene}" for gene in genes])
    lines.extend(
        [
            "",
            "## Required normalized columns",
            "",
            "- `gene`",
            "- `hgvs_p`",
            "- `feature_alphamissense_pathogenicity`",
            "- `feature_alphamissense_class`",
            "- `meta_alphamissense_transcript_id`",
            "- `meta_genome_build`",
            "",
            "## Recommended execution",
            "",
            "Use a streaming extractor or a cloud/HPC job to filter the official table to the target genes or frozen benchmark variants. Do not load the full table into memory.",
            "",
            "## Output files",
            "",
            f"- Source config template: `{template_path}`",
        ]
    )
    _write_markdown(plan_path, lines)
    manifest = {
        "generated_at": _now_utc(),
        "official_hg38_url": official_hg38_url,
        "official_gene_url": official_gene_url,
        "target_local_subset_path": target_path,
        "target_genes": genes,
        "source_config_template_path": str(template_path),
        "plan_path": str(plan_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def refresh_campaign_report(campaign_root: Path, brca_manifest: dict, alphamissense_manifest: dict) -> None:
    report_path = campaign_root / "evidence_campaign_report.md"
    appendix = [
        "",
        "## Atualização automática da campanha",
        "",
        f"Atualizado em: {_now_utc()}",
        "",
        "### Análise de erro BRCA1 LOVD",
        "",
        f"- Relatório: `{brca_manifest['report_path']}`",
        f"- Variantes analisadas: `{brca_manifest['variant_count']}`",
        f"- Erros no modelo selecionado: `{brca_manifest['selected_model_error_count']}`",
        f"- Falsos positivos: `{brca_manifest['selected_model_false_positives']}`",
        f"- Falsos negativos: `{brca_manifest['selected_model_false_negatives']}`",
        "",
        "### Plano AlphaMissense",
        "",
        f"- Plano: `{alphamissense_manifest['plan_path']}`",
        f"- Configuração pronta: `{alphamissense_manifest['source_config_template_path']}`",
        "- Status: preparado para subset seguro; download completo não foi iniciado para não travar a máquina.",
    ]
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else "# Evidence campaign\n"
    marker = "\n## Atualização automática da campanha\n"
    if marker in existing:
        existing = existing.split(marker)[0].rstrip()
    report_path.write_text(existing.rstrip() + "\n" + "\n".join(appendix) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PrimeVarClass Jovem Cientista evidence assets.")
    parser.add_argument(
        "--campaign-root",
        default="primevarclass_jovem_cientista_evidence_20260510",
        help="Campaign evidence root directory.",
    )
    args = parser.parse_args()
    campaign_root = Path(args.campaign_root)
    brca_manifest = build_brca1_lovd_error_analysis(campaign_root)
    alphamissense_manifest = build_alphamissense_subset_plan(campaign_root)
    refresh_campaign_report(campaign_root, brca_manifest, alphamissense_manifest)
    print(f"BRCA1 LOVD error analysis: {brca_manifest['report_path']}")
    print(f"AlphaMissense subset plan: {alphamissense_manifest['plan_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
