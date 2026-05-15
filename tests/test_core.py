import unittest
import os
from pathlib import Path
import sys
import json
import sqlite3
import tarfile
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from primevarclass import (
    export_alphamissense_priority_enrichment_package,
    export_biological_discovery_package,
    build_dataset_from_dataframe,
    build_dataset_from_source_config,
    build_study_validation_lock,
    classify_acmg_strength_from_lr,
    create_app,
    dataset_schema_template,
    encode_variant_features,
    export_calibration_rescue_package,
    export_locked_calibration_holdout_package,
    export_claim_strength_package,
    export_competition_jury_audit_package,
    export_competition_readiness_package,
    export_brca1_engine_execution_package,
    export_brca1_fragment_preparation_package,
    export_brca1_paired_mutant_execution_package,
    export_brca1_mutant_geometry_qc_package,
    export_brca1_structural_campaign,
    export_continuous_learning_package,
    export_development_progress_dashboard,
    export_study_cohort_freeze,
    export_cohort_independence_package,
    export_comparative_evidence_package,
    export_external_robustness_package,
    export_final_mile_package,
    export_gene_expansion_assessment,
    export_gnomad_gene_subset,
    export_independent_data_expansion_package,
    export_independent_data_staging_closure_package,
    export_independent_open_source_autostage_package,
    export_launch_readiness_package,
    export_multigene_annotation_enrichment_package,
    export_multigene_rollout_plan,
    export_multigene_real_benchmark_package,
    export_multigene_study_factory,
    export_platform_completion_assessment,
    export_protein_impact_package,
    export_public_sync_closure_package,
    export_quantum_proteomics_package,
    export_quantum_vqe_benchmark_package,
    export_prime_intelligence_package,
    export_prospective_validation_closure_package,
    export_validation_credibility_closure,
    export_real_data_handoff_autofill,
    export_real_data_handoff_application,
    export_real_data_candidate_promotion,
    export_real_data_handoff_reconciliation,
    export_translational_impact_package,
    export_translational_pilot_package,
    export_study_execution_board,
    export_study_validation_lock,
    export_public_source_resolution,
    export_study_public_config_resolution,
    export_study_preflight,
    export_real_data_preparation_bundle,
    ingest_sources_from_config,
    load_study_design,
    parse_variant,
    run_candidate_public_benchmark_pipeline,
    run_public_benchmark_pipeline,
    run_publication_study,
    run_full_training_pipeline_from_dataframe,
    refresh_frozen_study_assessment,
    train_baseline_model,
    apply_source_preset,
)
from primevarclass.core import run_gene_stratified_experiments
from primevarclass.study import (
    build_gene_adaptive_blend_manifest,
    build_gene_calibrated_blend_manifest,
    build_gene_robust_blend_manifest,
    build_gene_specialist_manifest,
    evaluate_gene_adaptive_blend_on_cohort,
    evaluate_gene_calibrated_blend_on_cohort,
    evaluate_gene_specialist_on_cohort,
    train_gene_adaptive_blend_models,
    train_gene_calibrated_blend_models,
    train_gene_specialist_models,
)


class ParseVariantTests(unittest.TestCase):
    def test_parse_variant_accepts_valid_brca_missense(self):
        variant = parse_variant("BRCA1 p.Cys61Gly")
        self.assertEqual(variant.gene, "BRCA1")
        self.assertEqual(variant.aa_ref, "C")
        self.assertEqual(variant.position, 61)
        self.assertEqual(variant.aa_alt, "G")

    def test_parse_variant_accepts_valid_non_brca_missense(self):
        variant = parse_variant("TP53 p.Arg175His")
        self.assertEqual(variant.gene, "TP53")
        self.assertEqual(variant.aa_ref, "R")
        self.assertEqual(variant.position, 175)
        self.assertEqual(variant.aa_alt, "H")


class PrimeFeatureEncodingTests(unittest.TestCase):
    def test_encode_variant_features_adds_prime_topology_signals(self):
        variant = parse_variant("BRCA1 p.Cys61Gly")
        features = encode_variant_features(variant, mode="hybrid")

        self.assertIn("prime_gap_delta", features)
        self.assertIn("prime_curvature_score", features)
        self.assertIn("prime_mod_30_transition", features)
        self.assertIn("prime_twin_transition", features)
        self.assertIn("prime_sophie_transition", features)
        self.assertGreaterEqual(features["prime_gap_span_ref"], 0)
        self.assertGreaterEqual(features["prime_gap_span_alt"], 0)
        self.assertGreaterEqual(features["prime_curvature_score"], 0)


class DatasetBuilderTests(unittest.TestCase):
    def test_build_dataset_accepts_multigene_rows_by_default(self):
        raw = pd.DataFrame(
            [
                {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": "Pathogenic"},
                {"gene": "TP53", "hgvs_p": "p.Arg175His", "label": "Pathogenic"},
                {"gene": "BRCA2", "hgvs_p": "p.Lys3326Ter", "label": "Benign"},
                {"gene": "BRCA2", "hgvs_p": "p.Asp2723His", "label": "VUS"},
                {"gene": None, "hgvs_p": "p.Ile21Val", "label": "Benign"},
            ]
        )

        built, report = build_dataset_from_dataframe(raw, mode="hybrid", keep_metadata=True)

        self.assertEqual(len(built), 2)
        self.assertEqual(report.valid_rows, 2)
        self.assertEqual(set(built["gene"].astype(str)), {"BRCA1", "TP53"})
        self.assertEqual(report.excluded_invalid_gene, 0)
        self.assertEqual(report.excluded_non_missense, 1)
        self.assertEqual(report.excluded_invalid_label, 1)
        self.assertEqual(report.excluded_missing, 1)

    def test_build_dataset_can_apply_gene_allowlist(self):
        raw = pd.DataFrame(
            [
                {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": "Pathogenic"},
                {"gene": "TP53", "hgvs_p": "p.Arg175His", "label": "Pathogenic"},
            ]
        )

        built, report = build_dataset_from_dataframe(
            raw,
            mode="hybrid",
            keep_metadata=True,
            gene_allowlist=["TP53"],
        )

        self.assertEqual(len(built), 1)
        self.assertEqual(set(built["gene"].astype(str)), {"TP53"})
        self.assertEqual(report.excluded_invalid_gene, 1)


class TrainingTests(unittest.TestCase):
    def test_train_baseline_model_scales_cv_to_small_dataset(self):
        built, report = build_dataset_from_dataframe(dataset_schema_template(), mode="hybrid", keep_metadata=True)
        self.assertEqual(report.valid_rows, 4)

        _, metrics = train_baseline_model(built)

        self.assertEqual(metrics["cv_folds"], 2)
        self.assertEqual(metrics["model_family"], "random_forest")
        self.assertIn("auc_roc", metrics)
        self.assertIn("mcc", metrics)

    def test_train_baseline_model_supports_logistic_regression(self):
        built, report = build_dataset_from_dataframe(dataset_schema_template(), mode="hybrid", keep_metadata=True)
        self.assertEqual(report.valid_rows, 4)

        _, metrics = train_baseline_model(built, model_family="logistic_regression")

        self.assertEqual(metrics["cv_folds"], 2)
        self.assertEqual(metrics["model_family"], "logistic_regression")
        self.assertIn("auc_roc", metrics)

    def test_build_dataset_preserves_feature_prefixed_columns(self):
        raw = dataset_schema_template().copy()
        raw["feature_gnomad_af"] = [0.000002, 0.00012, 0.000004, 0.00009]
        raw["feature_mave_score"] = [-1.8, 0.4, -1.1, 0.35]
        raw["meta_dataset"] = ["study"] * len(raw)

        built, report = build_dataset_from_dataframe(raw, mode="hybrid", keep_metadata=True)

        self.assertEqual(report.valid_rows, 4)
        self.assertIn("feature_gnomad_af", built.columns)
        self.assertIn("feature_mave_score", built.columns)
        self.assertIn("meta_dataset", built.columns)

    def test_run_gene_stratified_experiments_discovers_dynamic_genes(self):
        raw = pd.DataFrame(
            [
                {"gene": "TP53", "hgvs_p": "p.Arg175His", "label": "Pathogenic"},
                {"gene": "TP53", "hgvs_p": "p.Arg248Gln", "label": "Pathogenic"},
                {"gene": "TP53", "hgvs_p": "p.Pro72Arg", "label": "Benign"},
                {"gene": "TP53", "hgvs_p": "p.Lys132Asn", "label": "Benign"},
                {"gene": "PTEN", "hgvs_p": "p.Cys124Ser", "label": "Pathogenic"},
                {"gene": "PTEN", "hgvs_p": "p.Gly129Glu", "label": "Pathogenic"},
                {"gene": "PTEN", "hgvs_p": "p.Lys13Arg", "label": "Benign"},
                {"gene": "PTEN", "hgvs_p": "p.Asp24Gly", "label": "Benign"},
            ]
        )

        built, report = build_dataset_from_dataframe(raw, mode="hybrid", keep_metadata=True)

        self.assertEqual(report.valid_rows, 8)
        mock_metrics = pd.DataFrame([{"experiment": "prime_only", "auc_roc": 0.8, "auc_pr": 0.7, "mcc": 0.4}])
        with patch("primevarclass.core.run_experiment_suite", return_value=(mock_metrics, {}, {}, {})) as mocked_suite:
            results = run_gene_stratified_experiments(built)

        self.assertEqual(set(results.keys()), {"TP53", "PTEN", "combined"})
        self.assertFalse(results["TP53"].empty)
        self.assertFalse(results["PTEN"].empty)
        evaluated_gene_sets = [set(call.args[0]["gene"].astype(str)) for call in mocked_suite.call_args_list]
        self.assertIn({"TP53"}, evaluated_gene_sets)
        self.assertIn({"PTEN"}, evaluated_gene_sets)
        self.assertIn({"TP53", "PTEN"}, evaluated_gene_sets)


class CalibrationTests(unittest.TestCase):
    def test_acmg_strength_mapping(self):
        self.assertEqual(classify_acmg_strength_from_lr(19.0), "PP3_strong")
        self.assertEqual(classify_acmg_strength_from_lr(4.5), "PP3_moderate")
        self.assertEqual(classify_acmg_strength_from_lr(0.2), "BP4_moderate")


class MultiSourceIngestionTests(unittest.TestCase):
    def test_ingestion_without_gene_allowlist_keeps_multigene_rows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"

            pd.DataFrame(
                [
                    {"gene": "TP53", "hgvs_p": "p.Arg175His", "label": "Pathogenic"},
                    {"gene": "PTEN", "hgvs_p": "p.Cys124Ser", "label": "Pathogenic"},
                    {"gene": "TP53", "hgvs_p": "p.Pro72Arg", "label": "Benign"},
                    {"gene": "PTEN", "hgvs_p": "p.Lys13Arg", "label": "Benign"},
                ]
            ).to_csv(cohort_path, index=False)

            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "multigene_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                    ]
                ),
                encoding="utf-8",
            )

            ingestion = ingest_sources_from_config(str(config_path), output_dir=None)
            integrated_df = ingestion["integrated_dataframe"]

            self.assertEqual(set(integrated_df["gene"].astype(str)), {"TP53", "PTEN"})
            self.assertEqual(len(integrated_df), 4)

    def test_ingestion_merges_cohort_and_annotation_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            sqlite_path = tmp_path / "annotations.sqlite"
            config_path = tmp_path / "sources.toml"

            cohort_df = dataset_schema_template().copy()
            cohort_df.to_csv(cohort_path, index=False)

            connection = sqlite3.connect(sqlite_path)
            try:
                pd.DataFrame(
                    [
                        {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "revel": 0.99, "bayesdel": 0.74},
                        {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "revel": 0.91, "bayesdel": 0.55},
                    ]
                ).to_sql("variant_annotations", connection, index=False, if_exists="replace")
            finally:
                connection.close()

            config_path.write_text(
                "\n".join(
                    [
                        "[ingestion]",
                        'deduplicate_on = ["gene", "hgvs_p", "label"]',
                        "",
                        "[[sources]]",
                        'name = "cohort_demo"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar"',
                        "",
                        "[[sources]]",
                        'name = "annotation_db"',
                        'kind = "annotation"',
                        'type = "sqlite"',
                        f'path = "{sqlite_path.as_posix()}"',
                        'query = "SELECT gene, hgvs_p, revel, bayesdel FROM variant_annotations"',
                        'join_on = ["gene", "hgvs_p"]',
                    ]
                ),
                encoding="utf-8",
            )

            ingestion = ingest_sources_from_config(str(config_path), output_dir=None)
            integrated_df = ingestion["integrated_dataframe"]

            self.assertEqual(len(integrated_df), 4)
            self.assertIn("revel", integrated_df.columns)
            brca1_row = integrated_df.loc[integrated_df["hgvs_p"] == "BRCA1 p.Cys61Gly"].iloc[0]
            self.assertAlmostEqual(float(brca1_row["revel"]), 0.99, places=6)

    def test_build_dataset_runs_from_source_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"

            dataset_schema_template().to_csv(cohort_path, index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "cohort_demo"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar"',
                    ]
                ),
                encoding="utf-8",
            )

            built_df, build_report, source_report = build_dataset_from_source_config(
                config_path=str(config_path),
                mode="hybrid",
                keep_metadata=True,
                high_confidence_only=False,
            )

            self.assertEqual(build_report.valid_rows, 4)
            self.assertEqual(len(built_df), 4)
            self.assertEqual(len(source_report), 1)

    def test_ingestion_writes_data_release_manifest_when_output_dir_is_set(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"
            output_dir = tmp_path / "ingestion_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "cohort_demo"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar"',
                    ]
                ),
                encoding="utf-8",
            )

            ingestion = ingest_sources_from_config(str(config_path), output_dir=str(output_dir))

            manifest_path = Path(ingestion["output_paths"]["data_release_manifest_path"])
            registry_path = Path(ingestion["output_paths"]["data_release_registry_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(registry_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["release_type"], "data_ingestion")
            self.assertEqual(manifest["n_rows"], 4)
            self.assertEqual(len(manifest["sources"]), 1)
            self.assertIn("integrated_dataset_fingerprint", manifest)
            self.assertIn("artifact_fingerprints", manifest)
            self.assertIn("provenance", manifest["sources"][0])
            self.assertIn("file_fingerprint", manifest["sources"][0]["provenance"])

    def test_public_brca_example_config_adds_real_like_external_features(self):
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_example.toml"

        built_df, build_report, source_report = build_dataset_from_source_config(
            config_path=str(config_path),
            mode="hybrid",
            keep_metadata=True,
            high_confidence_only=False,
        )

        self.assertEqual(build_report.valid_rows, 4)
        self.assertEqual(len(source_report), 3)
        self.assertIn("feature_gnomad_af", built_df.columns)
        self.assertIn("feature_mave_score", built_df.columns)
        self.assertIn("meta_mavedb_urn", built_df.columns)

    def test_ingestion_builds_public_source_assessment_and_exports_reports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            gnomad_path = tmp_path / "gnomad_brca_v4.1.tsv"
            mavedb_path = tmp_path / "mavedb_urn_mavedb_brca1_ring_2026-03-15.csv"
            enigma_path = tmp_path / "enigma_brca_2026-02-20.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "ingestion_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_pro": "p.Cys61Gly", "score": -1.8, "urn": "urn:mavedb:BRCA1-RING-2026"},
                    {"gene": "BRCA2", "hgvs_pro": "p.Gly2508Ser", "score": -1.1, "urn": "urn:mavedb:BRCA2-DBD-2026"},
                ]
            ).to_csv(mavedb_path, index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "protein_change": "p.Cys61Gly", "classification": "Pathogenic"},
                    {"gene": "BRCA2", "protein_change": "p.Gly2508Ser", "classification": "Likely pathogenic"},
                ]
            ).to_csv(enigma_path, sep="\t", index=False)

            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        "",
                        "[[sources]]",
                        'name = "mavedb_scores"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{mavedb_path.as_posix()}"',
                        'preset = "mavedb_score_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        "",
                        "[[sources]]",
                        'name = "enigma_labels"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{enigma_path.as_posix()}"',
                        'preset = "enigma_brca"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "2026.02"',
                        'release_date = "2026-02-20"',
                    ]
                ),
                encoding="utf-8",
            )

            ingestion = ingest_sources_from_config(str(config_path), output_dir=str(output_dir))

            assessment = ingestion["public_source_assessment"]
            sync_plan = ingestion["public_source_sync_plan"]
            self.assertEqual(assessment["summary"]["n_recognized_public_sources"], 4)
            self.assertGreaterEqual(assessment["summary"]["release_coverage_percent"], 75)
            self.assertGreaterEqual(assessment["summary"]["schema_coverage_percent"], 80)
            self.assertGreaterEqual(assessment["summary"]["overall_readiness_percent"], 80)
            self.assertTrue(assessment["summary"]["ready_for_public_benchmark"])
            self.assertTrue(Path(ingestion["output_paths"]["public_source_catalog_report_json"]).exists())
            self.assertTrue(Path(ingestion["output_paths"]["public_source_catalog_report_markdown"]).exists())
            self.assertTrue(Path(ingestion["output_paths"]["public_source_sync_plan_json"]).exists())
            self.assertTrue(Path(ingestion["output_paths"]["public_source_sync_plan_markdown"]).exists())
            self.assertEqual(sync_plan["summary"]["n_sync_candidates"], 4)
            self.assertGreaterEqual(sync_plan["summary"]["n_automatable_sources"], 2)
            self.assertTrue(any(item["profile_id"] == "enigma" and not item["can_auto_sync"] for item in sync_plan["sync_items"]))

            manifest_path = Path(ingestion["output_paths"]["data_release_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("public_source_assessment", manifest)
            self.assertIn("public_source_sync_plan", manifest)
            self.assertIn("public_source_catalog_report_json", manifest["artifact_fingerprints"])
            self.assertIn("public_source_sync_plan_json", manifest["artifact_fingerprints"])
            source_names = {item["source_name"] for item in assessment["sources"]}
            self.assertEqual(source_names, {"clinvar_main", "gnomad_annotations", "mavedb_scores", "enigma_labels"})
            self.assertTrue(all(item["schema_coverage_percent"] >= 80 for item in assessment["sources"]))

    def test_export_independent_data_expansion_package_builds_registry_and_templates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exported = export_independent_data_expansion_package(
                output_dir=tmp_dir,
                target_genes=["BRCA1", "TP53", "KRAS"],
            )

            manifest_path = Path(exported["independent_data_expansion_manifest_path"])
            registry_path = Path(exported["independent_public_database_registry_path"])
            plan_path = Path(exported["independent_training_validation_plan_path"])
            template_path = Path(exported["independent_source_templates_path"])

            self.assertTrue(manifest_path.exists())
            self.assertTrue(registry_path.exists())
            self.assertTrue(plan_path.exists())
            self.assertTrue(template_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            registry = pd.read_csv(registry_path)
            template_text = template_path.read_text(encoding="utf-8")

            self.assertGreaterEqual(manifest["summary"]["database_count"], 14)
            self.assertGreaterEqual(manifest["summary"]["supported_preset_count"], 14)
            self.assertTrue(manifest["summary"]["ready_for_more_real_data_training"])
            self.assertIn("ClinGen Evidence Repository", set(registry["display_name"]))
            self.assertIn("cBioPortal Datahub", set(registry["display_name"]))
            self.assertIn("AlphaMissense", set(registry["display_name"]))
            self.assertIn('preset = "clingen_erepo_table"', template_text)
            self.assertIn('preset = "alphamissense_table"', template_text)

    def test_export_independent_data_staging_closure_package_audits_local_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clinvar_dir = tmp_path / "data" / "raw" / "clinvar"
            gnomad_dir = tmp_path / "data" / "raw" / "gnomad"
            mavedb_dir = tmp_path / "data" / "raw" / "mavedb"
            brca_exchange_dir = tmp_path / "data" / "raw" / "brca_exchange"
            for directory in [clinvar_dir, gnomad_dir, mavedb_dir, brca_exchange_dir]:
                directory.mkdir(parents=True, exist_ok=True)

            clinvar_dir.joinpath("variant_summary.txt").write_text(
                "GeneSymbol\tName\tClinicalSignificance\n" + ("BRCA1\tp.Cys61Gly\tPathogenic\n" * 40),
                encoding="utf-8",
            )
            gnomad_dir.joinpath("brca_missense_annotations.tsv").write_text(
                "gene\thgvs_p\taf\n" + ("BRCA1\tp.Cys61Gly\t0.000001\n" * 40),
                encoding="utf-8",
            )
            gnomad_dir.joinpath("gnomad_gene_subset_variants.tsv").write_text(
                "gene\tvariant_id\tAF\n" + ("TP53\t17-1-A-G\t0.0\n" * 20) + ("PTEN\t10-1-A-G\t0.0\n" * 20),
                encoding="utf-8",
            )
            mavedb_dir.joinpath("brca_function_scores.csv").write_text(
                "gene,hgvs_p,score\n" + ("BRCA1,p.Cys61Gly,-1.2\n" * 40),
                encoding="utf-8",
            )
            brca_exchange_dir.joinpath("enigma_brca_curated.tsv").write_text(
                "gene\thgvs_p\tlabel\n" + ("BRCA1\tp.Cys61Gly\tPathogenic\n" * 40),
                encoding="utf-8",
            )

            expansion = export_independent_data_expansion_package(
                output_dir=str(tmp_path / "expansion"),
                target_genes=["BRCA1", "BRCA2", "TP53", "PTEN"],
            )
            exported = export_independent_data_staging_closure_package(
                output_dir=str(tmp_path / "closure"),
                independent_data_expansion_manifest_path=expansion["independent_data_expansion_manifest_path"],
                workspace_root=tmp_path,
                target_genes=["BRCA1", "BRCA2", "TP53", "PTEN"],
            )

            manifest_path = Path(exported["independent_data_staging_closure_manifest_path"])
            inventory_path = Path(exported["independent_data_staging_inventory_path"])
            gap_plan_path = Path(exported["independent_data_staging_gap_plan_path"])
            ready_config_path = Path(exported["independent_ready_source_config_path"])

            self.assertTrue(manifest_path.exists())
            self.assertTrue(inventory_path.exists())
            self.assertTrue(gap_plan_path.exists())
            self.assertTrue(ready_config_path.exists())
            self.assertTrue(exported["summary"]["ready_for_next_training_round"])
            self.assertGreater(exported["summary"]["line_level_real_data_execution_percent"], 0)
            self.assertGreaterEqual(exported["summary"]["ready_source_count"], 2)
            inventory = pd.read_csv(inventory_path)
            gnomad_row = inventory[inventory["source_id"] == "gnomad"].iloc[0]
            self.assertEqual(int(gnomad_row["gene_coverage_percent"]), 100)
            self.assertIn('name = "clinvar_local_staged"', ready_config_path.read_text(encoding="utf-8"))

    def test_export_independent_open_source_autostage_package_builds_public_tables(self):
        def fake_download(url, path, timeout_sec=120):
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("gene\thgvs_p\tclassification\n" + ("BRCA1\tp.Cys61Gly\tPathogenic\n" * 40), encoding="utf-8")
            return {"path": str(path), "size_bytes": path.stat().st_size, "url": url}

        def fake_http_json(url, method="GET", payload=None, timeout_sec=20, headers=None):
            if "uniprot" in url:
                return {
                    "primaryAccession": "P38398",
                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                    "sequence": {"length": 1863},
                    "features": [{"type": "Domain"}],
                    "comments": [{"type": "DISEASE"}],
                    "keywords": [{"name": "DNA repair"}],
                }
            if "alphafold" in url:
                return [{"cifUrl": "https://alphafold/model.cif", "paeDocUrl": "https://alphafold/pae.json", "confidenceScore": 91, "uniprotStart": 1, "uniprotEnd": 1863}]
            if "search.rcsb.org" in url:
                return {"result_set": [{"identifier": "1ABC"}]}
            if "data.rcsb.org" in url:
                return {"experimental_method": ["X-RAY DIFFRACTION"], "rcsb_entry_info": {"resolution_combined": [2.1], "polymer_entity_count": 2, "nonpolymer_entity_count": 1}}
            if "civicdb" in url:
                return {"data": {"genes": {"nodes": [{"id": 6, "name": "BRCA1", "description": "Curated gene", "variants": {"totalCount": 65}}]}}}
            if "cbioportal" in url:
                return [{"proteinChange": "E9Q", "mutationType": "Missense_Mutation", "sampleId": "S1", "studyId": "brca", "keyword": "BRCA1 E9 missense"}]
            if "gdc.cancer.gov" in url:
                return {"data": {"gene_id": "ENSG00000012048", "symbol": "BRCA1", "name": "BRCA1 DNA repair associated", "biotype": "protein_coding"}}
            if "gwas" in url:
                return {"_embedded": {"associations": [{"snp_allele": [{"rs_id": "rs1"}], "p_value": 1e-9, "beta": "0.1", "efo_traits": [{"efo_trait": "breast cancer"}], "accession_id": "GCST1", "pubmed_id": "1"}]}}
            if "opentargets" in url:
                return {"data": {"target": {"id": "ENSG00000012048", "approvedSymbol": "BRCA1", "associatedDiseases": {"count": 1, "rows": [{"score": 0.8, "disease": {"id": "EFO_1", "name": "breast carcinoma"}}]}}}}
            if "pharmgkb" in url:
                return {"data": [{"id": "PA25411", "symbol": "BRCA1", "name": "BRCA1 DNA repair associated", "vipTier": "Cancer Genome", "alleleType": "None", "cpicGene": False}]}
            return {}

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("primevarclass.independent_public_autostager._download_file", side_effect=fake_download), patch(
                "primevarclass.independent_public_autostager._http_json", side_effect=fake_http_json
            ):
                exported = export_independent_open_source_autostage_package(
                    output_dir=str(Path(tmp_dir) / "autostage"),
                    workspace_root=tmp_dir,
                    target_genes=["BRCA1"],
                )

            self.assertEqual(exported["summary"]["attempted_source_count"], 10)
            self.assertEqual(exported["summary"]["staged_source_count"], 10)
            self.assertTrue(Path(exported["independent_open_source_autostage_manifest_path"]).exists())
            self.assertTrue((Path(tmp_dir) / "data/raw/uniprot/target_gene_features.tsv").exists())
            self.assertTrue((Path(tmp_dir) / "data/raw/opentargets/target_disease_associations.tsv").exists())

    def test_expanded_public_source_presets_normalize_independent_sources(self):
        clingen = apply_source_preset(
            pd.DataFrame(
                [
                    {
                        "Gene": "TP53",
                        "HGVS": "p.Arg175His",
                        "Classification": "Pathogenic",
                        "CAID": "CA123",
                        "Expert Panel": "TP53 VCEP",
                    }
                ]
            ),
            "clingen_erepo_table",
        )
        alphamissense = apply_source_preset(
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "protein_variant": "C61G",
                        "am_pathogenicity": 0.93,
                        "am_class": "likely_pathogenic",
                    }
                ]
            ),
            "alphamissense_table",
        )

        self.assertEqual(clingen.loc[0, "gene"], "TP53")
        self.assertEqual(clingen.loc[0, "hgvs_p"], "TP53 p.Arg175His")
        self.assertEqual(alphamissense.loc[0, "hgvs_p"], "BRCA1 p.C61G")
        self.assertIn("feature_alphamissense_pathogenicity", alphamissense.columns)

    def test_export_continuous_learning_package_builds_runner_and_policy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            gnomad_path = tmp_path / "gnomad_brca_v4.1.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "continuous_learning"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "v4.1"',
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_continuous_learning_package(
                config_path=str(config_path),
                output_dir=str(output_dir),
            )

            self.assertTrue(Path(exported["continuous_learning_manifest_path"]).exists())
            self.assertTrue(Path(exported["continuous_learning_report_markdown_path"]).exists())
            self.assertTrue(Path(exported["continuous_learning_runner_path"]).exists())
            manifest = json.loads(Path(exported["continuous_learning_manifest_path"]).read_text(encoding="utf-8"))
            connector_catalog = pd.read_csv(exported["continuous_learning_connector_catalog_path"])
            runner_text = Path(exported["continuous_learning_runner_path"]).read_text(encoding="utf-8")

            self.assertGreaterEqual(manifest["summary"]["configured_public_source_count"], 2)
            self.assertGreaterEqual(manifest["summary"]["script_ready_source_count"], 1)
            self.assertIn("AlphaFold DB", set(connector_catalog["display_name"]))
            self.assertIn("export_public_source_resolution", runner_text)
            self.assertIn("train_from_source_config", runner_text)

    def test_http_post_source_can_feed_annotation_preset(self):
        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body)
                if payload.get("text") != "BRCA1":
                    self.send_response(400)
                    self.end_headers()
                    return

                response = [
                    {
                        "gene": "BRCA1",
                        "hgvs_pro": "p.Cys61Gly",
                        "score": -1.9,
                        "annotation": "loss_of_function",
                        "urn": "urn:mavedb:BRCA1-RING-HTTP",
                    }
                ]
                encoded = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format, *args):
                return

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"

            dataset_schema_template().to_csv(cohort_path, index=False)

            server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config_path.write_text(
                    "\n".join(
                        [
                            "[[sources]]",
                            'name = "cohort_demo"',
                            'kind = "cohort"',
                            'type = "file"',
                            'format = "csv"',
                            f'path = "{cohort_path.as_posix()}"',
                            'preset = "clinvar"',
                            "",
                            "[[sources]]",
                            'name = "mavedb_http"',
                            'kind = "annotation"',
                            'type = "http"',
                            'format = "json"',
                            f'url = "http://127.0.0.1:{server.server_port}/scores"',
                            'http_method = "POST"',
                            'preset = "mavedb_score_table"',
                            'join_on = ["gene", "hgvs_p"]',
                            'body_json = { text = "BRCA1" }',
                        ]
                    ),
                    encoding="utf-8",
                )

                built_df, build_report, _ = build_dataset_from_source_config(
                    config_path=str(config_path),
                    mode="hybrid",
                    keep_metadata=True,
                    high_confidence_only=False,
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual(build_report.valid_rows, 4)
            self.assertIn("feature_mave_score", built_df.columns)
            brca1_row = built_df.loc[built_df["variant"] == "BRCA1 p.C61G"].iloc[0]
            self.assertAlmostEqual(float(brca1_row["feature_mave_score"]), -1.9, places=6)

    def test_ingestion_manifest_tracks_multisource_provenance(self):
        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                response = [
                    {
                        "gene": "BRCA1",
                        "hgvs_pro": "p.Cys61Gly",
                        "score": -1.7,
                        "annotation": "functional_impact",
                        "urn": "urn:mavedb:BRCA1-RING-GET",
                    }
                ]
                encoded = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("ETag", '"demo-etag"')
                self.send_header("Last-Modified", "Wed, 01 Apr 2026 10:00:00 GMT")
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format, *args):
                return

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            sqlite_path = tmp_path / "annotations.sqlite"
            config_path = tmp_path / "sources.toml"
            output_dir = tmp_path / "ingestion_output"

            dataset_schema_template().to_csv(cohort_path, index=False)

            connection = sqlite3.connect(sqlite_path)
            try:
                pd.DataFrame(
                    [
                        {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "revel": 0.99},
                        {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "revel": 0.91},
                    ]
                ).to_sql("variant_annotations", connection, index=False, if_exists="replace")
            finally:
                connection.close()

            server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config_path.write_text(
                    "\n".join(
                        [
                            "[[sources]]",
                            'name = "cohort_demo"',
                            'kind = "cohort"',
                            'type = "file"',
                            'format = "csv"',
                            f'path = "{cohort_path.as_posix()}"',
                            'preset = "clinvar"',
                            "",
                            "[[sources]]",
                            'name = "annotation_db"',
                            'kind = "annotation"',
                            'type = "sqlite"',
                            f'path = "{sqlite_path.as_posix()}"',
                            'query = "SELECT gene, hgvs_p, revel FROM variant_annotations"',
                            'join_on = ["gene", "hgvs_p"]',
                            "",
                            "[[sources]]",
                            'name = "mavedb_http"',
                            'kind = "annotation"',
                            'type = "http"',
                            'format = "json"',
                            f'url = "http://127.0.0.1:{server.server_port}/scores"',
                            'preset = "mavedb_score_table"',
                            'join_on = ["gene", "hgvs_p"]',
                        ]
                    ),
                    encoding="utf-8",
                )

                ingestion = ingest_sources_from_config(str(config_path), output_dir=str(output_dir))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            manifest_path = Path(ingestion["output_paths"]["data_release_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            by_name = {row["name"]: row for row in manifest["sources"]}

            cohort_source = by_name["cohort_demo"]
            self.assertEqual(cohort_source["provenance"]["file_fingerprint"]["path"], str(cohort_path.resolve()))
            self.assertTrue(cohort_source["provenance"]["file_fingerprint"]["sha256"])

            sqlite_source = by_name["annotation_db"]["provenance"]["sqlite"]
            self.assertIn("variant_annotations", sqlite_source["tables"])
            self.assertEqual(sqlite_source["row_count_raw"], 2)
            self.assertTrue(sqlite_source["database_fingerprint"]["sha256"])

            http_source = by_name["mavedb_http"]["provenance"]["http"]
            self.assertEqual(http_source["response"]["status_code"], 200)
            self.assertEqual(http_source["response"]["etag"], '"demo-etag"')
            self.assertTrue(http_source["response"]["payload_sha256"])

            self.assertIn("integrated_sources", manifest["artifact_fingerprints"])
            self.assertIn("source_ingestion_report", manifest["artifact_fingerprints"])
            self.assertTrue(manifest["integrated_dataset_fingerprint"]["sha256_csv"])
class RealDataPreparationTests(unittest.TestCase):
    def test_export_real_data_preparation_bundle_generates_real_artifacts_and_configs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            workspace_root = tmp_path / "workspace"
            output_dir = tmp_path / "preparation_output"
            workspace_root.mkdir(parents=True, exist_ok=True)

            clinvar_path = tmp_path / "variant_summary.txt.gz"
            brca_release_path = tmp_path / "release-01-05-26.tar.gz"
            mavedb_dump_path = tmp_path / "mavedb_dump.zip"

            pd.DataFrame(
                [
                    {
                        "GeneSymbol": "BRCA1",
                        "Protein change": "p.Cys61Gly",
                        "ClinicalSignificance": "Pathogenic",
                        "ReviewStatus": "reviewed by expert panel",
                        "VariationID": "17657",
                        "Name": "NM_007294.4(BRCA1):c.181T>G (p.Cys61Gly)",
                        "LastEvaluated": "Jan 05, 2026",
                    },
                    {
                        "GeneSymbol": "BRCA2",
                        "Protein change": "p.Asn372His",
                        "ClinicalSignificance": "Benign",
                        "ReviewStatus": "reviewed by expert panel",
                        "VariationID": "9329",
                        "Name": "NM_000059.4(BRCA2):c.1114A>C (p.Asn372His)",
                        "LastEvaluated": "Jan 12, 2015",
                    },
                    {
                        "GeneSymbol": "BRCA1",
                        "Protein change": "p.Met18Thr",
                        "ClinicalSignificance": "Likely benign",
                        "ReviewStatus": "criteria provided, multiple submitters, no conflicts",
                        "VariationID": "99991",
                        "Name": "NM_007294.4(BRCA1):c.53T>C (p.Met18Thr)",
                        "LastEvaluated": "Feb 02, 2024",
                    },
                    {
                        "GeneSymbol": "BRCA2",
                        "Protein change": "p.Gly4Ala",
                        "ClinicalSignificance": "Likely benign",
                        "ReviewStatus": "criteria provided, multiple submitters, no conflicts",
                        "VariationID": "99992",
                        "Name": "NM_000059.4(BRCA2):c.11G>C (p.Gly4Ala)",
                        "LastEvaluated": "Mar 15, 2024",
                    },
                ]
            ).to_csv(clinvar_path, sep="\t", index=False, compression="gzip")

            variants_output = pd.DataFrame(
                [
                    {
                        "gene_symbol": "BRCA1",
                        "protein": "p.Cys61Gly",
                        "source": "LOVD",
                        "classification_lovd": "Pathogenic",
                        "clinical_significance_enigma": "Pathogenic",
                        "ca_id": "CA000001",
                        "HGVS_protein_LOVD": "NP_009225.1:p.(Cys61Gly)",
                        "allele_frequency_genome_gnomadv3": "",
                        "allele_count_genome_gnomadv3": "",
                        "allele_number_genome_gnomadv3": "",
                        "faf95_popmax_genome_gnomadv3": "",
                    },
                    {
                        "gene_symbol": "BRCA2",
                        "protein": "p.Pro2Ser",
                        "source": "LOVD",
                        "classification_lovd": "Benign",
                        "clinical_significance_enigma": "",
                        "ca_id": "CA000002",
                        "HGVS_protein_LOVD": "NP_000050.3:p.(Pro2Ser)",
                        "allele_frequency_genome_gnomadv3": "0.000004223",
                        "allele_count_genome_gnomadv3": "1",
                        "allele_number_genome_gnomadv3": "236824",
                        "faf95_popmax_genome_gnomadv3": "",
                    },
                    {
                        "gene_symbol": "BRCA1",
                        "protein": "p.Met18Thr",
                        "source": "LOVD",
                        "classification_lovd": "Benign",
                        "clinical_significance_enigma": "",
                        "ca_id": "CA000002B",
                        "HGVS_protein_LOVD": "NP_009225.1:p.(Met18Thr)",
                        "allele_frequency_genome_gnomadv3": "",
                        "allele_count_genome_gnomadv3": "",
                        "allele_number_genome_gnomadv3": "",
                        "faf95_popmax_genome_gnomadv3": "",
                    },
                    {
                        "gene_symbol": "BRCA2",
                        "protein": "p.Gly4Ala",
                        "source": "LOVD",
                        "classification_lovd": "Likely benign",
                        "clinical_significance_enigma": "",
                        "ca_id": "CA000003",
                        "HGVS_protein_LOVD": "NP_000050.3:p.(Gly4Ala)",
                        "allele_frequency_genome_gnomadv3": "",
                        "allele_count_genome_gnomadv3": "",
                        "allele_number_genome_gnomadv3": "",
                        "faf95_popmax_genome_gnomadv3": "",
                    },
                    {
                        "gene_symbol": "BRCA2",
                        "protein": "p.Asp1902Asn",
                        "source": "ENIGMA",
                        "classification_lovd": "",
                        "clinical_significance_enigma": "Benign",
                        "ca_id": "CA023014",
                        "HGVS_protein_ENIGMA": "NP_000050.2:p.(Asp1902Asn)",
                        "allele_frequency_genome_gnomadv3": "0.000002100",
                        "allele_count_genome_gnomadv3": "1",
                        "allele_number_genome_gnomadv3": "476000",
                        "faf95_popmax_genome_gnomadv3": "0.000002100",
                    },
                ]
            )
            variants_output_path = tmp_path / "variants_output.tsv"
            variants_output.to_csv(variants_output_path, sep="\t", index=False)
            with tarfile.open(brca_release_path, "w:gz") as archive:
                archive.add(variants_output_path, arcname="output/variants_output.tsv")

            mavedb_main = {
                "experimentSets": [
                    {
                        "urn": "urn:mavedb:00000003",
                        "experiments": [
                            {
                                "title": "BRCA1 Y2H",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000003-b-2",
                                        "title": "BRCA1 Y2H",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "BRCA1"}],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "urn": "urn:mavedb:00001224",
                        "experiments": [
                            {
                                "title": "BRCA2 DNA binding domain",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00001224-a-1",
                                        "title": "BRCA2 DNA binding domain",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "BRCA2"}],
                                    }
                                ],
                            }
                        ],
                    },
                ]
            }
            brca1_scores = pd.DataFrame(
                [
                    {"hgvs_pro": "p.Cys61Gly", "score": -2.5, "score_se": 0.1},
                    {"hgvs_pro": "p.Cys64Gly", "score": -1.2, "score_se": 0.2},
                ]
            )
            brca2_scores = pd.DataFrame(
                [
                    {"hgvs_pro": "p.Pro2Ser", "score": 0.4, "score_se": 0.05},
                ]
            )
            with zipfile.ZipFile(mavedb_dump_path, "w") as archive:
                archive.writestr("main.json", json.dumps(mavedb_main))
                archive.writestr("csv/urn-mavedb-00000003-b-2.scores.csv", brca1_scores.to_csv(index=False))
                archive.writestr("csv/urn-mavedb-00001224-a-1.scores.csv", brca2_scores.to_csv(index=False))

            gnomad_payloads = [
                {
                    "data": {
                        "gene": {
                            "variants": [
                                {
                                    "variant_id": "17-43045682-T-C",
                                    "hgvsp": "p.Cys61Gly",
                                    "transcript_consequence": {
                                        "gene_symbol": "BRCA1",
                                        "hgvsp": "p.Cys61Gly",
                                        "major_consequence": "missense_variant",
                                        "is_canonical": True,
                                        "transcript_id": "ENST00000357654",
                                    },
                                    "exome": {
                                        "ac": 2,
                                        "an": 100000,
                                        "af": 0.00002,
                                        "populations": [{"id": "sas", "ac": 2, "an": 10000}],
                                    },
                                    "genome": None,
                                    "joint": {"ac": 2, "an": 110000, "fafmax": {"faf95_max": 0.000018}},
                                },
                                {
                                    "variant_id": "17-43050000-A-G",
                                    "hgvsp": "p.Gly10Gly",
                                    "transcript_consequence": {
                                        "gene_symbol": "BRCA1",
                                        "hgvsp": "p.Gly10Gly",
                                        "major_consequence": "synonymous_variant",
                                        "is_canonical": True,
                                        "transcript_id": "ENST00000357654",
                                    },
                                    "exome": {"ac": 1, "an": 100000, "af": 0.00001, "populations": []},
                                    "genome": None,
                                    "joint": {"ac": 1, "an": 110000, "fafmax": {"faf95_max": 0.000009}},
                                },
                            ]
                        }
                    }
                },
                {
                    "data": {
                        "gene": {
                            "variants": [
                                {
                                    "variant_id": "13-32310000-C-T",
                                    "hgvsp": "p.Pro2Ser",
                                    "transcript_consequence": {
                                        "gene_symbol": "BRCA2",
                                        "hgvsp": "p.Pro2Ser",
                                        "major_consequence": "missense_variant",
                                        "is_canonical": True,
                                        "transcript_id": "ENST00000380152",
                                    },
                                    "exome": {
                                        "ac": 1,
                                        "an": 50000,
                                        "af": 0.00002,
                                        "populations": [{"id": "afr", "ac": 1, "an": 20000}],
                                    },
                                    "genome": None,
                                    "joint": {"ac": 1, "an": 60000, "fafmax": {"faf95_max": 0.000016}},
                                },
                                {
                                    "variant_id": "13-32310010-G-C",
                                    "hgvsp": "p.Gly4Ala",
                                    "transcript_consequence": {
                                        "gene_symbol": "BRCA2",
                                        "hgvsp": "p.Gly4Ala",
                                        "major_consequence": "missense_variant",
                                        "is_canonical": True,
                                        "transcript_id": "ENST00000380152",
                                    },
                                    "exome": None,
                                    "genome": {
                                        "ac": 3,
                                        "an": 80000,
                                        "af": 0.0000375,
                                        "populations": [{"id": "nfe", "ac": 3, "an": 40000}],
                                    },
                                    "joint": {"ac": 3, "an": 80000, "fafmax": {"faf95_max": 0.00003}},
                                },
                            ]
                        }
                    }
                },
            ]

            with patch("primevarclass.real_data_preparation._gnomad_graphql_post", side_effect=gnomad_payloads), patch(
                "primevarclass.real_data_preparation.time.sleep", return_value=None
            ):
                results = export_real_data_preparation_bundle(
                    clinvar_variant_summary_path=str(clinvar_path),
                    brca_exchange_release_path=str(brca_release_path),
                    mavedb_dump_path=str(mavedb_dump_path),
                    output_dir=str(output_dir),
                    workspace_root=str(workspace_root),
                )

            manifest_path = Path(results["real_data_preparation_manifest_path"])
            report_path = Path(results["real_data_preparation_report_markdown_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(report_path.exists())

            artifact_paths = {key: Path(value) for key, value in results["artifact_paths"].items()}
            config_paths = {key: Path(value) for key, value in results["config_paths"].items()}
            for path in list(artifact_paths.values()) + list(config_paths.values()):
                self.assertTrue(path.exists())

            training_df = pd.read_csv(artifact_paths["training_table"], sep="\t")
            clinvar_expert_df = pd.read_csv(artifact_paths["clinvar_expert_table"], sep="\t")
            clinvar_expert_brca1_df = pd.read_csv(artifact_paths["clinvar_expert_brca1_table"], sep="\t")
            clinvar_expert_brca2_df = pd.read_csv(artifact_paths["clinvar_expert_brca2_table"], sep="\t")
            external_df = pd.read_csv(artifact_paths["external_table"], sep="\t")
            external_brca1_df = pd.read_csv(artifact_paths["external_brca1_table"], sep="\t")
            external_brca2_df = pd.read_csv(artifact_paths["external_brca2_table"], sep="\t")
            enigma_df = pd.read_csv(artifact_paths["enigma_table"], sep="\t")
            gnomad_df = pd.read_csv(artifact_paths["gnomad_table"], sep="\t")
            mavedb_df = pd.read_csv(artifact_paths["mavedb_table"])

            self.assertEqual(len(training_df), 2)
            self.assertEqual(len(clinvar_expert_df), 2)
            self.assertEqual(len(clinvar_expert_brca1_df), 1)
            self.assertEqual(len(clinvar_expert_brca2_df), 1)
            self.assertEqual(len(external_df), 2)
            self.assertEqual(len(external_brca1_df), 1)
            self.assertEqual(len(external_brca2_df), 1)
            self.assertEqual(len(enigma_df), 2)
            self.assertEqual(len(gnomad_df), 3)
            self.assertEqual(len(mavedb_df), 3)
            self.assertTrue((external_df["Protein change"] == "p.Cys61Gly").any())
            self.assertFalse((training_df["Protein change"] == "p.Cys61Gly").any())
            self.assertTrue((clinvar_expert_df["Protein change"] == "p.Cys61Gly").any())

            benchmark_config = config_paths["benchmark_config"]
            benchmark_text = benchmark_config.read_text(encoding="utf-8")
            self.assertIn("configs/public_brca_real.toml", benchmark_text)
            self.assertIn("configs/public_brca_external_real_clinvar_expert_brca1.toml", benchmark_text)
            self.assertIn("configs/public_brca_external_real_clinvar_expert_brca2.toml", benchmark_text)
            self.assertIn("configs/public_brca_external_real_brca1.toml", benchmark_text)
            self.assertIn("configs/public_brca_external_real_brca2.toml", benchmark_text)

            original_cwd = Path.cwd()
            try:
                os.chdir(workspace_root)
                built_df, build_report, source_report = build_dataset_from_source_config(
                    config_path=str(config_paths["training_config"]),
                    mode="hybrid",
                    keep_metadata=True,
                    high_confidence_only=False,
                )
                self.assertEqual(build_report.valid_rows, 2)
                self.assertEqual(len(source_report), 3)
                self.assertIn("feature_gnomad_af", built_df.columns)
                self.assertIn("feature_mave_score", built_df.columns)

                study = load_study_design(str(benchmark_config))
                self.assertEqual(study.name, "Public BRCA Benchmark Real Data")
                self.assertEqual(len(study.cohorts), 5)
            finally:
                os.chdir(original_cwd)


class ScientificDiscoveryTests(unittest.TestCase):
    def test_export_gene_expansion_assessment_ranks_non_brca_candidates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clinvar_path = tmp_path / "variant_summary.txt.gz"
            mavedb_dump_path = tmp_path / "mavedb_dump.zip"

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Met18Thr", "ClinicalSignificance": "Likely benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg175His", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg248Gln", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg273His", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Pro72Arg", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "KRAS", "Protein change": "p.Gly12Asp", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "KRAS", "Protein change": "p.Gly13Asp", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter"},
                ]
            ).to_csv(clinvar_path, sep="\t", index=False, compression="gzip")

            mavedb_main = {
                "experimentSets": [
                    {
                        "experiments": [
                            {
                                "title": "TP53 deep mutational scan",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000011-a-1",
                                        "title": "TP53 score set 1",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "TP53"}],
                                    },
                                    {
                                        "urn": "urn:mavedb:00000011-a-2",
                                        "title": "TP53 score set 2",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "TP53"}],
                                    },
                                ],
                            },
                            {
                                "title": "KRAS saturation assay",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000012-a-1",
                                        "title": "KRAS score set 1",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "KRAS"}],
                                    }
                                ],
                            },
                            {
                                "title": "BRCA1 control assay",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000013-a-1",
                                        "title": "BRCA1 score set 1",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "BRCA1"}],
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
            with zipfile.ZipFile(mavedb_dump_path, "w") as archive:
                archive.writestr("main.json", json.dumps(mavedb_main))
                archive.writestr(
                    "csv/urn-mavedb-00000011-a-1.scores.csv",
                    pd.DataFrame(
                        [
                            {"hgvs_pro": "p.Arg175His", "score": -2.1},
                            {"hgvs_pro": "p.Arg248Gln", "score": -1.9},
                            {"hgvs_pro": "p.Pro72Arg", "score": 0.8},
                        ]
                    ).to_csv(index=False),
                )
                archive.writestr(
                    "csv/urn-mavedb-00000011-a-2.scores.csv",
                    pd.DataFrame(
                        [
                            {"hgvs_pro": "p.Arg273His", "score": -1.8},
                            {"hgvs_pro": "p.Pro72Arg", "score": 0.9},
                        ]
                    ).to_csv(index=False),
                )
                archive.writestr(
                    "csv/urn-mavedb-00000012-a-1.scores.csv",
                    pd.DataFrame(
                        [
                            {"hgvs_pro": "p.Gly12Asp", "score": -2.4},
                            {"hgvs_pro": "p.Gly13Asp", "score": -2.1},
                        ]
                    ).to_csv(index=False),
                )
                archive.writestr(
                    "csv/urn-mavedb-00000013-a-1.scores.csv",
                    pd.DataFrame([{"hgvs_pro": "p.Cys61Gly", "score": -2.7}]).to_csv(index=False),
                )

            results = export_gene_expansion_assessment(
                clinvar_variant_summary_path=str(clinvar_path),
                mavedb_dump_path=str(mavedb_dump_path),
                output_dir=str(tmp_path / "gene_expansion"),
            )

            manifest = json.loads(Path(results["gene_expansion_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["summary"]["overlap_gene_count"], 2)
            self.assertEqual(manifest["summary"]["top_candidate_genes"][0], "TP53")
            self.assertIn("KRAS", manifest["summary"]["top_candidate_genes"])
            self.assertTrue(Path(results["gene_expansion_panel_template_path"]).exists())

    def test_export_biological_discovery_package_generates_hotspots_and_hypotheses(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            artifact_root = tmp_path / "artifacts"
            artifact_root.mkdir(parents=True, exist_ok=True)

            training_path = artifact_root / "training.tsv"
            clinvar_expert_path = artifact_root / "clinvar_expert.tsv"
            external_path = artifact_root / "external.tsv"
            enigma_path = artifact_root / "enigma.tsv"
            gnomad_path = artifact_root / "gnomad.tsv"
            mavedb_path = artifact_root / "mavedb.csv"
            manifest_path = artifact_root / "real_data_preparation_manifest.json"

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys10Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "1", "Name": "BRCA1 p.Cys10Gly"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys20Arg", "ClinicalSignificance": "Likely pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "2", "Name": "BRCA1 p.Cys20Arg"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys30Tyr", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "3", "Name": "BRCA1 p.Cys30Tyr"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys40Phe", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "4", "Name": "BRCA1 p.Cys40Phe"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Met80Thr", "ClinicalSignificance": "Likely benign", "ReviewStatus": "criteria provided, single submitter", "VariationID": "5", "Name": "BRCA1 p.Met80Thr"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Ile90Val", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "6", "Name": "BRCA1 p.Ile90Val"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Leu100Pro", "ClinicalSignificance": "Likely benign", "ReviewStatus": "criteria provided, single submitter", "VariationID": "7", "Name": "BRCA1 p.Leu100Pro"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Val110Ala", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "8", "Name": "BRCA1 p.Val110Ala"},
                ]
            ).to_csv(training_path, sep="\t", index=False)

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel", "VariationID": "9", "Name": "BRCA1 p.Cys61Gly"}
                ]
            ).to_csv(clinvar_expert_path, sep="\t", index=False)

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "BRCA Exchange / LOVD external curated release 2026-01-05", "VariationID": "10", "Name": "BRCA1 p.Cys61Gly"}
                ]
            ).to_csv(external_path, sep="\t", index=False)

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Asp1902Asn", "ClinicalSignificance": "Benign", "ReviewStatus": "ENIGMA curated", "VariationID": "11", "Name": "BRCA1 p.Asp1902Asn"}
                ]
            ).to_csv(enigma_path, sep="\t", index=False)

            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys10Gly", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys20Arg", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys30Tyr", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys40Phe", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys35Trp", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Met80Thr", "af": 0.00002, "ac": 2, "an": 100000, "popmax_af": 0.00002},
                    {"gene": "BRCA1", "hgvs_p": "p.Ile90Val", "af": 0.00003, "ac": 3, "an": 100000, "popmax_af": 0.00003},
                    {"gene": "BRCA1", "hgvs_p": "p.Leu100Pro", "af": 0.00004, "ac": 4, "an": 100000, "popmax_af": 0.00004},
                    {"gene": "BRCA1", "hgvs_p": "p.Val110Ala", "af": 0.00005, "ac": 5, "an": 100000, "popmax_af": 0.00005},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)

            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys10Gly", "score": -2.4, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys20Arg", "score": -2.2, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys30Tyr", "score": -2.1, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys40Phe", "score": -2.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys35Trp", "score": -2.5, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Met80Thr", "score": 1.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Ile90Val", "score": 1.1, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Leu100Pro", "score": 1.2, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Val110Ala", "score": 1.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                ]
            ).to_csv(mavedb_path, index=False)

            manifest_path.write_text(
                json.dumps(
                    {
                        "artifact_paths": {
                            "training_table": str(training_path),
                            "clinvar_expert_table": str(clinvar_expert_path),
                            "external_table": str(external_path),
                            "enigma_table": str(enigma_path),
                            "gnomad_table": str(gnomad_path),
                            "mavedb_table": str(mavedb_path),
                        }
                    }
                ),
                encoding="utf-8",
            )

            results = export_biological_discovery_package(
                real_data_manifest_path=str(manifest_path),
                output_dir=str(tmp_path / "biological_discovery"),
            )

            manifest = json.loads(Path(results["biological_discovery_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["summary"]["hotspot_count"], 1)
            self.assertGreaterEqual(manifest["summary"]["review_upgrade_candidate_count"], 1)
            self.assertGreaterEqual(manifest["summary"]["hypothesis_variant_count"], 1)
            self.assertTrue(Path(results["biological_discovery_hotspots_path"]).exists())
            self.assertTrue(Path(results["biological_discovery_hypothesis_variants_path"]).exists())

    def test_export_protein_impact_package_builds_modeling_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            hypothesis_path = tmp_path / "hypotheses.csv"
            review_path = tmp_path / "review.csv"
            biological_manifest_path = tmp_path / "biological_discovery_manifest.json"

            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "hypothesis_score_percent": 98.0,
                        "functional_damage_score": 0.97,
                        "score_set_support": 2,
                        "popmax_af": 1e-7,
                    },
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "hypothesis_score_percent": 94.0,
                        "functional_damage_score": 0.92,
                        "score_set_support": 3,
                        "popmax_af": 1e-8,
                    },
                ]
            ).to_csv(hypothesis_path, index=False)
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "candidate_kind": "low_review_pathogenic_with_functional_support",
                        "evidence_score_percent": 99.0,
                        "functional_damage_score": 0.98,
                    }
                ]
            ).to_csv(review_path, index=False)
            biological_manifest_path.write_text(
                json.dumps(
                    {
                        "hypothesis_variants_path": str(hypothesis_path),
                        "review_upgrade_candidates_path": str(review_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exported = export_protein_impact_package(
                biological_discovery_manifest_path=str(biological_manifest_path),
                output_dir=str(tmp_path / "protein_impact"),
                max_modeling_variants=2,
            )

            manifest = json.loads(Path(exported["protein_impact_manifest_path"]).read_text(encoding="utf-8"))
            queue = pd.read_csv(exported["protein_modeling_queue_path"])
            self.assertEqual(manifest["summary"]["modeling_queue_count"], 2)
            self.assertGreaterEqual(manifest["summary"]["prime_mechanistic_alignment_percent"], 50)
            self.assertIn("RING domain", set(queue["structural_region"].astype(str)))
            self.assertIn("modeling_plan", queue.columns)

    def test_export_quantum_proteomics_package_generates_targets_and_templates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            queue_path = tmp_path / "protein_modeling_queue.csv"
            protein_manifest_path = tmp_path / "protein_impact_manifest.json"

            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                        "protein_impact_score_percent": 94.0,
                        "prime_mechanistic_score_percent": 88.0,
                        "prime_ref": 3,
                        "prime_alt": 7,
                        "prime_diff": 4.0,
                        "prime_ratio": 2.3333,
                        "biochemical_severity": 9.5,
                        "charge_abs_diff": 0,
                        "hydro_abs_diff": 2.9,
                        "position": 61,
                        "aa_ref": "C",
                        "aa_alt": "G",
                        "structural_region": "RING domain",
                        "domain_mechanism": "zinc_binding_or_E3_ligase_interface",
                        "domain_known": True,
                        "mechanism_tags": "cysteine_or_disulfide_shift;large_prime_displacement",
                        "recommended_assays": "mutant_structure_modeling;redox_or_metal_coordination_check",
                    },
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "model_request_id": "TP53_pArg175His",
                        "protein_impact_score_percent": 91.0,
                        "prime_mechanistic_score_percent": 72.0,
                        "prime_ref": 11,
                        "prime_alt": 7,
                        "prime_diff": 4.0,
                        "prime_ratio": 0.6364,
                        "biochemical_severity": 8.8,
                        "charge_abs_diff": 1,
                        "hydro_abs_diff": 3.1,
                        "position": 175,
                        "aa_ref": "R",
                        "aa_alt": "H",
                        "structural_region": "DNA-binding core domain",
                        "domain_mechanism": "DNA_binding_or_fold_stability",
                        "domain_known": True,
                        "mechanism_tags": "electrostatic_shift;hydrophobic_core_or_surface_shift",
                        "recommended_assays": "mutant_structure_modeling;DNA_binding_or_repair_readout",
                    },
                ]
            ).to_csv(queue_path, index=False)
            protein_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {"modeling_queue_count": 2},
                        "modeling_queue_path": str(queue_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exported = export_quantum_proteomics_package(
                protein_impact_manifest_path=str(protein_manifest_path),
                output_dir=str(tmp_path / "quantum_proteomics"),
                max_quantum_targets=2,
            )

            manifest = json.loads(Path(exported["quantum_proteomics_manifest_path"]).read_text(encoding="utf-8"))
            targets = pd.read_csv(exported["quantum_targets_path"])
            bridge = pd.read_csv(exported["prime_quantum_bridge_path"])
            vqe_targets = pd.read_csv(exported["vqe_targets_path"])
            templates = pd.read_csv(exported["quantum_job_templates_path"])
            self.assertEqual(manifest["summary"]["quantum_target_count"], 2)
            self.assertEqual(manifest["summary"]["vqe_target_count"], 2)
            self.assertGreaterEqual(manifest["summary"]["mean_quantum_priority_score_percent"], 70)
            self.assertGreaterEqual(manifest["summary"]["mean_vqe_readiness_score_percent"], 70)
            self.assertGreaterEqual(manifest["summary"]["mean_prime_quantum_coupling_score_percent"], 60)
            self.assertIn("metal_redox_or_cysteine_network", set(targets["quantum_vulnerability_class"].astype(str)))
            self.assertIn("prime_quantum_coupling_score_percent", set(bridge.columns))
            self.assertIn("prime_topology_signature", set(bridge.columns))
            self.assertIn("prime_active_space_seed", set(targets.columns))
            self.assertIn("prime_curvature_score", set(targets.columns))
            self.assertIn("recommended_ansatz", vqe_targets.columns)
            self.assertIn("prime_guided_initialization", vqe_targets.columns)
            self.assertTrue(Path(templates.iloc[0]["psi4_template_path"]).exists())
            vqe_templates = pd.read_csv(exported["vqe_job_templates_path"])
            self.assertTrue(Path(vqe_templates.iloc[0]["qiskit_nature_vqe_template_path"]).exists())
            self.assertTrue(Path(exported["quantum_proteomics_report_markdown_path"]).exists())

    def test_export_validation_credibility_closure_separates_software_and_final_proof(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            prime_path = tmp_path / "prime.json"
            biological_path = tmp_path / "bio.json"
            protein_path = tmp_path / "protein.json"
            quantum_path = tmp_path / "quantum.json"
            multigene_path = tmp_path / "multi.json"
            claim_path = tmp_path / "claim.json"
            engine_path = tmp_path / "engine.json"
            annotation_path = tmp_path / "annotation.json"
            prospective_path = tmp_path / "prospective.json"

            prime_path.write_text(json.dumps({"summary": {"overall_prime_intelligence_percent": 88}}), encoding="utf-8")
            biological_path.write_text(json.dumps({"summary": {"hotspot_count": 3, "hypothesis_variant_count": 80, "review_upgrade_candidate_count": 5}}), encoding="utf-8")
            protein_path.write_text(json.dumps({"summary": {"modeling_queue_count": 25, "modeling_queue_prime_alignment_percent": 96}}), encoding="utf-8")
            quantum_path.write_text(json.dumps({"summary": {"quantum_target_count": 12, "vqe_target_count": 12, "mean_vqe_readiness_score_percent": 87.5, "mean_prime_quantum_coupling_score_percent": 84.0, "high_prime_quantum_coupling_target_count": 8}}), encoding="utf-8")
            multigene_path.write_text(json.dumps({"summary": {"phase_1_gene_count": 1, "phase_1_genes": ["TP53"], "phase_2_genes": ["GCK"]}}), encoding="utf-8")
            claim_path.write_text(json.dumps({"summary": {"claim_tier": "strong", "claim_strength_percent": 97}}), encoding="utf-8")
            engine_path.write_text(json.dumps({"summary": {"execution_readiness_percent": 72}}), encoding="utf-8")
            annotation_path.write_text(json.dumps({"summary": {"line_level_annotation_readiness_percent": 88, "genomic_coordinate_coverage_percent": 90, "gnomad_line_evidence_coverage_percent": 85, "mavedb_line_evidence_coverage_percent": 80}}), encoding="utf-8")
            prospective_path.write_text(json.dumps({"summary": {"prospective_validation_readiness_percent": 82, "functional_structural_confirmation_queue_count": 8, "experimental_confirmation_completed_percent": 0, "final_scientific_proof_cap_percent": 88}}), encoding="utf-8")

            exported = export_validation_credibility_closure(
                output_dir=str(tmp_path / "closure"),
                prime_intelligence_manifest_path=str(prime_path),
                biological_discovery_manifest_path=str(biological_path),
                protein_impact_manifest_path=str(protein_path),
                quantum_proteomics_manifest_path=str(quantum_path),
                multigene_rollout_manifest_path=str(multigene_path),
                claim_strength_manifest_path=str(claim_path),
                brca1_engine_execution_manifest_path=str(engine_path),
                multigene_annotation_enrichment_manifest_path=str(annotation_path),
                prospective_validation_closure_manifest_path=str(prospective_path),
            )

            manifest = json.loads(Path(exported["validation_credibility_closure_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["summary"]["software_evidence_closure_percent"], 85)
            self.assertLessEqual(manifest["summary"]["scientific_credibility_percent"], manifest["summary"]["final_proof_cap_percent"])
            self.assertFalse(manifest["summary"]["ready_for_definitive_therapeutic_claims"])
            self.assertTrue(Path(exported["validation_credibility_report_markdown_path"]).exists())

    def test_export_quantum_vqe_benchmark_package_compares_prime_and_nonprime(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            vqe_targets_path = tmp_path / "vqe_targets.csv"
            quantum_manifest_path = tmp_path / "quantum_manifest.json"

            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                        "vqe_readiness_score_percent": 92.0,
                        "quantum_priority_score_percent": 90.0,
                        "prime_mechanistic_score_percent": 84.0,
                        "prime_quantum_coupling_score_percent": 81.0,
                        "prime_topology_signature": "stable_prime_topology",
                        "prime_fragment_strategy": "metal_shell_fragment_plus_first_coordination_layer",
                        "prime_active_space_seed": "6e/6o prime-seeded start",
                        "prime_shot_schedule": "1777;2741;4673",
                        "quantum_vulnerability_class": "metal_redox_or_cysteine_network",
                    },
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "model_request_id": "TP53_pArg175His",
                        "vqe_readiness_score_percent": 85.0,
                        "quantum_priority_score_percent": 88.0,
                        "prime_mechanistic_score_percent": 73.0,
                        "prime_quantum_coupling_score_percent": 69.0,
                        "prime_topology_signature": "curvature_shift_topology",
                        "prime_fragment_strategy": "dna_binding_fragment",
                        "prime_active_space_seed": "4e/4o prime-seeded start",
                        "prime_shot_schedule": "1327;2111;3253",
                        "quantum_vulnerability_class": "electrostatic_or_dna_binding_surface",
                    },
                ]
            ).to_csv(vqe_targets_path, index=False)
            quantum_manifest_path.write_text(
                json.dumps(
                    {
                        "vqe_targets_path": str(vqe_targets_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exported = export_quantum_vqe_benchmark_package(
                quantum_proteomics_manifest_path=str(quantum_manifest_path),
                output_dir=str(tmp_path / "quantum_benchmark"),
            )

            manifest = json.loads(Path(exported["quantum_vqe_benchmark_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["quantum_vqe_paired_benchmark_path"])
            self.assertEqual(manifest["summary"]["benchmark_target_count"], 2)
            self.assertGreater(manifest["summary"]["mean_overall_advantage_percent_points"], 0)
            self.assertGreaterEqual(manifest["summary"]["prime_guided_win_rate_percent"], 50)
            self.assertIn("paired_same_fragment_proxy", set(table["benchmark_mode"].astype(str)))

    def test_export_brca1_structural_campaign_builds_preflight_rows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            quantum_root = tmp_path / "quantum_output"
            (quantum_root / "quantum_job_templates").mkdir(parents=True)
            (quantum_root / "vqe_job_templates").mkdir(parents=True)
            protein_queue_path = tmp_path / "protein_queue.csv"
            protein_manifest_path = tmp_path / "protein_manifest.json"
            quantum_targets_path = tmp_path / "quantum_targets.csv"
            vqe_targets_path = tmp_path / "vqe_targets.csv"
            quantum_manifest_path = quantum_root / "quantum_proteomics_manifest.json"

            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                        "protein_impact_score_percent": 94.0,
                        "prime_mechanistic_score_percent": 88.0,
                        "charge_abs_diff": 0,
                        "hydro_abs_diff": 2.9,
                        "structural_region": "RING domain",
                        "domain_mechanism": "zinc_binding_or_E3_ligase_interface",
                        "mechanism_tags": "cysteine_or_disulfide_shift;large_prime_displacement",
                        "recommended_assays": "mutant_structure_modeling",
                        "queue_rank": 1,
                    }
                ]
            ).to_csv(protein_queue_path, index=False)
            protein_manifest_path.write_text(json.dumps({"modeling_queue_path": str(protein_queue_path)}), encoding="utf-8")

            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                        "quantum_priority_score_percent": 92.0,
                        "prime_quantum_coupling_score_percent": 84.0,
                        "quantum_vulnerability_class": "metal_redox_or_cysteine_network",
                        "recommended_quantum_methods": "xTB_GFN2_screen;DFT_fragment_single_point",
                        "drug_discovery_angle": "Test altered metal coordination.",
                    }
                ]
            ).to_csv(quantum_targets_path, index=False)
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                    }
                ]
            ).to_csv(vqe_targets_path, index=False)
            for suffix in [".xtb.sh", ".psi4.in", ".openmm_plan.py", ".vina_config.txt"]:
                (quantum_root / "quantum_job_templates" / f"BRCA1_pCys61Gly{suffix}").write_text("template", encoding="utf-8")
            (quantum_root / "vqe_job_templates" / "BRCA1_pCys61Gly.qiskit_nature_vqe.py").write_text("template", encoding="utf-8")
            quantum_manifest_path.write_text(
                json.dumps(
                    {
                        "quantum_targets_path": str(quantum_targets_path),
                        "vqe_targets_path": str(vqe_targets_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exported = export_brca1_structural_campaign(
                protein_impact_manifest_path=str(protein_manifest_path),
                quantum_proteomics_manifest_path=str(quantum_manifest_path),
                output_dir=str(tmp_path / "campaign"),
            )

            manifest = json.loads(Path(exported["brca1_structural_campaign_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["brca1_structural_campaign_path"])
            self.assertEqual(manifest["summary"]["campaign_target_count"], 1)
            self.assertGreater(manifest["summary"]["template_coverage_percent"], 0)
            self.assertTrue(Path(table.iloc[0]["xtb_template_path"]).exists())
            self.assertIn("campaign_status", table.columns)

    def test_export_multigene_annotation_enrichment_builds_row_level_matrix(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            multigene_root = tmp_path / "multigene"
            gnomad_dir = tmp_path / "gnomad"
            mavedb_dir = tmp_path / "mavedb"
            (multigene_root / "TP53").mkdir(parents=True)
            gnomad_dir.mkdir()
            mavedb_dir.mkdir()
            variant_summary_path = tmp_path / "variant_summary.tsv"
            multigene_manifest_path = tmp_path / "multigene_manifest.json"

            pd.DataFrame(
                [
                    {
                        "GeneSymbol": "TP53",
                        "Protein change": "p.Arg175His",
                        "ClinicalSignificance": "Pathogenic",
                        "ReviewStatus": "criteria provided, single submitter",
                        "VariationID": "123",
                        "Name": "TP53 p.Arg175His",
                        "LastEvaluated": "Jan 01, 2026",
                    }
                ]
            ).to_csv(multigene_root / "TP53" / "tp53_clinvar_training.tsv", sep="\t", index=False)
            pd.DataFrame(
                [
                    {
                        "GeneSymbol": "TP53",
                        "Assembly": "GRCh38",
                        "Chromosome": "17",
                        "Start": 7675088,
                        "Stop": 7675088,
                        "ReferenceAllele": "G",
                        "AlternateAllele": "A",
                        "VariationID": "123",
                        "PositionVCF": 7675088,
                        "ReferenceAlleleVCF": "G",
                        "AlternateAlleleVCF": "A",
                        "RS# (dbSNP)": "rs28934578",
                    }
                ]
            ).to_csv(variant_summary_path, sep="\t", index=False)
            pd.DataFrame(
                [{"gene": "TP53", "hgvs_p": "p.Arg175His", "af": 0.0001, "ac": 1, "an": 10000, "popmax_af": 0.0002}]
            ).to_csv(gnomad_dir / "tp53_missense_annotations.tsv", sep="\t", index=False)
            pd.DataFrame(
                [{"gene": "TP53", "hgvs_p": "p.Arg175His", "score": 0.12, "score_set_urn": "urn:mavedb:test", "assay_name": "TP53 assay"}]
            ).to_csv(mavedb_dir / "tp53_function_scores.csv", index=False)
            multigene_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "target_genes": ["TP53"],
                            "variant_summary_input_path": str(variant_summary_path),
                        }
                    }
                ),
                encoding="utf-8",
            )

            exported = export_multigene_annotation_enrichment_package(
                multigene_real_benchmark_manifest_path=str(multigene_manifest_path),
                output_dir=str(tmp_path / "annotation"),
                multigene_root=str(multigene_root),
                gnomad_dir=str(gnomad_dir),
                mavedb_dir=str(mavedb_dir),
                run_live_gnomad=False,
                run_live_mavedb=False,
                target_genes=["TP53"],
            )

            manifest = json.loads(Path(exported["multigene_annotation_enrichment_manifest_path"]).read_text(encoding="utf-8"))
            matrix = pd.read_csv(exported["multigene_variant_annotation_matrix_path"])
            self.assertEqual(manifest["summary"]["variant_row_count"], 1)
            self.assertEqual(manifest["summary"]["line_level_annotation_readiness_percent"], 100)
            self.assertEqual(matrix.iloc[0]["gnomad_variant_id"], "17-7675088-G-A")

    def test_export_brca1_engine_execution_package_writes_runner_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            campaign_path = tmp_path / "campaign.csv"
            manifest_path = tmp_path / "campaign_manifest.json"
            xtb_template = tmp_path / "BRCA1_pCys61Gly.xtb.sh"
            xtb_template.write_text("xtb template", encoding="utf-8")
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "model_request_id": "BRCA1_pCys61Gly",
                        "surrogate_structural_signal_percent": 95,
                        "drug_discovery_readiness_percent": 90,
                        "prime_quantum_structural_alignment_percent": 88,
                        "xtb_template_path": str(xtb_template),
                    }
                ]
            ).to_csv(campaign_path, index=False)
            manifest_path.write_text(json.dumps({"campaign_path": str(campaign_path)}), encoding="utf-8")

            with patch(
                "primevarclass.brca1_engine_execution._fetch_alphafold_metadata",
                return_value={
                    "status": "found",
                    "record_count": 1,
                    "records": [
                        {
                            "entry_id": "AF-P38398-F1",
                            "pdb_url": "https://alphafold.example/brca1.pdb",
                            "cif_url": "https://alphafold.example/brca1.cif",
                        }
                    ],
                },
            ):
                exported = export_brca1_engine_execution_package(
                    brca1_structural_campaign_manifest_path=str(manifest_path),
                    output_dir=str(tmp_path / "engine"),
                    execute_if_available=False,
                )

            manifest = json.loads(Path(exported["brca1_engine_execution_manifest_path"]).read_text(encoding="utf-8"))
            queue = pd.read_csv(exported["brca1_engine_execution_queue_path"])
            diagnostics = pd.read_csv(exported["structural_engine_diagnostics_path"])
            self.assertEqual(manifest["summary"]["queue_target_count"], 1)
            self.assertTrue(manifest["summary"]["alphafold_reference_available"])
            self.assertTrue(Path(exported["structural_engine_install_script_path"]).exists())
            self.assertTrue(Path(exported["structural_engine_doctor_script_path"]).exists())
            self.assertTrue(Path(exported["brca1_input_preparation_queue_path"]).exists())
            self.assertIn("engine", diagnostics.columns)
            self.assertIn("engine_missing_count", manifest["summary"])
            self.assertIn("execution_status", queue.columns)

    def test_export_brca1_fragment_preparation_extracts_alphafold_fragments(self):
        def pdb_atom(serial, atom_name, res_name, resseq, x, y, z, element):
            return (
                f"ATOM  {serial:5d} {atom_name:<4s} {res_name:>3s} A{resseq:4d}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{82.00:6.2f}          {element:>2s}"
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            reference_path = tmp_path / "AF-P38398-F1.pdb"
            queue_path = tmp_path / "input_queue.csv"
            manifest_path = tmp_path / "engine_manifest.json"

            atoms = []
            serial = 1
            for resseq, res_name, offset in [(9, "ALA", -1.5), (10, "CYS", 0.0), (11, "GLY", 1.5)]:
                for atom_name, dx, element in [("N", -0.4, "N"), ("CA", 0.0, "C"), ("C", 0.5, "C"), ("O", 0.9, "O"), ("CB", 0.2, "C")]:
                    atoms.append(pdb_atom(serial, atom_name, res_name, resseq, offset + dx, 0.0, 0.0, element))
                    serial += 1
            reference_path.write_text("\n".join(atoms + ["END"]) + "\n", encoding="utf-8")
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys10Gly", "model_request_id": "BRCA1_pCys10Gly"},
                    {"gene": "BRCA1", "hgvs_p": "p.Arg99His", "model_request_id": "BRCA1_pArg99His"},
                ]
            ).to_csv(queue_path, index=False)
            manifest_path.write_text(
                json.dumps(
                    {
                        "input_preparation_queue_path": str(queue_path),
                        "reference_structure_paths": {"pdb_path": str(reference_path)},
                        "engine_paths": {"xtb": ""},
                    }
                ),
                encoding="utf-8",
            )

            exported = export_brca1_fragment_preparation_package(
                brca1_engine_execution_manifest_path=str(manifest_path),
                output_dir=str(tmp_path / "fragments"),
                radius_angstrom=3.0,
                max_atoms=20,
                execute_xtb=False,
            )

            manifest = json.loads(Path(exported["brca1_fragment_preparation_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["brca1_prepared_fragment_table_path"])
            self.assertEqual(manifest["summary"]["target_count"], 2)
            self.assertEqual(manifest["summary"]["prepared_fragment_count"], 1)
            self.assertEqual(manifest["summary"]["xtb_attempted_count"], 0)
            self.assertFalse(manifest["summary"]["ready_for_mutant_effect_claims"])
            self.assertIn("prepared_reference_fragment", set(table["preparation_status"].astype(str)))
            self.assertIn("missing_reference_residue", set(table["preparation_status"].astype(str)))
            prepared_row = table.loc[table["preparation_status"].eq("prepared_reference_fragment")].iloc[0]
            self.assertGreaterEqual(int(prepared_row["fragment_atom_count"]), 5)
            self.assertTrue(Path(prepared_row["reference_fragment_pdb_path"]).exists())
            self.assertTrue(Path(exported["brca1_fragment_preparation_report_markdown_path"]).exists())

    def test_export_brca1_paired_mutant_execution_builds_draft_pairs(self):
        def pdb_atom(serial, atom_name, res_name, resseq, x, y, z, element):
            return (
                f"ATOM  {serial:5d} {atom_name:<4s} {res_name:>3s} A{resseq:4d}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{90.00:6.2f}          {element:>2s}"
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fragment_pdb = tmp_path / "BRCA1_pLeu10Asp.reference_fragment.pdb"
            prepared_table_path = tmp_path / "prepared.csv"
            fragment_manifest_path = tmp_path / "fragment_manifest.json"
            atoms = [
                pdb_atom(1, "N", "LEU", 10, 0.000, 0.000, 0.000, "N"),
                pdb_atom(2, "CA", "LEU", 10, 1.450, 0.000, 0.000, "C"),
                pdb_atom(3, "C", "LEU", 10, 2.050, 1.250, 0.000, "C"),
                pdb_atom(4, "O", "LEU", 10, 1.600, 2.350, 0.000, "O"),
                pdb_atom(5, "CB", "LEU", 10, 1.900, -0.850, 1.150, "C"),
                pdb_atom(6, "CG", "LEU", 10, 3.200, -1.300, 1.600, "C"),
            ]
            fragment_pdb.write_text("\n".join(atoms + ["END"]) + "\n", encoding="utf-8")
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Leu10Asp",
                        "model_request_id": "BRCA1_pLeu10Asp",
                        "preparation_status": "prepared_reference_fragment",
                        "reference_fragment_pdb_path": str(fragment_pdb),
                    }
                ]
            ).to_csv(prepared_table_path, index=False)
            fragment_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {"prepared_fragment_count": 1},
                        "prepared_fragment_table_path": str(prepared_table_path),
                        "engine_paths": {"xtb": ""},
                    }
                ),
                encoding="utf-8",
            )

            exported = export_brca1_paired_mutant_execution_package(
                brca1_fragment_preparation_manifest_path=str(fragment_manifest_path),
                output_dir=str(tmp_path / "paired"),
                execute_xtb=False,
            )

            manifest = json.loads(Path(exported["brca1_paired_mutant_execution_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["brca1_paired_mutant_table_path"])
            self.assertEqual(manifest["summary"]["draft_mutant_coordinate_count"], 1)
            self.assertEqual(manifest["summary"]["paired_xtb_attempted_count"], 0)
            self.assertFalse(manifest["summary"]["ready_for_publication_grade_mutant_effect_claims"])
            self.assertEqual(table.iloc[0]["mutation_coordinate_status"], "draft_sidechain_substitution")
            self.assertEqual(table.iloc[0]["coordinate_review_status"], "draft_needs_rotamer_protonation_and_domain_review")
            self.assertTrue(Path(table.iloc[0]["draft_mutant_fragment_pdb_path"]).exists())
            self.assertTrue(Path(exported["brca1_paired_mutant_execution_report_markdown_path"]).exists())

    def test_export_brca1_mutant_geometry_qc_reviews_draft_pairs(self):
        def pdb_atom(serial, atom_name, res_name, resseq, x, y, z, element):
            return (
                f"ATOM  {serial:5d} {atom_name:<4s} {res_name:>3s} A{resseq:4d}    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{90.00:6.2f}          {element:>2s}"
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            reference_path = tmp_path / "ref.pdb"
            mutant_path = tmp_path / "mut.pdb"
            mutant_xyz = tmp_path / "mut.xyz"
            paired_table_path = tmp_path / "paired.csv"
            paired_manifest_path = tmp_path / "paired_manifest.json"
            atoms = [
                pdb_atom(1, "N", "ASP", 10, 0.000, 0.000, 0.000, "N"),
                pdb_atom(2, "CA", "ASP", 10, 1.450, 0.000, 0.000, "C"),
                pdb_atom(3, "C", "ASP", 10, 2.050, 1.250, 0.000, "C"),
                pdb_atom(4, "O", "ASP", 10, 1.600, 2.350, 0.000, "O"),
                pdb_atom(5, "CB", "ASP", 10, 1.900, -0.850, 1.150, "C"),
                pdb_atom(6, "CG", "ASP", 10, 3.200, -1.300, 1.600, "C"),
            ]
            reference_path.write_text("\n".join(atoms + ["END"]) + "\n", encoding="utf-8")
            mutant_path.write_text("\n".join(atoms + ["END"]) + "\n", encoding="utf-8")
            mutant_xyz.write_text("2\nmock\nC 0 0 0\nO 1.2 0 0\n", encoding="utf-8")
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Leu10Asp",
                        "model_request_id": "BRCA1_pLeu10Asp",
                        "paired_status": "paired_xtb_completed",
                        "coordinate_review_status": "draft_needs_rotamer_protonation_and_domain_review",
                        "reference_pair_pdb_path": str(reference_path),
                        "draft_mutant_fragment_pdb_path": str(mutant_path),
                        "draft_mutant_fragment_xyz_path": str(mutant_xyz),
                    }
                ]
            ).to_csv(paired_table_path, index=False)
            paired_manifest_path.write_text(
                json.dumps(
                    {
                        "paired_mutant_table_path": str(paired_table_path),
                        "engine_paths": {"xtb": ""},
                    }
                ),
                encoding="utf-8",
            )

            exported = export_brca1_mutant_geometry_qc_package(
                brca1_paired_mutant_execution_manifest_path=str(paired_manifest_path),
                output_dir=str(tmp_path / "qc"),
                execute_xtb_opt=False,
            )

            manifest = json.loads(Path(exported["brca1_mutant_geometry_qc_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["brca1_mutant_geometry_qc_table_path"])
            self.assertEqual(manifest["summary"]["reviewed_pair_count"], 1)
            self.assertEqual(manifest["summary"]["xtb_optimization_attempted_count"], 0)
            self.assertIn(table.iloc[0]["geometry_qc_status"], {"geometry_pass", "needs_rotamer_or_coordinate_review"})
            self.assertFalse(manifest["summary"]["ready_for_reviewed_mutant_structure_claims"])
            self.assertTrue(Path(exported["brca1_mutant_geometry_qc_report_markdown_path"]).exists())

    def test_export_public_sync_closure_builds_resumable_gnomad_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            matrix_path = tmp_path / "annotation_matrix.csv"
            live_path = tmp_path / "gnomad_live.csv"
            local_release_path = tmp_path / "gnomad_subset.tsv"
            manifest_path = tmp_path / "annotation_manifest.json"
            pd.DataFrame(
                [
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "variation_id": "123",
                        "clinical_significance": "Pathogenic",
                        "review_status": "criteria provided",
                        "source_cohort_kind": "combined_external",
                        "gnomad_variant_id": "17-7675088-G-A",
                        "coordinate_ready": True,
                        "mavedb_line_available": True,
                        "source_trace_ready": True,
                    },
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Pro72Arg",
                        "variation_id": "124",
                        "clinical_significance": "Benign",
                        "review_status": "criteria provided",
                        "source_cohort_kind": "training",
                        "gnomad_variant_id": "17-7676154-C-G",
                        "coordinate_ready": True,
                        "mavedb_line_available": False,
                        "source_trace_ready": True,
                    },
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg248Gln",
                        "variation_id": "125",
                        "clinical_significance": "Pathogenic",
                        "review_status": "criteria provided",
                        "source_cohort_kind": "combined_external",
                        "gnomad_variant_id": "17-111-A-T",
                        "coordinate_ready": True,
                        "mavedb_line_available": True,
                        "source_trace_ready": True,
                    },
                ]
            ).to_csv(matrix_path, index=False)
            pd.DataFrame(
                [
                    {
                        "variant_id": "17-7675088-G-A",
                        "status": "found",
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "variation_id": "123",
                        "live_gnomad_af": 0.00001,
                        "live_gnomad_ac": 1,
                        "live_gnomad_an": 100000,
                        "error": "",
                    },
                    {
                        "variant_id": "17-7676154-C-G",
                        "status": "graphql_error",
                        "gene": "TP53",
                        "hgvs_p": "p.Pro72Arg",
                        "variation_id": "124",
                        "live_gnomad_af": "",
                        "live_gnomad_ac": "",
                        "live_gnomad_an": "",
                        "error": "temporary schema error",
                    }
                ]
            ).to_csv(live_path, index=False)
            pd.DataFrame(
                [
                    {
                        "chrom": "17",
                        "pos": 111,
                        "ref": "A",
                        "alt": "T",
                        "AF": 0.00002,
                        "AC": 2,
                        "AN": 100000,
                    }
                ]
            ).to_csv(local_release_path, sep="\t", index=False)
            manifest_path.write_text(
                json.dumps(
                    {
                        "variant_annotation_matrix_path": str(matrix_path),
                        "gnomad_live_query_results_path": str(live_path),
                    }
                ),
                encoding="utf-8",
            )

            exported = export_public_sync_closure_package(
                multigene_annotation_enrichment_manifest_path=str(manifest_path),
                output_dir=str(tmp_path / "sync"),
                gnomad_release_table_path=str(local_release_path),
            )

            manifest = json.loads(Path(exported["public_sync_closure_manifest_path"]).read_text(encoding="utf-8"))
            queue = pd.read_csv(exported["gnomad_sync_queue_path"])
            status_by_gene = pd.read_csv(exported["gnomad_sync_status_by_gene_path"])
            self.assertEqual(manifest["summary"]["variant_row_count"], 3)
            self.assertGreaterEqual(manifest["summary"]["sync_infrastructure_readiness_percent"], 80)
            self.assertEqual(int((queue["gnomad_sync_status"] == "cached_found").sum()), 2)
            self.assertEqual(int((queue["gnomad_sync_status"] == "graphql_error_retry_later").sum()), 1)
            self.assertEqual(manifest["summary"]["gnomad_retryable_error_count"], 1)
            self.assertEqual(manifest["summary"]["local_gnomad_release_rows_matched"], 1)
            self.assertIn("definitive_cached_percent", status_by_gene.columns)
            self.assertTrue(Path(exported["resume_gnomad_sync_script_path"]).exists())

    def test_export_gnomad_gene_subset_writes_gene_level_table(self):
        def fake_post_graphql(query, variables, timeout_sec):
            gene = variables["gene"]
            return {
                "data": {
                    "gene": {
                        "symbol": gene,
                        "gene_id": f"ENSG_{gene}",
                        "chrom": "17",
                        "start": 100,
                        "stop": 200,
                        "variants": [
                            {
                                "variant_id": "17-111-A-T",
                                "chrom": "17",
                                "pos": 111,
                                "ref": "A",
                                "alt": "T",
                                "consequence": "missense_variant",
                                "hgvsp": f"p.{gene}Test",
                                "flags": [],
                                "exome": {"ac": 1, "an": 100000, "af": 0.00001},
                                "genome": None,
                            }
                        ],
                    }
                }
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("primevarclass.gnomad_gene_subset._post_graphql", side_effect=fake_post_graphql):
                exported = export_gnomad_gene_subset(
                    output_dir=str(Path(tmp_dir) / "gnomad_subset"),
                    target_genes=["TP53", "F9"],
                    sleep_seconds=0,
                )

            manifest = json.loads(Path(exported["gnomad_gene_subset_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["gnomad_gene_subset_variants_path"], sep="\t")
            self.assertEqual(manifest["summary"]["gene_count_fetched"], 2)
            self.assertEqual(manifest["summary"]["variant_row_count"], 2)
            self.assertIn("gnomad_variant_id", table.columns)

    def test_export_prospective_validation_closure_locks_gates_and_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            annotation_matrix_path = tmp_path / "annotation_matrix.csv"
            annotation_manifest_path = tmp_path / "annotation_manifest.json"
            engine_queue_path = tmp_path / "engine_queue.csv"
            engine_manifest_path = tmp_path / "engine_manifest.json"
            validation_manifest_path = tmp_path / "validation_manifest.json"
            public_sync_manifest_path = tmp_path / "public_sync_manifest.json"
            paired_table_path = tmp_path / "paired.csv"
            paired_manifest_path = tmp_path / "paired_manifest.json"

            pd.DataFrame(
                [
                    {
                        "gene": "TP53",
                        "hgvs_p": "p.Arg175His",
                        "mavedb_line_available": True,
                        "gnomad_line_available": True,
                        "annotation_status": "coordinate_gnomad_mavedb_complete",
                    }
                ]
            ).to_csv(annotation_matrix_path, index=False)
            annotation_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "line_level_annotation_readiness_percent": 92,
                            "gnomad_line_evidence_coverage_percent": 90,
                            "mavedb_line_evidence_coverage_percent": 85,
                        },
                        "variant_annotation_matrix_path": str(annotation_matrix_path),
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "execution_status": "blocked_engines_missing",
                    }
                ]
            ).to_csv(engine_queue_path, index=False)
            engine_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "execution_readiness_percent": 70,
                            "engine_availability_percent": 0,
                            "alphafold_reference_available": True,
                        },
                        "execution_queue_path": str(engine_queue_path),
                    }
                ),
                encoding="utf-8",
            )
            validation_manifest_path.write_text(
                json.dumps({"summary": {"software_evidence_closure_percent": 94}}),
                encoding="utf-8",
            )
            public_sync_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "effective_line_level_annotation_readiness_percent": 98,
                            "effective_gnomad_line_evidence_percent": 100,
                            "mavedb_line_evidence_percent": 90,
                            "gnomad_coordinate_missing_count": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.Cys61Gly",
                        "paired_status": "paired_xtb_completed",
                        "delta_mutant_minus_reference_hartree": 0.42,
                    }
                ]
            ).to_csv(paired_table_path, index=False)
            paired_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "paired_mutant_execution_readiness_percent": 100,
                            "paired_xtb_completed_count": 1,
                        },
                        "paired_mutant_table_path": str(paired_table_path),
                    }
                ),
                encoding="utf-8",
            )

            exported = export_prospective_validation_closure_package(
                multigene_annotation_enrichment_manifest_path=str(annotation_manifest_path),
                brca1_engine_execution_manifest_path=str(engine_manifest_path),
                validation_credibility_closure_manifest_path=str(validation_manifest_path),
                public_sync_closure_manifest_path=str(public_sync_manifest_path),
                brca1_paired_mutant_execution_manifest_path=str(paired_manifest_path),
                output_dir=str(tmp_path / "prospective"),
            )

            manifest = json.loads(Path(exported["prospective_validation_closure_manifest_path"]).read_text(encoding="utf-8"))
            gates = pd.read_csv(exported["prospective_validation_gates_path"])
            queue = pd.read_csv(exported["functional_structural_confirmation_queue_path"])
            cohort_plan = pd.read_csv(exported["prospective_validation_cohort_plan_path"])
            criteria = pd.read_csv(exported["experimental_confirmation_criteria_path"])
            handoff = pd.read_csv(exported["partner_lab_handoff_sheet_path"])
            sop_manifest = pd.read_csv(exported["sop_template_manifest_path"])
            self.assertGreaterEqual(manifest["summary"]["prospective_validation_readiness_percent"], 75)
            self.assertEqual(manifest["summary"]["experimental_package_artifact_readiness_percent"], 100)
            self.assertTrue(manifest["summary"]["ready_for_irb_or_partner_handoff"])
            self.assertFalse(manifest["summary"]["ready_for_definitive_therapeutic_claims"])
            self.assertGreaterEqual(len(gates), 4)
            self.assertGreaterEqual(len(queue), 1)
            self.assertGreaterEqual(len(cohort_plan), 5)
            self.assertIn("PVC-BLINDED-MULTIGENE-HOLDOUT", set(cohort_plan["cohort_id"].astype(str)))
            self.assertIn("COMPUTATIONAL_REPRODUCIBILITY", set(criteria["criterion_id"].astype(str)))
            self.assertIn("PVC-BLIND-0001", set(handoff["blinding_id"].astype(str)))
            self.assertIn("SOP_BRCA1_HDR_SGE", set(sop_manifest["sop_id"].astype(str)))
            self.assertTrue(Path(exported["statistical_analysis_plan_path"]).exists())
            self.assertTrue(Path(exported["external_partner_handoff_packet_path"]).exists())
            self.assertIn("paired_xtb_completed", set(queue["software_status"].astype(str)))
            row_level_gate = gates.loc[gates["gate_id"].eq("row_level_public_annotation")].iloc[0]
            self.assertGreaterEqual(int(row_level_gate["score_percent"]), 90)

    def test_export_multigene_real_benchmark_package_builds_real_clinvar_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            variant_summary_path = tmp_path / "variant_summary.tsv"
            workspace_root = tmp_path / "workspace"
            gene_expansion_manifest_path = tmp_path / "gene_expansion_manifest.json"

            pd.DataFrame(
                [
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg175His", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "1", "Name": "TP53 p.Arg175His", "LastEvaluated": "Jan 01, 2025"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Pro72Arg", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "2", "Name": "TP53 p.Pro72Arg", "LastEvaluated": "Jan 02, 2025"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg248Gln", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel", "VariationID": "3", "Name": "TP53 p.Arg248Gln", "LastEvaluated": "Jan 03, 2025"},
                    {"GeneSymbol": "PTEN", "Protein change": "p.Cys124Ser", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "4", "Name": "PTEN p.Cys124Ser", "LastEvaluated": "Jan 01, 2025"},
                    {"GeneSymbol": "PTEN", "Protein change": "p.Gly129Glu", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "5", "Name": "PTEN p.Gly129Glu", "LastEvaluated": "Jan 02, 2025"},
                    {"GeneSymbol": "PTEN", "Protein change": "p.Lys267Arg", "ClinicalSignificance": "Benign", "ReviewStatus": "reviewed by expert panel", "VariationID": "6", "Name": "PTEN p.Lys267Arg", "LastEvaluated": "Jan 03, 2025"},
                ]
            ).to_csv(variant_summary_path, sep="\t", index=False)
            gene_expansion_manifest_path.write_text(
                json.dumps(
                    {
                        "top_candidates": [
                            {"gene": "TP53", "expansion_priority_percent": 85.3, "clinvar_expert_rows": 254, "mavedb_score_set_count": 15, "gnomad_direct_api_ready": True},
                            {"gene": "PTEN", "expansion_priority_percent": 74.5, "clinvar_expert_rows": 168, "mavedb_score_set_count": 6, "gnomad_direct_api_ready": True},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            exported = export_multigene_real_benchmark_package(
                clinvar_variant_summary_path=str(variant_summary_path),
                output_dir=str(tmp_path / "multigene_benchmark"),
                workspace_root=str(workspace_root),
                target_genes=["TP53", "PTEN"],
                gene_expansion_manifest_path=str(gene_expansion_manifest_path),
                run_study=False,
            )

            manifest = json.loads(Path(exported["multigene_real_benchmark_manifest_path"]).read_text(encoding="utf-8"))
            gene_progress = pd.read_csv(exported["multigene_gene_progress_path"])
            self.assertEqual(manifest["summary"]["gene_count"], 2)
            self.assertFalse(manifest["summary"]["study_executed"])
            self.assertEqual(set(gene_progress["gene"].astype(str)), {"TP53", "PTEN"})
            self.assertTrue((workspace_root / "data" / "raw" / "multigene" / "tp53" / "tp53_clinvar_training.tsv").exists())

    def test_export_development_progress_dashboard_builds_area_table(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            prime_path = tmp_path / "prime.json"
            biological_path = tmp_path / "bio.json"
            protein_path = tmp_path / "protein.json"
            quantum_path = tmp_path / "quantum.json"
            quantum_benchmark_path = tmp_path / "quantum_benchmark.json"
            structural_path = tmp_path / "structural.json"
            multigene_path = tmp_path / "multigene.json"
            continuous_path = tmp_path / "continuous.json"
            validation_path = tmp_path / "validation.json"

            prime_path.write_text(json.dumps({"summary": {"overall_prime_intelligence_percent": 84}}), encoding="utf-8")
            biological_path.write_text(json.dumps({"summary": {"hotspot_count": 2, "review_upgrade_candidate_count": 5, "hypothesis_variant_count": 200}}), encoding="utf-8")
            protein_path.write_text(json.dumps({"summary": {"modeling_queue_count": 20, "prime_mechanistic_alignment_percent": 82}}), encoding="utf-8")
            quantum_path.write_text(json.dumps({"summary": {"mean_vqe_readiness_score_percent": 87, "mean_prime_quantum_coupling_score_percent": 76, "mean_quantum_priority_score_percent": 89}}), encoding="utf-8")
            quantum_benchmark_path.write_text(json.dumps({"summary": {"benchmark_support_percent": 90, "prime_guided_win_rate_percent": 100}}), encoding="utf-8")
            structural_path.write_text(json.dumps({"summary": {"campaign_readiness_percent": 70, "mean_surrogate_structural_signal_percent": 84, "mean_drug_discovery_readiness_percent": 78}}), encoding="utf-8")
            multigene_path.write_text(json.dumps({"summary": {"overall_multigene_benchmark_percent": 79, "ready_genes": ["TP53", "PTEN"], "mean_gene_progress_percent": 78}}), encoding="utf-8")
            continuous_path.write_text(json.dumps({"summary": {"continuous_learning_readiness_percent": 68, "auto_sync_coverage_percent": 100, "benchmark_readiness_percent": 36}}), encoding="utf-8")
            validation_path.write_text(json.dumps({"summary": {"scientific_credibility_percent": 91, "software_evidence_closure_percent": 93, "final_proof_cap_percent": 92}}), encoding="utf-8")

            exported = export_development_progress_dashboard(
                output_dir=str(tmp_path / "progress"),
                prime_intelligence_manifest_path=str(prime_path),
                biological_discovery_manifest_path=str(biological_path),
                protein_impact_manifest_path=str(protein_path),
                quantum_proteomics_manifest_path=str(quantum_path),
                quantum_vqe_benchmark_manifest_path=str(quantum_benchmark_path),
                brca1_structural_campaign_manifest_path=str(structural_path),
                multigene_real_benchmark_manifest_path=str(multigene_path),
                continuous_learning_manifest_path=str(continuous_path),
                validation_credibility_closure_manifest_path=str(validation_path),
            )

            manifest = json.loads(Path(exported["development_progress_manifest_path"]).read_text(encoding="utf-8"))
            table = pd.read_csv(exported["development_progress_table_path"])
            self.assertEqual(manifest["summary"]["areas_tracked"], 10)
            self.assertGreater(manifest["summary"]["overall_progress_percent"], 0)
            self.assertIn("area", table.columns)
            self.assertIn("progress_percent", table.columns)

    def test_export_prime_intelligence_package_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            training_table = tmp_path / "training.tsv"
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": 1},
                    {"gene": "BRCA1", "hgvs_p": "p.Ala1708Glu", "label": 1},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "label": 0},
                    {"gene": "BRCA2", "hgvs_p": "p.Asp2723His", "label": 0},
                ]
            ).to_csv(training_table, sep="\t", index=False)

            hotspots_path = tmp_path / "hotspots.csv"
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "window_start": 1,
                        "window_end": 120,
                        "variant_count": 2,
                        "positive_rate": 1.0,
                        "hotspot_score_percent": 82.0,
                    }
                ]
            ).to_csv(hotspots_path, index=False)

            review_path = tmp_path / "review.csv"
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly"},
                    {"gene": "BRCA1", "hgvs_p": "p.Ala1708Glu"},
                ]
            ).to_csv(review_path, index=False)

            hypothesis_path = tmp_path / "hypotheses.csv"
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "hypothesis_score_percent": 98.0},
                    {"gene": "BRCA1", "hgvs_p": "p.Ala1708Glu", "hypothesis_score_percent": 96.0},
                ]
            ).to_csv(hypothesis_path, index=False)

            biological_manifest_path = tmp_path / "biological_manifest.json"
            biological_manifest_path.write_text(
                json.dumps(
                    {
                        "artifact_paths": {"training_table": str(training_table)},
                        "hotspots_path": str(hotspots_path),
                        "review_upgrade_candidates_path": str(review_path),
                        "hypothesis_variants_path": str(hypothesis_path),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            gene_expansion_manifest_path = tmp_path / "gene_expansion_manifest.json"
            gene_expansion_manifest_path.write_text(
                json.dumps(
                    {
                        "top_candidates": [
                            {"gene": "TP53", "expansion_priority_percent": 85.3, "priority_band": "ready"},
                            {"gene": "PTEN", "expansion_priority_percent": 74.5, "priority_band": "strong"},
                            {"gene": "KRAS", "expansion_priority_percent": 70.6, "priority_band": "strong"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            pd.DataFrame(
                [
                    {"feature": "gene", "importance_mean": 0.09, "importance_std": 0.01},
                    {"feature": "position", "importance_mean": 0.08, "importance_std": 0.01},
                    {"feature": "prime_product", "importance_mean": 0.03, "importance_std": 0.01},
                    {"feature": "prime_diff", "importance_mean": 0.02, "importance_std": 0.01},
                    {"feature": "biochemical_severity_score", "importance_mean": 0.01, "importance_std": 0.01},
                ]
            ).to_csv(tmp_path / "study_feature_importance_hybrid.csv", index=False)

            pd.DataFrame(
                [
                    {"feature": "codon_count_ref", "importance_mean": 0.04, "importance_std": 0.01},
                    {"feature": "prime_ref", "importance_mean": 0.03, "importance_std": 0.01},
                    {"feature": "prime_diff", "importance_mean": 0.02, "importance_std": 0.01},
                    {"feature": "prime_product", "importance_mean": 0.02, "importance_std": 0.01},
                ]
            ).to_csv(tmp_path / "study_feature_importance_prime_only.csv", index=False)

            results = {
                "study_design": type("StudyDesign", (), {"baseline_experiment": "external_predictors_only"})(),
                "training_metrics": pd.DataFrame(
                    [
                        {"experiment": "hybrid__random_forest", "feature_set": "hybrid", "auc_roc": 0.84, "auc_pr": 0.72, "mcc": 0.48},
                        {"experiment": "prime_only__random_forest", "feature_set": "prime_only", "auc_roc": 0.76, "auc_pr": 0.50, "mcc": 0.30},
                        {"experiment": "biochemical_only__random_forest", "feature_set": "biochemical_only", "auc_roc": 0.80, "auc_pr": 0.67, "mcc": 0.41},
                        {"experiment": "external_predictors_only__random_forest", "feature_set": "external_predictors_only", "auc_roc": 0.62, "auc_pr": 0.46, "mcc": 0.22},
                    ]
                ),
                "external_evaluation_metrics": pd.DataFrame(
                    [
                        {"cohort": "expert_a", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "feature_set": "hybrid", "auc_roc": 0.91, "auc_pr": 0.84, "mcc": 0.70},
                        {"cohort": "expert_a", "evaluation_group": "combined", "experiment": "biochemical_only__random_forest", "feature_set": "biochemical_only", "auc_roc": 0.84, "auc_pr": 0.75, "mcc": 0.55},
                        {"cohort": "expert_b", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "feature_set": "hybrid", "auc_roc": 0.89, "auc_pr": 0.81, "mcc": 0.63},
                        {"cohort": "expert_b", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "feature_set": "external_predictors_only", "auc_roc": 0.82, "auc_pr": 0.72, "mcc": 0.49},
                    ]
                ),
                "external_pairwise_comparisons": pd.DataFrame(
                    [
                        {"cohort": "expert_a", "metric": "auc_roc", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only", "delta_mean": 0.05, "ci_lower_95": 0.01, "ci_upper_95": 0.09},
                        {"cohort": "expert_b", "metric": "auc_roc", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only", "delta_mean": 0.03, "ci_lower_95": 0.005, "ci_upper_95": 0.07},
                    ]
                ),
                "training_metrics_path": str(tmp_path / "study_training_metrics.csv"),
            }

            export_paths = export_prime_intelligence_package(
                results,
                output_dir=str(tmp_path),
                biological_discovery_manifest_path=str(biological_manifest_path),
                gene_expansion_manifest_path=str(gene_expansion_manifest_path),
            )

            self.assertTrue(Path(export_paths["prime_intelligence_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["prime_intelligence_report_markdown_path"]).exists())
            manifest = json.loads(Path(export_paths["prime_intelligence_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertGreaterEqual(manifest["summary"]["overall_prime_intelligence_percent"], 70)
            self.assertEqual(manifest["summary"]["best_prime_internal_experiment"], "hybrid__random_forest")
            self.assertEqual(manifest["summary"]["top_candidate_gene_beyond_brca"], "TP53")

    def test_export_multigene_rollout_plan_prioritizes_phase_1_genes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            gene_expansion_manifest_path = tmp_path / "gene_expansion_manifest.json"
            prime_intelligence_manifest_path = tmp_path / "prime_intelligence_manifest.json"

            gene_expansion_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {"top_candidate_genes": ["TP53", "PTEN", "MSH2"]},
                        "top_candidates": [
                            {"gene": "TP53", "expansion_priority_percent": 85.3, "priority_band": "ready", "clinvar_labeled_rows": 784, "clinvar_expert_rows": 254, "mavedb_score_set_count": 15, "mavedb_score_rows": 53905, "gnomad_direct_api_ready": True},
                            {"gene": "PTEN", "expansion_priority_percent": 74.5, "priority_band": "strong", "clinvar_labeled_rows": 505, "clinvar_expert_rows": 168, "mavedb_score_set_count": 6, "mavedb_score_rows": 25537, "gnomad_direct_api_ready": True},
                            {"gene": "MSH2", "expansion_priority_percent": 73.9, "priority_band": "strong", "clinvar_labeled_rows": 858, "clinvar_expert_rows": 150, "mavedb_score_set_count": 3, "mavedb_score_rows": 18606, "gnomad_direct_api_ready": True},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            prime_intelligence_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "cross_gene_runway_percent": 85,
                            "prime_biological_alignment_percent": 81,
                            "top_candidate_gene_beyond_brca": "TP53",
                        }
                    }
                ),
                encoding="utf-8",
            )

            manifest = export_multigene_rollout_plan(
                gene_expansion_manifest_path=str(gene_expansion_manifest_path),
                prime_intelligence_manifest_path=str(prime_intelligence_manifest_path),
                output_dir=str(tmp_path / "rollout"),
                max_phase_1=2,
                max_phase_2=1,
                max_total_genes=3,
            )

            self.assertGreaterEqual(manifest["summary"]["overall_rollout_readiness_percent"], 75)
            self.assertEqual(manifest["summary"]["phase_1_genes"][0], "TP53")
            self.assertEqual(manifest["summary"]["prime_top_candidate_gene"], "TP53")

    def test_export_multigene_study_factory_generates_scaffolds(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            rollout_manifest_path = tmp_path / "multigene_rollout_manifest.json"
            rollout_csv_path = tmp_path / "multigene_rollout_plan.csv"

            pd.DataFrame(
                [
                    {"gene": "TP53", "rank": 1, "rollout_phase": "phase_1_immediate", "expansion_priority_percent": 85.3, "prime_priority": "high"},
                    {"gene": "PTEN", "rank": 2, "rollout_phase": "phase_2_expansion", "expansion_priority_percent": 74.5, "prime_priority": "medium"},
                ]
            ).to_csv(rollout_csv_path, index=False)
            rollout_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "phase_1_genes": ["TP53"],
                            "phase_2_genes": ["PTEN"],
                            "phase_3_genes": [],
                        },
                        "rollout_csv_path": str(rollout_csv_path),
                    }
                ),
                encoding="utf-8",
            )

            manifest = export_multigene_study_factory(
                rollout_manifest_path=str(rollout_manifest_path),
                output_dir=str(tmp_path / "study_factory"),
                workspace_root=str(tmp_path / "workspace"),
            )

            scaffold_index = pd.read_csv(manifest["scaffold_index_path"])
            tasks = pd.read_csv(manifest["tasks_path"])
            self.assertEqual(set(scaffold_index["gene"].astype(str)), {"TP53", "PTEN"})
            self.assertIn("benchmark_config_path", scaffold_index.columns)
            self.assertGreaterEqual(len(tasks), 10)
            self.assertTrue(Path(manifest["markdown_path"]).exists())


class StudyBenchmarkTests(unittest.TestCase):
    def test_load_study_design_reads_train_and_external_cohorts(self):
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        study = load_study_design(str(config_path))

        self.assertEqual(study.name, "Public BRCA Benchmark Example")
        self.assertEqual(len(study.cohorts or []), 2)
        self.assertEqual((study.cohorts or [])[0].role, "train")
        self.assertEqual(study.consensus_top_k, 3)

    def test_load_study_design_reads_model_families_when_declared(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "study.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[study]",
                        'name = "Advanced Benchmark"',
                        'model_families = ["random_forest", "logistic_regression"]',
                        "consensus_top_k = 2",
                        "",
                        "[[cohorts]]",
                        'name = "train_set"',
                        'role = "train"',
                        'source_config = "configs/public_brca_example.toml"',
                    ]
                ),
                encoding="utf-8",
            )

            study = load_study_design(str(config_path))

        self.assertEqual(study.model_families, ["random_forest", "logistic_regression"])
        self.assertEqual(study.consensus_top_k, 2)

    def test_gene_balanced_specialist_selects_per_gene_and_scores_external_cohort(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.95, "signal_external": 0.82},
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Arg71Gly", "signal_prime": 0.91, "signal_external": 0.77},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.12, "signal_external": 0.18},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Met18Thr", "signal_prime": 0.09, "signal_external": 0.21},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.84, "signal_external": 0.93},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Gly2508Ser", "signal_prime": 0.81, "signal_external": 0.89},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.23, "signal_external": 0.09},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Lys2729Asn", "signal_prime": 0.27, "signal_external": 0.14},
            ]
        )
        gene_training_metrics = {
            "BRCA1": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.92, "auc_pr": 0.88, "mcc": 0.74},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.81, "auc_pr": 0.75, "mcc": 0.55},
                ]
            ),
            "BRCA2": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.90, "auc_pr": 0.66, "mcc": 0.42},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.87, "auc_pr": 0.80, "mcc": 0.69},
                ]
            ),
        }
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }

        manifest = build_gene_specialist_manifest(
            gene_training_metrics=gene_training_metrics,
            train_df=train_df,
            feature_sets=feature_sets,
            primary_metric="auc_roc",
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        selected = {row["gene"]: row["selected_experiment"] for row in manifest.to_dict(orient="records")}
        self.assertEqual(selected["BRCA1"], "hybrid_plus_external")
        self.assertEqual(selected["BRCA2"], "external_predictors_only")

        specialists = train_gene_specialist_models(
            train_df=train_df,
            specialist_manifest=manifest,
            feature_sets=feature_sets,
        )
        self.assertEqual(set(specialists.keys()), {"BRCA1", "BRCA2"})

        external_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Ala1708Glu", "signal_prime": 0.88, "signal_external": 0.79},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Leu52Phe", "signal_prime": 0.18, "signal_external": 0.20},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Asp2723His", "signal_prime": 0.73, "signal_external": 0.86},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Gly3076Ala", "signal_prime": 0.26, "signal_external": 0.11},
            ]
        )
        metrics_df, score_frame = evaluate_gene_specialist_on_cohort(
            trained_gene_specialists=specialists,
            df=external_df,
            cohort_name="external_validation",
            cohort_role="external_test",
        )

        self.assertFalse(metrics_df.empty)
        self.assertIn("gene_balanced_specialist", set(metrics_df["experiment"].astype(str)))
        self.assertIn("score__gene_balanced_specialist", score_frame.columns)
        self.assertEqual(set(metrics_df["evaluation_group"].astype(str)), {"combined", "BRCA1", "BRCA2"})

    def test_gene_balanced_specialist_falls_back_to_global_models_when_local_gene_training_is_too_small(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.95, "signal_external": 0.82},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.12, "signal_external": 0.18},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.84, "signal_external": 0.93},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.23, "signal_external": 0.09},
            ]
        )
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }
        global_training_metrics = pd.DataFrame(
            [
                {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.91, "auc_pr": 0.88, "mcc": 0.74},
                {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.84, "auc_pr": 0.78, "mcc": 0.58},
            ]
        )

        manifest = build_gene_specialist_manifest(
            gene_training_metrics={},
            train_df=train_df,
            feature_sets=feature_sets,
            global_training_metrics=global_training_metrics,
            primary_metric="auc_roc",
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        self.assertEqual(set(manifest["training_origin"].astype(str)), {"global_fallback"})

        global_model = object()
        specialists = train_gene_specialist_models(
            train_df=train_df,
            specialist_manifest=manifest,
            feature_sets=feature_sets,
            global_trained_models={"hybrid_plus_external": global_model},
        )

        self.assertEqual(set(specialists.keys()), {"BRCA1", "BRCA2"})
        self.assertTrue(all(payload["training_origin"] == "global_fallback" for payload in specialists.values()))
        self.assertTrue(all(payload["pipeline"] is global_model for payload in specialists.values()))

    def test_gene_adaptive_blend_falls_back_to_global_metrics_when_local_gene_metrics_are_missing(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.95, "signal_external": 0.82},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.12, "signal_external": 0.18},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.84, "signal_external": 0.93},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.23, "signal_external": 0.09},
            ]
        )
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }
        global_training_metrics = pd.DataFrame(
            [
                {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.91, "auc_pr": 0.88, "mcc": 0.74},
                {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.84, "auc_pr": 0.78, "mcc": 0.58},
            ]
        )

        manifest = build_gene_adaptive_blend_manifest(
            gene_training_metrics={},
            train_df=train_df,
            feature_sets=feature_sets,
            global_training_metrics=global_training_metrics,
            primary_metric="auc_roc",
            baseline_experiment="external_predictors_only",
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        self.assertEqual(set(manifest["selection_origin"].astype(str)), {"global_fallback"})

        global_prime_model = object()
        global_baseline_model = object()
        blends = train_gene_adaptive_blend_models(
            train_df=train_df,
            blend_manifest=manifest,
            feature_sets=feature_sets,
            global_trained_models={
                "hybrid_plus_external": global_prime_model,
                "external_predictors_only": global_baseline_model,
            },
        )

        self.assertEqual(set(blends.keys()), {"BRCA1", "BRCA2"})
        self.assertTrue(all(payload["training_origin"] == "global_fallback" for payload in blends.values()))
        self.assertTrue(all(payload["prime_model"] is global_prime_model for payload in blends.values()))
        self.assertTrue(all(payload["baseline_model"] is global_baseline_model for payload in blends.values()))

    def test_gene_adaptive_blend_builds_and_scores_external_cohort(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.96, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Arg71Gly", "signal_prime": 0.90, "signal_external": 0.74},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.20, "signal_external": 0.32},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Met18Thr", "signal_prime": 0.16, "signal_external": 0.29},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.78, "signal_external": 0.91},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Gly2508Ser", "signal_prime": 0.75, "signal_external": 0.87},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.31, "signal_external": 0.18},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Lys2729Asn", "signal_prime": 0.28, "signal_external": 0.14},
            ]
        )
        gene_training_metrics = {
            "BRCA1": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.91, "auc_pr": 0.84, "mcc": 0.67},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.83, "auc_pr": 0.73, "mcc": 0.52},
                ]
            ),
            "BRCA2": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.88, "auc_pr": 0.68, "mcc": 0.46},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.86, "auc_pr": 0.79, "mcc": 0.66},
                ]
            ),
        }
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }

        manifest = build_gene_adaptive_blend_manifest(
            gene_training_metrics=gene_training_metrics,
            train_df=train_df,
            feature_sets=feature_sets,
            primary_metric="auc_roc",
            baseline_experiment="external_predictors_only",
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        self.assertTrue(((manifest["blend_weight_prime"].astype(float) >= 0.0) & (manifest["blend_weight_prime"].astype(float) <= 1.0)).all())

        blends = train_gene_adaptive_blend_models(
            train_df=train_df,
            blend_manifest=manifest,
            feature_sets=feature_sets,
        )
        self.assertEqual(set(blends.keys()), {"BRCA1", "BRCA2"})

        external_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Ala1708Glu", "signal_prime": 0.85, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Leu52Phe", "signal_prime": 0.22, "signal_external": 0.28},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Asp2723His", "signal_prime": 0.71, "signal_external": 0.88},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Gly3076Ala", "signal_prime": 0.30, "signal_external": 0.16},
            ]
        )
        metrics_df, score_frame = evaluate_gene_adaptive_blend_on_cohort(
            trained_gene_blends=blends,
            df=external_df,
            cohort_name="external_validation",
            cohort_role="external_test",
        )

        self.assertFalse(metrics_df.empty)
        self.assertIn("hybrid_external_gene_adaptive_blend", set(metrics_df["experiment"].astype(str)))
        self.assertIn("score__hybrid_external_gene_adaptive_blend", score_frame.columns)
        self.assertEqual(set(metrics_df["evaluation_group"].astype(str)), {"combined", "BRCA1", "BRCA2"})

    def test_gene_calibrated_blend_builds_and_scores_external_cohort(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.96, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Arg71Gly", "signal_prime": 0.90, "signal_external": 0.74},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.20, "signal_external": 0.32},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Met18Thr", "signal_prime": 0.16, "signal_external": 0.29},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.78, "signal_external": 0.91},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Gly2508Ser", "signal_prime": 0.75, "signal_external": 0.87},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.31, "signal_external": 0.18},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Lys2729Asn", "signal_prime": 0.28, "signal_external": 0.14},
            ]
        )
        gene_training_metrics = {
            "BRCA1": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.91, "auc_pr": 0.84, "mcc": 0.67},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.83, "auc_pr": 0.73, "mcc": 0.52},
                ]
            ),
            "BRCA2": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.88, "auc_pr": 0.68, "mcc": 0.46},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.86, "auc_pr": 0.79, "mcc": 0.66},
                ]
            ),
        }
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }

        adaptive_manifest = build_gene_adaptive_blend_manifest(
            gene_training_metrics=gene_training_metrics,
            train_df=train_df,
            feature_sets=feature_sets,
            primary_metric="auc_roc",
            baseline_experiment="external_predictors_only",
        )
        manifest = build_gene_calibrated_blend_manifest(
            train_df=train_df,
            blend_manifest=adaptive_manifest,
            feature_sets=feature_sets,
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        self.assertTrue({"calibrator_kind", "calibrator_slope", "calibrator_intercept"}.issubset(set(manifest.columns)))

        blends = train_gene_calibrated_blend_models(
            train_df=train_df,
            blend_manifest=manifest,
            feature_sets=feature_sets,
        )
        self.assertEqual(set(blends.keys()), {"BRCA1", "BRCA2"})
        self.assertTrue(all("calibrator" in payload for payload in blends.values()))

        external_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Ala1708Glu", "signal_prime": 0.85, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Leu52Phe", "signal_prime": 0.22, "signal_external": 0.28},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Asp2723His", "signal_prime": 0.71, "signal_external": 0.88},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Gly3076Ala", "signal_prime": 0.30, "signal_external": 0.16},
            ]
        )
        metrics_df, score_frame = evaluate_gene_calibrated_blend_on_cohort(
            trained_gene_blends=blends,
            df=external_df,
            cohort_name="external_validation",
            cohort_role="external_test",
        )

        self.assertFalse(metrics_df.empty)
        self.assertIn("hybrid_external_gene_calibrated_blend", set(metrics_df["experiment"].astype(str)))
        self.assertIn("score__hybrid_external_gene_calibrated_blend", score_frame.columns)
        self.assertEqual(set(metrics_df["evaluation_group"].astype(str)), {"combined", "BRCA1", "BRCA2"})

    def test_gene_robust_blend_builds_and_scores_external_cohort(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Cys61Gly", "signal_prime": 0.96, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Arg71Gly", "signal_prime": 0.90, "signal_external": 0.74},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Ile21Val", "signal_prime": 0.20, "signal_external": 0.32},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Met18Thr", "signal_prime": 0.16, "signal_external": 0.29},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Trp1692Cys", "signal_prime": 0.78, "signal_external": 0.91},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Gly2508Ser", "signal_prime": 0.75, "signal_external": 0.87},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Val2109Ile", "signal_prime": 0.31, "signal_external": 0.18},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Lys2729Asn", "signal_prime": 0.28, "signal_external": 0.14},
            ]
        )
        gene_training_metrics = {
            "BRCA1": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.91, "auc_pr": 0.84, "mcc": 0.67},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.83, "auc_pr": 0.73, "mcc": 0.52},
                ]
            ),
            "BRCA2": pd.DataFrame(
                [
                    {"experiment": "hybrid_plus_external", "feature_set": "hybrid_plus_external", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.88, "auc_pr": 0.68, "mcc": 0.46},
                    {"experiment": "external_predictors_only", "feature_set": "external_predictors_only", "model_family": "random_forest", "is_primary_experiment": 1, "auc_roc": 0.86, "auc_pr": 0.79, "mcc": 0.66},
                ]
            ),
        }
        feature_sets = {
            "hybrid_plus_external": ["signal_prime", "signal_external"],
            "external_predictors_only": ["signal_external"],
        }

        manifest = build_gene_robust_blend_manifest(
            gene_training_metrics=gene_training_metrics,
            train_df=train_df,
            feature_sets=feature_sets,
            baseline_experiment="external_predictors_only",
        )

        self.assertEqual(set(manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
        self.assertEqual(set(manifest["optimization_mode"].astype(str)), {"robust"})

        blends = train_gene_adaptive_blend_models(
            train_df=train_df,
            blend_manifest=manifest,
            feature_sets=feature_sets,
        )
        self.assertEqual(set(blends.keys()), {"BRCA1", "BRCA2"})

        external_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "label": 1, "variant": "BRCA1 p.Ala1708Glu", "signal_prime": 0.85, "signal_external": 0.76},
                {"gene": "BRCA1", "label": 0, "variant": "BRCA1 p.Leu52Phe", "signal_prime": 0.22, "signal_external": 0.28},
                {"gene": "BRCA2", "label": 1, "variant": "BRCA2 p.Asp2723His", "signal_prime": 0.71, "signal_external": 0.88},
                {"gene": "BRCA2", "label": 0, "variant": "BRCA2 p.Gly3076Ala", "signal_prime": 0.30, "signal_external": 0.16},
            ]
        )
        metrics_df, score_frame = evaluate_gene_adaptive_blend_on_cohort(
            trained_gene_blends=blends,
            df=external_df,
            cohort_name="external_validation",
            cohort_role="external_test",
            experiment_name="hybrid_external_gene_robust_blend",
            model_family="gene_robust_blend",
        )

        self.assertFalse(metrics_df.empty)
        self.assertIn("hybrid_external_gene_robust_blend", set(metrics_df["experiment"].astype(str)))
        self.assertIn("score__hybrid_external_gene_robust_blend", score_frame.columns)
        self.assertEqual(set(metrics_df["evaluation_group"].astype(str)), {"combined", "BRCA1", "BRCA2"})

    def test_run_publication_study_generates_external_metrics(self):
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_publication_study(
                config_path=str(config_path),
                output_dir=tmp_dir,
            )

            external_metrics = results["external_evaluation_metrics"]
            self.assertFalse(external_metrics.empty)
            self.assertIn("cohort", external_metrics.columns)
            self.assertIn("evaluation_group", external_metrics.columns)
            self.assertIn("consensus_top3", set(external_metrics["experiment"].astype(str)))
            self.assertIn("gene_balanced_specialist", set(external_metrics["experiment"].astype(str)))
            self.assertIn("hybrid_external_gene_robust_blend", set(external_metrics["experiment"].astype(str)))
            self.assertIn("hybrid_external_gene_calibrated_blend", set(external_metrics["experiment"].astype(str)))
            self.assertIn("gene_balanced_specialist", set(results["training_metrics"]["experiment"].astype(str)))
            self.assertIn("hybrid_external_gene_robust_blend", set(results["training_metrics"]["experiment"].astype(str)))
            self.assertIn("hybrid_external_gene_calibrated_blend", set(results["training_metrics"]["experiment"].astype(str)))
            self.assertTrue(Path(results["consensus_members_path"]).exists())
            self.assertTrue(Path(results["gene_specialist_manifest_path"]).exists())
            self.assertTrue(Path(results["gene_robust_blend_manifest_path"]).exists())
            self.assertTrue(Path(results["gene_calibrated_blend_manifest_path"]).exists())
            self.assertTrue(Path(results["study_summary_report_path"]).exists())
            self.assertTrue(Path(results["cohort_independence_manifest_path"]).exists())
            self.assertTrue(Path(results["cohort_independence_report_markdown_path"]).exists())
            self.assertTrue(Path(results["study_cohort_freeze_manifest_path"]).exists())
            self.assertTrue(Path(results["study_cohort_freeze_markdown_path"]).exists())
            self.assertTrue(Path(results["scientific_dossier_markdown_path"]).exists())
            self.assertTrue(Path(results["scientific_dossier_html_path"]).exists())
            self.assertTrue(Path(results["publication_readiness_report_markdown_path"]).exists())
            self.assertTrue(Path(results["publication_readiness_report_html_path"]).exists())
            self.assertTrue(Path(results["publication_readiness_manifest_path"]).exists())
            self.assertTrue(Path(results["comparative_evidence_manifest_path"]).exists())
            self.assertTrue(Path(results["comparative_evidence_report_markdown_path"]).exists())
            self.assertTrue(Path(results["claim_strength_manifest_path"]).exists())
            self.assertTrue(Path(results["claim_strength_report_markdown_path"]).exists())
            self.assertTrue(Path(results["baseline_coverage_manifest_path"]).exists())
            self.assertTrue(Path(results["methods_package_manifest_path"]).exists())
            self.assertTrue(Path(results["manuscript_package_markdown_path"]).exists())
            self.assertTrue(Path(results["manuscript_package_html_path"]).exists())
            self.assertTrue(Path(results["manuscript_package_manifest_path"]).exists())
            self.assertTrue(Path(results["study_validation_lock_manifest_path"]).exists())
            self.assertTrue(Path(results["study_validation_lock_markdown_path"]).exists())
            self.assertTrue(Path(results["study_release_manifest_path"]).exists())
            self.assertTrue(Path(results["study_release_registry_path"]).exists())
            readiness_manifest = json.loads(Path(results["publication_readiness_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", readiness_manifest)
            self.assertIn("overall_readiness_percent", readiness_manifest["summary"])
            self.assertIn("ready_for_submission", readiness_manifest["summary"])
            comparative_manifest = json.loads(Path(results["comparative_evidence_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", comparative_manifest)
            self.assertIn("overall_comparative_strength_percent", comparative_manifest["summary"])
            gene_specialist_manifest = pd.read_csv(results["gene_specialist_manifest_path"])
            self.assertEqual(set(gene_specialist_manifest["gene"].astype(str)), {"BRCA1", "BRCA2"})
            claim_manifest = json.loads(Path(results["claim_strength_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", claim_manifest)
            self.assertIn("overall_claim_strength_percent", claim_manifest["summary"])
            baseline_manifest = json.loads(Path(results["baseline_coverage_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", baseline_manifest)
            self.assertIn("overall_coverage_percent", baseline_manifest["summary"])
            methods_manifest = json.loads(Path(results["methods_package_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", methods_manifest)
            self.assertIn("best_internal_experiment", methods_manifest["summary"])
            manuscript_manifest = json.loads(Path(results["manuscript_package_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manuscript_manifest)
            self.assertIn("best_internal_experiment", manuscript_manifest["summary"])
            validation_manifest = json.loads(Path(results["study_validation_lock_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", validation_manifest)
            self.assertIn("overall_validation_lock_percent", validation_manifest["summary"])
            study_release_manifest = json.loads(Path(results["study_release_manifest_path"]).read_text(encoding="utf-8"))
            independence_manifest = json.loads(Path(results["cohort_independence_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", independence_manifest)
            self.assertIn("overall_independence_percent", independence_manifest["summary"])
            freeze_manifest = json.loads(Path(results["study_cohort_freeze_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", freeze_manifest)
            self.assertIn("overall_real_data_readiness_percent", freeze_manifest["summary"])
            self.assertIn("claim_strength_manifest_path", study_release_manifest)
            self.assertIn("claim_strength_percent", study_release_manifest)
            self.assertIn("claim_tier", study_release_manifest)
            self.assertIn("publication_readiness_manifest_path", study_release_manifest)
            self.assertIn("publication_readiness_percent", study_release_manifest)
            self.assertIn("publication_ready_for_submission", study_release_manifest)
            self.assertIn("cohort_independence_manifest_path", study_release_manifest)
            self.assertIn("cohort_independence_percent", study_release_manifest)
            self.assertIn("study_cohort_freeze_manifest_path", study_release_manifest)
            self.assertIn("real_data_readiness_percent", study_release_manifest)
            self.assertIn("comparative_evidence_manifest_path", study_release_manifest)
            self.assertIn("comparative_evidence_percent", study_release_manifest)
            self.assertIn("baseline_coverage_manifest_path", study_release_manifest)
            self.assertIn("methods_package_manifest_path", study_release_manifest)
            self.assertIn("manuscript_package_manifest_path", study_release_manifest)
            self.assertIn("study_validation_lock_manifest_path", study_release_manifest)
            self.assertIn("validation_lock_percent", study_release_manifest)

    def test_export_study_preflight_generates_manifest(self):
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_paths = export_study_preflight(
                config_path=str(config_path),
                output_dir=tmp_dir,
            )

            self.assertTrue(Path(export_paths["study_preflight_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["study_preflight_report_markdown_path"]).exists())
            self.assertTrue(Path(export_paths["study_preflight_cohorts_path"]).exists())
            self.assertTrue(Path(export_paths["study_preflight_independence_pairs_path"]).exists())
            preflight_manifest = json.loads(Path(export_paths["study_preflight_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", preflight_manifest)
            self.assertIn("overall_preflight_percent", preflight_manifest["summary"])
            self.assertIn("ready_to_run", preflight_manifest["summary"])
            self.assertIn("cohort_independence_percent", preflight_manifest["summary"])

    def test_export_study_cohort_freeze_detects_example_sources(self):
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_paths = export_study_cohort_freeze(
                config_path=str(config_path),
                output_dir=tmp_dir,
            )

            self.assertTrue(Path(export_paths["study_cohort_freeze_manifest_path"]).exists())
            manifest = json.loads(Path(export_paths["study_cohort_freeze_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertFalse(manifest["summary"]["ready_for_real_data_study"])
            self.assertGreaterEqual(manifest["summary"]["n_example_blocked_cohorts"], 1)

    def test_export_cohort_independence_generates_manifest(self):
        train_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": 1},
                {"gene": "BRCA1", "hgvs_p": "p.Ala1708Glu", "label": 1},
                {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "label": 0},
            ]
        )
        external_df = pd.DataFrame(
            [
                {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "label": 0},
                {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "label": 0},
                {"gene": "BRCA2", "hgvs_p": "p.Trp2626Cys", "label": 1},
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            export_paths = export_cohort_independence_package(
                [
                    {"cohort_name": "train", "role": "train", "dataframe": train_df},
                    {"cohort_name": "external", "role": "external_test", "dataframe": external_df},
                ],
                output_dir=tmp_dir,
            )

            self.assertTrue(Path(export_paths["cohort_independence_manifest_path"]).exists())
            manifest = json.loads(Path(export_paths["cohort_independence_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertLess(manifest["summary"]["overall_independence_percent"], 100)
            self.assertEqual(manifest["summary"]["max_variant_overlap_percent"], 66)

    def test_export_comparative_evidence_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_a_path = tmp_path / "study_scores_clinvar_expert_external_a.csv"
            cohort_b_path = tmp_path / "study_scores_external_b.csv"
            pd.DataFrame(
                [
                    {"variant": "BRCA1 p.Cys61Gly", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.93, "score__external_predictors_only__random_forest": 0.78},
                    {"variant": "BRCA1 p.Met1775Arg", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.89, "score__external_predictors_only__random_forest": 0.41},
                    {"variant": "BRCA1 p.Val1736Ala", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.18, "score__external_predictors_only__random_forest": 0.55},
                    {"variant": "BRCA1 p.Ser1613Gly", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.11, "score__external_predictors_only__random_forest": 0.29},
                ]
            ).to_csv(cohort_a_path, index=False)
            pd.DataFrame(
                [
                    {"variant": "BRCA2 p.Asp2723His", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.87, "score__external_predictors_only__random_forest": 0.73},
                    {"variant": "BRCA2 p.Trp2626Cys", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.84, "score__external_predictors_only__random_forest": 0.39},
                    {"variant": "BRCA2 p.Lys3326Ter", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.22, "score__external_predictors_only__random_forest": 0.58},
                    {"variant": "BRCA2 p.Val2109Ile", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.19, "score__external_predictors_only__random_forest": 0.31},
                ]
            ).to_csv(cohort_b_path, index=False)

            results = {
                "study_design": type(
                    "StudyDesignStub",
                    (),
                    {
                        "name": "Comparative Study",
                        "primary_metric": "auc_roc",
                        "baseline_experiment": "external_predictors_only__random_forest",
                    },
                )(),
                "training_metrics": pd.DataFrame(
                    [
                        {"experiment": "hybrid__random_forest", "auc_roc": 0.91, "auc_pr": 0.89, "mcc": 0.74, "is_primary_experiment": 1},
                        {"experiment": "external_predictors_only__random_forest", "auc_roc": 0.86, "auc_pr": 0.82, "mcc": 0.61, "is_primary_experiment": 1},
                    ]
                ),
                "external_evaluation_metrics": pd.DataFrame(
                    [
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.88},
                        {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.84},
                    ]
                ),
                "external_pairwise_comparisons": pd.DataFrame(
                    [
                        {
                            "cohort": "clinvar_expert_external_a",
                            "cohort_role": "external_test",
                            "experiment": "hybrid__random_forest",
                            "baseline_experiment": "external_predictors_only__random_forest",
                            "metric": "auc_roc",
                            "delta_mean": 0.041,
                            "ci_lower_95": 0.010,
                            "ci_upper_95": 0.072,
                            "n_bootstrap_valid": 180,
                        },
                        {
                            "cohort": "external_b",
                            "cohort_role": "external_test",
                            "experiment": "hybrid__random_forest",
                            "baseline_experiment": "external_predictors_only__random_forest",
                            "metric": "auc_roc",
                            "delta_mean": 0.018,
                            "ci_lower_95": -0.004,
                            "ci_upper_95": 0.038,
                            "n_bootstrap_valid": 176,
                        },
                    ]
                ),
                "external_score_paths": {
                    "clinvar_expert_external_a": str(cohort_a_path),
                    "external_b": str(cohort_b_path),
                },
            }

            export_paths = export_comparative_evidence_package(results, output_dir=tmp_dir)

            self.assertTrue(Path(export_paths["comparative_evidence_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["comparative_evidence_report_markdown_path"]).exists())
            self.assertTrue(Path(export_paths["comparative_evidence_feature_sets_path"]).exists())
            self.assertTrue(Path(export_paths["comparative_evidence_pooled_support_path"]).exists())
            manifest = json.loads(Path(export_paths["comparative_evidence_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertGreaterEqual(manifest["summary"]["overall_comparative_strength_percent"], 60)
            self.assertEqual(manifest["summary"]["best_supported_experiment"], "hybrid__random_forest")
            self.assertEqual(manifest["summary"]["aggregate_supported_experiment"], "hybrid__random_forest")
            self.assertGreaterEqual(manifest["summary"]["aggregate_directional_confidence_percent"], 90)
            self.assertGreaterEqual(manifest["summary"]["best_experiment_high_confidence_clinical_positive_rate_percent"], 100)
            self.assertGreaterEqual(manifest["summary"]["pooled_directional_confidence_percent"], 80)
            self.assertGreater(manifest["summary"]["pooled_delta_auc_roc"], 0)

    def test_export_claim_strength_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_a_path = tmp_path / "study_scores_clinvar_expert_external_a.csv"
            cohort_b_path = tmp_path / "study_scores_external_b.csv"
            pd.DataFrame(
                [
                    {"variant": "BRCA1 p.Cys61Gly", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.94, "score__external_predictors_only__random_forest": 0.79},
                    {"variant": "BRCA1 p.Arg71Gly", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.90, "score__external_predictors_only__random_forest": 0.38},
                    {"variant": "BRCA1 p.Val1736Ala", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.16, "score__external_predictors_only__random_forest": 0.61},
                    {"variant": "BRCA1 p.Ser1613Gly", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.12, "score__external_predictors_only__random_forest": 0.30},
                ]
            ).to_csv(cohort_a_path, index=False)
            pd.DataFrame(
                [
                    {"variant": "BRCA2 p.Asp2723His", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.88, "score__external_predictors_only__random_forest": 0.74},
                    {"variant": "BRCA2 p.Trp2626Cys", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.85, "score__external_predictors_only__random_forest": 0.37},
                    {"variant": "BRCA2 p.Lys3326Ter", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.21, "score__external_predictors_only__random_forest": 0.62},
                    {"variant": "BRCA2 p.Val2109Ile", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.18, "score__external_predictors_only__random_forest": 0.32},
                ]
            ).to_csv(cohort_b_path, index=False)

            results = {
                "study_design": type(
                    "StudyDesignStub",
                    (),
                    {
                        "name": "Claim Strength Study",
                        "primary_metric": "auc_roc",
                        "baseline_experiment": "external_predictors_only__random_forest",
                    },
                )(),
                "external_evaluation_metrics": pd.DataFrame(
                    [
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.88, "auc_pr": 0.84, "mcc": 0.61},
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.83, "auc_pr": 0.79, "mcc": 0.53},
                        {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.85, "auc_pr": 0.81, "mcc": 0.58},
                        {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.82, "auc_pr": 0.77, "mcc": 0.5},
                    ]
                ),
                "external_pairwise_comparisons": pd.DataFrame(
                    [
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_roc", "delta_mean": 0.041, "ci_lower_95": 0.01, "ci_upper_95": 0.072, "n_bootstrap_valid": 180},
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_pr", "delta_mean": 0.039, "ci_lower_95": 0.005, "ci_upper_95": 0.068, "n_bootstrap_valid": 180},
                        {"cohort": "external_b", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_roc", "delta_mean": 0.022, "ci_lower_95": 0.001, "ci_upper_95": 0.043, "n_bootstrap_valid": 176},
                        {"cohort": "external_b", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_pr", "delta_mean": 0.018, "ci_lower_95": -0.002, "ci_upper_95": 0.038, "n_bootstrap_valid": 176},
                    ]
                ),
                "external_score_paths": {
                    "clinvar_expert_external_a": str(cohort_a_path),
                    "external_b": str(cohort_b_path),
                },
            }

            export_paths = export_claim_strength_package(results, output_dir=tmp_dir)

            self.assertTrue(Path(export_paths["claim_strength_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["claim_strength_report_markdown_path"]).exists())
            self.assertTrue(Path(export_paths["claim_strength_candidates_path"]).exists())
            self.assertTrue(Path(export_paths["claim_strength_pooled_metric_path"]).exists())
            manifest = json.loads(Path(export_paths["claim_strength_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertGreaterEqual(manifest["summary"]["overall_claim_strength_percent"], 60)
            self.assertEqual(manifest["summary"]["selected_experiment"], "hybrid__random_forest")
            self.assertGreaterEqual(manifest["summary"]["selected_aggregate_auc_roc_confidence_percent"], 90)
            self.assertGreaterEqual(manifest["summary"]["selected_high_confidence_clinical_score_percent"], 60)
            self.assertGreaterEqual(manifest["summary"]["selected_pooled_auc_roc_support_percent"], 80)
            self.assertGreaterEqual(manifest["summary"]["selected_effective_cross_metric_support_percent"], 60)
            self.assertGreaterEqual(manifest["summary"]["selected_effective_head_to_head_leadership_percent"], 60)
            self.assertGreaterEqual(manifest["summary"]["selected_effective_no_regression_percent"], 80)
            self.assertGreaterEqual(manifest["summary"]["selected_clinical_credibility_percent"], 80)

    def test_export_external_robustness_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_a_path = tmp_path / "study_scores_clinvar_expert_external_a.csv"
            cohort_b_path = tmp_path / "study_scores_external_b.csv"
            pd.DataFrame(
                [
                    {
                        "variant": "BRCA1 p.Cys61Gly",
                        "gene": "BRCA1",
                        "label": 1,
                        "score__hybrid__random_forest": 0.92,
                        "score__external_predictors_only__random_forest": 0.76,
                    },
                    {
                        "variant": "BRCA1 p.Met1775Arg",
                        "gene": "BRCA1",
                        "label": 1,
                        "score__hybrid__random_forest": 0.88,
                        "score__external_predictors_only__random_forest": 0.72,
                    },
                    {
                        "variant": "BRCA1 p.Val1736Ala",
                        "gene": "BRCA1",
                        "label": 0,
                        "score__hybrid__random_forest": 0.18,
                        "score__external_predictors_only__random_forest": 0.31,
                    },
                    {
                        "variant": "BRCA1 p.Ser1613Gly",
                        "gene": "BRCA1",
                        "label": 0,
                        "score__hybrid__random_forest": 0.12,
                        "score__external_predictors_only__random_forest": 0.28,
                    },
                ]
            ).to_csv(cohort_a_path, index=False)
            pd.DataFrame(
                [
                    {
                        "variant": "BRCA2 p.Asp2723His",
                        "gene": "BRCA2",
                        "label": 1,
                        "score__hybrid__random_forest": 0.86,
                        "score__external_predictors_only__random_forest": 0.78,
                    },
                    {
                        "variant": "BRCA2 p.Trp2626Cys",
                        "gene": "BRCA2",
                        "label": 1,
                        "score__hybrid__random_forest": 0.81,
                        "score__external_predictors_only__random_forest": 0.71,
                    },
                    {
                        "variant": "BRCA2 p.Lys3326Ter",
                        "gene": "BRCA2",
                        "label": 0,
                        "score__hybrid__random_forest": 0.26,
                        "score__external_predictors_only__random_forest": 0.34,
                    },
                    {
                        "variant": "BRCA2 p.Asn372His",
                        "gene": "BRCA2",
                        "label": 0,
                        "score__hybrid__random_forest": 0.20,
                        "score__external_predictors_only__random_forest": 0.29,
                    },
                ]
            ).to_csv(cohort_b_path, index=False)

            results = {
                "study_design": type(
                    "StudyDesignStub",
                    (),
                    {
                        "name": "External Robustness Study",
                        "baseline_experiment": "external_predictors_only__random_forest",
                    },
                )(),
                "claim_strength_assessment": {
                    "summary": {
                        "selected_experiment": "hybrid__random_forest",
                        "selected_baseline_experiment": "external_predictors_only__random_forest",
                    }
                },
                "external_evaluation_metrics": pd.DataFrame(
                    [
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.88, "auc_pr": 0.84, "mcc": 0.61},
                        {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.83, "auc_pr": 0.79, "mcc": 0.53},
                        {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.85, "auc_pr": 0.81, "mcc": 0.58},
                        {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.82, "auc_pr": 0.77, "mcc": 0.50},
                    ]
                ),
                "external_score_paths": {
                    "clinvar_expert_external_a": str(cohort_a_path),
                    "external_b": str(cohort_b_path),
                },
            }

            export_paths = export_external_robustness_package(results, output_dir=tmp_dir)

            self.assertTrue(Path(export_paths["external_robustness_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["external_robustness_report_markdown_path"]).exists())
            self.assertTrue(Path(export_paths["external_robustness_calibration_path"]).exists())
            self.assertTrue(Path(export_paths["external_robustness_pooled_support_path"]).exists())
            manifest = json.loads(Path(export_paths["external_robustness_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertGreaterEqual(manifest["summary"]["overall_external_robustness_percent"], 60)
            self.assertEqual(manifest["summary"]["selected_experiment"], "hybrid__random_forest")
            self.assertGreaterEqual(manifest["summary"]["exact_sign_confidence_percent"], 80)
            self.assertGreaterEqual(manifest["summary"]["high_confidence_clinical_robustness_percent"], 60)
            self.assertGreaterEqual(manifest["summary"]["pooled_calibration_support_percent"], 60)
            self.assertGreaterEqual(manifest["summary"]["pooled_high_confidence_clinical_support_percent"], 40)
            self.assertGreaterEqual(manifest["summary"]["effective_high_confidence_clinical_robustness_percent"], 60)
            self.assertEqual(Path(manifest["pooled_support_path"]).name, "external_robustness_pooled_support.csv")

    def test_export_calibration_rescue_package_generates_thresholds_and_error_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            study_dir = tmp_path / "study"
            study_dir.mkdir()
            (study_dir / "claim_strength_manifest.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "selected_experiment": "hybrid__random_forest",
                            "selected_baseline_experiment": "external_predictors_only__random_forest",
                        }
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"variant": "BRCA1 p.Cys61Gly", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.72, "score__external_predictors_only__random_forest": 0.61},
                    {"variant": "BRCA1 p.Met1775Arg", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.62, "score__external_predictors_only__random_forest": 0.58},
                    {"variant": "BRCA1 p.Val1736Ala", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.70, "score__external_predictors_only__random_forest": 0.48},
                    {"variant": "BRCA1 p.Ser1613Gly", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.56, "score__external_predictors_only__random_forest": 0.41},
                    {"variant": "BRCA1 p.Ala1708Glu", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.42, "score__external_predictors_only__random_forest": 0.36},
                    {"variant": "BRCA1 p.Arg1699Gln", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.39, "score__external_predictors_only__random_forest": 0.33},
                ]
            ).to_csv(study_dir / "study_scores_bridges_like_external_validation_brca1.csv", index=False)
            pd.DataFrame(
                [
                    {"variant": "BRCA2 p.Asp2723His", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.81, "score__external_predictors_only__random_forest": 0.62},
                    {"variant": "BRCA2 p.Trp2626Cys", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.77, "score__external_predictors_only__random_forest": 0.59},
                    {"variant": "BRCA2 p.Lys3326Ter", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.31, "score__external_predictors_only__random_forest": 0.42},
                    {"variant": "BRCA2 p.Asn372His", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.24, "score__external_predictors_only__random_forest": 0.39},
                ]
            ).to_csv(study_dir / "study_scores_clinvar_expert_external_brca2.csv", index=False)
            cohort_dir = study_dir / "cohorts"
            cohort_dir.mkdir()
            pd.DataFrame(
                [
                    {"variant": "BRCA1 p.Cys61Gly", "feature_gnomad_af": None, "feature_mave_score": 0.14, "prime_diff": 12, "prime_ratio": 1.3},
                    {"variant": "BRCA1 p.Val1736Ala", "feature_gnomad_af": None, "feature_mave_score": None, "prime_diff": -4, "prime_ratio": 0.8},
                    {"variant": "BRCA1 p.Ser1613Gly", "feature_gnomad_af": 0.0001, "feature_mave_score": None, "prime_diff": 2, "prime_ratio": 1.1},
                ]
            ).to_csv(cohort_dir / "bridges_like_external_validation_brca1_processed_dataset.csv", index=False)

            results = export_calibration_rescue_package(
                study_dir=str(study_dir),
                output_dir=str(tmp_path / "calibration_rescue"),
                focus_cohort="bridges_like_external_validation_brca1",
            )

            self.assertTrue(Path(results["calibration_rescue_manifest_path"]).exists())
            self.assertTrue(Path(results["calibration_rescue_thresholds_path"]).exists())
            self.assertTrue(Path(results["calibration_rescue_error_triage_queue_path"]).exists())
            manifest = json.loads(Path(results["calibration_rescue_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["candidate_experiment"], "hybrid__random_forest")
            self.assertEqual(manifest["baseline_experiment"], "external_predictors_only__random_forest")
            self.assertGreaterEqual(manifest["n_cohorts"], 2)
            summary = pd.read_csv(results["calibration_rescue_summary_path"])
            self.assertIn("calibrated_ece", summary.columns)
            self.assertIn("best_calibrated_threshold", summary.columns)
            queue = pd.read_csv(results["calibration_rescue_error_triage_queue_path"])
            self.assertIn("priority_score", queue.columns)
            self.assertIn("calibration_effect", queue.columns)

    def test_export_locked_calibration_holdout_uses_disjoint_test_split(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            study_dir = tmp_path / "study"
            study_dir.mkdir()
            (study_dir / "claim_strength_manifest.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "selected_experiment": "hybrid__random_forest",
                            "selected_baseline_experiment": "external_predictors_only__random_forest",
                        }
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"variant": "BRCA1 p.Ala1Val", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.82, "score__external_predictors_only__random_forest": 0.62},
                    {"variant": "BRCA1 p.Ala2Val", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.75, "score__external_predictors_only__random_forest": 0.61},
                    {"variant": "BRCA1 p.Ala3Val", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.70, "score__external_predictors_only__random_forest": 0.59},
                    {"variant": "BRCA1 p.Ala4Val", "gene": "BRCA1", "label": 1, "score__hybrid__random_forest": 0.64, "score__external_predictors_only__random_forest": 0.58},
                    {"variant": "BRCA1 p.Gly1Ser", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.44, "score__external_predictors_only__random_forest": 0.47},
                    {"variant": "BRCA1 p.Gly2Ser", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.39, "score__external_predictors_only__random_forest": 0.43},
                    {"variant": "BRCA1 p.Gly3Ser", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.35, "score__external_predictors_only__random_forest": 0.41},
                    {"variant": "BRCA1 p.Gly4Ser", "gene": "BRCA1", "label": 0, "score__hybrid__random_forest": 0.29, "score__external_predictors_only__random_forest": 0.38},
                ]
            ).to_csv(study_dir / "study_scores_bridges_like_external_validation_brca1.csv", index=False)
            pd.DataFrame(
                [
                    {"variant": "BRCA2 p.Ala1Val", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.83, "score__external_predictors_only__random_forest": 0.65},
                    {"variant": "BRCA2 p.Ala2Val", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.77, "score__external_predictors_only__random_forest": 0.62},
                    {"variant": "BRCA2 p.Ala3Val", "gene": "BRCA2", "label": 1, "score__hybrid__random_forest": 0.73, "score__external_predictors_only__random_forest": 0.60},
                    {"variant": "BRCA2 p.Gly1Ser", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.41, "score__external_predictors_only__random_forest": 0.45},
                    {"variant": "BRCA2 p.Gly2Ser", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.33, "score__external_predictors_only__random_forest": 0.42},
                    {"variant": "BRCA2 p.Gly3Ser", "gene": "BRCA2", "label": 0, "score__hybrid__random_forest": 0.26, "score__external_predictors_only__random_forest": 0.39},
                ]
            ).to_csv(study_dir / "study_scores_clinvar_expert_external_brca2.csv", index=False)

            results = export_locked_calibration_holdout_package(
                study_dir=str(study_dir),
                output_dir=str(tmp_path / "locked_holdout"),
                focus_cohort="bridges_like_external_validation_brca1",
                split_seed_prime=104729,
            )

            manifest = json.loads(Path(results["locked_calibration_holdout_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["split_algorithm"], "stratified_sha256_prime_seed")
            self.assertGreaterEqual(manifest["n_cohorts"], 2)
            self.assertGreater(manifest["n_heldout_test_variants"], 0)
            summary = pd.read_csv(results["locked_calibration_holdout_summary_path"])
            self.assertIn("locked_calibrated_test_ece", summary.columns)
            self.assertTrue(summary["test_has_both_classes"].all())
            assignments = pd.read_csv(results["locked_calibration_holdout_assignments_path"])
            self.assertIn("split", assignments.columns)
            self.assertTrue(set(assignments["split"]).issuperset({"calibration", "test"}))
            overlap = assignments.groupby(["cohort", "variant"])["split"].nunique().max()
            self.assertEqual(overlap, 1)

    def test_export_competition_readiness_prioritizes_claims_and_variants(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            campaign = tmp_path / "campaign"
            brca = campaign / "brca_real_quick"
            locked_dir = campaign / "locked_calibration_holdout"
            calibration_dir = campaign / "calibration_rescue"
            error_dir = campaign / "brca1_lovd_error_analysis"
            alpha_dir = campaign / "alphamissense_subset_plan"
            prospective_dir = tmp_path / "prospective"
            for path in [brca, locked_dir, calibration_dir, error_dir, alpha_dir, prospective_dir]:
                path.mkdir(parents=True)
            (brca / "publication_readiness_manifest.json").write_text(json.dumps({"summary": {"overall_readiness_percent": 95}}), encoding="utf-8")
            (brca / "study_validation_lock_manifest.json").write_text(json.dumps({"summary": {"overall_validation_lock_percent": 94, "cohort_independence_percent": 100}}), encoding="utf-8")
            (brca / "claim_strength_manifest.json").write_text(json.dumps({"summary": {"overall_claim_strength_percent": 98}}), encoding="utf-8")
            (brca / "external_robustness_manifest.json").write_text(json.dumps({"summary": {"overall_external_robustness_percent": 75}}), encoding="utf-8")
            (campaign / "competition_evidence_manifest.json").write_text(
                json.dumps({"passed_targeted_tests": 37, "total_targeted_tests": 37}),
                encoding="utf-8",
            )
            locked_queue_path = locked_dir / "locked_calibration_holdout_error_queue.csv"
            pd.DataFrame(
                [
                    {
                        "cohort": "bridges_like_external_validation_brca1",
                        "variant": "BRCA1 p.C1501Y",
                        "gene": "BRCA1",
                        "label": 0,
                        "calibration_effect": "persistent_on_locked_test",
                        "raw_score": 0.97,
                        "locked_calibrated_score": 0.88,
                        "baseline_score": 0.49,
                        "priority_score": 1.7,
                        "feature_gnomad_af": "",
                        "feature_mave_score": "",
                        "prime_diff": 12,
                        "prime_ratio": 3.4,
                        "biochemical_severity_score": 7.8,
                    }
                ]
            ).to_csv(locked_queue_path, index=False)
            (locked_dir / "locked_calibration_holdout_manifest.json").write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "n_heldout_test_variants": 417,
                        "raw_test_calibration_safety_rate_percent": 50,
                        "locked_calibrated_test_safety_rate_percent": 100,
                        "error_queue_path": str(locked_queue_path),
                    }
                ),
                encoding="utf-8",
            )
            calibration_queue_path = calibration_dir / "calibration_rescue_error_triage_queue.csv"
            pd.DataFrame([{"variant": "BRCA1 p.C1501Y", "gene": "BRCA1"}]).to_csv(calibration_queue_path, index=False)
            (calibration_dir / "calibration_rescue_manifest.json").write_text(
                json.dumps({"calibrated_safety_rate_percent": 100, "error_triage_queue_path": str(calibration_queue_path)}),
                encoding="utf-8",
            )
            selected_errors_path = error_dir / "brca1_lovd_selected_model_errors.csv"
            pd.DataFrame([{"variant": "BRCA1 p.C1501Y", "gene": "BRCA1", "error_type": "false_positive"}]).to_csv(selected_errors_path, index=False)
            (error_dir / "brca1_lovd_error_analysis_manifest.json").write_text(
                json.dumps(
                    {
                        "selected_model_error_count": 32,
                        "selected_model_errors_path": str(selected_errors_path),
                        "feature_coverage": {"gnomad_af_coverage_percent": 36.31, "mavedb_score_coverage_percent": 6.55},
                    }
                ),
                encoding="utf-8",
            )
            (alpha_dir / "alphamissense_subset_plan_manifest.json").write_text(
                json.dumps({"target_genes": ["BRCA1", "BRCA2"], "plan_path": "alpha.md"}),
                encoding="utf-8",
            )
            prospective_queue_path = prospective_dir / "functional_structural_confirmation_queue.csv"
            pd.DataFrame([{"gene": "BRCA1", "hgvs_p": "p.C1501Y", "lab_status": "not_started"}]).to_csv(prospective_queue_path, index=False)
            prospective_manifest_path = prospective_dir / "prospective_validation_closure_manifest.json"
            prospective_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "prospective_validation_readiness_percent": 88,
                            "functional_structural_confirmation_queue_count": 1,
                        },
                        "functional_structural_confirmation_queue_path": str(prospective_queue_path),
                    }
                ),
                encoding="utf-8",
            )

            exported = export_competition_readiness_package(
                campaign_root=str(campaign),
                output_dir=str(tmp_path / "competition_readiness"),
                prospective_validation_closure_manifest_path=str(prospective_manifest_path),
                max_priority_variants=10,
            )

            manifest = json.loads(Path(exported["competition_readiness_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["competition_readiness_percent"], 80)
            self.assertFalse(manifest["ready_for_definitive_clinical_claims"])
            queue = pd.read_csv(exported["competition_priority_variant_queue_path"])
            self.assertEqual(queue.iloc[0]["variant"], "BRCA1 p.C1501Y")
            self.assertIn("recommended_next_action", queue.columns)
            claims = pd.read_csv(exported["scientific_claims_boundary_path"])
            self.assertIn("not_yet", set(claims["status"]))
            strategy = pd.read_csv(exported["competition_strategy_matrix_path"])
            self.assertIn("Locked external validation", set(strategy["front"]))

    def test_export_alphamissense_priority_enrichment_prepares_targets_and_local_coverage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            campaign = tmp_path / "campaign"
            readiness_dir = campaign / "competition_readiness"
            cohort_dir = campaign / "brca_real_quick" / "cohorts"
            readiness_dir.mkdir(parents=True)
            cohort_dir.mkdir(parents=True)
            priority_path = readiness_dir / "competition_priority_variant_queue.csv"
            pd.DataFrame(
                [
                    {
                        "competition_priority_score": 4.1,
                        "variant": "BRCA1 p.C1501Y",
                        "gene": "BRCA1",
                        "hgvs_p": "p.C1501Y",
                        "label": 0,
                        "cohort": "bridges_like_external_validation_brca1",
                        "calibration_effect": "persistent_on_locked_test",
                    },
                    {
                        "competition_priority_score": 3.2,
                        "variant": "BRCA1 p.R213M",
                        "gene": "BRCA1",
                        "hgvs_p": "p.R213M",
                        "label": 1,
                        "cohort": "bridges_like_external_validation_brca1",
                        "calibration_effect": "persistent_on_locked_test",
                    },
                ]
            ).to_csv(priority_path, index=False)
            (readiness_dir / "competition_readiness_manifest.json").write_text(
                json.dumps({"priority_queue_path": str(priority_path)}),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "variant": "BRCA1 p.C1501Y",
                        "gene": "BRCA1",
                        "variant_id": "12345",
                        "meta_gnomad_variant_id": "17-43000001-G-A",
                        "meta_gnomad_reference_genome": "GRCh38",
                    },
                    {
                        "variant": "BRCA1 p.R213M",
                        "gene": "BRCA1",
                        "variant_id": "67890",
                        "meta_gnomad_variant_id": "",
                        "meta_gnomad_reference_genome": "",
                    },
                ]
            ).to_csv(cohort_dir / "bridges_like_external_validation_brca1_processed_dataset.csv", index=False)
            alpha_subset = tmp_path / "target_gene_alphamissense.tsv"
            pd.DataFrame(
                [
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.C1501Y",
                        "feature_alphamissense_pathogenicity": 0.91,
                        "feature_alphamissense_class": "likely_pathogenic",
                    },
                    {
                        "gene": "BRCA1",
                        "hgvs_p": "p.R213M",
                        "feature_alphamissense_pathogenicity": 0.88,
                        "feature_alphamissense_class": "pathogenic",
                    }
                ]
            ).to_csv(alpha_subset, sep="\t", index=False)

            exported = export_alphamissense_priority_enrichment_package(
                campaign_root=str(campaign),
                output_dir=str(tmp_path / "alpha_enrichment"),
                local_alphamissense_subset_path=str(alpha_subset),
                max_targets=2,
            )

            manifest = json.loads(Path(exported["alphamissense_priority_enrichment_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["target_count"], 2)
            self.assertEqual(manifest["coordinate_ready_count"], 1)
            self.assertEqual(manifest["matched_alphamissense_count"], 2)
            self.assertEqual(manifest["priority_benchmark"]["n_complete_alphamissense_rows"], 2)
            coordinate_targets = pd.read_csv(exported["alphamissense_priority_coordinate_targets_path"])
            self.assertEqual(coordinate_targets.iloc[0]["chromosome"], "chr17")
            matched = pd.read_csv(exported["alphamissense_priority_matched_coverage_path"])
            self.assertIn("feature_alphamissense_pathogenicity", matched.columns)
            overlay = pd.read_csv(exported["alphamissense_priority_functional_overlay_path"])
            self.assertIn("alphamissense_label_alignment", overlay.columns)
            benchmark = pd.read_csv(exported["alphamissense_priority_benchmark_metrics_path"])
            self.assertIn("AlphaMissense priority overlay", set(benchmark["model"]))
            self.assertTrue(Path(exported["alphamissense_priority_discordance_hypotheses_path"]).exists())
            self.assertTrue(Path(exported["alphamissense_priority_extractor_script_path"]).exists())
            self.assertTrue(Path(exported["alphamissense_priority_aa_extractor_script_path"]).exists())

    def test_export_competition_jury_audit_scores_official_rubric_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            campaign = tmp_path / "campaign"
            (campaign / "competition_readiness").mkdir(parents=True)
            (campaign / "alphamissense_priority_enrichment").mkdir(parents=True)
            (campaign / "brca_real_quick").mkdir(parents=True)
            (campaign / "competition_evidence_summary.md").write_text("# summary", encoding="utf-8")
            (campaign / "competition_first_place_strategy.md").write_text("# strategy", encoding="utf-8")
            (campaign / "competition_evidence_manifest.json").write_text(
                json.dumps({"passed_targeted_tests": 10, "total_targeted_tests": 10}),
                encoding="utf-8",
            )
            (campaign / "competition_readiness" / "competition_readiness_manifest.json").write_text(
                json.dumps(
                    {
                        "competition_readiness_percent": 93.1,
                        "paper_readiness_percent": 91.1,
                        "web_launch_scientific_readiness_percent": 89.1,
                    }
                ),
                encoding="utf-8",
            )
            (campaign / "alphamissense_priority_enrichment" / "alphamissense_priority_enrichment_manifest.json").write_text(
                json.dumps(
                    {
                        "local_subset_coverage_percent": 100,
                        "priority_benchmark": {
                            "best_auc_roc": 0.97,
                            "functional_support_rate_percent": 92,
                            "status": "priority_overlay_evaluated",
                        },
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"area": "Validation lock", "score_percent": 94, "status": "ready", "evidence": ""},
                    {"area": "AlphaMissense priority benchmark", "score_percent": 97.3, "status": "ready", "evidence": ""},
                    {"area": "External robustness", "score_percent": 75, "status": "partial", "evidence": ""},
                    {"area": "Calibration rescue", "score_percent": 100, "status": "ready", "evidence": ""},
                    {"area": "Locked calibration holdout", "score_percent": 100, "status": "ready", "evidence": ""},
                    {"area": "Baseline and ablation", "score_percent": 74, "status": "partial", "evidence": ""},
                    {"area": "Claim strength", "score_percent": 98, "status": "strong", "evidence": ""},
                ]
            ).to_csv(campaign / "competition_evidence_scorecard.csv", index=False)
            for filename, payload in {
                "study_validation_lock_manifest.json": {"summary": {"overall_validation_lock_percent": 94}},
                "claim_strength_manifest.json": {"summary": {"overall_claim_strength_percent": 98}},
                "publication_readiness_manifest.json": {"summary": {"overall_readiness_percent": 95}},
                "external_robustness_manifest.json": {"summary": {"overall_external_robustness_percent": 75}},
            }.items():
                (campaign / "brca_real_quick" / filename).write_text(json.dumps(payload), encoding="utf-8")
            pd.DataFrame(
                [
                    {"feature_set": "prime_only", "experiment": "prime_only__logistic_regression", "auc_roc": 0.71, "auc_pr": 0.55, "mcc": 0.2},
                    {"feature_set": "hybrid", "experiment": "hybrid__logistic_regression", "auc_roc": 0.82, "auc_pr": 0.7, "mcc": 0.4},
                ]
            ).to_csv(campaign / "brca_real_quick" / "study_training_metrics.csv", index=False)
            pd.DataFrame(
                [
                    {"cohort": "external_a", "evaluation_group": "combined", "feature_set": "prime_only", "auc_roc": 0.68},
                    {"cohort": "external_a", "evaluation_group": "combined", "feature_set": "hybrid", "auc_roc": 0.8},
                ]
            ).to_csv(campaign / "brca_real_quick" / "study_external_evaluation.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "variant": "BRCA1 p.L1844P",
                        "gene": "BRCA1",
                        "label": 0,
                        "locked_calibrated_score": 0.67,
                        "feature_alphamissense_pathogenicity": 0.89,
                        "feature_alphamissense_class": "pathogenic",
                        "alphamissense_label_alignment": "discordant_am_pathogenic_for_benign_label",
                        "hypothesis_priority": "highest",
                        "evidence_gap": "needs confirmation",
                    }
                ]
            ).to_csv(campaign / "alphamissense_priority_enrichment" / "alphamissense_priority_discordance_hypotheses.csv", index=False)

            exported = export_competition_jury_audit_package(
                campaign_root=str(campaign),
                output_dir=str(tmp_path / "jury_audit"),
            )

            manifest = json.loads(Path(exported["competition_jury_audit_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreater(manifest["estimated_jury_points"], 80)
            scorecard = pd.read_csv(exported["competition_jury_scorecard_path"])
            self.assertEqual(int(scorecard["official_points"].sum()), 100)
            risks = pd.read_csv(exported["competition_jury_risk_register_path"])
            self.assertIn("R1", set(risks["risk_id"]))
            cases_text = Path(exported["mechanistic_case_studies_path"]).read_text(encoding="utf-8")
            self.assertIn("BRCA1 p.L1844P", cases_text)

    def test_export_study_validation_lock_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            required_files = {
                "cohort_independence_manifest_path": tmp_path / "cohort_independence_manifest.json",
                "comparative_evidence_manifest_path": tmp_path / "comparative_evidence_manifest.json",
                "claim_strength_manifest_path": tmp_path / "claim_strength_manifest.json",
                "publication_readiness_manifest_path": tmp_path / "publication_readiness_manifest.json",
                "baseline_coverage_manifest_path": tmp_path / "baseline_coverage_manifest.json",
                "methods_package_manifest_path": tmp_path / "methods_package_manifest.json",
                "manuscript_package_manifest_path": tmp_path / "manuscript_package_manifest.json",
                "training_metrics_path": tmp_path / "training_metrics.csv",
            }
            for path in required_files.values():
                path.write_text("{}", encoding="utf-8")

            results = {
                "study_design": type("StudyDesignStub", (), {"name": "Validation Lock Study"})(),
                "cohort_independence_assessment": {"summary": {"overall_independence_percent": 100, "max_variant_overlap_percent": 0}},
                "comparative_evidence_assessment": {"summary": {"overall_comparative_strength_percent": 78, "best_supported_experiment": "hybrid__random_forest"}},
                "claim_strength_assessment": {"summary": {"overall_claim_strength_percent": 74, "claim_tier": "moderate", "selected_experiment": "hybrid__random_forest"}},
                "publication_readiness_assessment": {"summary": {"overall_readiness_percent": 86, "overall_status": "ready", "ready_for_submission": True}},
                "baseline_coverage_assessment": {"summary": {"overall_coverage_percent": 90, "best_prime_experiment": "hybrid__random_forest"}},
                "methods_package_summary": {"best_internal_experiment": "hybrid__random_forest"},
                "manuscript_package_summary": {"best_external_experiment": "hybrid__random_forest"},
                "model_paths": {"registry": str(tmp_path / "models.csv")},
                "manuscript_package_markdown_path": str(tmp_path / "manuscript_package.md"),
                **{key: str(value) for key, value in required_files.items()},
            }
            Path(results["manuscript_package_markdown_path"]).write_text("# manuscript", encoding="utf-8")
            Path(results["model_paths"]["registry"]).write_text("experiment,model_path\nhybrid,model.joblib\n", encoding="utf-8")

            export_paths = export_study_validation_lock(results, output_dir=tmp_dir)

            self.assertTrue(Path(export_paths["study_validation_lock_manifest_path"]).exists())
            manifest = json.loads(Path(export_paths["study_validation_lock_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertGreaterEqual(manifest["summary"]["overall_validation_lock_percent"], 70)
            self.assertTrue(manifest["summary"]["ready_for_statistical_validation"])

    def test_refresh_frozen_study_assessment_rebuilds_packages_from_exported_csvs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_path = tmp_path / "study.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[study]",
                        'name = "Frozen Refresh Study"',
                        'mode = "hybrid"',
                        "high_confidence_only = false",
                        "keep_metadata = true",
                        'primary_metric = "auc_roc"',
                        'baseline_experiment = "external_predictors_only__random_forest"',
                        "",
                        "[[cohorts]]",
                        'name = "training"',
                        'role = "train"',
                        'source_config = "configs/train.toml"',
                        "",
                        "[[cohorts]]",
                        'name = "clinvar_expert_external_a"',
                        'role = "external_test"',
                        'source_config = "configs/ext_a.toml"',
                        "",
                        "[[cohorts]]",
                        'name = "external_b"',
                        'role = "external_test"',
                        'source_config = "configs/ext_b.toml"',
                    ]
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"experiment": "hybrid__random_forest", "auc_roc": 0.91, "auc_pr": 0.89, "mcc": 0.74, "is_primary_experiment": 1},
                    {"experiment": "external_predictors_only__random_forest", "auc_roc": 0.86, "auc_pr": 0.82, "mcc": 0.61, "is_primary_experiment": 1},
                ]
            ).to_csv(tmp_path / "study_training_metrics.csv", index=False)
            pd.DataFrame(
                [
                    {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.88, "auc_pr": 0.84, "mcc": 0.61},
                    {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.83, "auc_pr": 0.79, "mcc": 0.53},
                    {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "hybrid__random_forest", "auc_roc": 0.85, "auc_pr": 0.81, "mcc": 0.58},
                    {"cohort": "external_b", "cohort_role": "external_test", "evaluation_group": "combined", "experiment": "external_predictors_only__random_forest", "auc_roc": 0.82, "auc_pr": 0.77, "mcc": 0.50},
                ]
            ).to_csv(tmp_path / "study_external_evaluation.csv", index=False)
            pd.DataFrame(
                [
                    {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_roc", "delta_mean": 0.041, "ci_lower_95": 0.01, "ci_upper_95": 0.072, "n_bootstrap_valid": 180},
                    {"cohort": "clinvar_expert_external_a", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_pr", "delta_mean": 0.039, "ci_lower_95": 0.005, "ci_upper_95": 0.068, "n_bootstrap_valid": 180},
                    {"cohort": "external_b", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_roc", "delta_mean": 0.022, "ci_lower_95": 0.001, "ci_upper_95": 0.043, "n_bootstrap_valid": 176},
                    {"cohort": "external_b", "cohort_role": "external_test", "experiment": "hybrid__random_forest", "baseline_experiment": "external_predictors_only__random_forest", "metric": "auc_pr", "delta_mean": 0.018, "ci_lower_95": -0.002, "ci_upper_95": 0.038, "n_bootstrap_valid": 176},
                ]
            ).to_csv(tmp_path / "study_external_pairwise.csv", index=False)
            pd.DataFrame(
                [
                    {"cohort_name": "training", "role": "train"},
                    {"cohort_name": "clinvar_expert_external_a", "role": "external_test"},
                    {"cohort_name": "external_b", "role": "external_test"},
                ]
            ).to_csv(tmp_path / "study_cohort_manifest.csv", index=False)
            pd.DataFrame(
                [
                    {"label": 1, "score__hybrid__random_forest": 0.92, "score__external_predictors_only__random_forest": 0.75},
                    {"label": 1, "score__hybrid__random_forest": 0.86, "score__external_predictors_only__random_forest": 0.72},
                    {"label": 0, "score__hybrid__random_forest": 0.19, "score__external_predictors_only__random_forest": 0.31},
                    {"label": 0, "score__hybrid__random_forest": 0.11, "score__external_predictors_only__random_forest": 0.27},
                ]
            ).to_csv(tmp_path / "study_scores_clinvar_expert_external_a.csv", index=False)
            pd.DataFrame(
                [
                    {"label": 1, "score__hybrid__random_forest": 0.84, "score__external_predictors_only__random_forest": 0.74},
                    {"label": 1, "score__hybrid__random_forest": 0.79, "score__external_predictors_only__random_forest": 0.69},
                    {"label": 0, "score__hybrid__random_forest": 0.24, "score__external_predictors_only__random_forest": 0.33},
                    {"label": 0, "score__hybrid__random_forest": 0.17, "score__external_predictors_only__random_forest": 0.26},
                ]
            ).to_csv(tmp_path / "study_scores_external_b.csv", index=False)

            refresh = refresh_frozen_study_assessment(
                study_output_dir=str(tmp_path),
                study_config_path=str(config_path),
            )

            self.assertTrue(Path(refresh["comparative_evidence_manifest_path"]).exists())
            self.assertTrue(Path(refresh["claim_strength_manifest_path"]).exists())
            self.assertTrue(Path(refresh["publication_readiness_manifest_path"]).exists())
            self.assertTrue(Path(refresh["external_robustness_manifest_path"]).exists())
            self.assertTrue(Path(refresh["prime_intelligence_manifest_path"]).exists())
            self.assertGreaterEqual(refresh["claim_summary"]["selected_high_confidence_clinical_score_percent"], 60)
            self.assertIn("overall_readiness_percent", refresh["publication_summary"])
            self.assertGreaterEqual(refresh["external_robustness_summary"]["overall_external_robustness_percent"], 60)
            self.assertGreaterEqual(refresh["prime_intelligence_summary"]["overall_prime_intelligence_percent"], 60)

    def test_export_study_execution_board_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            registry_path = tmp_path / "model_registry.csv"
            release_manifest_path = tmp_path / "study_release_manifest.json"
            dossier_path = tmp_path / "scientific_dossier.md"
            freeze_manifest_path = tmp_path / "study_cohort_freeze_manifest.json"
            comparative_manifest_path = tmp_path / "comparative_evidence_manifest.json"
            claim_manifest_path = tmp_path / "claim_strength_manifest.json"
            methods_manifest_path = tmp_path / "methods_package_manifest.json"
            manuscript_manifest_path = tmp_path / "manuscript_package_manifest.json"
            validation_manifest_path = tmp_path / "study_validation_lock_manifest.json"

            for path, content in [
                (registry_path, "experiment,model_path\nhybrid,model.joblib\n"),
                (release_manifest_path, "{}"),
                (dossier_path, "# dossier"),
                (freeze_manifest_path, "{}"),
                (comparative_manifest_path, "{}"),
                (claim_manifest_path, "{}"),
                (methods_manifest_path, "{}"),
                (manuscript_manifest_path, "{}"),
                (validation_manifest_path, "{}"),
            ]:
                path.write_text(content, encoding="utf-8")

            export_paths = export_study_execution_board(
                public_resolution={
                    "summary": {
                        "config_path": "public-study.toml",
                        "overall_resolution_percent": 94,
                        "n_ready_cohorts": 2,
                        "n_cohorts": 2,
                        "n_live_public_ready_cohorts": 2,
                        "ready_for_resolved_study": True,
                    }
                },
                preflight_export={
                    "preflight": {
                        "summary": {
                            "overall_preflight_percent": 91,
                            "n_critical_gaps": 0,
                            "ready_to_run": True,
                        },
                        "recommended_actions": [],
                    }
                },
                study_results={
                    "publication_readiness_assessment": {
                        "summary": {
                            "overall_readiness_percent": 88,
                            "overall_status": "ready",
                            "ready_for_submission": True,
                        },
                        "criteria": [
                            {
                                "criterion_id": "comparative_evidence",
                                "score_percent": 82,
                            }
                        ],
                    },
                    "study_cohort_freeze_summary": {
                        "overall_real_data_readiness_percent": 92,
                        "n_example_blocked_cohorts": 0,
                        "ready_for_real_data_study": True,
                    },
                    "claim_strength_assessment": {
                        "summary": {
                            "overall_claim_strength_percent": 79,
                            "claim_tier": "moderate",
                        }
                    },
                    "study_validation_lock": {
                        "summary": {
                            "overall_validation_lock_percent": 84,
                            "ready_for_submission_lock": True,
                            "ready_for_translational_pilot": True,
                        }
                    },
                    "baseline_coverage_assessment": {
                        "summary": {
                            "overall_coverage_percent": 90,
                            "best_prime_experiment": "hybrid_plus_external",
                        }
                    },
                    "methods_package_summary": {"best_internal_experiment": "hybrid_rf"},
                    "manuscript_package_summary": {"best_external_experiment": "hybrid_plus_external"},
                    "model_paths": {"registry": str(registry_path)},
                    "study_release_manifest_path": str(release_manifest_path),
                    "scientific_dossier_markdown_path": str(dossier_path),
                    "study_cohort_freeze_manifest_path": str(freeze_manifest_path),
                    "comparative_evidence_manifest_path": str(comparative_manifest_path),
                    "claim_strength_manifest_path": str(claim_manifest_path),
                    "methods_package_manifest_path": str(methods_manifest_path),
                    "manuscript_package_manifest_path": str(manuscript_manifest_path),
                    "study_validation_lock_manifest_path": str(validation_manifest_path),
                },
                output_dir=str(tmp_path / "execution_board"),
            )

            self.assertTrue(Path(export_paths["study_execution_board_manifest_path"]).exists())
            self.assertTrue(Path(export_paths["study_execution_board_markdown_path"]).exists())
            self.assertTrue(Path(export_paths["study_execution_board_html_path"]).exists())
            manifest = json.loads(Path(export_paths["study_execution_board_manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["summary"]["overall_execution_percent"], 80)
            self.assertTrue(manifest["summary"]["ready_for_benchmark_lock"])
            self.assertEqual(manifest["summary"]["real_data_readiness_percent"], 92)

    def test_export_translational_pilot_package_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            study_release_manifest_path = tmp_path / "study_release_manifest.json"
            study_summary_path = tmp_path / "study_summary_report.txt"
            validation_manifest_path = tmp_path / "study_validation_lock_manifest.json"
            claim_manifest_path = tmp_path / "claim_strength_manifest.json"
            publication_manifest_path = tmp_path / "publication_readiness_manifest.json"
            freeze_manifest_path = tmp_path / "study_cohort_freeze_manifest.json"
            handoff_manifest_path = tmp_path / "study_real_data_handoff_manifest.json"
            execution_manifest_path = tmp_path / "study_execution_board_manifest.json"

            for path in [
                study_release_manifest_path,
                study_summary_path,
                validation_manifest_path,
                claim_manifest_path,
                publication_manifest_path,
                freeze_manifest_path,
                handoff_manifest_path,
                execution_manifest_path,
            ]:
                path.write_text("{}", encoding="utf-8")

            exported = export_translational_pilot_package(
                summary={
                    "real_data_handoff_percent": 100,
                    "n_real_data_tasks": 2,
                    "ready_for_real_data_study": False,
                },
                resolution={
                    "summary": {
                        "real_data_handoff_percent": 100,
                    },
                    "study_real_data_handoff_manifest_path": str(handoff_manifest_path),
                },
                preflight={
                    "preflight": {
                        "summary": {
                            "overall_preflight_percent": 93,
                        }
                    }
                },
                study_results={
                    "publication_readiness_assessment": {
                        "summary": {
                            "overall_readiness_percent": 81,
                        }
                    },
                    "claim_strength_assessment": {
                        "summary": {
                            "overall_claim_strength_percent": 37,
                            "claim_tier": "insufficient",
                        }
                    },
                    "study_validation_lock": {
                        "summary": {
                            "overall_validation_lock_percent": 70,
                            "ready_for_translational_pilot": False,
                        }
                    },
                    "study_cohort_freeze_summary": {
                        "overall_real_data_readiness_percent": 19,
                    },
                    "study_release_manifest_path": str(study_release_manifest_path),
                    "study_summary_report_path": str(study_summary_path),
                    "study_validation_lock_manifest_path": str(validation_manifest_path),
                    "claim_strength_manifest_path": str(claim_manifest_path),
                    "publication_readiness_manifest_path": str(publication_manifest_path),
                    "study_cohort_freeze_manifest_path": str(freeze_manifest_path),
                },
                execution_board={
                    "study_execution_board": {
                        "summary": {
                            "overall_execution_percent": 79,
                        }
                    },
                    "study_execution_board_manifest_path": str(execution_manifest_path),
                },
                output_dir=str(tmp_path / "pilot_package"),
            )

            self.assertTrue(Path(exported["translational_pilot_package_manifest_path"]).exists())
            self.assertTrue(Path(exported["translational_pilot_package_markdown_path"]).exists())
            self.assertTrue(Path(exported["translational_pilot_package_html_path"]).exists())
            manifest = json.loads(Path(exported["translational_pilot_package_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertEqual(manifest["summary"]["pilot_mode"], "shadow_mode")
            self.assertTrue(manifest["summary"]["ready_for_demo_pilot"])
            self.assertTrue(manifest["summary"]["ready_for_shadow_pilot"])
            self.assertFalse(manifest["summary"]["ready_for_live_pilot"])

    def test_export_final_mile_package_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            handoff_report_path = tmp_path / "study_real_data_handoff.md"
            comparative_report_path = tmp_path / "comparative_evidence_report.md"
            claim_report_path = tmp_path / "claim_strength_report.md"
            publication_report_path = tmp_path / "publication_readiness_report.md"
            pilot_report_path = tmp_path / "translational_pilot_package.md"

            for path in [
                handoff_report_path,
                comparative_report_path,
                claim_report_path,
                publication_report_path,
                pilot_report_path,
            ]:
                path.write_text("report", encoding="utf-8")

            exported = export_final_mile_package(
                summary={
                    "real_data_readiness_percent": 19,
                    "real_data_handoff_percent": 100,
                    "n_real_data_tasks": 6,
                    "n_critical_real_data_tasks": 6,
                    "comparative_evidence_percent": 25,
                    "claim_strength_percent": 37,
                    "publication_readiness_percent": 71,
                    "validation_lock_percent": 69,
                    "pilot_package_percent": 87,
                },
                resolution={
                    "study_real_data_handoff_markdown_path": str(handoff_report_path),
                    "study_cohort_freeze_markdown_path": str(tmp_path / "study_cohort_freeze_report.md"),
                },
                preflight={},
                study_results={
                    "comparative_evidence_report_markdown_path": str(comparative_report_path),
                    "claim_strength_report_markdown_path": str(claim_report_path),
                    "publication_readiness_report_markdown_path": str(publication_report_path),
                    "publication_readiness_assessment": {"summary": {"overall_readiness_percent": 71}},
                    "claim_strength_assessment": {"summary": {"overall_claim_strength_percent": 37, "claim_tier": "insufficient"}},
                    "comparative_evidence_assessment": {"summary": {"overall_comparative_strength_percent": 25}},
                    "study_validation_lock": {"summary": {"overall_validation_lock_percent": 69}},
                    "study_cohort_freeze_summary": {"overall_real_data_readiness_percent": 19},
                },
                execution_board={},
                pilot_package={
                    "translational_pilot_package_summary": {
                        "overall_pilot_package_percent": 87,
                        "pilot_mode": "shadow_mode",
                        "ready_for_shadow_pilot": True,
                        "ready_for_live_pilot": False,
                    },
                    "translational_pilot_package_markdown_path": str(pilot_report_path),
                },
                output_dir=str(tmp_path / "final_mile"),
            )

            self.assertTrue(Path(exported["final_mile_package_manifest_path"]).exists())
            self.assertTrue(Path(exported["final_mile_package_markdown_path"]).exists())
            self.assertTrue(Path(exported["final_mile_package_html_path"]).exists())
            manifest = json.loads(Path(exported["final_mile_package_manifest_path"]).read_text(encoding="utf-8"))
            self.assertIn("summary", manifest)
            self.assertFalse(manifest["summary"]["ready_for_real_data_execution"])
            self.assertFalse(manifest["summary"]["ready_for_final_evidence_round"])
            self.assertFalse(manifest["summary"]["ready_for_submission_closeout"])
            self.assertGreaterEqual(manifest["summary"]["n_critical_blockers"], 3)

    def test_export_real_data_handoff_reconciliation_generates_tracker_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tasks_path = tmp_path / "study_real_data_handoff_tasks.csv"
            pd.DataFrame(
                [
                    {
                        "task_id": "train::clinvar::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train",
                        "cohort_role": "train",
                        "source_name": "clinvar_main",
                        "profile_id": "clinvar",
                        "task_type": "replace_example_source",
                        "owner_hint": "data_curation",
                        "blocking_reason": "example path",
                        "recommended_action": "Trocar por dataset real.",
                        "current_path": "data/examples/demo.tsv",
                        "target_path": str(tmp_path / "real_clinvar.tsv"),
                        "release_value": "placeholder",
                        "resolution_status": "blocked",
                    },
                    {
                        "task_id": "external::mavedb::lock_public_release_metadata",
                        "priority": "critical",
                        "cohort_name": "external",
                        "cohort_role": "external_test",
                        "source_name": "mavedb_scores",
                        "profile_id": "mavedb",
                        "task_type": "lock_public_release_metadata",
                        "owner_hint": "release_governance",
                        "blocking_reason": "placeholder release",
                        "recommended_action": "Preencher release final.",
                        "current_path": "",
                        "target_path": "",
                        "release_value": "placeholder",
                        "resolution_status": "blocked",
                    },
                ]
            ).to_csv(tasks_path, index=False)

            resolved_file = tmp_path / "real_clinvar.tsv"
            resolved_file.write_text("gene\thgvs_p\tlabel\nBRCA1\tp.Cys61Gly\tPathogenic\n", encoding="utf-8")

            tracker_path = tmp_path / "study_real_data_handoff_tracker.csv"
            pd.DataFrame(
                [
                    {
                        "task_id": "train::clinvar::replace_example_source",
                        "completion_status": "completed",
                        "provided_path": str(resolved_file),
                        "release_version": "",
                        "release_date": "",
                        "notes": "",
                    },
                    {
                        "task_id": "external::mavedb::lock_public_release_metadata",
                        "completion_status": "completed",
                        "provided_path": "",
                        "release_version": "2026.04",
                        "release_date": "2026-04-03",
                        "notes": "release locked",
                    },
                ]
            ).to_csv(tracker_path, index=False)

            exported = export_real_data_handoff_reconciliation(
                study_name="Public BRCA Benchmark Example",
                handoff_tasks_path=str(tasks_path),
                tracker_path=str(tracker_path),
                output_dir=str(tmp_path / "handoff_reconciliation"),
            )

            self.assertTrue(Path(exported["study_real_data_handoff_tracker_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_reconciliation_manifest_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_reconciliation_markdown_path"]).exists())
            manifest = json.loads(Path(exported["study_real_data_handoff_reconciliation_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["overall_handoff_reconciliation_percent"], 100)
            self.assertTrue(manifest["summary"]["ready_to_rerun_resolution"])
            self.assertTrue(manifest["summary"]["ready_to_rerun_public_study"])

    def test_export_real_data_handoff_autofill_generates_tracker_matches(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tasks_path = tmp_path / "study_real_data_handoff_tasks.csv"
            delivery_dir = tmp_path / "delivery_drop"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            tracker_path = tmp_path / "study_real_data_handoff_tracker.csv"

            pd.DataFrame(
                [
                    {
                        "task_id": "train::clinvar::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train",
                        "cohort_role": "train",
                        "source_name": "clinvar_variant_summary",
                        "profile_id": "clinvar",
                        "task_type": "replace_example_source",
                        "owner_hint": "data_curation",
                        "blocking_reason": "example path",
                        "recommended_action": "Trocar ClinVar por tabela real.",
                        "current_path": "data/examples/clinvar_variant_summary_like.tsv",
                        "target_path": str(tmp_path / "clinvar_variant_summary.tsv"),
                        "release_value": "",
                        "resolution_status": "blocked",
                    },
                    {
                        "task_id": "train::gnomad::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train",
                        "cohort_role": "train",
                        "source_name": "gnomad_brca_annotations",
                        "profile_id": "gnomad",
                        "task_type": "replace_example_source",
                        "owner_hint": "data_curation",
                        "blocking_reason": "example path",
                        "recommended_action": "Trocar gnomAD por tabela real.",
                        "current_path": "data/examples/gnomad_brca_annotations.tsv",
                        "target_path": str(tmp_path / "gnomad_brca_annotations.tsv"),
                        "release_value": "",
                        "resolution_status": "blocked",
                    },
                ]
            ).to_csv(tasks_path, index=False)

            (delivery_dir / "clinvar_variant_summary_2026_04_03.tsv").write_text(
                "gene\thgvs_p\tlabel\nBRCA1\tp.Cys61Gly\tPathogenic\n",
                encoding="utf-8",
            )
            (delivery_dir / "gnomad_brca_annotations_release_2026_04.tsv").write_text(
                "gene\thgvs_p\tfeature_af\nBRCA1\tp.Cys61Gly\t0.0001\n",
                encoding="utf-8",
            )

            exported = export_real_data_handoff_autofill(
                study_name="Public BRCA Benchmark Example",
                handoff_tasks_path=str(tasks_path),
                tracker_path=str(tracker_path),
                delivery_dir=str(delivery_dir),
                output_dir=str(tmp_path / "handoff_autofill"),
            )

            self.assertTrue(Path(exported["study_real_data_handoff_autofill_manifest_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_autofill_tracker_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_autofill_matches_path"]).exists())
            manifest = json.loads(Path(exported["study_real_data_handoff_autofill_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["overall_handoff_autofill_percent"], 100)
            self.assertEqual(manifest["summary"]["n_autofilled_tasks"], 2)
            self.assertTrue(manifest["summary"]["ready_for_reconciliation_rerun"])

    def test_export_platform_completion_assessment_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exported = export_platform_completion_assessment(
                roadmap={
                    "summary": {
                        "overall_progress_percent": 100,
                        "completed_stages": 7,
                    },
                    "stages": [{"stage_id": "x", "progress_percent": 100}],
                },
                evidence_summary={
                    "real_data_readiness_percent": 19,
                    "comparative_evidence_percent": 25,
                    "claim_strength_percent": 37,
                    "publication_readiness_percent": 71,
                    "translational_impact_percent": 49,
                    "ready_for_submission_lock": False,
                    "ready_for_shadow_rollout": False,
                    "ready_for_real_data_study": False,
                },
                output_dir=tmp_dir,
            )

            self.assertTrue(Path(exported["platform_completion_manifest_path"]).exists())
            manifest = json.loads(Path(exported["platform_completion_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["overall_platform_completion_percent"], 100)
            self.assertTrue(manifest["summary"]["development_complete"])
            self.assertTrue(manifest["summary"]["scientific_validation_pending"])

    def test_export_real_data_handoff_application_generates_candidate_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_config_path = tmp_path / "cohort_sources.toml"
            source_config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{(tmp_path / "demo.tsv").as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                    ]
                ),
                encoding="utf-8",
            )
            study_config_path = tmp_path / "study.toml"
            study_config_path.write_text(
                "\n".join(
                    [
                        "[study]",
                        'name = "Candidate Study"',
                        "",
                        "[[cohorts]]",
                        'name = "train_cohort"',
                        'role = "train"',
                        f'source_config = "{source_config_path.as_posix()}"',
                    ]
                ),
                encoding="utf-8",
            )
            real_file = tmp_path / "real.tsv"
            real_file.write_text("gene\thgvs_p\tlabel\nBRCA1\tp.Cys61Gly\tPathogenic\n", encoding="utf-8")
            reconciliation_tasks_path = tmp_path / "reconciliation_tasks.csv"
            pd.DataFrame(
                [
                    {
                        "task_id": "train_cohort::clinvar_main::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train_cohort",
                        "cohort_role": "train",
                        "source_name": "clinvar_main",
                        "profile_id": "clinvar",
                        "task_type": "replace_example_source",
                        "provided_path": str(real_file),
                        "release_version": "2026-04",
                        "release_date": "2026-04-03",
                        "validated": True,
                        "recommended_action": "Trocar o arquivo de exemplo.",
                    }
                ]
            ).to_csv(reconciliation_tasks_path, index=False)

            exported = export_real_data_handoff_application(
                study_config_path=str(study_config_path),
                cohort_rows=[
                    {
                        "cohort_name": "train_cohort",
                        "role": "train",
                        "original_source_config": str(source_config_path),
                        "mode_override": None,
                        "high_confidence_only_override": None,
                    }
                ],
                handoff_reconciliation_tasks_path=str(reconciliation_tasks_path),
                output_dir=str(tmp_path / "application"),
            )

            self.assertTrue(Path(exported["study_real_data_candidate_config_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_application_manifest_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_handoff_application_markdown_path"]).exists())
            candidate_text = Path(exported["study_real_data_candidate_config_path"]).read_text(encoding="utf-8")
            self.assertIn("train_cohort_candidate_source_config.toml", candidate_text)
            source_candidate_text = Path(tmp_path / "application" / "train_cohort_candidate_source_config.toml").read_text(encoding="utf-8")
            self.assertIn('path = "C:/Users/', source_candidate_text)
            self.assertIn("/real.tsv\"", source_candidate_text.replace("\\", "/"))

    def test_export_real_data_candidate_promotion_generates_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidate_config_path = tmp_path / "study_real_data_candidate_config.toml"
            candidate_config_path.write_text("[study]\nname = \"Candidate Study\"\n", encoding="utf-8")
            application_manifest_path = tmp_path / "study_real_data_handoff_application_manifest.json"
            application_manifest_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "n_tasks": 2,
                            "n_validated_tasks": 2,
                            "n_applied_changes": 3,
                            "overall_handoff_application_percent": 100,
                            "ready_for_candidate_resolution": True,
                            "ready_for_candidate_public_study": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            reconciliation_tasks_path = tmp_path / "reconciliation_tasks.csv"
            pd.DataFrame(
                [
                    {
                        "task_id": "train::clinvar::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train",
                        "source_name": "clinvar",
                        "validated": True,
                        "validation_state": "validated",
                    },
                    {
                        "task_id": "external::mavedb::lock_public_release_metadata",
                        "priority": "high",
                        "cohort_name": "external",
                        "source_name": "mavedb",
                        "validated": True,
                        "validation_state": "validated",
                    },
                ]
            ).to_csv(reconciliation_tasks_path, index=False)

            exported = export_real_data_candidate_promotion(
                study_name="Candidate Study",
                candidate_config_path=str(candidate_config_path),
                handoff_application_manifest_path=str(application_manifest_path),
                handoff_reconciliation_tasks_path=str(reconciliation_tasks_path),
                output_dir=str(tmp_path / "promotion"),
            )

            self.assertTrue(Path(exported["study_real_data_candidate_promotion_manifest_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_candidate_promotion_markdown_path"]).exists())
            self.assertTrue(Path(exported["study_real_data_candidate_promotion_criteria_path"]).exists())
            summary = exported["study_real_data_candidate_promotion_summary"]
            self.assertTrue(summary["ready_to_promote_candidate_config"])
            self.assertTrue(summary["ready_to_run_candidate_public_study"])
            self.assertIn("primevarclass --study-config", summary["candidate_public_study_command"])

    def test_export_translational_impact_package_generates_registry_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pilot_manifest = tmp_path / "pilot_manifest.json"
            final_mile_manifest = tmp_path / "final_mile_manifest.json"
            pilot_manifest.write_text("{}", encoding="utf-8")
            final_mile_manifest.write_text("{}", encoding="utf-8")

            exported = export_translational_impact_package(
                summary={
                    "pilot_package_percent": 88,
                    "final_mile_percent": 76,
                    "real_data_candidate_promotion_percent": 91,
                    "study_real_data_candidate_promotion_manifest_path": str(tmp_path / "candidate_promotion_manifest.json"),
                    "study_execution_board_manifest_path": str(tmp_path / "study_execution_board_manifest.json"),
                    "public_study_run_manifest_path": str(tmp_path / "public_study_run_manifest.json"),
                },
                pilot_package={
                    "translational_pilot_package_summary": {
                        "study_name": "Impact Study",
                        "overall_pilot_package_percent": 88,
                        "ready_for_demo_pilot": True,
                        "ready_for_shadow_pilot": True,
                        "pilot_mode": "shadow_mode",
                    },
                    "translational_pilot_package_manifest_path": str(pilot_manifest),
                },
                final_mile_package={
                    "final_mile_package_summary": {
                        "overall_final_mile_percent": 76,
                    },
                    "final_mile_package_manifest_path": str(final_mile_manifest),
                },
                candidate_promotion_summary={"overall_candidate_promotion_percent": 91},
                session_rows=[
                    {
                        "session_id": "shadow-001",
                        "study_name": "Impact Study",
                        "pilot_mode": "shadow_mode",
                        "site_name": "Lab",
                        "institution": "PrimeVarClass",
                        "team_name": "BRCA",
                        "operator_name": "Wesley",
                        "status": "completed",
                        "cases_reviewed": 15,
                        "variants_flagged": 5,
                        "started_at": "2026-04-03T10:00:00Z",
                        "completed_at": "2026-04-03T11:00:00Z",
                        "outcome_summary": "Sessao concluida.",
                        "notes": "",
                        "created_at": "2026-04-03T10:00:00Z",
                        "updated_at": "2026-04-03T11:00:00Z",
                    },
                    {
                        "session_id": "shadow-002",
                        "study_name": "Impact Study",
                        "pilot_mode": "shadow_mode",
                        "site_name": "Lab",
                        "institution": "PrimeVarClass",
                        "team_name": "BRCA",
                        "operator_name": "Wesley",
                        "status": "completed",
                        "cases_reviewed": 10,
                        "variants_flagged": 3,
                        "started_at": "2026-04-04T10:00:00Z",
                        "completed_at": "2026-04-04T11:00:00Z",
                        "outcome_summary": "Sessao concluida.",
                        "notes": "",
                        "created_at": "2026-04-04T10:00:00Z",
                        "updated_at": "2026-04-04T11:00:00Z",
                    },
                ],
                feedback_rows=[
                    {
                        "feedback_id": "f1",
                        "session_id": "shadow-001",
                        "study_name": "Impact Study",
                        "operator_name": "Wesley",
                        "role": "pi",
                        "confidence_score": 5,
                        "actionability_score": 4,
                        "time_saved_minutes": 30,
                        "adoption_recommendation": "recommended",
                        "incident_level": "none",
                        "notes": "",
                        "created_at": "2026-04-03T11:10:00Z",
                    },
                    {
                        "feedback_id": "f2",
                        "session_id": "shadow-002",
                        "study_name": "Impact Study",
                        "operator_name": "Wesley",
                        "role": "pi",
                        "confidence_score": 4,
                        "actionability_score": 5,
                        "time_saved_minutes": 20,
                        "adoption_recommendation": "recommended",
                        "incident_level": "none",
                        "notes": "",
                        "created_at": "2026-04-04T11:10:00Z",
                    },
                ],
                output_dir=str(tmp_path / "impact"),
            )

            self.assertTrue(Path(exported["translational_impact_package_manifest_path"]).exists())
            self.assertTrue(Path(exported["translational_impact_package_markdown_path"]).exists())
            self.assertTrue(Path(exported["translational_impact_sessions_path"]).exists())
            summary = exported["translational_impact_package_summary"]
            self.assertGreaterEqual(summary["overall_translational_impact_percent"], 1)
            self.assertTrue(summary["ready_for_shadow_rollout"])
            self.assertTrue(summary["ready_for_institutional_rollout"])

    def test_run_public_benchmark_pipeline_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_path = tmp_path / "public_study.toml"
            config_path.write_text("[study]\nname = \"Public Study\"\n", encoding="utf-8")

            resolved_config_path = tmp_path / "resolved_study_config.toml"
            resolved_config_path.write_text("[study]\nname = \"Resolved Public Study\"\n", encoding="utf-8")
            resolution_manifest_path = tmp_path / "resolution_manifest.json"
            resolution_report_path = tmp_path / "resolution_report.md"
            cohort_freeze_manifest_path = tmp_path / "study_cohort_freeze_manifest.json"
            cohort_freeze_report_path = tmp_path / "study_cohort_freeze_report.md"
            real_data_handoff_manifest_path = tmp_path / "study_real_data_handoff_manifest.json"
            real_data_handoff_report_path = tmp_path / "study_real_data_handoff.md"
            preflight_manifest_path = tmp_path / "preflight_manifest.json"
            preflight_report_path = tmp_path / "preflight_report.md"
            study_release_manifest_path = tmp_path / "study_release_manifest.json"
            study_summary_path = tmp_path / "study_summary_report.txt"
            publication_manifest_path = tmp_path / "publication_readiness_manifest.json"
            execution_manifest_path = tmp_path / "study_execution_board_manifest.json"
            execution_report_path = tmp_path / "study_execution_board.md"
            execution_html_path = tmp_path / "study_execution_board.html"

            for path in [
                resolution_manifest_path,
                resolution_report_path,
                cohort_freeze_manifest_path,
                cohort_freeze_report_path,
                real_data_handoff_manifest_path,
                real_data_handoff_report_path,
                preflight_manifest_path,
                preflight_report_path,
                study_release_manifest_path,
                study_summary_path,
                publication_manifest_path,
                execution_manifest_path,
                execution_report_path,
                execution_html_path,
            ]:
                path.write_text("{}", encoding="utf-8")

            with (
                patch(
                    "primevarclass.public_study_runner.export_study_public_config_resolution",
                    return_value={
                        "summary": {
                            "overall_resolution_percent": 96,
                            "real_data_readiness_percent": 68,
                            "real_data_handoff_percent": 95,
                            "ready_for_resolved_study": True,
                            "ready_for_live_public_study": True,
                            "ready_for_real_data_study": False,
                            "ready_for_lab_handoff": True,
                            "n_real_data_tasks": 3,
                            "n_critical_real_data_tasks": 2,
                        },
                        "recommended_actions": [],
                        "resolved_study_config_path": str(resolved_config_path),
                        "study_public_config_resolution_manifest_path": str(resolution_manifest_path),
                        "study_public_config_resolution_report_markdown_path": str(resolution_report_path),
                        "study_cohort_freeze_manifest_path": str(cohort_freeze_manifest_path),
                        "study_cohort_freeze_markdown_path": str(cohort_freeze_report_path),
                        "study_real_data_handoff_manifest_path": str(real_data_handoff_manifest_path),
                        "study_real_data_handoff_markdown_path": str(real_data_handoff_report_path),
                    },
                ),
                patch(
                    "primevarclass.public_study_runner.export_study_preflight",
                    return_value={
                        "preflight": {
                            "summary": {
                                "overall_preflight_percent": 92,
                                "ready_to_run": True,
                            },
                            "recommended_actions": [],
                        },
                        "study_preflight_manifest_path": str(preflight_manifest_path),
                        "study_preflight_report_markdown_path": str(preflight_report_path),
                    },
                ),
                patch(
                    "primevarclass.public_study_runner.run_publication_study",
                    return_value={
                        "study_cohort_freeze_manifest_path": str(cohort_freeze_manifest_path),
                        "study_cohort_freeze_markdown_path": str(cohort_freeze_report_path),
                        "publication_readiness_assessment": {
                            "summary": {
                                "overall_readiness_percent": 87,
                            }
                        },
                        "study_release_manifest_path": str(study_release_manifest_path),
                        "study_summary_report_path": str(study_summary_path),
                        "publication_readiness_manifest_path": str(publication_manifest_path),
                    },
                ),
                patch(
                    "primevarclass.public_study_runner.export_study_execution_board",
                    return_value={
                        "study_execution_board": {
                            "summary": {
                                "overall_execution_percent": 89,
                                "ready_for_benchmark_lock": True,
                                "ready_for_submission_lock": True,
                                "ready_for_translational_pilot": True,
                            },
                            "recommended_actions": [],
                        },
                        "study_execution_board_manifest_path": str(execution_manifest_path),
                        "study_execution_board_markdown_path": str(execution_report_path),
                        "study_execution_board_html_path": str(execution_html_path),
                    },
                ),
            ):
                results = run_public_benchmark_pipeline(
                    config_path=str(config_path),
                    output_dir=str(tmp_path / "public_run"),
                    require_live_public_ready=True,
                )

            self.assertTrue(Path(results["public_study_run_manifest_path"]).exists())
            self.assertTrue(Path(results["public_study_run_report_markdown_path"]).exists())
            manifest = json.loads(Path(results["public_study_run_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["resolution_percent"], 96)
            self.assertEqual(manifest["summary"]["real_data_readiness_percent"], 68)
            self.assertEqual(manifest["summary"]["real_data_handoff_percent"], 95)
            self.assertIn("pilot_package_percent", manifest["summary"])
            self.assertIn("translational_impact_percent", manifest["summary"])
            self.assertIn("pilot_mode", manifest["summary"])
            self.assertIn("final_mile_percent", manifest["summary"])
            self.assertTrue(manifest["summary"]["ready_for_benchmark_lock"])
            self.assertEqual(manifest["cohort_freeze_manifest_path"], str(cohort_freeze_manifest_path))
            self.assertEqual(manifest["real_data_handoff_manifest_path"], str(real_data_handoff_manifest_path))
            self.assertTrue(Path(results["translational_pilot_package_manifest_path"]).exists())
            self.assertTrue(Path(results["translational_pilot_package_markdown_path"]).exists())
            self.assertTrue(Path(results["translational_pilot_package_html_path"]).exists())
            self.assertTrue(Path(results["translational_impact_package_manifest_path"]).exists())
            self.assertTrue(Path(results["translational_impact_package_markdown_path"]).exists())
            self.assertTrue(Path(results["translational_impact_package_html_path"]).exists())
            self.assertTrue(Path(results["final_mile_package_manifest_path"]).exists())
            self.assertTrue(Path(results["final_mile_package_markdown_path"]).exists())
            self.assertTrue(Path(results["final_mile_package_html_path"]).exists())

    def test_run_candidate_public_benchmark_pipeline_generates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidate_config_path = tmp_path / "study_real_data_candidate_config.toml"
            candidate_config_path.write_text("[study]\nname = \"Candidate Public Study\"\n", encoding="utf-8")
            promotion_manifest_path = tmp_path / "study_real_data_candidate_promotion_manifest.json"
            promotion_manifest_path.write_text(
                json.dumps({"summary": {"overall_candidate_promotion_percent": 91, "ready_to_run_candidate_public_study": True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            public_run_manifest_path = tmp_path / "public_study_run_manifest.json"
            public_run_report_path = tmp_path / "public_study_run_report.md"
            public_run_manifest_path.write_text("{}", encoding="utf-8")
            public_run_report_path.write_text("# report", encoding="utf-8")

            with patch(
                "primevarclass.candidate_public_runner.run_public_benchmark_pipeline",
                return_value={
                    "output_dir": str(tmp_path / "candidate_run"),
                    "summary": {
                        "resolution_percent": 100,
                        "preflight_percent": 93,
                        "real_data_readiness_percent": 81,
                        "comparative_evidence_percent": 77,
                        "claim_strength_percent": 74,
                        "publication_readiness_percent": 85,
                        "ready_for_submission_lock": True,
                        "ready_for_shadow_rollout": True,
                    },
                    "public_study_run_manifest_path": str(public_run_manifest_path),
                    "public_study_run_report_markdown_path": str(public_run_report_path),
                    "recommended_actions": ["Revisar resultados comparativos."],
                },
            ):
                results = run_candidate_public_benchmark_pipeline(
                    candidate_config_path=str(candidate_config_path),
                    output_dir=str(tmp_path / "candidate_output"),
                    candidate_promotion_manifest_path=str(promotion_manifest_path),
                    require_candidate_ready=True,
                )

            self.assertTrue(Path(results["candidate_public_run_manifest_path"]).exists())
            self.assertTrue(Path(results["candidate_public_run_report_markdown_path"]).exists())
            summary = results["candidate_public_run_summary"]
            self.assertTrue(summary["candidate_ready_before_launch"])
            self.assertEqual(summary["candidate_promotion_percent"], 91)
            self.assertTrue(summary["ready_for_submission_lock"])


class ApiTests(unittest.TestCase):
    def test_api_serves_workbench(self):
        client = TestClient(create_app())

        response = client.get("/workbench")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        self.assertIn("PrimeVarClass | Bancada científica", response.text)
        self.assertIn("/workbench/assets/workbench.css", response.text)
        self.assertIn("language-select", response.text)
        self.assertIn("module-switcher", response.text)
        self.assertIn("Guia rápido para usuários", response.text)
        self.assertNotIn("Progresso do projeto", response.text)
        self.assertNotIn("ux_references", response.text)
        self.assertIn("Catálogo público real", response.text)
        self.assertIn("Gerar pacote inicial", response.text)
        self.assertIn("Resolver catálogo", response.text)
        self.assertIn("Executar simulação", response.text)
        self.assertIn("Ver histórico", response.text)
        self.assertIn("Pré-validação e inspeção", response.text)
        self.assertIn("Resolver estudo público", response.text)
        self.assertIn("Autopreencher entrega", response.text)
        self.assertIn("Executar estudo público final", response.text)
        self.assertIn("Executar estudo candidato", response.text)
        self.assertIn("prontidão com dados reais", response.text.lower())
        self.assertIn("trava de validação", response.text.lower())
        self.assertIn("Expansão científica e números primos", response.text)
        self.assertIn("Gerar expansão gênica", response.text)
        self.assertIn("Gerar impacto proteico", response.text)
        self.assertIn("Gerar proteômica quântica", response.text)
        self.assertIn("Fechar validação prospectiva", response.text)
        self.assertIn("Fechar credibilidade", response.text)
        self.assertIn("Mapear bancos independentes", response.text)
        self.assertIn("Auto-stage fontes abertas", response.text)
        self.assertIn("Fechar staging independente", response.text)
        self.assertIn("Planejar expansão", response.text)
        self.assertIn("Gerar estruturas de estudo", response.text)
        self.assertIn("Impacto social e translacional", response.text)
        self.assertIn("Prontidão científica e web", response.text)

    def test_launch_readiness_endpoint_and_export(self):
        client = TestClient(create_app())

        response = client.get("/launch/readiness")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("checks", payload)
        self.assertIn("overall_launch_readiness_percent", payload["summary"])
        self.assertTrue(any(item["gate_id"] == "api_service" for item in payload["checks"]))
        self.assertTrue(any(item["gate_id"] == "workbench_ui" for item in payload["checks"]))

        with tempfile.TemporaryDirectory() as tmp_dir:
            results = export_launch_readiness_package(
                output_dir=tmp_dir,
                workspace_root=Path(__file__).resolve().parents[1],
                include_absolute_paths=False,
            )

            self.assertTrue(Path(results["launch_readiness_manifest_path"]).exists())
            self.assertTrue(Path(results["launch_readiness_report_markdown_path"]).exists())
            self.assertTrue(Path(results["launch_readiness_checklist_path"]).exists())
            self.assertIn("overall_launch_readiness_percent", results["launch_readiness_summary"])

    def test_api_builds_independent_data_expansion_package(self):
        client = TestClient(create_app())

        with tempfile.TemporaryDirectory() as tmp_dir:
            response = client.post(
                "/science/independent-data-expansion",
                json={
                    "output_dir": tmp_dir,
                    "target_genes": ["BRCA1", "TP53", "KRAS"],
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertGreaterEqual(payload["summary"]["database_count"], 14)
            self.assertGreaterEqual(payload["summary"]["independent_data_expansion_percent"], 80)
            self.assertTrue(Path(payload["independent_data_expansion_manifest_path"]).exists())
            self.assertTrue(Path(payload["independent_source_templates_path"]).exists())

    def test_api_builds_independent_data_staging_closure_package(self):
        client = TestClient(create_app())

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            for relative_dir in [
                "data/raw/clinvar",
                "data/raw/gnomad",
                "data/raw/mavedb",
                "data/raw/brca_exchange",
            ]:
                (tmp_path / relative_dir).mkdir(parents=True, exist_ok=True)
            (tmp_path / "data/raw/clinvar/variant_summary.txt").write_text(
                "GeneSymbol\tName\tClinicalSignificance\n" + ("BRCA1\tp.Cys61Gly\tPathogenic\n" * 40),
                encoding="utf-8",
            )
            (tmp_path / "data/raw/gnomad/brca_missense_annotations.tsv").write_text(
                "gene\thgvs_p\taf\n" + ("BRCA1\tp.Cys61Gly\t0.000001\n" * 40),
                encoding="utf-8",
            )
            (tmp_path / "data/raw/mavedb/brca_function_scores.csv").write_text(
                "gene,hgvs_p,score\n" + ("BRCA1,p.Cys61Gly,-1.2\n" * 40),
                encoding="utf-8",
            )
            (tmp_path / "data/raw/brca_exchange/enigma_brca_curated.tsv").write_text(
                "gene\thgvs_p\tlabel\n" + ("BRCA1\tp.Cys61Gly\tPathogenic\n" * 40),
                encoding="utf-8",
            )

            response = client.post(
                "/science/independent-data-staging-closure",
                json={
                    "output_dir": str(tmp_path / "closure"),
                    "workspace_root": str(tmp_path),
                    "target_genes": ["BRCA1", "BRCA2", "TP53", "PTEN"],
                },
            )

            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertTrue(payload["summary"]["ready_for_next_training_round"])
            self.assertGreater(payload["summary"]["line_level_real_data_execution_percent"], 0)
            self.assertTrue(Path(payload["independent_data_staging_closure_manifest_path"]).exists())
            self.assertTrue(Path(payload["independent_ready_source_config_path"]).exists())

    def test_api_builds_independent_open_source_autostage_package(self):
        client = TestClient(create_app())
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_path = Path(tmp_dir) / "autostage_manifest.json"
            status_path = Path(tmp_dir) / "autostage_status.csv"
            error_path = Path(tmp_dir) / "autostage_errors.csv"
            manifest_path.write_text("{}", encoding="utf-8")
            status_path.write_text("source_id\tstatus\nuniprot\tstaged\n", encoding="utf-8")
            error_path.write_text("source_id\tstatus\n", encoding="utf-8")
            mocked_results = {
                "summary": {
                    "attempted_source_count": 10,
                    "staged_source_count": 9,
                    "autostaging_readiness_percent": 90,
                    "ready_for_staging_closure_refresh": True,
                },
                "staged_sources": [{"source_id": "uniprot", "status": "staged"}],
                "errors": [],
                "independent_open_source_autostage_manifest_path": str(manifest_path),
                "independent_open_source_autostage_status_path": str(status_path),
                "independent_open_source_autostage_errors_path": str(error_path),
            }

            with patch("primevarclass.api.export_independent_open_source_autostage_package", return_value=mocked_results):
                response = client.post(
                    "/science/independent-open-source-autostage",
                    json={
                        "output_dir": str(Path(tmp_dir) / "autostage"),
                        "target_genes": ["BRCA1"],
                    },
                )

            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["summary"]["autostaging_readiness_percent"], 90)
            self.assertEqual(payload["staged_sources"][0]["source_id"], "uniprot")

    def test_api_exposes_bilingual_knowledge_docs(self):
        client = TestClient(create_app())

        response = client.get("/knowledge")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        docs = {item["doc_id"]: item for item in payload["docs"]}
        self.assertIn("manual", docs)
        self.assertIn("manual_en", docs)
        self.assertIn("glossary", docs)
        self.assertIn("glossary_en", docs)
        self.assertIn("feedback_en", docs)
        self.assertIn("ux_references", docs)
        self.assertEqual(docs["manual"]["language"], "pt-BR")
        self.assertEqual(docs["manual_en"]["language"], "en")
        self.assertTrue(docs["manual_en"]["available"])
        self.assertTrue(docs["manual"]["pdf_available"])
        self.assertTrue(docs["glossary"]["pdf_available"])
        self.assertEqual(docs["manual"]["pdf_url"], "/knowledge/manual.pdf")

        manual_response = client.get("/knowledge/manual_en")
        glossary_response = client.get("/knowledge/glossary_en")
        manual_pdf_response = client.get("/knowledge/manual.pdf")
        glossary_pdf_response = client.get("/knowledge/glossary.pdf")

        self.assertEqual(manual_response.status_code, 200)
        self.assertEqual(glossary_response.status_code, 200)
        self.assertEqual(manual_pdf_response.status_code, 200)
        self.assertEqual(glossary_pdf_response.status_code, 200)
        self.assertEqual(manual_pdf_response.headers["content-type"], "application/pdf")
        self.assertIn("PrimeVarClass - User Manual", manual_response.text)
        self.assertIn("PrimeVarClass - Glossary", glossary_response.text)

    def test_api_exposes_project_roadmap_progress(self):
        client = TestClient(create_app())

        response = client.get("/roadmap/progress")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("stages", payload)
        self.assertEqual(payload["summary"]["overall_progress_percent"], 100)
        self.assertTrue(payload["summary"]["development_complete"])
        self.assertTrue(payload["summary"]["scientific_validation_pending"])
        self.assertGreaterEqual(len(payload["stages"]), 5)
        self.assertTrue(all(stage["progress_percent"] == 100 for stage in payload["stages"]))
        self.assertTrue(all("progress_bar" in stage for stage in payload["stages"]))

    def test_api_runs_multigene_rollout_and_study_factory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            clinvar_path = tmp_path / "variant_summary.txt.gz"
            mavedb_dump_path = tmp_path / "mavedb_dump.zip"

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg175His", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg248Gln", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "TP53", "Protein change": "p.Arg273His", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts"},
                    {"GeneSymbol": "PTEN", "Protein change": "p.Arg130Gln", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel"},
                    {"GeneSymbol": "PTEN", "Protein change": "p.Gly127Arg", "ClinicalSignificance": "Likely pathogenic", "ReviewStatus": "criteria provided, single submitter"},
                ]
            ).to_csv(clinvar_path, sep="\t", index=False, compression="gzip")

            mavedb_main = {
                "experimentSets": [
                    {
                        "experiments": [
                            {
                                "title": "TP53 assay",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000011-a-1",
                                        "title": "TP53 set",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "TP53"}],
                                    }
                                ],
                            },
                            {
                                "title": "PTEN assay",
                                "scoreSets": [
                                    {
                                        "urn": "urn:mavedb:00000012-a-1",
                                        "title": "PTEN set",
                                        "processingState": "success",
                                        "targetGenes": [{"name": "PTEN"}],
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
            with zipfile.ZipFile(mavedb_dump_path, "w") as archive:
                archive.writestr("main.json", json.dumps(mavedb_main))
                archive.writestr(
                    "csv/urn-mavedb-00000011-a-1.scores.csv",
                    pd.DataFrame(
                        [
                            {"hgvs_pro": "p.Arg175His", "score": -2.1},
                            {"hgvs_pro": "p.Arg248Gln", "score": -1.9},
                            {"hgvs_pro": "p.Arg273His", "score": -1.8},
                        ]
                    ).to_csv(index=False),
                )
                archive.writestr(
                    "csv/urn-mavedb-00000012-a-1.scores.csv",
                    pd.DataFrame(
                        [
                            {"hgvs_pro": "p.Arg130Gln", "score": -2.0},
                            {"hgvs_pro": "p.Gly127Arg", "score": -1.7},
                        ]
                    ).to_csv(index=False),
                )

            client = TestClient(create_app())

            expansion_response = client.post(
                "/science/gene-expansion",
                json={
                    "clinvar_variant_summary_path": str(clinvar_path),
                    "mavedb_dump_path": str(mavedb_dump_path),
                    "output_dir": str(tmp_path / "gene_expansion"),
                },
            )
            self.assertEqual(expansion_response.status_code, 200)
            expansion_payload = expansion_response.json()
            self.assertTrue(Path(expansion_payload["gene_expansion_manifest_path"]).exists())
            self.assertGreaterEqual(expansion_payload["summary"]["recommended_gene_count"], 2)

            rollout_response = client.post(
                "/science/multigene-rollout",
                json={
                    "gene_expansion_manifest_path": expansion_payload["gene_expansion_manifest_path"],
                    "output_dir": str(tmp_path / "rollout"),
                    "max_phase_1": 1,
                    "max_phase_2": 1,
                    "max_total_genes": 2,
                },
            )
            self.assertEqual(rollout_response.status_code, 200)
            rollout_payload = rollout_response.json()
            self.assertTrue(Path(rollout_payload["multigene_rollout_manifest_path"]).exists())
            self.assertEqual(rollout_payload["summary"]["phase_1_gene_count"], 1)

            factory_response = client.post(
                "/science/multigene-study-factory",
                json={
                    "rollout_manifest_path": rollout_payload["multigene_rollout_manifest_path"],
                    "output_dir": str(tmp_path / "study_factory"),
                    "workspace_root": str(tmp_path / "workspace"),
                },
            )
            self.assertEqual(factory_response.status_code, 200)
            factory_payload = factory_response.json()
            self.assertTrue(Path(factory_payload["multigene_study_factory_manifest_path"]).exists())
            self.assertTrue(Path(factory_payload["multigene_study_scaffold_index_path"]).exists())
            self.assertGreaterEqual(factory_payload["summary"]["total_scaffolded_genes"], 1)

    def test_api_runs_biological_discovery_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            artifact_root = tmp_path / "artifacts"
            artifact_root.mkdir(parents=True, exist_ok=True)

            training_path = artifact_root / "training.tsv"
            clinvar_expert_path = artifact_root / "clinvar_expert.tsv"
            external_path = artifact_root / "external.tsv"
            enigma_path = artifact_root / "enigma.tsv"
            gnomad_path = artifact_root / "gnomad.tsv"
            mavedb_path = artifact_root / "mavedb.csv"
            manifest_path = artifact_root / "real_data_preparation_manifest.json"

            pd.DataFrame(
                [
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys10Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "1", "Name": "BRCA1 p.Cys10Gly"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys20Arg", "ClinicalSignificance": "Likely pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "2", "Name": "BRCA1 p.Cys20Arg"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys30Tyr", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "3", "Name": "BRCA1 p.Cys30Tyr"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Cys40Phe", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "criteria provided, single submitter", "VariationID": "4", "Name": "BRCA1 p.Cys40Phe"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Met80Thr", "ClinicalSignificance": "Likely benign", "ReviewStatus": "criteria provided, single submitter", "VariationID": "5", "Name": "BRCA1 p.Met80Thr"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Ile90Val", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "6", "Name": "BRCA1 p.Ile90Val"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Leu100Pro", "ClinicalSignificance": "Likely benign", "ReviewStatus": "criteria provided, single submitter", "VariationID": "7", "Name": "BRCA1 p.Leu100Pro"},
                    {"GeneSymbol": "BRCA1", "Protein change": "p.Val110Ala", "ClinicalSignificance": "Benign", "ReviewStatus": "criteria provided, multiple submitters, no conflicts", "VariationID": "8", "Name": "BRCA1 p.Val110Ala"},
                ]
            ).to_csv(training_path, sep="\t", index=False)

            pd.DataFrame(
                [{"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "reviewed by expert panel", "VariationID": "9", "Name": "BRCA1 p.Cys61Gly"}]
            ).to_csv(clinvar_expert_path, sep="\t", index=False)
            pd.DataFrame(
                [{"GeneSymbol": "BRCA1", "Protein change": "p.Cys61Gly", "ClinicalSignificance": "Pathogenic", "ReviewStatus": "BRCA Exchange / LOVD external curated release 2026-01-05", "VariationID": "10", "Name": "BRCA1 p.Cys61Gly"}]
            ).to_csv(external_path, sep="\t", index=False)
            pd.DataFrame(
                [{"GeneSymbol": "BRCA1", "Protein change": "p.Asp1902Asn", "ClinicalSignificance": "Benign", "ReviewStatus": "ENIGMA curated", "VariationID": "11", "Name": "BRCA1 p.Asp1902Asn"}]
            ).to_csv(enigma_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys10Gly", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys20Arg", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys30Tyr", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys40Phe", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys35Trp", "af": 0.0, "ac": 0, "an": 100000, "popmax_af": 1e-7},
                    {"gene": "BRCA1", "hgvs_p": "p.Met80Thr", "af": 0.00002, "ac": 2, "an": 100000, "popmax_af": 0.00002},
                    {"gene": "BRCA1", "hgvs_p": "p.Ile90Val", "af": 0.00003, "ac": 3, "an": 100000, "popmax_af": 0.00003},
                    {"gene": "BRCA1", "hgvs_p": "p.Leu100Pro", "af": 0.00004, "ac": 4, "an": 100000, "popmax_af": 0.00004},
                    {"gene": "BRCA1", "hgvs_p": "p.Val110Ala", "af": 0.00005, "ac": 5, "an": 100000, "popmax_af": 0.00005},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys10Gly", "score": -2.4, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys20Arg", "score": -2.2, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys30Tyr", "score": -2.1, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys40Phe", "score": -2.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Cys35Trp", "score": -2.5, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Met80Thr", "score": 1.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Ile90Val", "score": 1.1, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Leu100Pro", "score": 1.2, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                    {"gene": "BRCA1", "hgvs_p": "p.Val110Ala", "score": 1.0, "score_set_urn": "urn:mavedb:test-a", "assay_name": "BRCA1 functional scan"},
                ]
            ).to_csv(mavedb_path, index=False)

            manifest_path.write_text(
                json.dumps(
                    {
                        "artifact_paths": {
                            "training_table": str(training_path),
                            "clinvar_expert_table": str(clinvar_expert_path),
                            "external_table": str(external_path),
                            "enigma_table": str(enigma_path),
                            "gnomad_table": str(gnomad_path),
                            "mavedb_table": str(mavedb_path),
                        }
                    }
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/science/biological-discovery",
                json={
                    "real_data_manifest_path": str(manifest_path),
                    "output_dir": str(tmp_path / "biological_discovery"),
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(Path(payload["biological_discovery_manifest_path"]).exists())
            self.assertGreaterEqual(payload["summary"]["hotspot_count"], 1)
            self.assertGreaterEqual(payload["summary"]["hypothesis_variant_count"], 1)

            protein_response = client.post(
                "/science/protein-impact",
                json={
                    "biological_discovery_manifest_path": payload["biological_discovery_manifest_path"],
                    "output_dir": str(tmp_path / "protein_impact"),
                    "max_modeling_variants": 3,
                },
            )
            self.assertEqual(protein_response.status_code, 200)
            protein_payload = protein_response.json()
            self.assertTrue(Path(protein_payload["protein_impact_manifest_path"]).exists())
            self.assertGreaterEqual(protein_payload["summary"]["modeling_queue_count"], 1)

            quantum_response = client.post(
                "/science/quantum-proteomics",
                json={
                    "protein_impact_manifest_path": protein_payload["protein_impact_manifest_path"],
                    "output_dir": str(tmp_path / "quantum_proteomics"),
                    "max_quantum_targets": 2,
                },
            )
            self.assertEqual(quantum_response.status_code, 200)
            quantum_payload = quantum_response.json()
            self.assertTrue(Path(quantum_payload["quantum_proteomics_manifest_path"]).exists())
            self.assertGreaterEqual(quantum_payload["summary"]["quantum_target_count"], 1)

            closure_response = client.post(
                "/science/validation-credibility-closure",
                json={
                    "output_dir": str(tmp_path / "closure"),
                    "biological_discovery_manifest_path": payload["biological_discovery_manifest_path"],
                    "protein_impact_manifest_path": protein_payload["protein_impact_manifest_path"],
                    "quantum_proteomics_manifest_path": quantum_payload["quantum_proteomics_manifest_path"],
                },
            )
            self.assertEqual(closure_response.status_code, 200)
            closure_payload = closure_response.json()
            self.assertTrue(Path(closure_payload["validation_credibility_closure_manifest_path"]).exists())
            self.assertIn("why_not_100_percent", closure_payload["summary"])

    def test_api_tracks_translational_pilot_sessions_and_feedback(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TestClient(create_app(job_root=str(Path(tmp_dir) / "jobs")))

            session_response = client.post(
                "/impact/pilot/sessions",
                json={
                    "session_id": "shadow-001",
                    "study_name": "Impact Study",
                    "pilot_mode": "shadow_mode",
                    "site_name": "Lab A",
                    "status": "completed",
                    "cases_reviewed": 12,
                    "variants_flagged": 4,
                    "outcome_summary": "Sessao concluida.",
                },
            )
            self.assertEqual(session_response.status_code, 200)
            session_payload = session_response.json()
            self.assertEqual(session_payload["session"]["session_id"], "shadow-001")

            feedback_response = client.post(
                "/impact/pilot/feedback",
                json={
                    "session_id": "shadow-001",
                    "study_name": "Impact Study",
                    "confidence_score": 5,
                    "actionability_score": 4,
                    "time_saved_minutes": 25,
                    "adoption_recommendation": "recommended",
                    "incident_level": "none",
                },
            )
            self.assertEqual(feedback_response.status_code, 200)
            feedback_payload = feedback_response.json()
            self.assertEqual(feedback_payload["feedback"]["session_id"], "shadow-001")

            dashboard_response = client.get("/impact/translational/dashboard", params={"study_name": "Impact Study"})
            self.assertEqual(dashboard_response.status_code, 200)
            dashboard_payload = dashboard_response.json()
            summary = dashboard_payload["dashboard"]["summary"]
            self.assertEqual(summary["n_sessions"], 1)
            self.assertEqual(summary["n_feedback_entries"], 1)
            self.assertGreaterEqual(summary["rollout_signal_percent"], 1)

    def test_api_runs_study_and_returns_publication_readiness_summary(self):
        client = TestClient(create_app())
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            response = client.post(
                "/study/run",
                json={
                    "config_path": str(config_path),
                    "output_dir": tmp_dir,
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("publication_readiness_percent", payload)
            self.assertIn("publication_ready_for_submission", payload)
            self.assertIn("cohort_independence_percent", payload)
            self.assertIn("real_data_readiness_percent", payload)
            self.assertIn("ready_for_real_data_study", payload)
            self.assertTrue(Path(payload["cohort_independence_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_cohort_freeze_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_cohort_freeze_markdown_path"]).exists())
            self.assertTrue(Path(payload["publication_readiness_manifest_path"]).exists())
            self.assertTrue(Path(payload["publication_readiness_report_markdown_path"]).exists())
            self.assertTrue(Path(payload["comparative_evidence_manifest_path"]).exists())
            self.assertTrue(Path(payload["comparative_evidence_report_markdown_path"]).exists())
            self.assertIn("comparative_evidence_percent", payload)
            self.assertTrue(Path(payload["claim_strength_manifest_path"]).exists())
            self.assertTrue(Path(payload["claim_strength_report_markdown_path"]).exists())
            self.assertIn("claim_strength_percent", payload)
            self.assertIn("claim_tier", payload)
            self.assertTrue(Path(payload["baseline_coverage_manifest_path"]).exists())
            self.assertTrue(Path(payload["methods_package_manifest_path"]).exists())
            self.assertTrue(Path(payload["manuscript_package_manifest_path"]).exists())
            self.assertTrue(Path(payload["manuscript_package_markdown_path"]).exists())
            self.assertTrue(Path(payload["study_validation_lock_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_validation_lock_markdown_path"]).exists())
            self.assertIn("validation_lock_percent", payload)

    def test_api_runs_study_preflight(self):
        client = TestClient(create_app())
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            response = client.post(
                "/study/preflight",
                json={
                    "config_path": str(config_path),
                    "output_dir": tmp_dir,
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("summary", payload)
            self.assertIn("overall_preflight_percent", payload["summary"])
            self.assertIn("cohort_independence_percent", payload["summary"])
            self.assertTrue(Path(payload["study_preflight_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_preflight_independence_pairs_path"]).exists())

    def test_api_inspects_study_bundle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
            run_publication_study(
                config_path=str(config_path),
                output_dir=tmp_dir,
            )

            client = TestClient(create_app())
            response = client.post(
                "/study/bundle/inspect",
                json={"result_dir": tmp_dir},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("summary", payload)
            self.assertTrue(payload["summary"]["has_publication_readiness"])
            self.assertTrue(payload["summary"]["has_cohort_independence"])
            self.assertTrue(payload["summary"]["has_cohort_freeze"])
            self.assertTrue(payload["summary"]["has_comparative_evidence"])
            self.assertTrue(payload["summary"]["has_claim_strength"])
            self.assertTrue(payload["summary"]["has_baseline_coverage"])
            self.assertTrue(payload["summary"]["has_methods_package"])
            self.assertTrue(payload["summary"]["has_manuscript_package"])
            self.assertTrue(payload["summary"]["has_validation_lock"])
            self.assertIn("real_data_readiness_percent", payload["summary"])

    def test_api_resolves_public_source_catalog_to_staged_subset(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            gnomad_path = tmp_path / "gnomad_release.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                    {"gene": "TP53", "hgvs_p": "p.Arg175His", "af": 0.00012},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "local_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "v4.1"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            execute_response = client.post(
                "/public-sources/catalog/bootstrap/execute",
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                    "dry_run": False,
                },
            )
            self.assertEqual(execute_response.status_code, 200)

            resolve_response = client.post(
                "/public-sources/catalog/resolve",
                json={
                    "config_path": str(config_path),
                    "bootstrap_output_dir": str(output_dir),
                    "output_dir": str(output_dir),
                },
            )
            self.assertEqual(resolve_response.status_code, 200)
            payload = resolve_response.json()
            self.assertTrue(Path(payload["resolved_config_path"]).exists())
            self.assertTrue(Path(payload["public_source_resolution_manifest_path"]).exists())
            self.assertGreaterEqual(payload["summary"]["overall_resolution_percent"], 90)
            self.assertTrue(payload["summary"]["ready_for_resolved_config"])
            gnomad_row = next(item for item in payload["source_rows"] if item["source_name"] == "gnomad_annotations")
            self.assertEqual(gnomad_row["resolution_status"], "resolved_from_staged_artifact")
            self.assertTrue(str(gnomad_row["resolved_path"]).endswith("gnomad_brca_subset.tsv"))

    def test_api_resolves_public_study_config(self):
        client = TestClient(create_app())
        config_path = Path(__file__).resolve().parents[1] / "configs" / "public_brca_benchmark_example.toml"
        with tempfile.TemporaryDirectory() as tmp_dir:
            response = client.post(
                "/study/public-config/resolve",
                json={
                    "config_path": str(config_path),
                    "output_dir": tmp_dir,
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(Path(payload["resolved_study_config_path"]).exists())
            self.assertTrue(Path(payload["study_public_config_resolution_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_public_config_resolution_cohorts_path"]).exists())
            self.assertTrue(Path(payload["study_cohort_freeze_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_cohort_freeze_markdown_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_markdown_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_tracker_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_reconciliation_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_reconciliation_markdown_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_candidate_config_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_application_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_application_markdown_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_candidate_promotion_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_candidate_promotion_markdown_path"]).exists())
            self.assertTrue(payload["summary"]["ready_for_resolved_study"])
            self.assertGreaterEqual(payload["summary"]["n_ready_cohorts"], 2)
            self.assertIn("real_data_readiness_percent", payload["summary"])
            self.assertIn("real_data_handoff_percent", payload["summary"])
            self.assertIn("real_data_handoff_reconciliation_percent", payload["summary"])
            self.assertIn("real_data_handoff_application_percent", payload["summary"])
            self.assertIn("real_data_candidate_promotion_percent", payload["summary"])
            self.assertFalse(payload["summary"]["ready_for_real_data_study"])
            self.assertTrue(payload["summary"]["ready_for_lab_handoff"])
            self.assertGreaterEqual(payload["summary"]["n_real_data_tasks"], 1)

    def test_api_autofills_real_data_handoff_tracker(self):
        client = TestClient(create_app())
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tasks_path = tmp_path / "study_real_data_handoff_tasks.csv"
            delivery_dir = tmp_path / "delivery_drop"
            delivery_dir.mkdir(parents=True, exist_ok=True)
            tracker_path = tmp_path / "study_real_data_handoff_tracker.csv"
            pd.DataFrame(
                [
                    {
                        "task_id": "train::clinvar::replace_example_source",
                        "priority": "critical",
                        "cohort_name": "train",
                        "cohort_role": "train",
                        "source_name": "clinvar_variant_summary",
                        "profile_id": "clinvar",
                        "task_type": "replace_example_source",
                        "owner_hint": "data_curation",
                        "blocking_reason": "example path",
                        "recommended_action": "Trocar ClinVar por tabela real.",
                        "current_path": "data/examples/clinvar_variant_summary_like.tsv",
                        "target_path": str(tmp_path / "clinvar_variant_summary.tsv"),
                        "release_value": "",
                        "resolution_status": "blocked",
                    }
                ]
            ).to_csv(tasks_path, index=False)
            (delivery_dir / "clinvar_variant_summary_2026_04_03.tsv").write_text(
                "gene\thgvs_p\tlabel\nBRCA1\tp.Cys61Gly\tPathogenic\n",
                encoding="utf-8",
            )

            response = client.post(
                "/study/real-data-handoff/autofill",
                json={
                    "study_name": "Public BRCA Benchmark Example",
                    "handoff_tasks_path": str(tasks_path),
                    "tracker_path": str(tracker_path),
                    "delivery_dir": str(delivery_dir),
                    "output_dir": str(tmp_path / "handoff_autofill"),
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["overall_handoff_autofill_percent"], 100)
            self.assertTrue(payload["summary"]["ready_for_reconciliation_rerun"])
            self.assertTrue(Path(payload["study_real_data_handoff_autofill_manifest_path"]).exists())
            self.assertTrue(Path(payload["study_real_data_handoff_autofill_tracker_path"]).exists())

    def test_api_runs_public_study_pipeline(self):
        client = TestClient(create_app())
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "public_pipeline"
            output_dir.mkdir(parents=True, exist_ok=True)
            result_payload = {
                "summary": {
                    "resolution_percent": 98,
                    "real_data_readiness_percent": 66,
                    "real_data_handoff_percent": 97,
                    "real_data_handoff_reconciliation_percent": 45,
                    "real_data_handoff_application_percent": 25,
                    "real_data_candidate_promotion_percent": 39,
                    "ready_for_real_data_study": False,
                    "ready_for_lab_handoff": True,
                    "n_real_data_tasks": 4,
                    "n_critical_real_data_tasks": 2,
                    "n_handoff_validated_tasks": 1,
                    "n_handoff_pending_tasks": 3,
                    "n_handoff_invalid_tasks": 0,
                    "n_handoff_applied_changes": 1,
                    "ready_to_rerun_resolution_from_handoff": False,
                    "ready_to_rerun_public_study_from_handoff": False,
                    "ready_for_candidate_resolution_from_handoff": True,
                    "ready_for_candidate_public_study_from_handoff": False,
                    "ready_to_promote_candidate_config": True,
                    "ready_to_run_candidate_public_study": False,
                    "preflight_percent": 94,
                    "cohort_independence_percent": 100,
                    "publication_readiness_percent": 88,
                    "comparative_evidence_percent": 88,
                    "claim_strength_percent": 81,
                    "claim_tier": "moderate",
                    "validation_lock_percent": 84,
                    "execution_board_percent": 90,
                    "pilot_package_percent": 83,
                    "pilot_mode": "shadow_mode",
                    "ready_for_demo_pilot": True,
                    "ready_for_shadow_pilot": True,
                    "ready_for_live_pilot": False,
                    "translational_impact_percent": 78,
                    "ready_for_assisted_pilot_ops": True,
                    "ready_for_shadow_rollout": True,
                    "ready_for_institutional_rollout": False,
                    "final_mile_percent": 61,
                    "ready_for_real_data_execution": False,
                    "ready_for_final_evidence_round": False,
                    "ready_for_submission_closeout": False,
                    "ready_for_live_transition": False,
                    "n_final_mile_blockers": 5,
                    "n_final_mile_critical_blockers": 4,
                    "top_final_mile_blocker_phase": "science",
                    "top_final_mile_blocker_title": "Comparative evidence ainda insuficiente",
                    "ready_for_benchmark_lock": True,
                    "ready_for_submission_lock": False,
                    "ready_for_translational_pilot": True,
                },
                "study_output_dir": str(output_dir / "resolved_study_run"),
                "resolved_study_config_path": str(output_dir / "resolved_study_config.toml"),
                "study_public_config_resolution_manifest_path": str(output_dir / "resolution_manifest.json"),
                "study_public_config_resolution_report_markdown_path": str(output_dir / "resolution_report.md"),
                "study_cohort_freeze_manifest_path": str(output_dir / "study_cohort_freeze_manifest.json"),
                "study_cohort_freeze_markdown_path": str(output_dir / "study_cohort_freeze_report.md"),
                "study_real_data_handoff_manifest_path": str(output_dir / "study_real_data_handoff_manifest.json"),
                "study_real_data_handoff_markdown_path": str(output_dir / "study_real_data_handoff.md"),
                "study_real_data_handoff_tracker_path": str(output_dir / "study_real_data_handoff_tracker.csv"),
                "study_real_data_handoff_reconciliation_manifest_path": str(output_dir / "study_real_data_handoff_reconciliation_manifest.json"),
                "study_real_data_handoff_reconciliation_markdown_path": str(output_dir / "study_real_data_handoff_reconciliation.md"),
                "study_real_data_handoff_reconciliation_html_path": str(output_dir / "study_real_data_handoff_reconciliation.html"),
                "study_real_data_handoff_reconciliation_tasks_path": str(output_dir / "study_real_data_handoff_reconciliation_tasks.csv"),
                "study_real_data_candidate_config_path": str(output_dir / "study_real_data_candidate_config.toml"),
                "study_real_data_handoff_application_manifest_path": str(output_dir / "study_real_data_handoff_application_manifest.json"),
                "study_real_data_handoff_application_markdown_path": str(output_dir / "study_real_data_handoff_application.md"),
                "study_real_data_handoff_application_html_path": str(output_dir / "study_real_data_handoff_application.html"),
                "study_real_data_handoff_application_sources_path": str(output_dir / "study_real_data_handoff_application_sources.csv"),
                "study_real_data_candidate_promotion_manifest_path": str(output_dir / "study_real_data_candidate_promotion_manifest.json"),
                "study_real_data_candidate_promotion_markdown_path": str(output_dir / "study_real_data_candidate_promotion.md"),
                "study_real_data_candidate_promotion_html_path": str(output_dir / "study_real_data_candidate_promotion.html"),
                "study_real_data_candidate_promotion_criteria_path": str(output_dir / "study_real_data_candidate_promotion_criteria.csv"),
                "study_real_data_candidate_promotion_blockers_path": str(output_dir / "study_real_data_candidate_promotion_blockers.csv"),
                "study_preflight_manifest_path": str(output_dir / "preflight_manifest.json"),
                "study_preflight_report_markdown_path": str(output_dir / "preflight_report.md"),
                "study_release_manifest_path": str(output_dir / "study_release_manifest.json"),
                "cohort_independence_manifest_path": str(output_dir / "cohort_independence_manifest.json"),
                "cohort_independence_report_markdown_path": str(output_dir / "cohort_independence_report.md"),
                "comparative_evidence_manifest_path": str(output_dir / "comparative_evidence_manifest.json"),
                "comparative_evidence_report_markdown_path": str(output_dir / "comparative_evidence_report.md"),
                "claim_strength_manifest_path": str(output_dir / "claim_strength_manifest.json"),
                "claim_strength_report_markdown_path": str(output_dir / "claim_strength_report.md"),
                "publication_readiness_manifest_path": str(output_dir / "publication_manifest.json"),
                "study_validation_lock_manifest_path": str(output_dir / "study_validation_lock_manifest.json"),
                "study_validation_lock_markdown_path": str(output_dir / "study_validation_lock.md"),
                "study_execution_board_manifest_path": str(output_dir / "study_execution_board_manifest.json"),
                "study_execution_board_markdown_path": str(output_dir / "study_execution_board.md"),
                "study_execution_board_html_path": str(output_dir / "study_execution_board.html"),
                "translational_pilot_package_manifest_path": str(output_dir / "translational_pilot_package_manifest.json"),
                "translational_pilot_package_markdown_path": str(output_dir / "translational_pilot_package.md"),
                "translational_pilot_package_html_path": str(output_dir / "translational_pilot_package.html"),
                "translational_pilot_package_criteria_path": str(output_dir / "translational_pilot_package_criteria.csv"),
                "translational_pilot_package_checklist_path": str(output_dir / "translational_pilot_package_checklist.csv"),
                "translational_impact_package_manifest_path": str(output_dir / "translational_impact_package_manifest.json"),
                "translational_impact_package_markdown_path": str(output_dir / "translational_impact_package.md"),
                "translational_impact_package_html_path": str(output_dir / "translational_impact_package.html"),
                "translational_impact_package_criteria_path": str(output_dir / "translational_impact_package_criteria.csv"),
                "translational_impact_sessions_path": str(output_dir / "translational_impact_sessions.csv"),
                "translational_impact_feedback_path": str(output_dir / "translational_impact_feedback.csv"),
                "final_mile_package_manifest_path": str(output_dir / "final_mile_package_manifest.json"),
                "final_mile_package_markdown_path": str(output_dir / "final_mile_package.md"),
                "final_mile_package_html_path": str(output_dir / "final_mile_package.html"),
                "final_mile_package_criteria_path": str(output_dir / "final_mile_package_criteria.csv"),
                "final_mile_package_blockers_path": str(output_dir / "final_mile_package_blockers.csv"),
                "final_mile_package_checklist_path": str(output_dir / "final_mile_package_checklist.csv"),
                "public_study_run_manifest_path": str(output_dir / "public_study_run_manifest.json"),
                "public_study_run_report_markdown_path": str(output_dir / "public_study_run_report.md"),
                "recommended_actions": ["Conectar a coorte real final."],
            }

            with patch("primevarclass.api.run_public_benchmark_pipeline", return_value=result_payload):
                response = client.post(
                    "/study/public-run",
                    json={
                        "config_path": str(Path(tmp_dir) / "public_benchmark.toml"),
                        "output_dir": str(output_dir),
                        "bootstrap_root_dir": str(Path(tmp_dir) / "bootstrap_root"),
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["resolution_percent"], 98)
            self.assertEqual(payload["real_data_readiness_percent"], 66)
            self.assertEqual(payload["real_data_handoff_percent"], 97)
            self.assertEqual(payload["real_data_handoff_reconciliation_percent"], 45)
            self.assertEqual(payload["real_data_handoff_application_percent"], 25)
            self.assertEqual(payload["real_data_candidate_promotion_percent"], 39)
            self.assertEqual(payload["cohort_independence_percent"], 100)
            self.assertEqual(payload["claim_strength_percent"], 81)
            self.assertEqual(payload["claim_tier"], "moderate")
            self.assertEqual(payload["validation_lock_percent"], 84)
            self.assertEqual(payload["execution_board_percent"], 90)
            self.assertEqual(payload["pilot_package_percent"], 83)
            self.assertEqual(payload["pilot_mode"], "shadow_mode")
            self.assertTrue(payload["ready_for_demo_pilot"])
            self.assertTrue(payload["ready_for_shadow_pilot"])
            self.assertFalse(payload["ready_for_live_pilot"])
            self.assertEqual(payload["translational_impact_percent"], 78)
            self.assertTrue(payload["ready_for_assisted_pilot_ops"])
            self.assertTrue(payload["ready_for_shadow_rollout"])
            self.assertFalse(payload["ready_for_institutional_rollout"])
            self.assertEqual(payload["final_mile_percent"], 61)
            self.assertFalse(payload["ready_for_real_data_execution"])
            self.assertFalse(payload["ready_for_final_evidence_round"])
            self.assertFalse(payload["ready_for_submission_closeout"])
            self.assertEqual(payload["n_final_mile_blockers"], 5)
            self.assertEqual(payload["n_final_mile_critical_blockers"], 4)
            self.assertTrue(payload["ready_for_benchmark_lock"])
            self.assertFalse(payload["ready_for_real_data_study"])
            self.assertTrue(payload["ready_for_lab_handoff"])
            self.assertEqual(payload["n_real_data_tasks"], 4)
            self.assertEqual(payload["n_critical_real_data_tasks"], 2)
            self.assertEqual(payload["n_handoff_validated_tasks"], 1)
            self.assertEqual(payload["n_handoff_pending_tasks"], 3)
            self.assertEqual(payload["n_handoff_applied_changes"], 1)
            self.assertFalse(payload["ready_to_rerun_resolution_from_handoff"])
            self.assertFalse(payload["ready_to_rerun_public_study_from_handoff"])
            self.assertTrue(payload["ready_for_candidate_resolution_from_handoff"])
            self.assertFalse(payload["ready_for_candidate_public_study_from_handoff"])
            self.assertTrue(payload["ready_to_promote_candidate_config"])
            self.assertFalse(payload["ready_to_run_candidate_public_study"])
            self.assertEqual(payload["recommended_actions"], ["Conectar a coorte real final."])
            self.assertEqual(payload["translational_pilot_package_manifest_path"], str(output_dir / "translational_pilot_package_manifest.json"))
            self.assertEqual(payload["translational_impact_package_manifest_path"], str(output_dir / "translational_impact_package_manifest.json"))
            self.assertEqual(payload["final_mile_package_manifest_path"], str(output_dir / "final_mile_package_manifest.json"))
            self.assertEqual(payload["study_real_data_handoff_reconciliation_manifest_path"], str(output_dir / "study_real_data_handoff_reconciliation_manifest.json"))
            self.assertEqual(payload["study_real_data_handoff_application_manifest_path"], str(output_dir / "study_real_data_handoff_application_manifest.json"))
            self.assertEqual(payload["study_real_data_candidate_promotion_manifest_path"], str(output_dir / "study_real_data_candidate_promotion_manifest.json"))

    def test_api_runs_candidate_public_study_pipeline(self):
        client = TestClient(create_app())
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "candidate_public_pipeline"
            output_dir.mkdir(parents=True, exist_ok=True)
            result_payload = {
                "summary": {
                    "resolution_percent": 100,
                    "real_data_readiness_percent": 82,
                    "comparative_evidence_percent": 79,
                    "claim_strength_percent": 76,
                    "publication_readiness_percent": 86,
                    "ready_for_submission_lock": True,
                    "ready_for_shadow_rollout": True,
                },
                "candidate_public_run_summary": {
                    "candidate_promotion_percent": 93,
                    "candidate_ready_before_launch": True,
                    "candidate_launch_percent": 95,
                    "ready_for_submission_lock": True,
                },
                "candidate_public_run_manifest_path": str(output_dir / "candidate_public_run_manifest.json"),
                "candidate_public_run_report_markdown_path": str(output_dir / "candidate_public_run_report.md"),
                "public_study_run_manifest_path": str(output_dir / "public_study_run_manifest.json"),
                "public_study_run_report_markdown_path": str(output_dir / "public_study_run_report.md"),
                "recommended_actions": ["Consolidar a rodada final do paper."],
            }

            with patch("primevarclass.api.run_candidate_public_benchmark_pipeline", return_value=result_payload):
                response = client.post(
                    "/study/public-run/candidate",
                    json={
                        "candidate_config_path": str(Path(tmp_dir) / "study_real_data_candidate_config.toml"),
                        "candidate_promotion_manifest_path": str(Path(tmp_dir) / "study_real_data_candidate_promotion_manifest.json"),
                        "output_dir": str(output_dir),
                        "require_candidate_ready": True,
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["publication_readiness_percent"], 86)
            self.assertEqual(payload["candidate_public_run_summary"]["candidate_promotion_percent"], 93)
            self.assertEqual(payload["candidate_public_run_manifest_path"], str(output_dir / "candidate_public_run_manifest.json"))

    def test_api_lists_models_and_scores_variant(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_full_training_pipeline_from_dataframe(
                raw_df=dataset_schema_template(),
                mode="hybrid",
                output_dir=tmp_dir,
                keep_metadata=True,
                high_confidence_only=False,
                model_families=["logistic_regression"],
            )
            model_dir = Path(tmp_dir) / "models"
            client = TestClient(create_app())

            list_response = client.get("/models", params={"model_dir": str(model_dir)})
            self.assertEqual(list_response.status_code, 200)
            list_payload = list_response.json()
            self.assertGreaterEqual(list_payload["n_models"], 1)

            registry_path = results["model_paths"]["registry"]
            registry_df = pd.read_csv(registry_path)
            experiment = str(registry_df.iloc[0]["experiment"])

            predict_response = client.post(
                "/predict/variant",
                json={
                    "model_dir": str(model_dir),
                    "experiment": experiment,
                    "gene": "BRCA1",
                    "hgvs_p": "p.Cys61Gly",
                    "feature_payload": {
                        "phylop": 7.2,
                        "gerp": 5.8,
                        "siphy": 12.4,
                        "revel": 0.94,
                    },
                },
            )
            self.assertEqual(predict_response.status_code, 200)
            payload = predict_response.json()
            self.assertEqual(payload["gene"], "BRCA1")
            self.assertIn("predicted_probability", payload)
            self.assertIn("evidence_summary", payload)
            self.assertTrue(payload["used_features"])

    def test_api_scores_batch_and_returns_prioritized_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_full_training_pipeline_from_dataframe(
                raw_df=dataset_schema_template(),
                mode="hybrid",
                output_dir=tmp_dir,
                keep_metadata=True,
                high_confidence_only=False,
                model_families=["logistic_regression"],
            )
            model_dir = Path(tmp_dir) / "models"
            registry_df = pd.read_csv(results["model_paths"]["registry"])
            experiment = str(registry_df.iloc[0]["experiment"])
            client = TestClient(create_app())

            response = client.post(
                "/predict/batch",
                json={
                    "model_dir": str(model_dir),
                    "experiment": experiment,
                    "variants": [
                        {
                            "sample_id": "case_001",
                            "gene": "BRCA1",
                            "hgvs_p": "p.Cys61Gly",
                            "feature_payload": {"phylop": 7.2, "gerp": 5.8, "siphy": 12.4, "revel": 0.94},
                        },
                        {
                            "sample_id": "case_002",
                            "gene": "TP53",
                            "hgvs_p": "p.Arg175His",
                        },
                    ],
                },
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["total_variants"], 2)
            self.assertEqual(payload["summary"]["n_success"], 2)
            self.assertEqual(payload["summary"]["n_error"], 0)
            self.assertEqual(len(payload["report"]), 2)
            self.assertIn("csv_report", payload)
            self.assertIn("tier_", payload["report"][0]["priority_tier"])

    def test_api_enqueues_training_job_and_exposes_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"
            output_dir = tmp_path / "job_output"
            job_root = tmp_path / "job_history"

            dataset_schema_template().to_csv(cohort_path, index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "cohort_demo"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app(job_root=str(job_root), profile_root=str(tmp_path / "profiles")))
            profile_response = client.post(
                "/users/profiles",
                json={
                    "profile_id": "analista-brca",
                    "display_name": "Analista BRCA",
                    "role": "clinical_scientist",
                    "institution": "PrimeVarClass Laboratory",
                },
            )
            self.assertEqual(profile_response.status_code, 200)
            headers = {"X-PrimeVarClass-Profile": "analista-brca"}
            enqueue_response = client.post(
                "/jobs/train/source-config",
                headers=headers,
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                    "mode": "hybrid",
                    "keep_metadata": True,
                    "high_confidence_only": False,
                    "model_families": ["logistic_regression"],
                },
            )
            self.assertEqual(enqueue_response.status_code, 200)
            job_payload = enqueue_response.json()
            job_id = job_payload["job_id"]

            deadline = time.time() + 180
            current_status = job_payload["status"]
            detail_payload = job_payload
            while time.time() < deadline and current_status not in {"completed", "failed"}:
                time.sleep(0.5)
                detail_response = client.get(f"/jobs/{job_id}", headers=headers)
                self.assertEqual(detail_response.status_code, 200)
                detail_payload = detail_response.json()
                current_status = detail_payload["status"]

            self.assertEqual(current_status, "completed")
            self.assertTrue(detail_payload["result"]["model_registry_path"])
            self.assertTrue(detail_payload["result"]["data_release_manifest_path"])
            self.assertEqual(detail_payload["submitted_by"]["profile_id"], "analista-brca")

            list_response = client.get("/jobs", headers=headers)
            self.assertEqual(list_response.status_code, 200)
            list_payload = list_response.json()
            self.assertGreaterEqual(list_payload["n_jobs"], 1)
            self.assertTrue(any(job["job_id"] == job_id for job in list_payload["jobs"]))

            report_response = client.get(f"/jobs/{job_id}/report", headers=headers)
            self.assertEqual(report_response.status_code, 200)
            self.assertIn("PrimeVarClass Job Report", report_response.text)
            self.assertIn("Analista BRCA", report_response.text)
            self.assertIn("Data release manifest", report_response.text)

            audit_response = client.get("/audit/events", headers=headers)
            self.assertEqual(audit_response.status_code, 200)
            audit_payload = audit_response.json()
            self.assertGreaterEqual(audit_payload["n_events"], 1)
            self.assertTrue(any(event["event_type"] == "job.created" for event in audit_payload["events"]))

    def test_api_manages_profiles_and_generates_markdown_batch_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_full_training_pipeline_from_dataframe(
                raw_df=dataset_schema_template(),
                mode="hybrid",
                output_dir=tmp_dir,
                keep_metadata=True,
                high_confidence_only=False,
            )
            model_dir = Path(tmp_dir) / "models"
            registry_df = pd.read_csv(results["model_paths"]["registry"])
            experiment = str(registry_df.iloc[0]["experiment"])
            client = TestClient(create_app(profile_root=str(Path(tmp_dir) / "profiles")))

            create_profile = client.post(
                "/users/profiles",
                json={
                    "profile_id": "dra-silva",
                    "display_name": "Dra. Silva",
                    "role": "molecular_geneticist",
                    "institution": "Laboratorio BRCA",
                },
            )
            self.assertEqual(create_profile.status_code, 200)
            headers = {"X-PrimeVarClass-Profile": "dra-silva"}

            context_response = client.get("/users/context", headers=headers)
            self.assertEqual(context_response.status_code, 200)
            self.assertEqual(context_response.json()["active_profile"]["profile_id"], "dra-silva")

            profiles_response = client.get("/users/profiles", headers=headers)
            self.assertEqual(profiles_response.status_code, 200)
            self.assertGreaterEqual(profiles_response.json()["n_profiles"], 1)

            batch_response = client.post(
                "/predict/batch",
                headers=headers,
                json={
                    "model_dir": str(model_dir),
                    "experiment": experiment,
                    "report_title": "Lote Abril BRCA",
                    "report_context": {
                        "laboratory_name": "Laboratorio BRCA",
                    },
                    "variants": [
                        {
                            "sample_id": "case_001",
                            "gene": "BRCA1",
                            "hgvs_p": "p.Cys61Gly",
                            "feature_payload": {"phylop": 7.2, "gerp": 5.8, "siphy": 12.4, "revel": 0.94},
                        }
                    ],
                },
            )
            self.assertEqual(batch_response.status_code, 200)
            batch_payload = batch_response.json()
            self.assertIn("markdown_report", batch_payload)
            self.assertIn("Lote Abril BRCA", batch_payload["markdown_report"])
            self.assertIn("Dra. Silva", batch_payload["markdown_report"])
            self.assertEqual(batch_payload["report_metadata"]["report_context"]["operator_profile_id"], "dra-silva")

    def test_api_manages_teams_and_enforces_membership(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_full_training_pipeline_from_dataframe(
                raw_df=dataset_schema_template(),
                mode="hybrid",
                output_dir=tmp_dir,
                keep_metadata=True,
                high_confidence_only=False,
            )
            model_dir = Path(tmp_dir) / "models"
            registry_df = pd.read_csv(results["model_paths"]["registry"])
            experiment = str(registry_df.iloc[0]["experiment"])
            client = TestClient(
                create_app(
                    profile_root=str(Path(tmp_dir) / "profiles"),
                    team_root=str(Path(tmp_dir) / "teams"),
                )
            )

            owner_response = client.post(
                "/users/profiles",
                json={
                    "profile_id": "lider-brca",
                    "display_name": "Lider BRCA",
                    "role": "principal_investigator",
                    "institution": "Centro BRCA",
                },
            )
            self.assertEqual(owner_response.status_code, 200)
            owner_headers = {"X-PrimeVarClass-Profile": "lider-brca"}

            team_response = client.post(
                "/teams",
                headers=owner_headers,
                json={
                    "team_id": "oncogenomica-brca",
                    "display_name": "Oncogenomica BRCA",
                    "institution": "Centro BRCA",
                    "description": "Equipe de pesquisa translacional",
                },
            )
            self.assertEqual(team_response.status_code, 200)
            self.assertEqual(team_response.json()["team"]["team_id"], "oncogenomica-brca")

            team_headers = {
                "X-PrimeVarClass-Profile": "lider-brca",
                "X-PrimeVarClass-Team": "oncogenomica-brca",
            }
            context_response = client.get("/teams/context", headers=team_headers)
            self.assertEqual(context_response.status_code, 200)
            self.assertEqual(context_response.json()["active_team"]["member_role"], "owner")

            batch_response = client.post(
                "/predict/batch",
                headers=team_headers,
                json={
                    "model_dir": str(model_dir),
                    "experiment": experiment,
                    "report_title": "Lote Governanca",
                    "variants": [
                        {
                            "sample_id": "case_001",
                            "gene": "BRCA1",
                            "hgvs_p": "p.Cys61Gly",
                            "feature_payload": {"phylop": 7.2, "gerp": 5.8, "siphy": 12.4, "revel": 0.94},
                        }
                    ],
                },
            )
            self.assertEqual(batch_response.status_code, 200)
            batch_payload = batch_response.json()
            self.assertIn("Oncogenomica BRCA", batch_payload["markdown_report"])
            self.assertEqual(batch_payload["report_metadata"]["report_context"]["team_id"], "oncogenomica-brca")

            visitor_response = client.post(
                "/users/profiles",
                json={
                    "profile_id": "visitante",
                    "display_name": "Visitante",
                    "role": "observer",
                    "institution": "Centro BRCA",
                },
            )
            self.assertEqual(visitor_response.status_code, 200)
            visitor_headers = {
                "X-PrimeVarClass-Profile": "visitante",
                "X-PrimeVarClass-Team": "oncogenomica-brca",
            }
            forbidden = client.get("/teams/context", headers=visitor_headers)
            self.assertEqual(forbidden.status_code, 403)

    def test_api_builds_team_dashboard_from_jobs_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TestClient(
                create_app(
                    job_root=str(Path(tmp_dir) / "jobs"),
                    audit_root=str(Path(tmp_dir) / "audit"),
                    profile_root=str(Path(tmp_dir) / "profiles"),
                    team_root=str(Path(tmp_dir) / "teams"),
                )
            )
            client.post(
                "/users/profiles",
                json={
                    "profile_id": "gestor-time",
                    "display_name": "Gestor Time",
                    "role": "lab_manager",
                    "institution": "Centro BRCA",
                },
            )
            owner_headers = {"X-PrimeVarClass-Profile": "gestor-time"}
            client.post(
                "/teams",
                headers=owner_headers,
                json={
                    "team_id": "painel-brca",
                    "display_name": "Painel BRCA",
                    "institution": "Centro BRCA",
                    "description": "Time de operacao",
                },
            )

            app = client.app
            app.state.job_manager.create_job(
                job_type="study_run",
                payload={"config_path": "study.toml"},
                submitted_by={"profile_id": "gestor-time", "display_name": "Gestor Time", "role": "lab_manager"},
                submitted_for_team={"team_id": "painel-brca", "display_name": "Painel BRCA", "member_role": "owner"},
            )
            app.state.audit_logger.log_event(
                event_type="study.compared",
                status="ok",
                actor="Gestor Time<lab_manager>@127.0.0.1:POST",
                request_path="/study/compare",
                metadata={"team_id": "painel-brca", "team_name": "Painel BRCA"},
            )

            headers = {
                "X-PrimeVarClass-Profile": "gestor-time",
                "X-PrimeVarClass-Team": "painel-brca",
            }
            response = client.get("/analytics/team-dashboard", headers=headers)
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["total_jobs"], 1)
            self.assertGreaterEqual(payload["summary"]["audit_events"], 1)
            self.assertIn("Painel BRCA", payload["markdown_report"])

    def test_api_compares_study_exports_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            baseline_dir = tmp_path / "baseline"
            candidate_dir = tmp_path / "candidate"
            output_dir = tmp_path / "comparison"
            baseline_dir.mkdir()
            candidate_dir.mkdir()

            pd.DataFrame(
                [
                    {
                        "experiment": "baseline_model",
                        "feature_set": "hybrid",
                        "model_family": "random_forest",
                        "auc_roc": 0.81,
                        "auc_pr": 0.78,
                        "mcc": 0.42,
                        "is_primary_experiment": 1,
                    }
                ]
            ).to_csv(baseline_dir / "study_training_metrics.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "cohort": "external_a",
                        "evaluation_group": "combined",
                        "experiment": "baseline_model",
                        "feature_set": "hybrid",
                        "model_family": "random_forest",
                        "auc_roc": 0.79,
                        "auc_pr": 0.75,
                        "mcc": 0.38,
                    }
                ]
            ).to_csv(baseline_dir / "study_external_evaluation.csv", index=False)
            (baseline_dir / "study_summary_report.txt").write_text("baseline summary", encoding="utf-8")

            pd.DataFrame(
                [
                    {
                        "experiment": "candidate_model",
                        "feature_set": "hybrid_plus_external",
                        "model_family": "extra_trees",
                        "auc_roc": 0.89,
                        "auc_pr": 0.84,
                        "mcc": 0.56,
                        "is_primary_experiment": 1,
                    }
                ]
            ).to_csv(candidate_dir / "study_training_metrics.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "cohort": "external_a",
                        "evaluation_group": "combined",
                        "experiment": "candidate_model",
                        "feature_set": "hybrid_plus_external",
                        "model_family": "extra_trees",
                        "auc_roc": 0.86,
                        "auc_pr": 0.82,
                        "mcc": 0.50,
                    }
                ]
            ).to_csv(candidate_dir / "study_external_evaluation.csv", index=False)
            (candidate_dir / "study_summary_report.txt").write_text("candidate summary", encoding="utf-8")

            client = TestClient(
                create_app(
                    profile_root=str(tmp_path / "profiles"),
                    team_root=str(tmp_path / "teams"),
                    audit_root=str(tmp_path / "audit"),
                )
            )
            client.post(
                "/users/profiles",
                json={
                    "profile_id": "comparador",
                    "display_name": "Comparador",
                    "role": "scientific_analyst",
                    "institution": "Centro BRCA",
                },
            )
            owner_headers = {"X-PrimeVarClass-Profile": "comparador"}
            client.post(
                "/teams",
                headers=owner_headers,
                json={
                    "team_id": "comparacao-brca",
                    "display_name": "Comparacao BRCA",
                    "institution": "Centro BRCA",
                },
            )

            headers = {
                "X-PrimeVarClass-Profile": "comparador",
                "X-PrimeVarClass-Team": "comparacao-brca",
            }
            response = client.post(
                "/study/compare",
                headers=headers,
                json={
                    "baseline_dir": str(baseline_dir),
                    "candidate_dir": str(candidate_dir),
                    "output_dir": str(output_dir),
                    "report_title": "Comparativo BRCA",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["report_title"], "Comparativo BRCA")
            self.assertGreater(payload["internal_delta"]["primary_metric_delta"], 0)
            self.assertTrue(Path(payload["export_paths"]["comparison_markdown_path"]).exists())
            self.assertTrue(Path(payload["export_paths"]["comparison_html_path"]).exists())
            self.assertIn("Comparativo BRCA", payload["markdown_report"])

    def test_api_generates_longitudinal_monitor_for_studies(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            study_a = tmp_path / "study_a"
            study_b = tmp_path / "study_b"
            output_dir = tmp_path / "longitudinal"
            study_a.mkdir()
            study_b.mkdir()

            manifest_a = {
                "release_id": "study_alpha_20260101",
                "generated_at": "2026-01-01T10:00:00Z",
                "study_name": "Study Alpha",
                "primary_metric": "auc_roc",
                "top_internal_experiment": "model_alpha",
                "internal_primary_metric": 0.81,
                "internal_auc_roc": 0.81,
                "internal_auc_pr": 0.78,
                "internal_mcc": 0.42,
                "top_external_experiment": "model_alpha",
                "mean_external_primary_metric": 0.77,
                "mean_external_auc_roc": 0.77,
                "mean_external_auc_pr": 0.74,
                "mean_external_mcc": 0.33,
            }
            manifest_b = {
                "release_id": "study_beta_20260201",
                "generated_at": "2026-02-01T10:00:00Z",
                "study_name": "Study Beta",
                "primary_metric": "auc_roc",
                "top_internal_experiment": "model_beta",
                "internal_primary_metric": 0.88,
                "internal_auc_roc": 0.88,
                "internal_auc_pr": 0.84,
                "internal_mcc": 0.55,
                "top_external_experiment": "model_beta",
                "mean_external_primary_metric": 0.83,
                "mean_external_auc_roc": 0.83,
                "mean_external_auc_pr": 0.80,
                "mean_external_mcc": 0.47,
            }
            (study_a / "study_release_manifest.json").write_text(json.dumps(manifest_a), encoding="utf-8")
            (study_b / "study_release_manifest.json").write_text(json.dumps(manifest_b), encoding="utf-8")

            client = TestClient(
                create_app(
                    profile_root=str(tmp_path / "profiles"),
                    team_root=str(tmp_path / "teams"),
                    audit_root=str(tmp_path / "audit"),
                )
            )
            client.post(
                "/users/profiles",
                json={
                    "profile_id": "monitor",
                    "display_name": "Monitor",
                    "role": "scientific_analyst",
                    "institution": "Centro BRCA",
                },
            )
            owner_headers = {"X-PrimeVarClass-Profile": "monitor"}
            client.post(
                "/teams",
                headers=owner_headers,
                json={
                    "team_id": "monitoramento-brca",
                    "display_name": "Monitoramento BRCA",
                    "institution": "Centro BRCA",
                },
            )
            headers = {
                "X-PrimeVarClass-Profile": "monitor",
                "X-PrimeVarClass-Team": "monitoramento-brca",
            }
            response = client.post(
                "/monitoring/studies/longitudinal",
                headers=headers,
                json={
                    "study_dirs": [str(study_a), str(study_b)],
                    "output_dir": str(output_dir),
                    "report_title": "Timeline BRCA",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["report_title"], "Timeline BRCA")
            self.assertEqual(payload["summary"]["n_versions"], 2)
            self.assertGreater(payload["summary"]["delta_internal_vs_previous"], 0)
            self.assertTrue(Path(payload["export_paths"]["timeline_path"]).exists())
            self.assertTrue(Path(payload["export_paths"]["longitudinal_markdown_path"]).exists())

    def test_api_loads_release_manifest_for_inspection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            config_path = tmp_path / "sources.toml"
            output_dir = tmp_path / "ingestion_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "cohort_demo"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar"',
                    ]
                ),
                encoding="utf-8",
            )

            ingestion = ingest_sources_from_config(str(config_path), output_dir=str(output_dir))
            manifest_path = ingestion["output_paths"]["data_release_manifest_path"]

            client = TestClient(create_app())
            response = client.post("/releases/manifest/load", json={"manifest_path": manifest_path})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["release_type"], "data_ingestion")
            self.assertEqual(payload["summary"]["n_sources"], 1)
            self.assertIn("file", payload["summary"]["source_types"])
            self.assertIn("integrated_dataset_fingerprint", payload["manifest"])
            self.assertTrue(payload["manifest"]["sources"][0]["provenance"]["file_fingerprint"]["sha256"])

    def test_api_inspects_public_source_catalog(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            gnomad_path = tmp_path / "gnomad_brca_v4.1.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "inspection_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/catalog/inspect",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["summary"]["n_recognized_public_sources"], 2)
            self.assertGreater(payload["summary"]["release_coverage_percent"], 0)
            self.assertGreaterEqual(payload["summary"]["schema_coverage_percent"], 80)
            self.assertTrue(Path(payload["output_paths"]["public_source_catalog_report_json"]).exists())
            self.assertTrue(Path(payload["output_paths"]["public_source_sync_plan_json"]).exists())
            self.assertIn("ClinVar", payload["markdown_report"])
            self.assertIn("sync_plan", payload)
            self.assertGreaterEqual(payload["sync_plan"]["summary"]["n_sync_candidates"], 2)

    def test_api_builds_continuous_learning_bundle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            gnomad_path = tmp_path / "gnomad_brca_v4.1.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "continuous_learning_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "v4.1"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/continuous-learning/build",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertGreaterEqual(payload["summary"]["configured_public_source_count"], 2)
            self.assertTrue(Path(payload["continuous_learning_manifest_path"]).exists())
            self.assertTrue(Path(payload["continuous_learning_runner_path"]).exists())
            self.assertTrue(Path(payload["continuous_learning_connector_catalog_path"]).exists())

    def test_api_generates_public_source_bootstrap_bundle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/catalog/bootstrap",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            bundle = payload["bundle"]
            self.assertEqual(bundle["summary"]["n_bundle_items"], 1)
            self.assertTrue(Path(bundle["manifest_path"]).exists())
            self.assertTrue(Path(bundle["guide_markdown_path"]).exists())
            self.assertTrue(Path(bundle["powershell_script_path"]).exists())
            script_text = Path(bundle["powershell_script_path"]).read_text(encoding="utf-8")
            self.assertIn("Invoke-WebRequest", script_text)
            self.assertIn("variant_summary.txt.gz", script_text)

    def test_api_generates_public_source_bootstrap_bundle_for_mavedb_urn(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            mavedb_path = tmp_path / "mavedb_scores.csv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_pro": "p.Cys61Gly", "score": -1.8, "urn": "urn:mavedb:BRCA1-RING-2026"},
                    {"gene": "BRCA2", "hgvs_pro": "p.Gly2508Ser", "score": -1.1, "urn": "urn:mavedb:BRCA2-DBD-2026"},
                ]
            ).to_csv(mavedb_path, index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                        "",
                        "[[sources]]",
                        'name = "mavedb_scores"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{mavedb_path.as_posix()}"',
                        'preset = "mavedb_score_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "urn:mavedb:BRCA1-RING-2026"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/catalog/bootstrap",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            bundle = payload["bundle"]
            self.assertEqual(bundle["summary"]["n_bundle_items"], 2)
            self.assertEqual(bundle["summary"]["n_script_executable_items"], 2)

            mavedb_item = next(item for item in bundle["bundle_items"] if item["profile_id"] == "mavedb")
            self.assertTrue(mavedb_item["can_execute_from_script"])
            self.assertEqual(mavedb_item["resolved_mavedb_urn"], "urn:mavedb:BRCA1-RING-2026")
            self.assertEqual(len(mavedb_item["expected_artifact_paths"]), 2)
            self.assertTrue(any("api.mavedb.org/api/v1/score-sets/" in step["url"] for step in mavedb_item["execution_plan"] if step["step_type"] == "download"))
            self.assertTrue(any("mapped-variants" in step["url"] for step in mavedb_item["execution_plan"] if step["step_type"] == "download"))

            script_text = Path(bundle["powershell_script_path"]).read_text(encoding="utf-8")
            self.assertIn("api.mavedb.org/api/v1/score-sets", script_text)
            self.assertIn("mapped_variants.json", script_text)

    def test_api_generates_public_source_bootstrap_bundle_for_gnomad_local_subset(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            gnomad_path = tmp_path / "gnomad_release.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                    {"gene": "TP53", "hgvs_p": "p.Arg175His", "af": 0.00012},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "local_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "v4.1"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/catalog/bootstrap",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            bundle = payload["bundle"]
            self.assertEqual(bundle["summary"]["n_bundle_items"], 1)
            self.assertEqual(bundle["summary"]["n_script_executable_items"], 1)

            gnomad_item = bundle["bundle_items"][0]
            self.assertEqual(gnomad_item["profile_id"], "gnomad")
            self.assertTrue(gnomad_item["can_execute_from_script"])
            self.assertTrue(gnomad_item["local_source_exists"])
            self.assertEqual(gnomad_item["source_format"], "tsv")
            self.assertEqual(len(gnomad_item["expected_artifact_paths"]), 2)
            self.assertTrue(any(step["step_type"] == "filter_variant_table" for step in gnomad_item["execution_plan"]))

            script_text = Path(bundle["powershell_script_path"]).read_text(encoding="utf-8")
            self.assertIn("gnomad_brca_subset.tsv", script_text)
            self.assertIn("filter local table", script_text)

    def test_api_executes_public_source_bootstrap_for_gnomad_local_subset(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            gnomad_path = tmp_path / "gnomad_release.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "hgvs_p": "p.Cys61Gly", "af": 0.000002},
                    {"gene": "BRCA2", "hgvs_p": "p.Gly2508Ser", "af": 0.000004},
                    {"gene": "TP53", "hgvs_p": "p.Arg175His", "af": 0.00012},
                ]
            ).to_csv(gnomad_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "local_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                        "",
                        "[[sources]]",
                        'name = "gnomad_annotations"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{gnomad_path.as_posix()}"',
                        'preset = "gnomad_variant_table"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_version = "v4.1"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            execute_response = client.post(
                "/public-sources/catalog/bootstrap/execute",
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                    "dry_run": False,
                    "selected_sources": ["gnomad_annotations"],
                },
            )
            self.assertEqual(execute_response.status_code, 200)
            execute_payload = execute_response.json()
            execution = execute_payload["execution"]
            self.assertEqual(execution["summary"]["n_completed_items"], 1)
            self.assertEqual(execution["summary"]["n_failed_items"], 0)

            gnomad_item = next(item for item in execution["execution_items"] if item["profile_id"] == "gnomad")
            self.assertEqual(gnomad_item["execution_status"], "completed")
            subset_path = Path(gnomad_item["artifact_state_after"]["expected_artifacts"][0]["path"])
            manifest_path = Path(gnomad_item["artifact_state_after"]["expected_artifacts"][1]["path"])
            self.assertTrue(subset_path.exists())
            self.assertTrue(manifest_path.exists())
            subset_df = pd.read_csv(subset_path, sep="\t")
            self.assertEqual(set(subset_df["gene"]), {"BRCA1", "BRCA2"})
            self.assertEqual(len(subset_df), 2)
            filter_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(filter_manifest["rows_input"], 3)
            self.assertEqual(filter_manifest["rows_output"], 2)

            history = execution["sync_history"]
            gnomad_status = next(item for item in history["source_statuses"] if item["profile_id"] == "gnomad")
            self.assertEqual(gnomad_status["latest_execution_status"], "completed")
            self.assertGreaterEqual(history["summary"]["sync_readiness_percent"], 80)

    def test_api_generates_public_source_bootstrap_bundle_for_enigma_curated_import(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            enigma_path = tmp_path / "enigma_curated.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            pd.DataFrame(
                [
                    {"gene": "BRCA1", "protein_change": "p.Cys61Gly", "classification": "Pathogenic"},
                    {"gene": "BRCA2", "protein_change": "p.Gly2508Ser", "classification": "Likely pathogenic"},
                ]
            ).to_csv(enigma_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "local_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                        "",
                        "[[sources]]",
                        'name = "enigma_labels"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{enigma_path.as_posix()}"',
                        'preset = "enigma_brca"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_date = "2026-02-20"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            response = client.post(
                "/public-sources/catalog/bootstrap",
                json={"config_path": str(config_path), "output_dir": str(output_dir)},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            bundle = payload["bundle"]
            self.assertEqual(bundle["summary"]["n_bundle_items"], 1)
            self.assertEqual(bundle["summary"]["n_script_executable_items"], 1)

            enigma_item = bundle["bundle_items"][0]
            self.assertEqual(enigma_item["profile_id"], "enigma")
            self.assertTrue(enigma_item["can_execute_from_script"])
            self.assertTrue(enigma_item["local_source_exists"])
            self.assertEqual(len(enigma_item["expected_artifact_paths"]), 2)
            self.assertTrue(any(step["step_type"] == "stage_local_file" for step in enigma_item["execution_plan"]))

            script_text = Path(bundle["powershell_script_path"]).read_text(encoding="utf-8")
            self.assertIn("stage curated local file", script_text)
            self.assertIn("enigma_curated_import.tsv", script_text)

    def test_api_executes_public_source_bootstrap_for_enigma_curated_import(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "cohort.csv"
            enigma_path = tmp_path / "enigma_curated.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, index=False)
            curated_df = pd.DataFrame(
                [
                    {"gene": "BRCA1", "protein_change": "p.Cys61Gly", "classification": "Pathogenic"},
                    {"gene": "BRCA2", "protein_change": "p.Gly2508Ser", "classification": "Likely pathogenic"},
                ]
            )
            curated_df.to_csv(enigma_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "local_training_cohort"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "csv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "none"',
                        "",
                        "[[sources]]",
                        'name = "enigma_labels"',
                        'kind = "annotation"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{enigma_path.as_posix()}"',
                        'preset = "enigma_brca"',
                        'join_on = ["gene", "hgvs_p"]',
                        'release_date = "2026-02-20"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            execute_response = client.post(
                "/public-sources/catalog/bootstrap/execute",
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                    "dry_run": False,
                    "selected_sources": ["enigma_labels"],
                },
            )
            self.assertEqual(execute_response.status_code, 200)
            execute_payload = execute_response.json()
            execution = execute_payload["execution"]
            self.assertEqual(execution["summary"]["n_completed_items"], 1)
            self.assertEqual(execution["summary"]["n_failed_items"], 0)

            enigma_item = next(item for item in execution["execution_items"] if item["profile_id"] == "enigma")
            self.assertEqual(enigma_item["execution_status"], "completed")
            staged_path = Path(enigma_item["artifact_state_after"]["expected_artifacts"][0]["path"])
            manifest_path = Path(enigma_item["artifact_state_after"]["expected_artifacts"][1]["path"])
            self.assertTrue(staged_path.exists())
            self.assertTrue(manifest_path.exists())
            staged_df = pd.read_csv(staged_path, sep="\t")
            self.assertEqual(len(staged_df), 2)
            self.assertEqual(set(staged_df["gene"]), {"BRCA1", "BRCA2"})
            stage_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(stage_manifest["staging_mode"], "curated_local_import")
            self.assertTrue(stage_manifest["output_path"].endswith("enigma_curated_import.tsv"))

            history = execution["sync_history"]
            enigma_status = next(item for item in history["source_statuses"] if item["profile_id"] == "enigma")
            self.assertEqual(enigma_status["latest_execution_status"], "completed")
            self.assertGreaterEqual(history["summary"]["sync_readiness_percent"], 80)

    def test_api_executes_public_source_bootstrap_dry_run_and_loads_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cohort_path = tmp_path / "clinvar_variant_summary_2026-03-01.tsv"
            config_path = tmp_path / "public_sources.toml"
            output_dir = tmp_path / "bootstrap_output"

            dataset_schema_template().to_csv(cohort_path, sep="\t", index=False)
            config_path.write_text(
                "\n".join(
                    [
                        "[[sources]]",
                        'name = "clinvar_main"',
                        'kind = "cohort"',
                        'type = "file"',
                        'format = "tsv"',
                        f'path = "{cohort_path.as_posix()}"',
                        'preset = "clinvar_variant_summary"',
                    ]
                ),
                encoding="utf-8",
            )

            client = TestClient(create_app())
            execute_response = client.post(
                "/public-sources/catalog/bootstrap/execute",
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                    "dry_run": True,
                },
            )
            self.assertEqual(execute_response.status_code, 200)
            execute_payload = execute_response.json()
            execution = execute_payload["execution"]
            self.assertEqual(execution["summary"]["n_items"], 1)
            self.assertEqual(execution["summary"]["n_dry_run_items"], 1)
            self.assertTrue(Path(execution["run_manifest_path"]).exists())
            self.assertTrue(Path(execution["sync_registry_path"]).exists())
            self.assertEqual(execution["sync_history"]["summary"]["n_runs"], 1)
            self.assertEqual(execution["sync_history"]["source_statuses"][0]["latest_execution_status"], "dry_run")
            self.assertGreater(execution["benchmark_readiness"]["summary"]["sync_readiness_percent"], 0)

            history_response = client.get(
                "/public-sources/catalog/bootstrap/history",
                params={
                    "output_dir": str(output_dir),
                    "config_path": str(config_path),
                },
            )
            self.assertEqual(history_response.status_code, 200)
            history_payload = history_response.json()
            self.assertEqual(history_payload["history"]["summary"]["n_runs"], 1)
            self.assertEqual(history_payload["history"]["source_statuses"][0]["latest_execution_status"], "dry_run")

            inspect_response = client.post(
                "/public-sources/catalog/inspect",
                json={
                    "config_path": str(config_path),
                    "output_dir": str(output_dir),
                },
            )
            self.assertEqual(inspect_response.status_code, 200)
            inspect_payload = inspect_response.json()
            self.assertEqual(inspect_payload["sync_history"]["summary"]["n_runs"], 1)
            self.assertGreater(inspect_payload["benchmark_readiness"]["summary"]["benchmark_readiness_percent"], 0)

    def test_api_requires_key_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            results = run_full_training_pipeline_from_dataframe(
                raw_df=dataset_schema_template(),
                mode="hybrid",
                output_dir=tmp_dir,
                keep_metadata=True,
                high_confidence_only=False,
            )
            model_dir = Path(tmp_dir) / "models"
            client = TestClient(create_app(api_key="laboratorio-seguro"))

            unauthorized = client.get("/models", params={"model_dir": str(model_dir)})
            self.assertEqual(unauthorized.status_code, 401)

            authorized = client.get(
                "/models",
                params={"model_dir": str(model_dir)},
                headers={"X-API-Key": "laboratorio-seguro"},
            )
            self.assertEqual(authorized.status_code, 200)
            self.assertGreaterEqual(authorized.json()["n_models"], 1)

            auth_status = client.get("/auth/status")
            self.assertEqual(auth_status.status_code, 200)
            self.assertTrue(auth_status.json()["auth_enabled"])


if __name__ == "__main__":
    unittest.main()
