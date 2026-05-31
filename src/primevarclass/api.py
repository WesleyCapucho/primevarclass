from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field

from .analytics import build_team_dashboard
from .audit import PrimeVarClassAuditLogger
from .biological_discovery import export_biological_discovery_package
from .candidate_public_runner import run_candidate_public_benchmark_pipeline
from .continuous_learning import export_continuous_learning_package
from .data_sources import ingest_sources_from_config, train_from_source_config
from .development_progress import export_development_progress_dashboard
from .deployment import load_model_registry, score_variant_batch_with_model, score_variant_with_model
from .gene_expansion import export_gene_expansion_assessment
from .gnomad_gene_subset import DEFAULT_TARGET_GENES, export_gnomad_gene_subset
from .handoff_autofill import export_real_data_handoff_autofill
from .independent_data_expansion import DEFAULT_EXPANSION_GENES, export_independent_data_expansion_package
from .independent_data_staging_closure import export_independent_data_staging_closure_package
from .independent_public_autostager import export_independent_open_source_autostage_package
from .jobs import PrimeVarClassJobManager
from .launch_readiness import build_launch_readiness_assessment, export_launch_readiness_package
from .public_config_resolver import export_public_source_resolution, export_study_public_config_resolution
from .public_bootstrap import (
    build_public_source_bootstrap_bundle,
    execute_public_source_bootstrap_bundle,
    load_public_source_sync_history,
)
from .monitoring import build_longitudinal_study_monitor, export_longitudinal_study_monitor
from .brca1_engine_execution import export_brca1_engine_execution_package
from .brca1_fragment_preparation import export_brca1_fragment_preparation_package
from .brca1_paired_mutant_execution import export_brca1_paired_mutant_execution_package
from .brca1_mutant_geometry_qc import export_brca1_mutant_geometry_qc_package
from .multigene_annotation_enrichment import export_multigene_annotation_enrichment_package
from .multigene_rollout import export_multigene_rollout_plan
from .multigene_study_factory import export_multigene_study_factory
from .protein_impact import export_protein_impact_package
from .prospective_validation_closure import export_prospective_validation_closure_package
from .public_sync_closure import export_public_sync_closure_package
from .quantum_proteomics import export_quantum_proteomics_package
from .profiles import PrimeVarClassProfileStore
from .public_study_runner import run_public_benchmark_pipeline
from .roadmap import build_roadmap_progress
from .security import mask_api_key, resolve_security_settings, verify_api_key
from .study_compare import build_study_comparison, export_study_comparison
from .study import run_publication_study
from .study_bundle_inspector import inspect_study_bundle
from .study_preflight import export_study_preflight
from .teams import PrimeVarClassTeamStore
from .translational_impact import PrimeVarClassPilotOpsStore, build_translational_impact_dashboard
from .validation_credibility_closure import export_validation_credibility_closure
from .versioning import load_release_manifest


class VariantPredictionRequest(BaseModel):
    model_dir: str
    experiment: str
    gene: str
    hgvs_p: str
    mode: str | None = None
    threshold: float = 0.5
    feature_payload: Dict[str, Any] = Field(default_factory=dict)
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)


class BatchVariantItem(BaseModel):
    sample_id: str | None = None
    gene: str
    hgvs_p: str
    mode: str | None = None
    feature_payload: Dict[str, Any] = Field(default_factory=dict)
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)


class BatchVariantPredictionRequest(BaseModel):
    model_dir: str
    experiment: str
    threshold: float = 0.5
    default_mode: str | None = None
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)
    variants: List[BatchVariantItem]


class SourceTrainingRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_api_training_results"
    mode: str = "hybrid"
    keep_metadata: bool = True
    high_confidence_only: bool = False
    model_families: List[str] | None = None


class StudyRunRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_api_study_results"
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class StudyPublicRunRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_api_public_study_results"
    bootstrap_root_dir: str | None = None
    delivery_dir: str | None = None
    require_live_public_ready: bool = False
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class CandidatePublicRunRequest(BaseModel):
    candidate_config_path: str
    output_dir: str = "primevarclass_api_candidate_public_study_results"
    candidate_promotion_manifest_path: str | None = None
    require_candidate_ready: bool = True
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class StudyPreflightRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_api_study_preflight"
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class StudyBundleInspectRequest(BaseModel):
    result_dir: str


class LaunchReadinessExportRequest(BaseModel):
    output_dir: str = "primevarclass_launch_readiness_results"
    workspace_root: str | None = None
    include_absolute_paths: bool = True
    report_context: Dict[str, Any] = Field(default_factory=dict)


class IndependentDataExpansionRequest(BaseModel):
    output_dir: str = "primevarclass_independent_data_expansion_results"
    target_genes: List[str] = Field(default_factory=lambda: list(DEFAULT_EXPANSION_GENES))
    include_restricted_sources: bool = False
    report_context: Dict[str, Any] = Field(default_factory=dict)


class IndependentDataStagingClosureRequest(BaseModel):
    output_dir: str = "primevarclass_independent_data_staging_closure_results"
    independent_data_expansion_manifest_path: str | None = None
    workspace_root: str | None = None
    target_genes: List[str] = Field(default_factory=lambda: list(DEFAULT_EXPANSION_GENES))
    report_context: Dict[str, Any] = Field(default_factory=dict)


class IndependentOpenSourceAutostageRequest(BaseModel):
    output_dir: str = "primevarclass_independent_open_source_autostage_results"
    workspace_root: str | None = None
    target_genes: List[str] = Field(default_factory=lambda: list(DEFAULT_EXPANSION_GENES))
    refresh: bool = False
    timeout_sec: int = 20
    max_gwas_per_gene: int = 8
    max_pdb_per_gene: int = 8
    report_context: Dict[str, Any] = Field(default_factory=dict)


class GeneExpansionRequest(BaseModel):
    clinvar_variant_summary_path: str
    mavedb_dump_path: str
    output_dir: str = "primevarclass_gene_expansion_results"
    exclude_genes: List[str] | None = None
    top_k: int = 12


class BiologicalDiscoveryRequest(BaseModel):
    real_data_manifest_path: str
    output_dir: str = "primevarclass_biological_discovery_results"


class MultigeneRolloutRequest(BaseModel):
    gene_expansion_manifest_path: str
    prime_intelligence_manifest_path: str | None = None
    output_dir: str = "primevarclass_multigene_rollout_results"
    max_phase_1: int = 3
    max_phase_2: int = 4
    max_total_genes: int = 10


class MultigeneStudyFactoryRequest(BaseModel):
    rollout_manifest_path: str
    output_dir: str = "primevarclass_multigene_study_factory_results"
    workspace_root: str | None = None
    include_phases: List[str] | None = None


class MultigeneAnnotationEnrichmentRequest(BaseModel):
    multigene_real_benchmark_manifest_path: str
    output_dir: str = "primevarclass_multigene_annotation_enrichment_results"
    variant_summary_path: str | None = None
    multigene_root: str | None = None
    gnomad_dir: str = "data/raw/gnomad"
    mavedb_dir: str = "data/raw/mavedb"
    target_genes: List[str] | None = None
    run_live_gnomad: bool = False
    max_live_gnomad_queries: int = 48
    max_live_gnomad_queries_per_gene: int = 8
    run_live_mavedb: bool = True
    max_live_mavedb_score_sets_per_gene: int = 1
    timeout_sec: int = 20


class PublicSyncClosureRequest(BaseModel):
    multigene_annotation_enrichment_manifest_path: str
    output_dir: str = "primevarclass_public_sync_closure_results"
    existing_gnomad_cache_path: str | None = None
    gnomad_release_table_path: str | None = None
    gnomad_batch_size: int = 25
    gnomad_sleep_seconds: int = 6


class GnomadGeneSubsetRequest(BaseModel):
    output_dir: str = "primevarclass_gnomad_gene_subset_results"
    target_genes: List[str] = Field(default_factory=lambda: list(DEFAULT_TARGET_GENES))
    dataset: str = "gnomad_r4"
    timeout_sec: int = 120
    max_retries: int = 2
    sleep_seconds: float = 1.0


class Brca1EngineExecutionRequest(BaseModel):
    brca1_structural_campaign_manifest_path: str
    output_dir: str = "primevarclass_brca1_engine_execution_results"
    uniprot_id: str = "P38398"
    timeout_sec: int = 20
    execute_if_available: bool = False
    max_execute: int = 3


class Brca1FragmentPreparationRequest(BaseModel):
    brca1_engine_execution_manifest_path: str
    output_dir: str = "primevarclass_brca1_fragment_preparation_results"
    radius_angstrom: float = 5.0
    max_atoms: int = 90
    execute_xtb: bool = False
    max_xtb_runs: int = 2
    xtb_timeout_sec: int = 240


class Brca1PairedMutantExecutionRequest(BaseModel):
    brca1_fragment_preparation_manifest_path: str
    output_dir: str = "primevarclass_brca1_paired_mutant_execution_results"
    execute_xtb: bool = False
    max_pairs: int = 3
    xtb_timeout_sec: int = 240


class Brca1MutantGeometryQcRequest(BaseModel):
    brca1_paired_mutant_execution_manifest_path: str
    output_dir: str = "primevarclass_brca1_mutant_geometry_qc_results"
    execute_xtb_opt: bool = False
    max_opt_pairs: int = 2
    xtb_timeout_sec: int = 360


class ProspectiveValidationClosureRequest(BaseModel):
    multigene_annotation_enrichment_manifest_path: str
    brca1_engine_execution_manifest_path: str
    output_dir: str = "primevarclass_prospective_validation_closure_results"
    validation_credibility_closure_manifest_path: str | None = None
    public_sync_closure_manifest_path: str | None = None
    brca1_paired_mutant_execution_manifest_path: str | None = None
    brca1_mutant_geometry_qc_manifest_path: str | None = None
    max_queue_rows: int = 12


class ProteinImpactRequest(BaseModel):
    biological_discovery_manifest_path: str
    output_dir: str = "primevarclass_protein_impact_results"
    max_modeling_variants: int = 25


class QuantumProteomicsRequest(BaseModel):
    protein_impact_manifest_path: str
    output_dir: str = "primevarclass_quantum_proteomics_results"
    max_quantum_targets: int = 12


class ValidationCredibilityClosureRequest(BaseModel):
    output_dir: str = "primevarclass_validation_credibility_closure_results"
    prime_intelligence_manifest_path: str | None = None
    biological_discovery_manifest_path: str | None = None
    protein_impact_manifest_path: str | None = None
    quantum_proteomics_manifest_path: str | None = None
    multigene_rollout_manifest_path: str | None = None
    brca1_engine_execution_manifest_path: str | None = None
    multigene_real_benchmark_manifest_path: str | None = None
    multigene_annotation_enrichment_manifest_path: str | None = None
    public_sync_closure_manifest_path: str | None = None
    prospective_validation_closure_manifest_path: str | None = None
    brca1_fragment_preparation_manifest_path: str | None = None
    brca1_paired_mutant_execution_manifest_path: str | None = None
    brca1_mutant_geometry_qc_manifest_path: str | None = None
    claim_strength_manifest_path: str | None = None


class DevelopmentProgressRequest(BaseModel):
    output_dir: str = "primevarclass_development_progress_results"
    prime_intelligence_manifest_path: str | None = None
    biological_discovery_manifest_path: str | None = None
    protein_impact_manifest_path: str | None = None
    quantum_proteomics_manifest_path: str | None = None
    quantum_vqe_benchmark_manifest_path: str | None = None
    brca1_structural_campaign_manifest_path: str | None = None
    brca1_engine_execution_manifest_path: str | None = None
    brca1_fragment_preparation_manifest_path: str | None = None
    brca1_paired_mutant_execution_manifest_path: str | None = None
    brca1_mutant_geometry_qc_manifest_path: str | None = None
    multigene_real_benchmark_manifest_path: str | None = None
    multigene_annotation_enrichment_manifest_path: str | None = None
    public_sync_closure_manifest_path: str | None = None
    continuous_learning_manifest_path: str | None = None
    validation_credibility_closure_manifest_path: str | None = None
    prospective_validation_closure_manifest_path: str | None = None


class UserProfileRequest(BaseModel):
    profile_id: str | None = None
    display_name: str
    role: str = "researcher"
    institution: str | None = None
    email: str | None = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)


class TeamRequest(BaseModel):
    team_id: str | None = None
    display_name: str
    institution: str | None = None
    description: str | None = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)
    owner_role: str = "owner"


class TeamMembershipRequest(BaseModel):
    profile_id: str
    team_role: str = "member"


class StudyComparisonRequest(BaseModel):
    baseline_dir: str
    candidate_dir: str
    output_dir: str = "primevarclass_study_comparison_results"
    primary_metric: str = "auc_roc"
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class LongitudinalMonitoringRequest(BaseModel):
    study_dirs: List[str]
    output_dir: str = "primevarclass_longitudinal_results"
    primary_metric: str = "auc_roc"
    report_title: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class ReleaseManifestRequest(BaseModel):
    manifest_path: str


class PublicSourceCatalogRequest(BaseModel):
    config_path: str
    output_dir: str | None = None


class PublicSourceBootstrapRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_public_source_bootstrap"


class PublicSourceBootstrapExecutionRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_public_source_bootstrap"
    dry_run: bool = True
    selected_sources: List[str] | None = None


class PublicSourceResolveRequest(BaseModel):
    config_path: str
    bootstrap_output_dir: str = "primevarclass_public_source_bootstrap"
    output_dir: str = "primevarclass_public_source_resolved"


class ContinuousLearningRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_continuous_learning_results"
    mode: str = "hybrid"
    high_confidence_only: bool = False
    model_families: List[str] | None = None


class StudyPublicResolveRequest(BaseModel):
    config_path: str
    output_dir: str = "primevarclass_public_study_resolution"
    bootstrap_root_dir: str | None = None
    delivery_dir: str | None = None


class StudyRealDataHandoffAutofillRequest(BaseModel):
    study_name: str = "PrimeVarClass Public Study"
    handoff_tasks_path: str
    delivery_dir: str
    output_dir: str = "primevarclass_real_data_handoff_autofill"
    tracker_path: str | None = None
    report_context: Dict[str, Any] = Field(default_factory=dict)


class PilotSessionRequest(BaseModel):
    session_id: str
    study_name: str | None = None
    pilot_mode: str = "shadow_mode"
    site_name: str | None = None
    institution: str | None = None
    team_name: str | None = None
    operator_name: str | None = None
    status: str = "planned"
    cases_reviewed: int = 0
    variants_flagged: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    outcome_summary: str | None = None
    notes: str | None = None


class PilotFeedbackRequest(BaseModel):
    session_id: str
    study_name: str | None = None
    feedback_id: str | None = None
    operator_name: str | None = None
    role: str | None = None
    confidence_score: int = 0
    actionability_score: int = 0
    time_saved_minutes: int = 0
    adoption_recommendation: str = "conditional"
    incident_level: str = "none"
    notes: str | None = None


UI_ASSET_NAMES = {"workbench.css", "workbench.js"}
KNOWLEDGE_DOCS = {
    "manual": "manual_usuario.md",
    "manual_en": "user_manual_en.md",
    "glossary": "glossario_primevarclass.md",
    "glossary_en": "glossary_primevarclass_en.md",
    "feedback": "feedback_playbook.md",
    "feedback_en": "feedback_playbook_en.md",
    "ux_references": "ux_accessibility_references.md",
}
KNOWLEDGE_PDFS = {
    "manual": "pdf/manual_usuario.pdf",
    "manual_en": "pdf/user_manual_en.pdf",
    "glossary": "pdf/glossario_primevarclass.pdf",
    "glossary_en": "pdf/glossary_primevarclass_en.pdf",
}


def _ui_root() -> Path:
    return Path(__file__).resolve().parent / "ui"


def _docs_root() -> Path:
    candidates = []
    if os.environ.get("PRIMEVARCLASS_DOCS_ROOT"):
        candidates.append(Path(str(os.environ["PRIMEVARCLASS_DOCS_ROOT"])))
    candidates.extend(
        [
            Path.cwd() / "docs",
            Path(__file__).resolve().parents[2] / "docs",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _summarize_training_response(results: dict) -> dict:
    return {
        "output_dir": results.get("summary_report_path", ""),
        "summary_report_path": results.get("summary_report_path"),
        "model_registry_path": results.get("model_paths", {}).get("registry"),
        "metrics_path": results.get("export_paths", {}).get("metrics"),
        "source_ingestion_report_path": results.get("source_ingestion_output_paths", {}).get("source_ingestion_report"),
        "data_release_manifest_path": results.get("source_ingestion_output_paths", {}).get("data_release_manifest_path"),
        "data_release_registry_path": results.get("source_ingestion_output_paths", {}).get("data_release_registry_path"),
        "public_source_catalog_report_json": results.get("source_ingestion_output_paths", {}).get("public_source_catalog_report_json"),
        "public_source_catalog_report_markdown": results.get("source_ingestion_output_paths", {}).get("public_source_catalog_report_markdown"),
        "public_source_sync_plan_json": results.get("source_ingestion_output_paths", {}).get("public_source_sync_plan_json"),
        "public_source_sync_plan_markdown": results.get("source_ingestion_output_paths", {}).get("public_source_sync_plan_markdown"),
        "public_source_assessment": results.get("public_source_assessment"),
        "public_source_sync_plan": results.get("public_source_sync_plan"),
        "n_models": len([key for key in results.get("model_paths", {}) if key != "registry"]),
    }


def _summarize_study_response(results: dict) -> dict:
    readiness_summary = ((results.get("publication_readiness_assessment") or {}).get("summary") or {})
    comparative_summary = ((results.get("comparative_evidence_assessment") or {}).get("summary") or {})
    independence_summary = ((results.get("cohort_independence_assessment") or {}).get("summary") or {})
    freeze_summary = results.get("study_cohort_freeze_summary") or {}
    claim_summary = ((results.get("claim_strength_assessment") or {}).get("summary") or {})
    external_robustness_summary = ((results.get("external_robustness_assessment") or {}).get("summary") or {})
    validation_summary = ((results.get("study_validation_lock") or {}).get("summary") or {})
    return {
        "training_metrics_path": results.get("training_metrics_path"),
        "study_summary_report_path": results.get("study_summary_report_path"),
        "external_evaluation_path": results.get("external_evaluation_path"),
        "model_registry_path": results.get("model_paths", {}).get("registry"),
        "consensus_members_path": results.get("consensus_members_path"),
        "cohort_manifest_path": results.get("cohort_manifest_path"),
        "cohort_independence_manifest_path": results.get("cohort_independence_manifest_path"),
        "cohort_independence_report_markdown_path": results.get("cohort_independence_report_markdown_path"),
        "cohort_independence_percent": independence_summary.get("overall_independence_percent"),
        "cohort_ready_for_external_validation": independence_summary.get("ready_for_external_validation"),
        "study_cohort_freeze_manifest_path": results.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_markdown_path": results.get("study_cohort_freeze_markdown_path"),
        "real_data_readiness_percent": freeze_summary.get("overall_real_data_readiness_percent"),
        "ready_for_real_data_study": freeze_summary.get("ready_for_real_data_study"),
        "scientific_dossier_markdown_path": results.get("scientific_dossier_markdown_path"),
        "scientific_dossier_html_path": results.get("scientific_dossier_html_path"),
        "publication_readiness_report_markdown_path": results.get("publication_readiness_report_markdown_path"),
        "publication_readiness_report_html_path": results.get("publication_readiness_report_html_path"),
        "publication_readiness_manifest_path": results.get("publication_readiness_manifest_path"),
        "publication_readiness_percent": readiness_summary.get("overall_readiness_percent"),
        "publication_ready_for_submission": readiness_summary.get("ready_for_submission"),
        "comparative_evidence_report_markdown_path": results.get("comparative_evidence_report_markdown_path"),
        "comparative_evidence_report_html_path": results.get("comparative_evidence_report_html_path"),
        "comparative_evidence_manifest_path": results.get("comparative_evidence_manifest_path"),
        "comparative_evidence_percent": comparative_summary.get("overall_comparative_strength_percent"),
        "comparative_best_supported_experiment": comparative_summary.get("best_supported_experiment"),
        "claim_strength_report_markdown_path": results.get("claim_strength_report_markdown_path"),
        "claim_strength_report_html_path": results.get("claim_strength_report_html_path"),
        "claim_strength_manifest_path": results.get("claim_strength_manifest_path"),
        "claim_strength_percent": claim_summary.get("overall_claim_strength_percent"),
        "claim_tier": claim_summary.get("claim_tier"),
        "external_robustness_report_markdown_path": results.get("external_robustness_report_markdown_path"),
        "external_robustness_report_html_path": results.get("external_robustness_report_html_path"),
        "external_robustness_manifest_path": results.get("external_robustness_manifest_path"),
        "external_robustness_percent": external_robustness_summary.get("overall_external_robustness_percent"),
        "external_exact_sign_confidence_percent": external_robustness_summary.get("exact_sign_confidence_percent"),
        "baseline_coverage_manifest_path": results.get("baseline_coverage_manifest_path"),
        "baseline_coverage_report_markdown_path": results.get("baseline_coverage_report_markdown_path"),
        "baseline_coverage_percent": ((results.get("baseline_coverage_assessment") or {}).get("summary") or {}).get("overall_coverage_percent"),
        "methods_package_manifest_path": results.get("methods_package_manifest_path"),
        "methods_package_markdown_path": results.get("methods_package_markdown_path"),
        "manuscript_package_markdown_path": results.get("manuscript_package_markdown_path"),
        "manuscript_package_html_path": results.get("manuscript_package_html_path"),
        "manuscript_package_manifest_path": results.get("manuscript_package_manifest_path"),
        "study_validation_lock_manifest_path": results.get("study_validation_lock_manifest_path"),
        "study_validation_lock_markdown_path": results.get("study_validation_lock_markdown_path"),
        "validation_lock_percent": validation_summary.get("overall_validation_lock_percent"),
        "validation_ready_for_statistical_validation": validation_summary.get("ready_for_statistical_validation"),
        "validation_ready_for_submission_lock": validation_summary.get("ready_for_submission_lock"),
        "validation_ready_for_translational_pilot": validation_summary.get("ready_for_translational_pilot"),
        "study_release_manifest_path": results.get("study_release_manifest_path"),
        "study_release_registry_path": results.get("study_release_registry_path"),
    }


def _summarize_public_study_run_response(results: dict) -> dict:
    summary = dict(results.get("summary") or {})
    return {
        "output_dir": results.get("output_dir") or results.get("study_output_dir"),
        "resolved_study_config_path": results.get("resolved_study_config_path"),
        "study_public_config_resolution_manifest_path": results.get("study_public_config_resolution_manifest_path"),
        "study_public_config_resolution_report_markdown_path": results.get("study_public_config_resolution_report_markdown_path"),
        "study_cohort_freeze_manifest_path": results.get("study_cohort_freeze_manifest_path"),
        "study_cohort_freeze_markdown_path": results.get("study_cohort_freeze_markdown_path"),
        "study_real_data_handoff_manifest_path": results.get("study_real_data_handoff_manifest_path"),
        "study_real_data_handoff_markdown_path": results.get("study_real_data_handoff_markdown_path"),
        "study_real_data_handoff_html_path": results.get("study_real_data_handoff_html_path"),
        "study_real_data_handoff_autofill_manifest_path": results.get("study_real_data_handoff_autofill_manifest_path"),
        "study_real_data_handoff_autofill_markdown_path": results.get("study_real_data_handoff_autofill_markdown_path"),
        "study_real_data_handoff_autofill_html_path": results.get("study_real_data_handoff_autofill_html_path"),
        "study_real_data_handoff_autofill_tracker_path": results.get("study_real_data_handoff_autofill_tracker_path"),
        "study_real_data_handoff_autofill_matches_path": results.get("study_real_data_handoff_autofill_matches_path"),
        "study_real_data_handoff_autofill_inventory_path": results.get("study_real_data_handoff_autofill_inventory_path"),
        "study_real_data_handoff_tracker_path": results.get("study_real_data_handoff_tracker_path"),
        "study_real_data_handoff_reconciliation_manifest_path": results.get("study_real_data_handoff_reconciliation_manifest_path"),
        "study_real_data_handoff_reconciliation_markdown_path": results.get("study_real_data_handoff_reconciliation_markdown_path"),
        "study_real_data_handoff_reconciliation_html_path": results.get("study_real_data_handoff_reconciliation_html_path"),
        "study_real_data_handoff_reconciliation_tasks_path": results.get("study_real_data_handoff_reconciliation_tasks_path"),
        "study_real_data_candidate_config_path": results.get("study_real_data_candidate_config_path"),
        "study_real_data_handoff_application_manifest_path": results.get("study_real_data_handoff_application_manifest_path"),
        "study_real_data_handoff_application_markdown_path": results.get("study_real_data_handoff_application_markdown_path"),
        "study_real_data_handoff_application_html_path": results.get("study_real_data_handoff_application_html_path"),
        "study_real_data_handoff_application_sources_path": results.get("study_real_data_handoff_application_sources_path"),
        "study_real_data_candidate_promotion_manifest_path": results.get("study_real_data_candidate_promotion_manifest_path"),
        "study_real_data_candidate_promotion_markdown_path": results.get("study_real_data_candidate_promotion_markdown_path"),
        "study_real_data_candidate_promotion_html_path": results.get("study_real_data_candidate_promotion_html_path"),
        "study_real_data_candidate_promotion_criteria_path": results.get("study_real_data_candidate_promotion_criteria_path"),
        "study_real_data_candidate_promotion_blockers_path": results.get("study_real_data_candidate_promotion_blockers_path"),
        "study_preflight_manifest_path": results.get("study_preflight_manifest_path"),
        "study_preflight_report_markdown_path": results.get("study_preflight_report_markdown_path"),
        "study_release_manifest_path": results.get("study_release_manifest_path"),
        "cohort_independence_manifest_path": results.get("cohort_independence_manifest_path"),
        "cohort_independence_report_markdown_path": results.get("cohort_independence_report_markdown_path"),
        "comparative_evidence_manifest_path": results.get("comparative_evidence_manifest_path"),
        "comparative_evidence_report_markdown_path": results.get("comparative_evidence_report_markdown_path"),
        "claim_strength_manifest_path": results.get("claim_strength_manifest_path"),
        "claim_strength_report_markdown_path": results.get("claim_strength_report_markdown_path"),
        "external_robustness_manifest_path": results.get("external_robustness_manifest_path"),
        "external_robustness_report_markdown_path": results.get("external_robustness_report_markdown_path"),
        "publication_readiness_manifest_path": results.get("publication_readiness_manifest_path"),
        "study_validation_lock_manifest_path": results.get("study_validation_lock_manifest_path"),
        "study_validation_lock_markdown_path": results.get("study_validation_lock_markdown_path"),
        "study_execution_board_manifest_path": results.get("study_execution_board_manifest_path"),
        "study_execution_board_markdown_path": results.get("study_execution_board_markdown_path"),
        "study_execution_board_html_path": results.get("study_execution_board_html_path"),
        "translational_pilot_package_manifest_path": results.get("translational_pilot_package_manifest_path"),
        "translational_pilot_package_markdown_path": results.get("translational_pilot_package_markdown_path"),
        "translational_pilot_package_html_path": results.get("translational_pilot_package_html_path"),
        "translational_pilot_package_criteria_path": results.get("translational_pilot_package_criteria_path"),
        "translational_pilot_package_checklist_path": results.get("translational_pilot_package_checklist_path"),
        "translational_impact_package_manifest_path": results.get("translational_impact_package_manifest_path"),
        "translational_impact_package_markdown_path": results.get("translational_impact_package_markdown_path"),
        "translational_impact_package_html_path": results.get("translational_impact_package_html_path"),
        "translational_impact_package_criteria_path": results.get("translational_impact_package_criteria_path"),
        "translational_impact_sessions_path": results.get("translational_impact_sessions_path"),
        "translational_impact_feedback_path": results.get("translational_impact_feedback_path"),
        "platform_completion_manifest_path": results.get("platform_completion_manifest_path"),
        "platform_completion_markdown_path": results.get("platform_completion_markdown_path"),
        "platform_completion_html_path": results.get("platform_completion_html_path"),
        "final_mile_package_manifest_path": results.get("final_mile_package_manifest_path"),
        "final_mile_package_markdown_path": results.get("final_mile_package_markdown_path"),
        "final_mile_package_html_path": results.get("final_mile_package_html_path"),
        "final_mile_package_criteria_path": results.get("final_mile_package_criteria_path"),
        "final_mile_package_blockers_path": results.get("final_mile_package_blockers_path"),
        "final_mile_package_checklist_path": results.get("final_mile_package_checklist_path"),
        "public_study_run_manifest_path": results.get("public_study_run_manifest_path"),
        "public_study_run_report_markdown_path": results.get("public_study_run_report_markdown_path"),
        "candidate_public_run_manifest_path": results.get("candidate_public_run_manifest_path"),
        "candidate_public_run_report_markdown_path": results.get("candidate_public_run_report_markdown_path"),
        "recommended_actions": results.get("recommended_actions") or [],
        "resolution_percent": summary.get("resolution_percent"),
        "real_data_readiness_percent": summary.get("real_data_readiness_percent"),
        "real_data_handoff_percent": summary.get("real_data_handoff_percent"),
        "real_data_handoff_autofill_percent": summary.get("real_data_handoff_autofill_percent"),
        "real_data_handoff_reconciliation_percent": summary.get("real_data_handoff_reconciliation_percent"),
        "real_data_handoff_application_percent": summary.get("real_data_handoff_application_percent"),
        "real_data_candidate_promotion_percent": summary.get("real_data_candidate_promotion_percent"),
        "ready_for_real_data_study": summary.get("ready_for_real_data_study"),
        "ready_for_lab_handoff": summary.get("ready_for_lab_handoff"),
        "n_real_data_tasks": summary.get("n_real_data_tasks"),
        "n_critical_real_data_tasks": summary.get("n_critical_real_data_tasks"),
        "n_handoff_autofilled_tasks": summary.get("n_handoff_autofilled_tasks"),
        "n_handoff_preserved_completed_tasks": summary.get("n_handoff_preserved_completed_tasks"),
        "n_handoff_unmatched_tasks": summary.get("n_handoff_unmatched_tasks"),
        "n_handoff_validated_tasks": summary.get("n_handoff_validated_tasks"),
        "n_handoff_pending_tasks": summary.get("n_handoff_pending_tasks"),
        "n_handoff_invalid_tasks": summary.get("n_handoff_invalid_tasks"),
        "ready_for_reconciliation_rerun_from_autofill": summary.get("ready_for_reconciliation_rerun_from_autofill"),
        "n_handoff_applied_changes": summary.get("n_handoff_applied_changes"),
        "ready_to_rerun_resolution_from_handoff": summary.get("ready_to_rerun_resolution_from_handoff"),
        "ready_to_rerun_public_study_from_handoff": summary.get("ready_to_rerun_public_study_from_handoff"),
        "ready_for_candidate_resolution_from_handoff": summary.get("ready_for_candidate_resolution_from_handoff"),
        "ready_for_candidate_public_study_from_handoff": summary.get("ready_for_candidate_public_study_from_handoff"),
        "ready_to_promote_candidate_config": summary.get("ready_to_promote_candidate_config"),
        "ready_to_run_candidate_public_study": summary.get("ready_to_run_candidate_public_study"),
        "preflight_percent": summary.get("preflight_percent"),
        "cohort_independence_percent": summary.get("cohort_independence_percent"),
        "comparative_evidence_percent": summary.get("comparative_evidence_percent"),
        "claim_strength_percent": summary.get("claim_strength_percent"),
        "claim_tier": summary.get("claim_tier"),
        "external_robustness_percent": summary.get("external_robustness_percent"),
        "external_exact_sign_confidence_percent": summary.get("external_robustness_exact_sign_confidence_percent"),
        "publication_readiness_percent": summary.get("publication_readiness_percent"),
        "validation_lock_percent": summary.get("validation_lock_percent"),
        "execution_board_percent": summary.get("execution_board_percent"),
        "pilot_package_percent": summary.get("pilot_package_percent"),
        "pilot_mode": summary.get("pilot_mode"),
        "ready_for_demo_pilot": summary.get("ready_for_demo_pilot"),
        "ready_for_shadow_pilot": summary.get("ready_for_shadow_pilot"),
        "ready_for_live_pilot": summary.get("ready_for_live_pilot"),
        "translational_impact_percent": summary.get("translational_impact_percent"),
        "ready_for_assisted_pilot_ops": summary.get("ready_for_assisted_pilot_ops"),
        "ready_for_shadow_rollout": summary.get("ready_for_shadow_rollout"),
        "ready_for_institutional_rollout": summary.get("ready_for_institutional_rollout"),
        "platform_completion_percent": summary.get("platform_completion_percent"),
        "development_complete": summary.get("development_complete"),
        "scientific_validation_pending": summary.get("scientific_validation_pending"),
        "evidence_execution_percent": summary.get("evidence_execution_percent"),
        "final_mile_percent": summary.get("final_mile_percent"),
        "ready_for_real_data_execution": summary.get("ready_for_real_data_execution"),
        "ready_for_final_evidence_round": summary.get("ready_for_final_evidence_round"),
        "ready_for_submission_closeout": summary.get("ready_for_submission_closeout"),
        "ready_for_live_transition": summary.get("ready_for_live_transition"),
        "n_final_mile_blockers": summary.get("n_final_mile_blockers"),
        "n_final_mile_critical_blockers": summary.get("n_final_mile_critical_blockers"),
        "top_final_mile_blocker_phase": summary.get("top_final_mile_blocker_phase"),
        "top_final_mile_blocker_title": summary.get("top_final_mile_blocker_title"),
        "ready_for_benchmark_lock": summary.get("ready_for_benchmark_lock"),
        "ready_for_submission_lock": summary.get("ready_for_submission_lock"),
        "ready_for_translational_pilot": summary.get("ready_for_translational_pilot"),
    }


def _summarize_gene_expansion_response(results: dict) -> dict:
    assessment = results.get("gene_expansion_assessment") or {}
    return {
        "summary": assessment.get("summary") or {},
        "top_candidates": assessment.get("top_candidates") or [],
        "gene_expansion_manifest_path": results.get("gene_expansion_manifest_path"),
        "gene_expansion_report_markdown_path": results.get("gene_expansion_report_markdown_path"),
        "gene_expansion_report_html_path": results.get("gene_expansion_report_html_path"),
        "gene_expansion_candidates_path": results.get("gene_expansion_candidates_path"),
        "gene_expansion_panel_template_path": results.get("gene_expansion_panel_template_path"),
    }


def _summarize_independent_data_expansion_response(results: dict) -> dict:
    return {
        "summary": results.get("summary") or {},
        "independent_data_expansion_manifest_path": results.get("independent_data_expansion_manifest_path"),
        "independent_public_database_registry_path": results.get("independent_public_database_registry_path"),
        "independent_training_validation_plan_path": results.get("independent_training_validation_plan_path"),
        "independent_gene_source_matrix_path": results.get("independent_gene_source_matrix_path"),
        "independent_source_templates_path": results.get("independent_source_templates_path"),
        "independent_data_expansion_report_markdown_path": results.get("independent_data_expansion_report_markdown_path"),
        "independent_data_expansion_report_html_path": results.get("independent_data_expansion_report_html_path"),
    }


def _summarize_independent_data_staging_closure_response(results: dict) -> dict:
    return {
        "summary": results.get("summary") or {},
        "independent_data_staging_closure_manifest_path": results.get("independent_data_staging_closure_manifest_path"),
        "independent_data_staging_inventory_path": results.get("independent_data_staging_inventory_path"),
        "independent_data_staging_gap_plan_path": results.get("independent_data_staging_gap_plan_path"),
        "independent_ready_source_config_path": results.get("independent_ready_source_config_path"),
        "independent_data_stage_runner_path": results.get("independent_data_stage_runner_path"),
        "independent_data_staging_closure_report_markdown_path": results.get("independent_data_staging_closure_report_markdown_path"),
        "independent_data_staging_closure_report_html_path": results.get("independent_data_staging_closure_report_html_path"),
    }


def _summarize_independent_open_source_autostage_response(results: dict) -> dict:
    return {
        "summary": results.get("summary") or {},
        "staged_sources": results.get("staged_sources") or [],
        "errors": results.get("errors") or [],
        "independent_open_source_autostage_manifest_path": results.get("independent_open_source_autostage_manifest_path"),
        "independent_open_source_autostage_status_path": results.get("independent_open_source_autostage_status_path"),
        "independent_open_source_autostage_errors_path": results.get("independent_open_source_autostage_errors_path"),
    }


def _summarize_biological_discovery_response(results: dict) -> dict:
    bundle = results.get("biological_discovery_package") or {}
    return {
        "summary": bundle.get("summary") or {},
        "artifact_paths": bundle.get("artifact_paths") or {},
        "biological_discovery_manifest_path": results.get("biological_discovery_manifest_path"),
        "biological_discovery_report_markdown_path": results.get("biological_discovery_report_markdown_path"),
        "biological_discovery_report_html_path": results.get("biological_discovery_report_html_path"),
        "biological_discovery_hotspots_path": results.get("biological_discovery_hotspots_path"),
        "biological_discovery_tolerant_regions_path": results.get("biological_discovery_tolerant_regions_path"),
        "biological_discovery_review_upgrade_candidates_path": results.get("biological_discovery_review_upgrade_candidates_path"),
        "biological_discovery_hypothesis_variants_path": results.get("biological_discovery_hypothesis_variants_path"),
        "biological_discovery_orientations_path": results.get("biological_discovery_orientations_path"),
    }


def _summarize_multigene_rollout_response(results: dict) -> dict:
    return {
        "summary": results.get("summary") or {},
        "recommended_actions": results.get("recommended_actions") or [],
        "report_context": results.get("report_context") or {},
        "multigene_rollout_manifest_path": results.get("manifest_path"),
        "multigene_rollout_markdown_path": results.get("markdown_path"),
        "multigene_rollout_html_path": results.get("html_path"),
        "multigene_rollout_csv_path": results.get("rollout_csv_path"),
    }


def _summarize_multigene_study_factory_response(results: dict) -> dict:
    return {
        "summary": results.get("summary") or {},
        "rollout_manifest_path": results.get("rollout_manifest_path"),
        "multigene_study_scaffold_index_path": results.get("scaffold_index_path"),
        "multigene_study_factory_tasks_path": results.get("tasks_path"),
        "multigene_study_factory_markdown_path": results.get("markdown_path"),
        "multigene_study_factory_manifest_path": results.get("manifest_path"),
    }


def _summarize_multigene_annotation_response(results: dict) -> dict:
    bundle = results.get("multigene_annotation_enrichment") or {}
    return {
        "summary": bundle.get("summary") or {},
        "multigene_annotation_enrichment_manifest_path": results.get("multigene_annotation_enrichment_manifest_path"),
        "multigene_variant_annotation_matrix_path": results.get("multigene_variant_annotation_matrix_path"),
        "multigene_annotation_coverage_by_gene_path": results.get("multigene_annotation_coverage_by_gene_path"),
        "gnomad_live_query_results_path": results.get("gnomad_live_query_results_path"),
        "mavedb_live_score_sets_path": results.get("mavedb_live_score_sets_path"),
        "multigene_annotation_enrichment_report_markdown_path": results.get("multigene_annotation_enrichment_report_markdown_path"),
        "multigene_annotation_enrichment_report_html_path": results.get("multigene_annotation_enrichment_report_html_path"),
    }


def _summarize_public_sync_closure_response(results: dict) -> dict:
    bundle = results.get("public_sync_closure") or {}
    return {
        "summary": bundle.get("summary") or {},
        "public_sync_closure_manifest_path": results.get("public_sync_closure_manifest_path"),
        "gnomad_sync_cache_path": results.get("gnomad_sync_cache_path"),
        "gnomad_sync_queue_path": results.get("gnomad_sync_queue_path"),
        "mavedb_reconciliation_queue_path": results.get("mavedb_reconciliation_queue_path"),
        "coordinate_exception_review_path": results.get("coordinate_exception_review_path"),
        "resume_gnomad_sync_script_path": results.get("resume_gnomad_sync_script_path"),
        "public_sync_closure_report_markdown_path": results.get("public_sync_closure_report_markdown_path"),
        "public_sync_closure_report_html_path": results.get("public_sync_closure_report_html_path"),
    }


def _summarize_gnomad_gene_subset_response(results: dict) -> dict:
    bundle = results.get("gnomad_gene_subset") or {}
    return {
        "summary": bundle.get("summary") or {},
        "gnomad_gene_subset_manifest_path": results.get("gnomad_gene_subset_manifest_path"),
        "gnomad_gene_subset_variants_path": results.get("gnomad_gene_subset_variants_path"),
        "gnomad_gene_subset_status_path": results.get("gnomad_gene_subset_status_path"),
        "gnomad_gene_subset_report_markdown_path": results.get("gnomad_gene_subset_report_markdown_path"),
        "gnomad_gene_subset_report_html_path": results.get("gnomad_gene_subset_report_html_path"),
    }


def _summarize_brca1_engine_execution_response(results: dict) -> dict:
    bundle = results.get("brca1_engine_execution") or {}
    return {
        "summary": bundle.get("summary") or {},
        "engine_state": bundle.get("engine_state") or {},
        "brca1_engine_execution_manifest_path": results.get("brca1_engine_execution_manifest_path"),
        "brca1_engine_execution_queue_path": results.get("brca1_engine_execution_queue_path"),
        "brca1_engine_execution_log_path": results.get("brca1_engine_execution_log_path"),
        "structural_engine_diagnostics_path": results.get("structural_engine_diagnostics_path"),
        "brca1_input_preparation_queue_path": results.get("brca1_input_preparation_queue_path"),
        "brca1_alphafold_reference_path": results.get("brca1_alphafold_reference_path"),
        "brca1_reference_structure_paths": results.get("brca1_reference_structure_paths"),
        "structural_engine_environment_path": results.get("structural_engine_environment_path"),
        "structural_engine_install_script_path": results.get("structural_engine_install_script_path"),
        "structural_engine_doctor_script_path": results.get("structural_engine_doctor_script_path"),
        "brca1_engine_run_script_path": results.get("brca1_engine_run_script_path"),
        "brca1_engine_execution_report_markdown_path": results.get("brca1_engine_execution_report_markdown_path"),
        "brca1_engine_execution_report_html_path": results.get("brca1_engine_execution_report_html_path"),
    }


def _summarize_brca1_fragment_preparation_response(results: dict) -> dict:
    bundle = results.get("brca1_fragment_preparation") or {}
    return {
        "summary": bundle.get("summary") or {},
        "brca1_fragment_preparation_manifest_path": results.get("brca1_fragment_preparation_manifest_path"),
        "brca1_prepared_fragment_table_path": results.get("brca1_prepared_fragment_table_path"),
        "brca1_xtb_baseline_execution_log_path": results.get("brca1_xtb_baseline_execution_log_path"),
        "brca1_prepared_fragments_dir": results.get("brca1_prepared_fragments_dir"),
        "brca1_fragment_preparation_report_markdown_path": results.get("brca1_fragment_preparation_report_markdown_path"),
        "brca1_fragment_preparation_report_html_path": results.get("brca1_fragment_preparation_report_html_path"),
    }


def _summarize_brca1_paired_mutant_execution_response(results: dict) -> dict:
    bundle = results.get("brca1_paired_mutant_execution") or {}
    return {
        "summary": bundle.get("summary") or {},
        "brca1_paired_mutant_execution_manifest_path": results.get("brca1_paired_mutant_execution_manifest_path"),
        "brca1_paired_mutant_table_path": results.get("brca1_paired_mutant_table_path"),
        "brca1_paired_mutant_xtb_execution_log_path": results.get("brca1_paired_mutant_xtb_execution_log_path"),
        "brca1_paired_mutant_fragments_dir": results.get("brca1_paired_mutant_fragments_dir"),
        "brca1_paired_mutant_execution_report_markdown_path": results.get("brca1_paired_mutant_execution_report_markdown_path"),
        "brca1_paired_mutant_execution_report_html_path": results.get("brca1_paired_mutant_execution_report_html_path"),
    }


def _summarize_brca1_mutant_geometry_qc_response(results: dict) -> dict:
    bundle = results.get("brca1_mutant_geometry_qc") or {}
    return {
        "summary": bundle.get("summary") or {},
        "brca1_mutant_geometry_qc_manifest_path": results.get("brca1_mutant_geometry_qc_manifest_path"),
        "brca1_mutant_geometry_qc_table_path": results.get("brca1_mutant_geometry_qc_table_path"),
        "brca1_xtb_optimization_log_path": results.get("brca1_xtb_optimization_log_path"),
        "brca1_mutant_geometry_qc_report_markdown_path": results.get("brca1_mutant_geometry_qc_report_markdown_path"),
        "brca1_mutant_geometry_qc_report_html_path": results.get("brca1_mutant_geometry_qc_report_html_path"),
    }


def _summarize_prospective_validation_response(results: dict) -> dict:
    bundle = results.get("prospective_validation_closure") or {}
    return {
        "summary": bundle.get("summary") or {},
        "prospective_validation_closure_manifest_path": results.get("prospective_validation_closure_manifest_path"),
        "prospective_validation_gates_path": results.get("prospective_validation_gates_path"),
        "functional_structural_confirmation_queue_path": results.get("functional_structural_confirmation_queue_path"),
        "prospective_validation_cohort_plan_path": results.get("prospective_validation_cohort_plan_path"),
        "experimental_confirmation_criteria_path": results.get("experimental_confirmation_criteria_path"),
        "partner_lab_handoff_sheet_path": results.get("partner_lab_handoff_sheet_path"),
        "statistical_analysis_plan_path": results.get("statistical_analysis_plan_path"),
        "statistical_analysis_plan_html_path": results.get("statistical_analysis_plan_html_path"),
        "external_partner_handoff_packet_path": results.get("external_partner_handoff_packet_path"),
        "external_partner_handoff_packet_html_path": results.get("external_partner_handoff_packet_html_path"),
        "sop_templates_dir": results.get("sop_templates_dir"),
        "sop_template_manifest_path": results.get("sop_template_manifest_path"),
        "prospective_validation_protocol_markdown_path": results.get("prospective_validation_protocol_markdown_path"),
        "prospective_validation_protocol_html_path": results.get("prospective_validation_protocol_html_path"),
    }


def _summarize_development_progress_response(results: dict) -> dict:
    bundle = results.get("development_progress") or {}
    return {
        "summary": bundle.get("summary") or {},
        "development_progress_manifest_path": results.get("development_progress_manifest_path"),
        "development_progress_table_path": results.get("development_progress_table_path"),
        "development_progress_report_markdown_path": results.get("development_progress_report_markdown_path"),
        "development_progress_report_html_path": results.get("development_progress_report_html_path"),
    }


def _summarize_protein_impact_response(results: dict) -> dict:
    bundle = results.get("protein_impact_package") or {}
    return {
        "summary": bundle.get("summary") or {},
        "protein_impact_manifest_path": results.get("protein_impact_manifest_path"),
        "protein_impact_report_markdown_path": results.get("protein_impact_report_markdown_path"),
        "protein_impact_report_html_path": results.get("protein_impact_report_html_path"),
        "protein_variant_triage_path": results.get("protein_variant_triage_path"),
        "protein_modeling_queue_path": results.get("protein_modeling_queue_path"),
        "protein_region_summary_path": results.get("protein_region_summary_path"),
    }


def _summarize_quantum_proteomics_response(results: dict) -> dict:
    bundle = results.get("quantum_proteomics_package") or {}
    return {
        "summary": bundle.get("summary") or {},
        "quantum_proteomics_manifest_path": results.get("quantum_proteomics_manifest_path"),
        "quantum_targets_path": results.get("quantum_targets_path"),
        "prime_quantum_bridge_path": results.get("prime_quantum_bridge_path"),
        "vqe_targets_path": results.get("vqe_targets_path"),
        "quantum_algorithm_portfolio_path": results.get("quantum_algorithm_portfolio_path"),
        "quantum_workflow_path": results.get("quantum_workflow_path"),
        "quantum_job_templates_path": results.get("quantum_job_templates_path"),
        "quantum_job_templates_dir": results.get("quantum_job_templates_dir"),
        "vqe_job_templates_path": results.get("vqe_job_templates_path"),
        "vqe_job_templates_dir": results.get("vqe_job_templates_dir"),
        "quantum_proteomics_report_markdown_path": results.get("quantum_proteomics_report_markdown_path"),
        "quantum_proteomics_report_html_path": results.get("quantum_proteomics_report_html_path"),
    }


def _summarize_validation_credibility_response(results: dict) -> dict:
    closure = results.get("validation_credibility_closure") or {}
    return {
        "summary": closure.get("summary") or {},
        "criteria": closure.get("criteria") or [],
        "remaining_actions": closure.get("remaining_actions") or [],
        "validation_credibility_closure_manifest_path": results.get("validation_credibility_closure_manifest_path"),
        "validation_credibility_criteria_path": results.get("validation_credibility_criteria_path"),
        "validation_credibility_remaining_actions_path": results.get("validation_credibility_remaining_actions_path"),
        "validation_credibility_report_markdown_path": results.get("validation_credibility_report_markdown_path"),
        "validation_credibility_report_html_path": results.get("validation_credibility_report_html_path"),
    }


def create_app(
    job_root: str | None = None,
    api_key: str | None = None,
    audit_root: str | None = None,
    profile_root: str | None = None,
    team_root: str | None = None,
) -> FastAPI:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    app = FastAPI(
        title="PrimeVarClass API",
        version="0.2.0",
        description=(
            "API cientifica para treinamento, benchmark e inferencia interpretavel "
            "de variantes missense, com validacao real BRCA-first e expansao multigenica."
        ),
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    cors_origins = [origin.strip() for origin in os.environ.get("PRIMEVARCLASS_CORS_ORIGINS", "").split(",") if origin.strip()]
    if cors_origins:
        allow_all_origins = "*" in cors_origins
        # Security Fix: restrict headers and do not allow credentials with wildcard origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=not allow_all_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-PrimeVarClass-Team", "X-PrimeVarClass-Profile"],
        )

    app.state.security = resolve_security_settings(api_key=api_key)
    env_job_root = os.environ.get("PRIMEVARCLASS_JOB_ROOT")
    env_audit_root = os.environ.get("PRIMEVARCLASS_AUDIT_ROOT")
    env_profile_root = os.environ.get("PRIMEVARCLASS_PROFILE_ROOT")
    env_team_root = os.environ.get("PRIMEVARCLASS_TEAM_ROOT")
    resolved_job_root = Path(job_root or env_job_root).resolve() if (job_root or env_job_root) else None
    shared_state_root = resolved_job_root or (Path.cwd() / "primevarclass_job_history")
    app.state.cors_origins = cors_origins
    app.state.audit_logger = PrimeVarClassAuditLogger(root_dir=audit_root or env_audit_root or (resolved_job_root or Path.cwd() / "primevarclass_job_history"))
    app.state.profile_store = PrimeVarClassProfileStore(root_dir=profile_root or env_profile_root or audit_root or env_audit_root or shared_state_root)
    app.state.team_store = PrimeVarClassTeamStore(root_dir=team_root or env_team_root or audit_root or env_audit_root or shared_state_root)
    app.state.pilot_ops_store = PrimeVarClassPilotOpsStore(root_dir=shared_state_root)
    app.state.job_manager = PrimeVarClassJobManager(
        root_dir=resolved_job_root,
        audit_logger=app.state.audit_logger,
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
        return response

    def _resolve_profile_from_request(request: Request) -> dict:
        cached = getattr(request.state, "profile_context", None)
        if cached is not None:
            return cached
        requested_profile_id = request.headers.get("X-PrimeVarClass-Profile")
        if requested_profile_id:
            profile = app.state.profile_store.mark_profile_used(requested_profile_id)
        else:
            profile = app.state.profile_store.resolve_profile(None)
        request.state.profile_context = profile
        return profile

    def _resolve_team_from_request(request: Request, require_membership: bool = False) -> dict:
        cached = getattr(request.state, "team_context", None)
        cached_require_membership = bool(getattr(request.state, "team_context_membership_checked", False))
        if cached is not None and (cached_require_membership or not require_membership):
            return cached

        profile = _resolve_profile_from_request(request)
        requested_team_id = request.headers.get("X-PrimeVarClass-Team")
        if not requested_team_id:
            team = app.state.team_store.resolve_team(None, profile.get("profile_id"))
            request.state.team_context = team
            request.state.team_context_membership_checked = True
            return team

        team = app.state.team_store.resolve_team(requested_team_id, profile.get("profile_id"))
        if require_membership:
            if team.get("is_guest") and team.get("requested_team_id"):
                raise HTTPException(status_code=404, detail="Time solicitado nao encontrado.")
            if profile.get("is_guest"):
                raise HTTPException(status_code=403, detail="Selecione um perfil valido antes de operar em um time.")
            if not team.get("member_role"):
                raise HTTPException(status_code=403, detail="Perfil sem permissao para o time solicitado.")
            team = app.state.team_store.mark_team_used(str(team.get("team_id")), str(profile.get("profile_id")))
        request.state.team_context = team
        request.state.team_context_membership_checked = require_membership
        return team

    def _actor_from_request(request: Request) -> str:
        profile = _resolve_profile_from_request(request)
        host = request.client.host if request.client else "unknown"
        label = str(profile.get("display_name") or profile.get("profile_id") or "unknown")
        role = str(profile.get("role") or "guest")
        return f"{label}<{role}>@{host}:{request.method}"

    def _audit_event(
        request: Request,
        event_type: str,
        status: str = "info",
        job_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        profile = _resolve_profile_from_request(request)
        team = _resolve_team_from_request(request, require_membership=False)
        resolved_metadata = dict(metadata or {})
        resolved_metadata.setdefault("profile_id", profile.get("profile_id"))
        resolved_metadata.setdefault("profile_role", profile.get("role"))
        resolved_metadata.setdefault("profile_institution", profile.get("institution"))
        resolved_metadata.setdefault("team_id", team.get("team_id"))
        resolved_metadata.setdefault("team_name", team.get("display_name"))
        resolved_metadata.setdefault("team_member_role", team.get("member_role"))
        app.state.audit_logger.log_event(
            event_type=event_type,
            status=status,
            actor=_actor_from_request(request),
            request_path=request.url.path,
            job_id=job_id,
            metadata=resolved_metadata,
        )

    def require_api_key(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> None:
        expected_api_key = app.state.security.api_key
        if not expected_api_key:
            raise HTTPException(status_code=500, detail="Configuracao de seguranca invalida: API Key nao configurada.")
            
        if verify_api_key(x_api_key, expected_api_key):
            _resolve_team_from_request(request, require_membership=True)
            return
            
        _audit_event(
            request,
            event_type="auth.denied",
            status="denied",
            metadata={"auth_enabled": True},
        )
        raise HTTPException(status_code=401, detail="API key invalida ou ausente.")

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse(url="/workbench", status_code=302)

    @app.get("/workbench", response_class=HTMLResponse, include_in_schema=False)
    def workbench() -> HTMLResponse:
        html = (_ui_root() / "workbench.html").read_text(encoding="utf-8")
        return HTMLResponse(content=html)

    @app.get("/workbench/assets/{asset_name}", include_in_schema=False)
    def workbench_assets(asset_name: str):
        if asset_name not in UI_ASSET_NAMES:
            raise HTTPException(status_code=404, detail="Asset nao encontrado.")
        asset_path = _ui_root() / asset_name
        if not asset_path.exists():
            raise HTTPException(status_code=404, detail="Asset nao encontrado.")
        media_type = "text/css" if asset_name.endswith(".css") else "application/javascript"
        return FileResponse(path=asset_path, media_type=media_type)

    @app.get("/knowledge")
    def knowledge_index() -> dict:
        docs = []
        for doc_id, filename in KNOWLEDGE_DOCS.items():
            path = _docs_root() / filename
            pdf_filename = KNOWLEDGE_PDFS.get(doc_id)
            pdf_path = _docs_root() / pdf_filename if pdf_filename else None
            docs.append(
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "language": "en" if doc_id.endswith("_en") else "pt-BR",
                    "available": path.exists(),
                    "url": f"/knowledge/{doc_id}",
                    "raw_markdown_url": f"/knowledge/{doc_id}.md",
                    "pdf_available": bool(pdf_path and pdf_path.exists()),
                    "pdf_url": f"/knowledge/{doc_id}.pdf" if pdf_filename else None,
                }
            )
        return {
            "n_docs": len(docs),
            "docs": docs,
        }

    @app.get("/knowledge/{doc_ref}", include_in_schema=False)
    def knowledge_doc(doc_ref: str):
        is_pdf = doc_ref.endswith(".pdf")
        doc_id = doc_ref.removesuffix(".pdf").removesuffix(".md")
        if is_pdf:
            pdf_filename = KNOWLEDGE_PDFS.get(doc_id)
            if not pdf_filename:
                raise HTTPException(status_code=404, detail="Documento nao encontrado.")
            pdf_path = _docs_root() / pdf_filename
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="Documento PDF nao encontrado.")
            return FileResponse(path=pdf_path, media_type="application/pdf", filename=Path(pdf_filename).name)
        filename = KNOWLEDGE_DOCS.get(doc_id)
        if not filename:
            raise HTTPException(status_code=404, detail="Documento nao encontrado.")
        path = _docs_root() / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Documento nao encontrado.")
        return FileResponse(path=path, media_type="text/markdown; charset=utf-8", filename=filename)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "PrimeVarClass API",
            "job_root": str(app.state.job_manager.root_dir),
            "auth_enabled": app.state.security.auth_enabled,
            "cors_enabled": bool(app.state.cors_origins),
            "profile_store_path": app.state.profile_store.profile_file_path,
            "team_store_path": app.state.team_store.team_file_path,
        }

    @app.get("/launch/readiness")
    def launch_readiness(
        request: Request,
        include_paths: bool = Query(False, description="Incluir caminhos absolutos locais na resposta."),
        workspace_root: str | None = Query(default=None, description="Raiz opcional do workspace a auditar."),
        _: None = Depends(require_api_key),
    ) -> dict:
        readiness = build_launch_readiness_assessment(
            workspace_root=workspace_root or Path.cwd(),
            include_absolute_paths=include_paths,
            report_context={
                "report_purpose": "api_launch_readiness",
                "operator": _actor_from_request(request),
            },
        )
        summary = readiness.get("summary") or {}
        _audit_event(
            request,
            event_type="launch.readiness_viewed",
            status="ok" if summary.get("overall_launch_readiness_percent", 0) >= 85 else "warning",
            metadata={
                "overall_launch_readiness_percent": summary.get("overall_launch_readiness_percent"),
                "critical_gap_count": summary.get("critical_gap_count"),
            },
        )
        return readiness

    @app.post("/launch/readiness/export")
    def export_launch_readiness(
        request: Request,
        payload: LaunchReadinessExportRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_launch_readiness_package(
                output_dir=payload.output_dir,
                workspace_root=payload.workspace_root or Path.cwd(),
                include_absolute_paths=payload.include_absolute_paths,
                report_context=payload.report_context,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        summary = results.get("launch_readiness_summary") or {}
        _audit_event(
            request,
            event_type="launch.readiness_exported",
            status="ok" if summary.get("overall_launch_readiness_percent", 0) >= 85 else "warning",
            metadata={
                "output_dir": payload.output_dir,
                "overall_launch_readiness_percent": summary.get("overall_launch_readiness_percent"),
                "critical_gap_count": summary.get("critical_gap_count"),
            },
        )
        return results

    @app.get("/auth/status")
    def auth_status() -> dict:
        return {
            "auth_enabled": app.state.security.auth_enabled,
            "api_key_hint": mask_api_key(app.state.security.api_key),
        }

    @app.get("/users/context")
    def user_context(request: Request, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(request)
        _audit_event(request, event_type="users.context_viewed", status="ok")
        return {
            "active_profile": profile,
            "profile_file_path": app.state.profile_store.profile_file_path,
        }

    @app.get("/users/profiles")
    def list_profiles(request: Request, _: None = Depends(require_api_key)) -> dict:
        profiles = app.state.profile_store.list_profiles()
        _audit_event(
            request,
            event_type="users.profiles_listed",
            status="ok",
            metadata={"n_profiles": len(profiles)},
        )
        return {
            "n_profiles": len(profiles),
            "profile_file_path": app.state.profile_store.profile_file_path,
            "profiles": profiles,
        }

    @app.post("/users/profiles")
    def upsert_profile(http_request: Request, request: UserProfileRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            profile = app.state.profile_store.upsert_profile(
                profile_id=request.profile_id,
                display_name=request.display_name,
                role=request.role,
                institution=request.institution,
                email=request.email,
                metadata=request.metadata_payload,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="users.profile_upserted",
            status="ok",
            metadata={"target_profile_id": profile.get("profile_id")},
        )
        return {
            "profile": profile,
            "profile_file_path": app.state.profile_store.profile_file_path,
        }

    @app.get("/teams/context")
    def team_context(request: Request, _: None = Depends(require_api_key)) -> dict:
        team = _resolve_team_from_request(request, require_membership=True)
        _audit_event(request, event_type="teams.context_viewed", status="ok")
        return {
            "active_team": team,
            "team_file_path": app.state.team_store.team_file_path,
        }

    @app.get("/teams")
    def list_teams(request: Request, _: None = Depends(require_api_key)) -> dict:
        teams = app.state.team_store.list_teams()
        _audit_event(request, event_type="teams.listed", status="ok", metadata={"n_teams": len(teams)})
        return {
            "n_teams": len(teams),
            "team_file_path": app.state.team_store.team_file_path,
            "teams": teams,
        }

    @app.post("/teams")
    def upsert_team(http_request: Request, request: TeamRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        try:
            team = app.state.team_store.upsert_team(
                team_id=request.team_id,
                display_name=request.display_name,
                institution=request.institution,
                description=request.description,
                metadata=request.metadata_payload,
            )
            membership = None
            if not profile.get("is_guest"):
                membership = app.state.team_store.assign_member(
                    team_id=str(team["team_id"]),
                    profile_id=str(profile["profile_id"]),
                    team_role=request.owner_role or "owner",
                )
                team = app.state.team_store.mark_team_used(str(team["team_id"]), str(profile["profile_id"]))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="teams.upserted",
            status="ok",
            metadata={"target_team_id": team.get("team_id")},
        )
        return {
            "team": team,
            "membership": membership,
            "team_file_path": app.state.team_store.team_file_path,
        }

    @app.get("/teams/{team_id}/members")
    def list_team_members(request: Request, team_id: str, _: None = Depends(require_api_key)) -> dict:
        try:
            members = app.state.team_store.list_members(team_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _audit_event(
            request,
            event_type="teams.members_listed",
            status="ok",
            metadata={"team_id": team_id, "n_members": len(members)},
        )
        return {
            "team_id": team_id,
            "n_members": len(members),
            "members": members,
        }

    @app.post("/teams/{team_id}/members")
    def add_team_member(http_request: Request, team_id: str, request: TeamMembershipRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            app.state.profile_store.get_profile(request.profile_id)
            membership = app.state.team_store.assign_member(
                team_id=team_id,
                profile_id=request.profile_id,
                team_role=request.team_role,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="teams.member_assigned",
            status="ok",
            metadata={"team_id": team_id, "target_profile_id": request.profile_id},
        )
        return {
            "membership": membership,
            "team_id": team_id,
        }

    @app.get("/jobs")
    def list_jobs(request: Request, limit: int = Query(25, ge=1, le=200), _: None = Depends(require_api_key)) -> dict:
        jobs = app.state.job_manager.list_jobs(limit=limit)
        _audit_event(request, event_type="jobs.listed", status="ok", metadata={"limit": limit, "n_jobs": len(jobs)})
        return {
            "job_root": str(app.state.job_manager.root_dir),
            "n_jobs": len(jobs),
            "jobs": jobs,
        }

    @app.get("/jobs/{job_id}")
    def get_job(request: Request, job_id: str, _: None = Depends(require_api_key)) -> dict:
        try:
            job = app.state.job_manager.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _audit_event(request, event_type="jobs.detail_viewed", status="ok", job_id=job_id)
        return job

    @app.get("/jobs/{job_id}/report")
    def get_job_report(request: Request, job_id: str, _: None = Depends(require_api_key)):
        try:
            job = app.state.job_manager.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        report_path = Path(str(job.get("report_path") or ""))
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Relatorio do job nao encontrado.")
        _audit_event(request, event_type="jobs.report_downloaded", status="ok", job_id=job_id)
        return FileResponse(path=report_path, media_type="text/markdown", filename=report_path.name)

    @app.get("/audit/events")
    def list_audit_events(request: Request, limit: int = Query(500, ge=1, le=500), _: None = Depends(require_api_key)) -> dict:
        events = app.state.audit_logger.list_events(limit=limit)
        _audit_event(request, event_type="audit.listed", status="ok", metadata={"limit": limit, "n_events": len(events)})
        return {
            "audit_file_path": app.state.audit_logger.audit_file_path,
            "n_events": len(events),
            "events": events,
        }

    @app.get("/impact/pilot/sessions")
    def list_pilot_sessions(
        request: Request,
        study_name: str | None = Query(default=None),
        _: None = Depends(require_api_key),
    ) -> dict:
        sessions = app.state.pilot_ops_store.list_sessions(study_name=study_name)
        _audit_event(
            request,
            event_type="impact.pilot_sessions_listed",
            status="ok",
            metadata={"study_name": study_name, "n_sessions": len(sessions)},
        )
        return {
            "registry_root": str(app.state.pilot_ops_store.root_dir),
            "study_name": study_name,
            "n_sessions": len(sessions),
            "sessions": sessions,
        }

    @app.post("/impact/pilot/sessions")
    def upsert_pilot_session(http_request: Request, request: PilotSessionRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()
        payload.setdefault("operator_name", profile.get("display_name"))
        payload.setdefault("institution", team.get("institution") or profile.get("institution"))
        payload.setdefault("team_name", team.get("display_name"))
        try:
            session = app.state.pilot_ops_store.upsert_session(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="impact.pilot_session_upserted",
            status="ok",
            metadata={"session_id": session.get("session_id"), "study_name": session.get("study_name"), "status": session.get("status")},
        )
        dashboard = build_translational_impact_dashboard(
            session_rows=app.state.pilot_ops_store.list_sessions(study_name=session.get("study_name") or None),
            feedback_rows=app.state.pilot_ops_store.list_feedback(study_name=session.get("study_name") or None),
            study_name=session.get("study_name") or None,
        )
        return {
            "registry_root": str(app.state.pilot_ops_store.root_dir),
            "session": session,
            "dashboard": dashboard,
        }

    @app.post("/impact/pilot/feedback")
    def add_pilot_feedback(http_request: Request, request: PilotFeedbackRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        payload = request.model_dump()
        payload.setdefault("operator_name", profile.get("display_name"))
        payload.setdefault("role", profile.get("role"))
        try:
            feedback = app.state.pilot_ops_store.add_feedback(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="impact.pilot_feedback_added",
            status="ok",
            metadata={"session_id": feedback.get("session_id"), "study_name": feedback.get("study_name")},
        )
        dashboard = build_translational_impact_dashboard(
            session_rows=app.state.pilot_ops_store.list_sessions(study_name=feedback.get("study_name") or None),
            feedback_rows=app.state.pilot_ops_store.list_feedback(study_name=feedback.get("study_name") or None),
            study_name=feedback.get("study_name") or None,
        )
        return {
            "registry_root": str(app.state.pilot_ops_store.root_dir),
            "feedback": feedback,
            "dashboard": dashboard,
        }

    @app.get("/impact/translational/dashboard")
    def get_translational_dashboard(
        request: Request,
        study_name: str | None = Query(default=None),
        _: None = Depends(require_api_key),
    ) -> dict:
        dashboard = build_translational_impact_dashboard(
            session_rows=app.state.pilot_ops_store.list_sessions(study_name=study_name),
            feedback_rows=app.state.pilot_ops_store.list_feedback(study_name=study_name),
            study_name=study_name,
        )
        _audit_event(
            request,
            event_type="impact.dashboard_viewed",
            status="ok",
            metadata={"study_name": study_name, "n_sessions": dashboard.get("summary", {}).get("n_sessions")},
        )
        return {
            "registry_root": str(app.state.pilot_ops_store.root_dir),
            "study_name": study_name,
            "dashboard": dashboard,
        }

    @app.get("/analytics/team-dashboard")
    def get_team_dashboard(
        request: Request,
        recent_limit: int = Query(10, ge=1, le=50),
        audit_limit: int = Query(500, ge=10, le=5000),
        _: None = Depends(require_api_key),
    ) -> dict:
        team = _resolve_team_from_request(request, require_membership=True)
        dashboard = build_team_dashboard(
            team=team,
            job_manager=app.state.job_manager,
            audit_logger=app.state.audit_logger,
            recent_limit=recent_limit,
            audit_limit=audit_limit,
        )
        _audit_event(
            request,
            event_type="analytics.team_dashboard_viewed",
            status="ok",
            metadata={"recent_limit": recent_limit, "audit_limit": audit_limit},
        )
        return dashboard

    @app.get("/roadmap/progress")
    def get_roadmap_progress(request: Request, _: None = Depends(require_api_key)) -> dict:
        roadmap = build_roadmap_progress()
        _audit_event(
            request,
            event_type="roadmap.progress_viewed",
            status="ok",
            metadata={"overall_progress_percent": roadmap.get("summary", {}).get("overall_progress_percent")},
        )
        return roadmap

    @app.post("/science/gene-expansion")
    def build_gene_expansion(http_request: Request, request: GeneExpansionRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_gene_expansion_assessment(
                clinvar_variant_summary_path=request.clinvar_variant_summary_path,
                mavedb_dump_path=request.mavedb_dump_path,
                output_dir=request.output_dir,
                exclude_genes=request.exclude_genes,
                top_k=request.top_k,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_gene_expansion_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.gene_expansion_completed",
            status="ok" if summary.get("recommended_gene_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "recommended_gene_count": summary.get("recommended_gene_count"),
                "top_candidate_gene": (summary.get("top_candidate_genes") or [None])[0],
            },
        )
        return response

    @app.post("/science/independent-data-expansion")
    def build_independent_data_expansion(
        http_request: Request,
        request: IndependentDataExpansionRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_independent_data_expansion_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_independent_data_expansion_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.independent_data_expansion_completed",
            status="ok" if summary.get("ready_for_more_real_data_training") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "database_count": summary.get("database_count"),
                "independent_data_expansion_percent": summary.get("independent_data_expansion_percent"),
            },
        )
        return response

    @app.post("/science/independent-data-staging-closure")
    def build_independent_data_staging_closure(
        http_request: Request,
        request: IndependentDataStagingClosureRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_independent_data_staging_closure_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_independent_data_staging_closure_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.independent_data_staging_closure_completed",
            status="ok" if summary.get("ready_for_next_training_round") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "ready_source_count": summary.get("ready_source_count"),
                "line_level_real_data_execution_percent": summary.get("line_level_real_data_execution_percent"),
                "independent_data_staging_closure_percent": summary.get("independent_data_staging_closure_percent"),
            },
        )
        return response

    @app.post("/science/independent-open-source-autostage")
    def build_independent_open_source_autostage(
        http_request: Request,
        request: IndependentOpenSourceAutostageRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_independent_open_source_autostage_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_independent_open_source_autostage_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.independent_open_source_autostage_completed",
            status="ok" if summary.get("ready_for_staging_closure_refresh") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "staged_source_count": summary.get("staged_source_count"),
                "attempted_source_count": summary.get("attempted_source_count"),
                "autostaging_readiness_percent": summary.get("autostaging_readiness_percent"),
            },
        )
        return response

    @app.post("/science/biological-discovery")
    def build_biological_discovery(http_request: Request, request: BiologicalDiscoveryRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_biological_discovery_package(
                real_data_manifest_path=request.real_data_manifest_path,
                output_dir=request.output_dir,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_biological_discovery_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.biological_discovery_completed",
            status="ok" if summary.get("hotspot_count") or summary.get("hypothesis_variant_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "hotspot_count": summary.get("hotspot_count"),
                "hypothesis_variant_count": summary.get("hypothesis_variant_count"),
            },
        )
        return response

    @app.post("/science/multigene-rollout")
    def build_multigene_rollout(http_request: Request, request: MultigeneRolloutRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_multigene_rollout_plan(
                gene_expansion_manifest_path=request.gene_expansion_manifest_path,
                prime_intelligence_manifest_path=request.prime_intelligence_manifest_path,
                output_dir=request.output_dir,
                max_phase_1=request.max_phase_1,
                max_phase_2=request.max_phase_2,
                max_total_genes=request.max_total_genes,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_multigene_rollout_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.multigene_rollout_completed",
            status="ok" if summary.get("phase_1_gene_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "phase_1_gene_count": summary.get("phase_1_gene_count"),
                "prime_top_candidate_gene": summary.get("prime_top_candidate_gene"),
            },
        )
        return response

    @app.post("/science/multigene-study-factory")
    def build_multigene_study_factory(http_request: Request, request: MultigeneStudyFactoryRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_multigene_study_factory(
                rollout_manifest_path=request.rollout_manifest_path,
                output_dir=request.output_dir,
                workspace_root=request.workspace_root,
                include_phases=request.include_phases,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_multigene_study_factory_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.multigene_study_factory_completed",
            status="ok" if summary.get("total_scaffolded_genes") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "workspace_root": summary.get("workspace_root"),
                "total_scaffolded_genes": summary.get("total_scaffolded_genes"),
            },
        )
        return response

    @app.post("/science/protein-impact")
    def build_protein_impact(http_request: Request, request: ProteinImpactRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_protein_impact_package(
                biological_discovery_manifest_path=request.biological_discovery_manifest_path,
                output_dir=request.output_dir,
                max_modeling_variants=request.max_modeling_variants,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_protein_impact_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.protein_impact_completed",
            status="ok" if summary.get("modeling_queue_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "modeling_queue_count": summary.get("modeling_queue_count"),
                "prime_mechanistic_alignment_percent": summary.get("prime_mechanistic_alignment_percent"),
            },
        )
        return response

    @app.post("/science/multigene-annotation-enrichment")
    def build_multigene_annotation_enrichment(
        http_request: Request,
        request: MultigeneAnnotationEnrichmentRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_multigene_annotation_enrichment_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_multigene_annotation_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.multigene_annotation_enrichment_completed",
            status="ok" if summary.get("variant_row_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "variant_row_count": summary.get("variant_row_count"),
                "line_level_annotation_readiness_percent": summary.get("line_level_annotation_readiness_percent"),
            },
        )
        return response

    @app.post("/science/public-sync-closure")
    def build_public_sync_closure(
        http_request: Request,
        request: PublicSyncClosureRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_public_sync_closure_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_public_sync_closure_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.public_sync_closure_completed",
            status="ok" if summary.get("ready_for_public_sync_completion") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "public_sync_closure_percent": summary.get("public_sync_closure_percent"),
                "gnomad_pending_or_retry_count": summary.get("gnomad_pending_or_retry_count"),
            },
        )
        return response

    @app.post("/science/gnomad-gene-subset")
    def build_gnomad_gene_subset_endpoint(
        http_request: Request,
        request: GnomadGeneSubsetRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_gnomad_gene_subset(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_gnomad_gene_subset_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.gnomad_gene_subset_completed",
            status="ok" if summary.get("query_success_percent", 0) >= 80 else "warning",
            metadata={
                "output_dir": request.output_dir,
                "variant_row_count": summary.get("variant_row_count"),
                "query_success_percent": summary.get("query_success_percent"),
            },
        )
        return response

    @app.post("/science/brca1-engine-execution")
    def build_brca1_engine_execution(
        http_request: Request,
        request: Brca1EngineExecutionRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_brca1_engine_execution_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_brca1_engine_execution_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.brca1_engine_execution_completed",
            status="ok" if summary.get("ready_to_execute_target_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "execution_readiness_percent": summary.get("execution_readiness_percent"),
                "ready_to_execute_target_count": summary.get("ready_to_execute_target_count"),
            },
        )
        return response

    @app.post("/science/brca1-fragment-preparation")
    def build_brca1_fragment_preparation(
        http_request: Request,
        request: Brca1FragmentPreparationRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_brca1_fragment_preparation_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_brca1_fragment_preparation_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.brca1_fragment_preparation_completed",
            status="ok" if summary.get("prepared_fragment_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "prepared_fragment_count": summary.get("prepared_fragment_count"),
                "xtb_completed_count": summary.get("xtb_completed_count"),
                "fragment_preparation_readiness_percent": summary.get("fragment_preparation_readiness_percent"),
            },
        )
        return response

    @app.post("/science/brca1-paired-mutant-execution")
    def build_brca1_paired_mutant_execution(
        http_request: Request,
        request: Brca1PairedMutantExecutionRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_brca1_paired_mutant_execution_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_brca1_paired_mutant_execution_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.brca1_paired_mutant_execution_completed",
            status="ok" if summary.get("draft_mutant_coordinate_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "draft_mutant_coordinate_count": summary.get("draft_mutant_coordinate_count"),
                "paired_xtb_completed_count": summary.get("paired_xtb_completed_count"),
                "paired_mutant_execution_readiness_percent": summary.get("paired_mutant_execution_readiness_percent"),
            },
        )
        return response

    @app.post("/science/brca1-mutant-geometry-qc")
    def build_brca1_mutant_geometry_qc(
        http_request: Request,
        request: Brca1MutantGeometryQcRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_brca1_mutant_geometry_qc_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_brca1_mutant_geometry_qc_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.brca1_mutant_geometry_qc_completed",
            status="ok" if summary.get("reviewed_pair_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "reviewed_pair_count": summary.get("reviewed_pair_count"),
                "geometry_pass_count": summary.get("geometry_pass_count"),
                "xtb_optimization_completed_count": summary.get("xtb_optimization_completed_count"),
            },
        )
        return response

    @app.post("/science/quantum-proteomics")
    def build_quantum_proteomics(http_request: Request, request: QuantumProteomicsRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_quantum_proteomics_package(
                protein_impact_manifest_path=request.protein_impact_manifest_path,
                output_dir=request.output_dir,
                max_quantum_targets=request.max_quantum_targets,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_quantum_proteomics_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.quantum_proteomics_completed",
            status="ok" if summary.get("quantum_target_count") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "quantum_target_count": summary.get("quantum_target_count"),
                "mean_quantum_priority_score_percent": summary.get("mean_quantum_priority_score_percent"),
            },
        )
        return response

    @app.post("/science/prospective-validation-closure")
    def build_prospective_validation_closure(
        http_request: Request,
        request: ProspectiveValidationClosureRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_prospective_validation_closure_package(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_prospective_validation_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.prospective_validation_closure_completed",
            status="ok" if summary.get("prospective_validation_readiness_percent") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "prospective_validation_readiness_percent": summary.get("prospective_validation_readiness_percent"),
                "experimental_confirmation_completed_percent": summary.get("experimental_confirmation_completed_percent"),
            },
        )
        return response

    @app.post("/science/validation-credibility-closure")
    def build_validation_credibility_closure(http_request: Request, request: ValidationCredibilityClosureRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = export_validation_credibility_closure(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_validation_credibility_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.validation_credibility_closure_completed",
            status="ok" if summary.get("ready_for_stronger_external_validation") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "scientific_credibility_percent": summary.get("scientific_credibility_percent"),
                "software_evidence_closure_percent": summary.get("software_evidence_closure_percent"),
            },
        )
        return response

    @app.post("/science/development-progress")
    def build_development_progress(
        http_request: Request,
        request: DevelopmentProgressRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            results = export_development_progress_dashboard(**request.model_dump())
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_development_progress_response(results)
        summary = response.get("summary") or {}
        _audit_event(
            http_request,
            event_type="science.development_progress_completed",
            status="ok",
            metadata={
                "output_dir": request.output_dir,
                "overall_progress_percent": summary.get("overall_progress_percent"),
                "areas_above_80_percent": summary.get("areas_above_80_percent"),
            },
        )
        return response

    @app.get("/models")
    def list_models(
        request: Request,
        model_dir: str = Query(..., description="Diretorio contendo model_registry.csv"),
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            registry_df = load_model_registry(model_dir)
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(request, event_type="models.listed", status="ok", metadata={"model_dir": model_dir, "n_models": len(registry_df)})
        return {
            "model_dir": model_dir,
            "n_models": int(len(registry_df)),
            "models": registry_df.to_dict(orient="records"),
        }

    @app.post("/releases/manifest/load")
    def inspect_release_manifest(http_request: Request, request: ReleaseManifestRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            manifest = load_release_manifest(request.manifest_path)
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        sources = manifest.get("sources") or []
        artifact_fingerprints = manifest.get("artifact_fingerprints") or {}
        summary = {
            "release_id": manifest.get("release_id"),
            "release_type": manifest.get("release_type"),
            "generated_at": manifest.get("generated_at"),
            "n_sources": int(len(sources)),
            "source_types": sorted({str(item.get("source_type")) for item in sources if item.get("source_type")}),
            "n_rows": manifest.get("n_rows"),
            "n_columns": manifest.get("n_columns"),
            "n_artifacts": int(len(artifact_fingerprints)),
        }
        _audit_event(
            http_request,
            event_type="release.manifest_loaded",
            status="ok",
            metadata={"manifest_path": request.manifest_path, "release_type": manifest.get("release_type")},
        )
        return {
            "manifest_path": manifest.get("manifest_path", request.manifest_path),
            "summary": summary,
            "manifest": manifest,
        }

    def _load_public_catalog_context(config_path: str, output_dir: str | None) -> tuple[dict, dict, dict, dict]:
        ingestion = ingest_sources_from_config(config_path=config_path, output_dir=output_dir)
        assessment = ingestion.get("public_source_assessment") or {}
        sync_plan = ingestion.get("public_source_sync_plan") or {}
        sync_history = (
            load_public_source_sync_history(
                output_dir=output_dir,
                public_source_assessment=assessment,
                public_source_sync_plan=sync_plan,
            )
            if output_dir
            else {}
        )
        return ingestion, assessment, sync_plan, sync_history

    @app.post("/public-sources/catalog/inspect")
    def inspect_public_source_catalog(http_request: Request, request: PublicSourceCatalogRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            ingestion, assessment, sync_plan, sync_history = _load_public_catalog_context(
                config_path=request.config_path,
                output_dir=request.output_dir,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        response = {
            "config_path": request.config_path,
            "summary": assessment.get("summary") or {},
            "sources": assessment.get("sources") or [],
            "warnings": assessment.get("warnings") or [],
            "markdown_report": assessment.get("markdown_report") or "",
            "sync_plan": sync_plan,
            "sync_history": sync_history,
            "benchmark_readiness": (sync_history.get("benchmark_readiness") or {}),
            "output_paths": {
                key: value
                for key, value in (ingestion.get("output_paths") or {}).items()
                if str(key).startswith("public_source_catalog_report")
                or str(key).startswith("public_source_sync_plan")
                or str(key).startswith("data_release_")
                or str(key) in {"integrated_sources", "source_ingestion_report"}
            },
        }
        _audit_event(
            http_request,
            event_type="public_sources.catalog_inspected",
            status="ok",
            metadata={
                "config_path": request.config_path,
                "n_recognized_public_sources": response["summary"].get("n_recognized_public_sources"),
                "release_coverage_percent": response["summary"].get("release_coverage_percent"),
                "sync_readiness_percent": (response.get("benchmark_readiness") or {}).get("summary", {}).get("sync_readiness_percent"),
            },
        )
        return response

    @app.post("/public-sources/catalog/bootstrap")
    def bootstrap_public_source_catalog(http_request: Request, request: PublicSourceBootstrapRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            ingestion, assessment, sync_plan, sync_history = _load_public_catalog_context(
                config_path=request.config_path,
                output_dir=request.output_dir,
            )
            bundle = build_public_source_bootstrap_bundle(
                config_path=request.config_path,
                public_source_assessment=assessment,
                public_source_sync_plan=sync_plan,
                output_dir=request.output_dir,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        _audit_event(
            http_request,
            event_type="public_sources.bootstrap_generated",
            status="ok",
            metadata={
                "config_path": request.config_path,
                "output_dir": request.output_dir,
                "n_bundle_items": bundle.get("summary", {}).get("n_bundle_items"),
            },
        )
        return {
            "config_path": request.config_path,
            "output_dir": request.output_dir,
            "bundle": bundle,
            "catalog_summary": assessment.get("summary") or {},
            "sync_summary": sync_plan.get("summary") or {},
            "sync_history": sync_history,
            "benchmark_readiness": (sync_history.get("benchmark_readiness") or {}),
            "output_paths": ingestion.get("output_paths") or {},
        }

    @app.post("/public-sources/catalog/bootstrap/execute")
    def execute_public_source_catalog_bootstrap(
        http_request: Request,
        request: PublicSourceBootstrapExecutionRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            ingestion, assessment, sync_plan, _ = _load_public_catalog_context(
                config_path=request.config_path,
                output_dir=request.output_dir,
            )
            execution = execute_public_source_bootstrap_bundle(
                config_path=request.config_path,
                public_source_assessment=assessment,
                public_source_sync_plan=sync_plan,
                output_dir=request.output_dir,
                dry_run=request.dry_run,
                selected_sources=request.selected_sources,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        _audit_event(
            http_request,
            event_type="public_sources.bootstrap_executed",
            status="ok" if not execution.get("summary", {}).get("n_failed_items") else "warning",
            metadata={
                "config_path": request.config_path,
                "output_dir": request.output_dir,
                "dry_run": request.dry_run,
                "n_items": execution.get("summary", {}).get("n_items"),
                "n_failed_items": execution.get("summary", {}).get("n_failed_items"),
            },
        )
        return {
            "config_path": request.config_path,
            "output_dir": request.output_dir,
            "catalog_summary": assessment.get("summary") or {},
            "sync_summary": sync_plan.get("summary") or {},
            "execution": execution,
            "output_paths": ingestion.get("output_paths") or {},
        }

    @app.post("/public-sources/catalog/resolve")
    def resolve_public_source_catalog(
        http_request: Request,
        request: PublicSourceResolveRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            resolution = export_public_source_resolution(
                config_path=request.config_path,
                bootstrap_output_dir=request.bootstrap_output_dir,
                output_dir=request.output_dir,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        summary = (resolution.get("resolution") or {}).get("summary") or {}
        _audit_event(
            http_request,
            event_type="public_sources.catalog_resolved",
            status="ok" if summary.get("ready_for_resolved_config") else "warning",
            metadata={
                "config_path": request.config_path,
                "bootstrap_output_dir": request.bootstrap_output_dir,
                "output_dir": request.output_dir,
                "overall_resolution_percent": summary.get("overall_resolution_percent"),
                "n_blocked_sources": summary.get("n_blocked_sources"),
            },
        )
        return {
            "config_path": request.config_path,
            "bootstrap_output_dir": request.bootstrap_output_dir,
            "output_dir": request.output_dir,
            "summary": summary,
            "recommended_actions": (resolution.get("resolution") or {}).get("recommended_actions") or [],
            "resolved_config_path": resolution.get("resolved_config_path"),
            "public_source_resolution_manifest_path": resolution.get("public_source_resolution_manifest_path"),
            "public_source_resolution_report_markdown_path": resolution.get("public_source_resolution_report_markdown_path"),
            "public_source_resolution_sources_path": resolution.get("public_source_resolution_sources_path"),
            "source_rows": (resolution.get("resolution") or {}).get("source_rows") or [],
        }

    @app.post("/public-sources/continuous-learning/build")
    def build_public_source_continuous_learning(
        http_request: Request,
        request: ContinuousLearningRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            bundle = export_continuous_learning_package(
                config_path=request.config_path,
                output_dir=request.output_dir,
                mode=request.mode,
                high_confidence_only=request.high_confidence_only,
                model_families=request.model_families,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        _audit_event(
            http_request,
            event_type="public_sources.continuous_learning_built",
            status="ok",
            metadata={
                "config_path": request.config_path,
                "output_dir": request.output_dir,
                "continuous_learning_readiness_percent": (bundle.get("summary") or {}).get("continuous_learning_readiness_percent"),
                "script_ready_source_count": (bundle.get("summary") or {}).get("script_ready_source_count"),
            },
        )
        return {
            "config_path": request.config_path,
            "output_dir": request.output_dir,
            "summary": bundle.get("summary") or {},
            "benchmark_readiness": bundle.get("benchmark_readiness") or {},
            "bootstrap_bundle": bundle.get("bootstrap_bundle") or {},
            "continuous_learning_manifest_path": bundle.get("continuous_learning_manifest_path"),
            "continuous_learning_report_markdown_path": bundle.get("continuous_learning_report_markdown_path"),
            "continuous_learning_report_html_path": bundle.get("continuous_learning_report_html_path"),
            "continuous_learning_connector_catalog_path": bundle.get("continuous_learning_connector_catalog_path"),
            "continuous_learning_automation_matrix_path": bundle.get("continuous_learning_automation_matrix_path"),
            "continuous_learning_retraining_policy_path": bundle.get("continuous_learning_retraining_policy_path"),
            "continuous_learning_governance_lanes_path": bundle.get("continuous_learning_governance_lanes_path"),
            "continuous_learning_runner_path": bundle.get("continuous_learning_runner_path"),
        }

    @app.get("/public-sources/catalog/bootstrap/history")
    def public_source_bootstrap_history(
        request: Request,
        output_dir: str = Query(..., description="Diretorio do bootstrap publico"),
        config_path: str | None = Query(default=None, description="Catalogo TOML opcional para enriquecer a leitura"),
        limit: int = Query(50, ge=1, le=500),
        _: None = Depends(require_api_key),
    ) -> dict:
        assessment = {}
        sync_plan = {}
        if config_path:
            try:
                _, assessment, sync_plan, _ = _load_public_catalog_context(config_path=config_path, output_dir=output_dir)
            except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        history = load_public_source_sync_history(
            output_dir=output_dir,
            public_source_assessment=assessment,
            public_source_sync_plan=sync_plan,
            limit=limit,
        )
        _audit_event(
            request,
            event_type="public_sources.bootstrap_history_viewed",
            status="ok",
            metadata={
                "output_dir": output_dir,
                "limit": limit,
                "n_runs": (history.get("summary") or {}).get("n_runs"),
            },
        )
        return {
            "output_dir": output_dir,
            "config_path": config_path,
            "history": history,
        }

    @app.post("/study/public-config/resolve")
    def resolve_study_public_config(
        http_request: Request,
        request: StudyPublicResolveRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            resolution = export_study_public_config_resolution(
                config_path=request.config_path,
                output_dir=request.output_dir,
                bootstrap_root_dir=request.bootstrap_root_dir,
                delivery_dir=request.delivery_dir,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        _audit_event(
            http_request,
            event_type="study.public_config_resolved",
            status="ok" if resolution.get("summary", {}).get("ready_for_resolved_study") else "warning",
            metadata={
                "config_path": request.config_path,
                "output_dir": request.output_dir,
                "bootstrap_root_dir": request.bootstrap_root_dir,
                "delivery_dir": request.delivery_dir,
                "overall_resolution_percent": resolution.get("summary", {}).get("overall_resolution_percent"),
            },
        )
        return {
            "config_path": request.config_path,
            "output_dir": request.output_dir,
            "bootstrap_root_dir": request.bootstrap_root_dir or request.output_dir,
            "delivery_dir": request.delivery_dir,
            "summary": resolution.get("summary") or {},
            "recommended_actions": resolution.get("recommended_actions") or [],
            "resolved_study_config_path": resolution.get("resolved_study_config_path"),
            "study_public_config_resolution_manifest_path": resolution.get("study_public_config_resolution_manifest_path"),
            "study_public_config_resolution_report_markdown_path": resolution.get("study_public_config_resolution_report_markdown_path"),
            "study_public_config_resolution_cohorts_path": resolution.get("study_public_config_resolution_cohorts_path"),
            "study_cohort_freeze_manifest_path": resolution.get("study_cohort_freeze_manifest_path"),
            "study_cohort_freeze_markdown_path": resolution.get("study_cohort_freeze_markdown_path"),
            "study_cohort_freeze_cohorts_path": resolution.get("study_cohort_freeze_cohorts_path"),
            "study_cohort_freeze_sources_path": resolution.get("study_cohort_freeze_sources_path"),
            "study_real_data_handoff_manifest_path": resolution.get("study_real_data_handoff_manifest_path"),
            "study_real_data_handoff_markdown_path": resolution.get("study_real_data_handoff_markdown_path"),
            "study_real_data_handoff_html_path": resolution.get("study_real_data_handoff_html_path"),
            "study_real_data_handoff_cohorts_path": resolution.get("study_real_data_handoff_cohorts_path"),
            "study_real_data_handoff_tasks_path": resolution.get("study_real_data_handoff_tasks_path"),
            "study_real_data_handoff_autofill_manifest_path": resolution.get("study_real_data_handoff_autofill_manifest_path"),
            "study_real_data_handoff_autofill_markdown_path": resolution.get("study_real_data_handoff_autofill_markdown_path"),
            "study_real_data_handoff_autofill_html_path": resolution.get("study_real_data_handoff_autofill_html_path"),
            "study_real_data_handoff_autofill_tracker_path": resolution.get("study_real_data_handoff_autofill_tracker_path"),
            "study_real_data_handoff_autofill_matches_path": resolution.get("study_real_data_handoff_autofill_matches_path"),
            "study_real_data_handoff_autofill_inventory_path": resolution.get("study_real_data_handoff_autofill_inventory_path"),
            "study_real_data_handoff_tracker_path": resolution.get("study_real_data_handoff_tracker_path"),
            "study_real_data_handoff_reconciliation_manifest_path": resolution.get("study_real_data_handoff_reconciliation_manifest_path"),
            "study_real_data_handoff_reconciliation_markdown_path": resolution.get("study_real_data_handoff_reconciliation_markdown_path"),
            "study_real_data_handoff_reconciliation_html_path": resolution.get("study_real_data_handoff_reconciliation_html_path"),
            "study_real_data_handoff_reconciliation_tasks_path": resolution.get("study_real_data_handoff_reconciliation_tasks_path"),
            "study_real_data_candidate_config_path": resolution.get("study_real_data_candidate_config_path"),
            "study_real_data_handoff_application_manifest_path": resolution.get("study_real_data_handoff_application_manifest_path"),
            "study_real_data_handoff_application_markdown_path": resolution.get("study_real_data_handoff_application_markdown_path"),
            "study_real_data_handoff_application_html_path": resolution.get("study_real_data_handoff_application_html_path"),
            "study_real_data_handoff_application_sources_path": resolution.get("study_real_data_handoff_application_sources_path"),
            "study_real_data_candidate_promotion_manifest_path": resolution.get("study_real_data_candidate_promotion_manifest_path"),
            "study_real_data_candidate_promotion_markdown_path": resolution.get("study_real_data_candidate_promotion_markdown_path"),
            "study_real_data_candidate_promotion_html_path": resolution.get("study_real_data_candidate_promotion_html_path"),
            "study_real_data_candidate_promotion_criteria_path": resolution.get("study_real_data_candidate_promotion_criteria_path"),
            "study_real_data_candidate_promotion_blockers_path": resolution.get("study_real_data_candidate_promotion_blockers_path"),
        }

    @app.post("/study/real-data-handoff/autofill")
    def autofill_real_data_handoff(
        http_request: Request,
        request: StudyRealDataHandoffAutofillRequest,
        _: None = Depends(require_api_key),
    ) -> dict:
        try:
            exported = export_real_data_handoff_autofill(
                study_name=request.study_name,
                handoff_tasks_path=request.handoff_tasks_path,
                delivery_dir=request.delivery_dir,
                tracker_path=request.tracker_path,
                output_dir=request.output_dir,
                report_context=request.report_context,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        summary = exported.get("study_real_data_handoff_autofill_summary") or {}
        _audit_event(
            http_request,
            event_type="study.real_data_handoff_autofilled",
            status="ok" if summary.get("ready_for_reconciliation_rerun") else "warning",
            metadata={
                "study_name": request.study_name,
                "handoff_tasks_path": request.handoff_tasks_path,
                "tracker_path": request.tracker_path,
                "delivery_dir": request.delivery_dir,
                "output_dir": request.output_dir,
                "autofill_percent": summary.get("overall_handoff_autofill_percent"),
            },
        )
        return {
            "study_name": request.study_name,
            "handoff_tasks_path": request.handoff_tasks_path,
            "tracker_path": request.tracker_path,
            "delivery_dir": request.delivery_dir,
            "output_dir": request.output_dir,
            "summary": summary,
            "recommended_actions": (exported.get("study_real_data_handoff_autofill") or {}).get("recommended_actions") or [],
            "study_real_data_handoff_autofill_manifest_path": exported.get("study_real_data_handoff_autofill_manifest_path"),
            "study_real_data_handoff_autofill_markdown_path": exported.get("study_real_data_handoff_autofill_markdown_path"),
            "study_real_data_handoff_autofill_html_path": exported.get("study_real_data_handoff_autofill_html_path"),
            "study_real_data_handoff_autofill_tracker_path": exported.get("study_real_data_handoff_autofill_tracker_path"),
            "study_real_data_handoff_autofill_matches_path": exported.get("study_real_data_handoff_autofill_matches_path"),
            "study_real_data_handoff_autofill_inventory_path": exported.get("study_real_data_handoff_autofill_inventory_path"),
        }

    @app.post("/predict/variant")
    def predict_variant(http_request: Request, request: VariantPredictionRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            result = score_variant_with_model(
                model_dir=request.model_dir,
                experiment=request.experiment,
                gene=request.gene,
                hgvs_p=request.hgvs_p,
                mode=request.mode,
                feature_payload=request.feature_payload,
                metadata_payload=request.metadata_payload,
                threshold=request.threshold,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="predict.single",
            status="ok",
            metadata={"experiment": request.experiment, "gene": request.gene, "hgvs_p": request.hgvs_p},
        )
        return result

    @app.post("/predict/batch")
    def predict_variant_batch(http_request: Request, request: BatchVariantPredictionRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_profile_id", profile.get("profile_id"))
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", profile.get("institution"))
        report_context.setdefault("team_id", team.get("team_id"))
        report_context.setdefault("team_name", team.get("display_name"))
        try:
            result = score_variant_batch_with_model(
                model_dir=request.model_dir,
                experiment=request.experiment,
                variants=[item.model_dump() for item in request.variants],
                default_mode=request.default_mode,
                threshold=request.threshold,
                report_title=request.report_title,
                report_context=report_context,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through HTTP response
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="predict.batch",
            status="ok",
            metadata={
                "experiment": request.experiment,
                "n_variants": len(request.variants),
                "report_title": request.report_title,
            },
        )
        return result

    @app.post("/train/source-config")
    def train_from_sources(http_request: Request, request: SourceTrainingRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            results = train_from_source_config(
                config_path=request.config_path,
                output_dir=request.output_dir,
                mode=request.mode,
                keep_metadata=request.keep_metadata,
                high_confidence_only=request.high_confidence_only,
                model_families=request.model_families,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_training_response(results)
        response["output_dir"] = request.output_dir
        _audit_event(http_request, event_type="train.sync_completed", status="ok", metadata={"output_dir": request.output_dir})
        return response

    @app.post("/jobs/train/source-config")
    def enqueue_train_from_sources(http_request: Request, request: SourceTrainingRequest, _: None = Depends(require_api_key)) -> dict:
        payload = request.model_dump()
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)

        def _runner(job_payload: dict) -> dict:
            results = train_from_source_config(**job_payload)
            response = _summarize_training_response(results)
            response["output_dir"] = job_payload.get("output_dir")
            return response

        job = app.state.job_manager.submit_job(
            job_type="train_source_config",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(http_request, event_type="train.job_enqueued", status="queued", job_id=job["job_id"], metadata={"output_dir": request.output_dir})
        return job

    @app.post("/study/preflight")
    def run_study_preflight_endpoint(http_request: Request, request: StudyPreflightRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        try:
            export_paths = export_study_preflight(
                config_path=request.config_path,
                output_dir=request.output_dir,
                report_context=report_context,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        preflight = export_paths.get("preflight") or {}
        _audit_event(
            http_request,
            event_type="study.preflight_completed",
            status="ok",
            metadata={"config_path": request.config_path, "output_dir": request.output_dir},
        )
        return {
            "output_dir": request.output_dir,
            "summary": preflight.get("summary") or {},
            "warnings": preflight.get("warnings") or [],
            "recommended_actions": preflight.get("recommended_actions") or [],
            "study_preflight_manifest_path": export_paths.get("study_preflight_manifest_path"),
            "study_preflight_report_markdown_path": export_paths.get("study_preflight_report_markdown_path"),
            "study_preflight_report_html_path": export_paths.get("study_preflight_report_html_path"),
            "study_preflight_criteria_path": export_paths.get("study_preflight_criteria_path"),
            "study_preflight_cohorts_path": export_paths.get("study_preflight_cohorts_path"),
            "study_preflight_independence_pairs_path": export_paths.get("study_preflight_independence_pairs_path"),
        }

    @app.post("/study/bundle/inspect")
    def inspect_study_bundle_endpoint(http_request: Request, request: StudyBundleInspectRequest, _: None = Depends(require_api_key)) -> dict:
        try:
            inspection = inspect_study_bundle(request.result_dir)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="study.bundle_inspected",
            status="ok",
            metadata={"result_dir": request.result_dir},
        )
        return inspection

    @app.post("/study/run")
    def run_study(http_request: Request, request: StudyRunRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        try:
            results = run_publication_study(
                config_path=request.config_path,
                output_dir=request.output_dir,
                report_context=report_context,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_study_response(results)
        response["output_dir"] = request.output_dir
        _audit_event(http_request, event_type="study.sync_completed", status="ok", metadata={"output_dir": request.output_dir})
        return response

    @app.post("/study/public-run")
    def run_public_study(http_request: Request, request: StudyPublicRunRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        try:
            results = run_public_benchmark_pipeline(
                config_path=request.config_path,
                output_dir=request.output_dir,
                bootstrap_root_dir=request.bootstrap_root_dir,
                delivery_dir=request.delivery_dir,
                report_context=report_context,
                require_live_public_ready=request.require_live_public_ready,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_public_study_run_response(results)
        _audit_event(
            http_request,
            event_type="study.public_pipeline_completed",
            status="ok" if response.get("ready_for_benchmark_lock") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "resolution_percent": response.get("resolution_percent"),
                "execution_board_percent": response.get("execution_board_percent"),
                "delivery_dir": request.delivery_dir,
            },
        )
        return response

    @app.post("/study/public-run/candidate")
    def run_candidate_public_study(http_request: Request, request: CandidatePublicRunRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        try:
            results = run_candidate_public_benchmark_pipeline(
                candidate_config_path=request.candidate_config_path,
                output_dir=request.output_dir,
                candidate_promotion_manifest_path=request.candidate_promotion_manifest_path,
                require_candidate_ready=request.require_candidate_ready,
                report_context=report_context,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = _summarize_public_study_run_response(results)
        response["candidate_public_run_summary"] = results.get("candidate_public_run_summary") or {}
        _audit_event(
            http_request,
            event_type="study.candidate_public_pipeline_completed",
            status="ok" if response.get("ready_for_benchmark_lock") else "warning",
            metadata={
                "output_dir": request.output_dir,
                "candidate_config_path": request.candidate_config_path,
                "candidate_launch_percent": (results.get("candidate_public_run_summary") or {}).get("candidate_launch_percent"),
            },
        )
        return response

    @app.post("/jobs/study/run")
    def enqueue_study_run(http_request: Request, request: StudyRunRequest, _: None = Depends(require_api_key)) -> dict:
        payload = request.model_dump()
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(payload.get("report_context", {}) or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        payload["report_context"] = report_context

        def _runner(job_payload: dict) -> dict:
            results = run_publication_study(**job_payload)
            response = _summarize_study_response(results)
            response["output_dir"] = job_payload.get("output_dir")
            return response

        job = app.state.job_manager.submit_job(
            job_type="study_run",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(http_request, event_type="study.job_enqueued", status="queued", job_id=job["job_id"], metadata={"output_dir": request.output_dir})
        return job

    @app.post("/jobs/study/public-run")
    def enqueue_public_study_run(http_request: Request, request: StudyPublicRunRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        payload = {
            "config_path": request.config_path,
            "output_dir": request.output_dir,
            "bootstrap_root_dir": request.bootstrap_root_dir,
            "delivery_dir": request.delivery_dir,
            "require_live_public_ready": request.require_live_public_ready,
            "report_context": report_context,
        }

        def _runner(job_payload: dict) -> dict:
            results = run_public_benchmark_pipeline(**job_payload)
            return _summarize_public_study_run_response(results)

        job = app.state.job_manager.submit_job(
            job_type="study_public_run",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="study.public_pipeline_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "delivery_dir": request.delivery_dir},
        )
        return job

    @app.post("/jobs/study/public-run/candidate")
    def enqueue_candidate_public_study_run(http_request: Request, request: CandidatePublicRunRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("operator_role", profile.get("role"))
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("report_title", request.report_title or None)
        payload = {
            "candidate_config_path": request.candidate_config_path,
            "output_dir": request.output_dir,
            "candidate_promotion_manifest_path": request.candidate_promotion_manifest_path,
            "require_candidate_ready": request.require_candidate_ready,
            "report_context": report_context,
        }

        def _runner(job_payload: dict) -> dict:
            results = run_candidate_public_benchmark_pipeline(**job_payload)
            response = _summarize_public_study_run_response(results)
            response["candidate_public_run_summary"] = results.get("candidate_public_run_summary") or {}
            return response

        job = app.state.job_manager.submit_job(
            job_type="candidate_public_study_run",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="study.candidate_public_pipeline_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "candidate_config_path": request.candidate_config_path},
        )
        return job

    @app.post("/jobs/science/gene-expansion")
    def enqueue_gene_expansion(http_request: Request, request: GeneExpansionRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_gene_expansion_assessment(**job_payload)
            return _summarize_gene_expansion_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_gene_expansion",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.gene_expansion_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "top_k": request.top_k},
        )
        return job

    @app.post("/jobs/science/biological-discovery")
    def enqueue_biological_discovery(http_request: Request, request: BiologicalDiscoveryRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_biological_discovery_package(**job_payload)
            return _summarize_biological_discovery_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_biological_discovery",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.biological_discovery_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir},
        )
        return job

    @app.post("/jobs/science/multigene-rollout")
    def enqueue_multigene_rollout(http_request: Request, request: MultigeneRolloutRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_multigene_rollout_plan(**job_payload)
            return _summarize_multigene_rollout_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_multigene_rollout",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.multigene_rollout_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "max_phase_1": request.max_phase_1},
        )
        return job

    @app.post("/jobs/science/multigene-study-factory")
    def enqueue_multigene_study_factory(http_request: Request, request: MultigeneStudyFactoryRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_multigene_study_factory(**job_payload)
            return _summarize_multigene_study_factory_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_multigene_study_factory",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.multigene_study_factory_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "workspace_root": request.workspace_root},
        )
        return job

    @app.post("/jobs/science/protein-impact")
    def enqueue_protein_impact(http_request: Request, request: ProteinImpactRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_protein_impact_package(**job_payload)
            return _summarize_protein_impact_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_protein_impact",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.protein_impact_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "max_modeling_variants": request.max_modeling_variants},
        )
        return job

    @app.post("/jobs/science/quantum-proteomics")
    def enqueue_quantum_proteomics(http_request: Request, request: QuantumProteomicsRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        payload = request.model_dump()

        def _runner(job_payload: dict) -> dict:
            results = export_quantum_proteomics_package(**job_payload)
            return _summarize_quantum_proteomics_response(results)

        job = app.state.job_manager.submit_job(
            job_type="science_quantum_proteomics",
            payload=payload,
            runner=_runner,
            submitted_by=profile,
            submitted_for_team=team,
        )
        _audit_event(
            http_request,
            event_type="science.quantum_proteomics_job_enqueued",
            status="queued",
            job_id=job["job_id"],
            metadata={"output_dir": request.output_dir, "max_quantum_targets": request.max_quantum_targets},
        )
        return job

    @app.post("/study/compare")
    def compare_studies(http_request: Request, request: StudyComparisonRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("comparison_purpose", "study_benchmark_comparison")
        try:
            comparison = build_study_comparison(
                baseline_dir=request.baseline_dir,
                candidate_dir=request.candidate_dir,
                primary_metric=request.primary_metric,
                report_title=request.report_title,
                report_context=report_context,
            )
            export_paths = export_study_comparison(comparison, output_dir=request.output_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="study.compared",
            status="ok",
            metadata={
                "baseline_dir": request.baseline_dir,
                "candidate_dir": request.candidate_dir,
                "output_dir": request.output_dir,
            },
        )
        return {
            "report_title": comparison.get("report_title"),
            "generated_at": comparison.get("generated_at"),
            "baseline_dir": comparison.get("baseline_dir"),
            "candidate_dir": comparison.get("candidate_dir"),
            "primary_metric": comparison.get("primary_metric"),
            "internal_delta": comparison.get("internal_delta"),
            "external_comparison": comparison.get("external_comparison").to_dict(orient="records"),
            "markdown_report": comparison.get("markdown_report"),
            "export_paths": export_paths,
        }

    @app.post("/monitoring/studies/longitudinal")
    def monitor_studies_longitudinally(http_request: Request, request: LongitudinalMonitoringRequest, _: None = Depends(require_api_key)) -> dict:
        profile = _resolve_profile_from_request(http_request)
        team = _resolve_team_from_request(http_request, require_membership=True)
        report_context = dict(request.report_context or {})
        report_context.setdefault("institution", team.get("institution") or profile.get("institution"))
        report_context.setdefault("team_name", team.get("display_name"))
        report_context.setdefault("operator_name", profile.get("display_name"))
        report_context.setdefault("monitoring_purpose", "longitudinal_study_tracking")
        try:
            monitor = build_longitudinal_study_monitor(
                study_dirs=request.study_dirs,
                primary_metric=request.primary_metric,
                report_title=request.report_title,
                report_context=report_context,
            )
            export_paths = export_longitudinal_study_monitor(monitor, output_dir=request.output_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _audit_event(
            http_request,
            event_type="monitoring.longitudinal_generated",
            status="ok",
            metadata={
                "n_studies": len(request.study_dirs),
                "output_dir": request.output_dir,
            },
        )
        return {
            "report_title": monitor.get("report_title"),
            "generated_at": monitor.get("generated_at"),
            "primary_metric": monitor.get("primary_metric"),
            "summary": monitor.get("summary"),
            "timeline": monitor.get("timeline").to_dict(orient="records"),
            "markdown_report": monitor.get("markdown_report"),
            "export_paths": export_paths,
        }

    return app


app = create_app()


def run_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run("primevarclass.api:app", host=host, port=port, reload=False)


def main() -> None:
    run_api()
