from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _percent(value: Any, default: int = 0) -> int:
    try:
        numeric = float(value)
    except Exception:
        return default
    if np.isnan(numeric) or np.isinf(numeric):
        return default
    return max(0, min(100, int(round(numeric))))


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


def _read_table(path_value: str | None) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _column_or_default(df: pd.DataFrame, column: str, default: Any = False) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _gene_assay_blueprint(gene: Any) -> dict[str, str]:
    normalized = str(gene or "").upper()
    blueprints: dict[str, dict[str, str]] = {
        "BRCA1": {
            "assay_family": "DNA repair and protein-domain integrity",
            "functional_assay": "HDR reporter, saturation genome editing, RAD51 foci, protein stability and localization",
            "structural_assay": "RING/BRCT domain model review, DSF/nanoDSF, HDX-MS, SPR/BLI or peptide/interface binding when applicable",
            "sample_material": "Mammalian HDR reporter cells or SGE library; purified RING/BRCT domain for biophysics",
            "controls": "Known pathogenic loss-of-function, known benign, synonymous/wild-type and assay-positive rescue controls",
            "sop_id": "SOP_BRCA1_HDR_SGE",
        },
        "TP53": {
            "assay_family": "Tumor suppressor transcriptional activity",
            "functional_assay": "p53 response-element luciferase/transactivation panel plus protein abundance and nuclear localization",
            "structural_assay": "DNA-binding domain stability, tetramerization/interface review, DSF/nanoDSF when purified protein is available",
            "sample_material": "p53-null cell reporter panel or yeast/human transcriptional reporter system",
            "controls": "Wild-type TP53, dominant-negative hotspot, benign polymorphism and empty-vector controls",
            "sop_id": "SOP_TP53_transactivation",
        },
        "PTEN": {
            "assay_family": "Phosphatase and PI3K/AKT signaling",
            "functional_assay": "Lipid/protein phosphatase activity, pAKT pathway rescue and cellular localization",
            "structural_assay": "Phosphatase/C2-domain model review, membrane-interface stability and DSF/nanoDSF",
            "sample_material": "PTEN-null cell rescue line and purified PTEN domain/protein when feasible",
            "controls": "Wild-type PTEN, catalytic-dead PTEN, benign controls and pathway-stimulation controls",
            "sop_id": "SOP_PTEN_phosphatase_AKT",
        },
        "MSH2": {
            "assay_family": "Mismatch repair",
            "functional_assay": "MMR reporter, microsatellite instability rescue, MutSalpha interaction and protein stability",
            "structural_assay": "MSH2/MSH6 interface model review, ATPase/DNA-binding domain stability and SEC-MALS when available",
            "sample_material": "MMR-deficient rescue cells; purified MSH2/MSH6 complex for structural work if available",
            "controls": "Wild-type MSH2, known Lynch pathogenic variant, benign variant and empty-vector control",
            "sop_id": "SOP_MSH2_mismatch_repair",
        },
        "KRAS": {
            "assay_family": "Small GTPase and MAPK signaling",
            "functional_assay": "GTP loading/hydrolysis, RAF binding, ERK phosphorylation and pathway dependence assays",
            "structural_assay": "Switch-I/Switch-II pocket review, nucleotide/effector binding, SPR/BLI/ITC and docking controls",
            "sample_material": "Isogenic cell signaling model and purified KRAS protein loaded with GDP/GTP analogs",
            "controls": "Wild-type KRAS, G12D/G12V or Q61 hotspot, inactive control and pathway inhibitor controls",
            "sop_id": "SOP_KRAS_GTPase_MAPK",
        },
        "GCK": {
            "assay_family": "Enzymatic glucose sensing",
            "functional_assay": "Glucokinase kinetic assay with glucose/ATP titration, thermal stability and cellular glucose response",
            "structural_assay": "Active-site/allosteric-site model review, DSF/nanoDSF and ligand-binding thermal shift",
            "sample_material": "Purified GCK protein and beta-cell/hepatocyte-compatible rescue model when feasible",
            "controls": "Wild-type GCK, MODY-associated loss-of-function, activating control and assay blank",
            "sop_id": "SOP_GCK_enzymatic",
        },
        "F9": {
            "assay_family": "Coagulation factor activity",
            "functional_assay": "FIX activity, secretion/antigen level, activation peptide processing and coagulation readout",
            "structural_assay": "Gla/EGF/protease-domain model review, secretion/stability assay and binding to pathway partners",
            "sample_material": "Expression/secretion cell model and purified FIX variant when feasible",
            "controls": "Wild-type F9, known hemophilia B variant, benign control and secretion-positive control",
            "sop_id": "SOP_F9_coagulation",
        },
    }
    return blueprints.get(
        normalized,
        {
            "assay_family": "Gene-specific functional validation",
            "functional_assay": "Select assay matched to disease biology, variant mechanism and available public functional evidence",
            "structural_assay": "Domain-aware mutant model review plus stability/binding assay when a structural hypothesis exists",
            "sample_material": "Disease-relevant cell model or purified domain selected by partner lab feasibility",
            "controls": "Wild-type, known pathogenic, known benign, empty-vector and assay-specific positive controls",
            "sop_id": "SOP_gene_specific_validation",
        },
    )


def _gate(gate_id: str, title: str, status: str, score_percent: int, evidence: str, remaining_action: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "title": title,
        "status": status,
        "score_percent": _percent(score_percent),
        "evidence": evidence,
        "remaining_action": remaining_action,
    }


def _build_gates(
    *,
    annotation_summary: dict[str, Any],
    public_sync_summary: dict[str, Any],
    engine_summary: dict[str, Any],
    paired_mutant_summary: dict[str, Any],
    mutant_geometry_qc_summary: dict[str, Any],
    validation_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    annotation_readiness = max(
        _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 0),
        _percent(public_sync_summary.get("effective_line_level_annotation_readiness_percent"), 0),
    )
    gnomad_coverage = max(
        _percent(annotation_summary.get("gnomad_line_evidence_coverage_percent"), 0),
        _percent(public_sync_summary.get("effective_gnomad_line_evidence_percent"), 0),
    )
    mavedb_coverage = max(
        _percent(annotation_summary.get("mavedb_line_evidence_coverage_percent"), 0),
        _percent(public_sync_summary.get("mavedb_line_evidence_percent"), 0),
    )
    coordinate_missing = int(public_sync_summary.get("gnomad_coordinate_missing_count") or 0)
    engine_readiness = _percent(engine_summary.get("execution_readiness_percent"), 0)
    engine_available = _percent(engine_summary.get("engine_availability_percent"), 0)
    paired_readiness = _percent(paired_mutant_summary.get("paired_mutant_execution_readiness_percent"), 0)
    paired_completed = int(paired_mutant_summary.get("paired_xtb_completed_count") or 0)
    geometry_qc_readiness = _percent(mutant_geometry_qc_summary.get("mutant_geometry_qc_readiness_percent"), 0)
    opt_completed = int(mutant_geometry_qc_summary.get("xtb_optimization_completed_count") or 0)
    structural_execution_score = _percent(
        engine_readiness * 0.40
        + engine_available * 0.20
        + paired_readiness * 0.25
        + geometry_qc_readiness * 0.15
    )
    software_evidence = _percent(validation_summary.get("software_evidence_closure_percent"), 0)
    return [
        _gate(
            "frozen_independent_benchmark",
            "Frozen independent/prospective benchmark",
            "ready_for_next_release_lock" if software_evidence >= 85 else "needs_more_software_evidence",
            min(100, int(round(software_evidence * 0.9 + 10))),
            f"Current software evidence closure={software_evidence}%.",
            "Freeze the next public ClinVar/gnomAD/MaveDB release before model refit and score it once without retuning.",
        ),
        _gate(
            "row_level_public_annotation",
            "Row-level gnomAD/MaveDB public annotation",
            "strong_with_coordinate_exceptions" if annotation_readiness >= 90 and coordinate_missing else ("strong" if annotation_readiness >= 80 else "partial"),
            annotation_readiness,
            f"gnomAD evidence={gnomad_coverage}%; MaveDB evidence={mavedb_coverage}%; coordinate missing={coordinate_missing}.",
            "Resolve remaining coordinate exceptions and complete VRS reconciliation for publication-grade variant identity.",
        ),
        _gate(
            "real_engine_structural_execution",
            "BRCA1 xTB/DFT/VQE/MD execution with real engines",
            "triage_executed_needs_reviewed_controls" if paired_completed else ("blocked_by_local_engines" if engine_available < 50 else "ready_to_execute"),
            structural_execution_score,
            f"Engine availability={engine_available}%; execution readiness={engine_readiness}%; paired xTB completed={paired_completed}; xTB optimizations={opt_completed}.",
            "Upgrade automated geometry QC into expert protonation/domain review plus DFT/OpenMM and docking controls.",
        ),
        _gate(
            "functional_assay_confirmation",
            "Orthogonal functional confirmation",
            "lab_required",
            68 if mavedb_coverage >= 80 and paired_completed else (55 if mavedb_coverage > 0 else 35),
            "MaveDB provides public functional evidence and BRCA1 paired xTB provides computational triage, but no new wet-lab confirmation has been generated by this platform run.",
            "Run HDR/SGE, transcriptional, enzymatic, or stability assays for the top predicted variants in an independent lab.",
        ),
        _gate(
            "structural_experimental_confirmation",
            "Structural experimental confirmation",
            "computational_triage_ready_lab_required" if paired_completed else "lab_required",
            74 if opt_completed else (70 if paired_completed else (50 if engine_summary.get("alphafold_reference_available") else 30)),
            "AlphaFold coordinates, draft paired xTB deltas, and automated geometry QC are available, but crystallography/cryo-EM/NMR or targeted biophysical confirmation is still external.",
            "Confirm selected structural mechanisms with biophysical assays, binding readouts, reviewed mutant models or experimental structures.",
        ),
        _gate(
            "therapeutic_translation_claim",
            "Therapeutic translation and drug-discovery claim",
            "hypothesis_only",
            45,
            "The platform can prioritize vulnerable mechanisms, but efficacy, binding, and rescue evidence are not complete.",
            "Only make therapeutic claims after binding, rescue, toxicity, and disease-relevant cellular evidence.",
        ),
    ]


def _experimental_queue(
    *,
    annotation_matrix: pd.DataFrame,
    engine_queue: pd.DataFrame,
    paired_mutant_table: pd.DataFrame,
    max_rows: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    paired_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    if not paired_mutant_table.empty:
        for _, paired in paired_mutant_table.iterrows():
            paired_lookup[(str(paired.get("gene") or ""), str(paired.get("hgvs_p") or ""))] = paired.to_dict()
    if not engine_queue.empty:
        for _, row in engine_queue.head(max_rows).iterrows():
            paired = paired_lookup.get((str(row.get("gene") or ""), str(row.get("hgvs_p") or "")), {})
            paired_status = paired.get("paired_status") or row.get("execution_status")
            delta = paired.get("delta_mutant_minus_reference_hartree")
            rows.append(
                {
                    "gene": row.get("gene"),
                    "hgvs_p": row.get("hgvs_p"),
                    "priority_layer": "BRCA1 structural/quantum",
                    "functional_confirmation": "HDR/SGE or homology-directed repair reporter; protein stability and localization",
                    "structural_confirmation": "Review draft mutant rotamer/protonation, rerun paired xTB/DFT, then MD stability and docking if pocket/interface is plausible",
                    "translation_endpoint": "Mechanistic vulnerability, rescue assay, or interaction disruption evidence",
                    "software_status": paired_status,
                    "paired_xtb_delta_hartree": delta,
                    "lab_status": "not_started",
                }
            )
    if not annotation_matrix.empty:
        candidates = annotation_matrix.loc[
            _column_or_default(annotation_matrix, "mavedb_line_available", False).astype(bool)
            | _column_or_default(annotation_matrix, "gnomad_line_available", False).astype(bool)
        ].copy()
        candidates = candidates.loc[~candidates["gene"].astype(str).eq("BRCA1")].head(max_rows)
        for _, row in candidates.iterrows():
            rows.append(
                {
                    "gene": row.get("gene"),
                    "hgvs_p": row.get("hgvs_p"),
                    "priority_layer": "multigene functional generalization",
                    "functional_confirmation": "Gene-specific assay matched to biology: transcriptional, enzymatic, mismatch repair, coagulation, or pathway readout",
                    "structural_confirmation": "Domain-aware mutant model and conservation/interface review",
                    "translation_endpoint": "Cross-gene generalization plus functional effect concordance",
                    "software_status": row.get("annotation_status"),
                    "lab_status": "not_started",
                }
            )
    queue = pd.DataFrame(rows)
    if queue.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "priority_layer",
                "functional_confirmation",
                "structural_confirmation",
                "translation_endpoint",
                "software_status",
                "lab_status",
            ]
        )
    return queue.drop_duplicates(subset=["gene", "hgvs_p", "priority_layer"], keep="first").head(max_rows * 2)


def _build_cohort_plan(
    *,
    annotation_summary: dict[str, Any],
    public_sync_summary: dict[str, Any],
    validation_summary: dict[str, Any],
) -> pd.DataFrame:
    annotation_ready = max(
        _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 0),
        _percent(public_sync_summary.get("effective_line_level_annotation_readiness_percent"), 0),
    )
    software_ready = _percent(validation_summary.get("software_evidence_closure_percent"), 0)
    rows = [
        {
            "cohort_id": "PVC-PROSPECTIVE-CLINVAR-NEXT-RELEASE",
            "role": "primary prospective temporal validation",
            "source": "Next ClinVar public release after model/protocol freeze",
            "inclusion_rule": "Missense variants in target genes absent from model fitting and threshold selection",
            "label_source": "ClinVar clinical significance after release lock, with review-status stratification",
            "blinding_rule": "Score all rows once before labels are opened to the analysis team",
            "lock_rule": "Archive release date, source checksums, model hash, feature schema and thresholds before scoring",
            "target_size": "All eligible rows; report per-gene counts and missingness",
            "primary_endpoint": "Pathogenic/likely pathogenic vs benign/likely benign discrimination",
            "success_criterion": "AUROC and AUPRC confidence intervals exceed locked baseline; calibration slope remains acceptable",
            "status": "ready_to_lock" if software_ready >= 85 else "software_evidence_needed",
        },
        {
            "cohort_id": "PVC-PROSPECTIVE-BRCA-EXCHANGE-TEMPORAL",
            "role": "BRCA-focused independent update",
            "source": "Next BRCA Exchange or ENIGMA-aligned release not used by this build",
            "inclusion_rule": "BRCA1/BRCA2 missense variants with stable identifiers and no training leakage",
            "label_source": "Curated BRCA Exchange/ENIGMA-style classification where available",
            "blinding_rule": "Variant scores generated without viewing the new curated labels",
            "lock_rule": "Version, checksum and excluded-overlap report must be stored with the run manifest",
            "target_size": "All eligible BRCA rows plus explicit unresolved/VUS accounting",
            "primary_endpoint": "BRCA-specific concordance, precision at top-K pathogenic predictions and calibration",
            "success_criterion": "No material regression versus retrospective BRCA benchmark and improved top-K triage value",
            "status": "ready_to_lock" if annotation_ready >= 80 else "row_level_annotation_needed",
        },
        {
            "cohort_id": "PVC-BLINDED-MULTIGENE-HOLDOUT",
            "role": "generalization validation",
            "source": "TP53, PTEN, MSH2, KRAS, GCK, F9 and BRCA1 independent held-out public rows",
            "inclusion_rule": "Variants selected before scoring, stratified by gene, label class and evidence density",
            "label_source": "ClinVar plus public functional evidence where available; discordant labels analyzed separately",
            "blinding_rule": "Per-gene labels and functional annotations remain hidden until score file is sealed",
            "lock_rule": "One model, one feature recipe, one threshold family; no gene-specific retuning after lock",
            "target_size": "Minimum 30 variants per gene when available; otherwise all high-confidence rows",
            "primary_endpoint": "Cross-gene AUROC/AUPRC, MCC, balanced accuracy and calibration",
            "success_criterion": "Performance remains directionally strong in at least five target genes without BRCA-only collapse",
            "status": "ready_to_lock" if annotation_ready >= 80 else "needs_more_line_level_public_data",
        },
        {
            "cohort_id": "PVC-MAVEDB-FUNCTIONAL-HOLDOUT",
            "role": "orthogonal functional validation",
            "source": "MaveDB score sets published after freeze or excluded from training",
            "inclusion_rule": "Variants with quantitative functional scores and mappable HGVS/protein coordinates",
            "label_source": "Locked functional score thresholds or continuous functional effect ranks",
            "blinding_rule": "PrimeVarClass scores sealed before functional score bins are joined",
            "lock_rule": "Functional thresholding method and missingness handling documented before analysis",
            "target_size": "All line-mappable rows per score set",
            "primary_endpoint": "Concordance with quantitative functional effect and rank enrichment",
            "success_criterion": "Significant enrichment of high-risk predictions among functional-loss variants after correction",
            "status": "ready_to_lock" if annotation_ready >= 80 else "needs_mavedb_line_mapping",
        },
        {
            "cohort_id": "PVC-GNOMAD-POPULATION-CONTROL",
            "role": "population constraint and benign-enrichment control",
            "source": "gnomAD target-gene subset frozen by release",
            "inclusion_rule": "Missense variants with population frequency, ancestry strata and quality filters",
            "label_source": "Population-frequency/control enrichment is treated as supporting evidence, not a clinical truth label",
            "blinding_rule": "Evaluate depletion/enrichment after risk scores are frozen",
            "lock_rule": "Frequency bins, quality filters and ancestry handling fixed before analysis",
            "target_size": "All high-quality target-gene rows",
            "primary_endpoint": "Risk-score depletion among common tolerated variation and enrichment among constrained regions",
            "success_criterion": "No systematic inflation of common benign/control variants into high-risk bins",
            "status": "ready_to_lock" if annotation_ready >= 80 else "needs_gnomad_release_reconciliation",
        },
        {
            "cohort_id": "PVC-PARTNER-SHADOW-MODE",
            "role": "real-world translational shadow validation",
            "source": "External lab/clinic partner de-identified variants",
            "inclusion_rule": "No treatment action; variants scored for research-use-only comparison with partner evidence",
            "label_source": "Partner-provided post-hoc functional, structural or clinical review outcome",
            "blinding_rule": "Partner receives blinded IDs and returns raw readouts before model interpretation is revealed",
            "lock_rule": "IRB/data-use agreement, data dictionary, model hash and analysis plan signed before transfer",
            "target_size": "Pilot 50-200 variants, then expand after calibration review",
            "primary_endpoint": "Operational concordance, failure-mode taxonomy and clinical/research usability",
            "success_criterion": "Partner confirms feasible workflow and identifies actionable experimental hypotheses",
            "status": "partner_required",
        },
    ]
    return pd.DataFrame(rows)


def _build_confirmation_criteria() -> pd.DataFrame:
    rows = [
        {
            "criterion_id": "BRCA1_HDR_SGE",
            "applies_to": "BRCA1 and BRCA DNA-repair variants",
            "primary_readout": "HDR/SGE functional score, RAD51 foci, protein stability and localization",
            "controls_required": "Wild-type, known pathogenic, known benign, synonymous/neutral and rescue controls",
            "replicate_rule": "At least 3 biological replicates or a validated SGE design with internal replicate structure",
            "pass_rule": "Variant effect direction agrees with sealed model risk bin and assay controls pass QC",
            "acmg_svi_use": "May support PS3/BS3-style functional evidence only after assay validity and odds strength are documented",
            "failure_mode_to_report": "Assay saturation, poor expression, localization artifact or discordant domain mechanism",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "TP53_TRANSCRIPTION",
            "applies_to": "TP53",
            "primary_readout": "Transactivation/luciferase response-element panel and protein abundance",
            "controls_required": "Wild-type TP53, hotspot pathogenic, benign polymorphism and empty vector",
            "replicate_rule": "At least 3 independent transfections or validated pooled reporter replicates",
            "pass_rule": "Loss/gain pattern is concordant across response elements and not explained only by expression loss",
            "acmg_svi_use": "Functional evidence can be considered only with calibrated control separation",
            "failure_mode_to_report": "Cell-line context dependence, dominant-negative behavior or expression instability",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "PTEN_PHOSPHATASE_AKT",
            "applies_to": "PTEN",
            "primary_readout": "Lipid/protein phosphatase activity, pAKT suppression and localization rescue",
            "controls_required": "Wild-type PTEN, catalytic-dead control, known benign and stimulation/inhibitor controls",
            "replicate_rule": "At least 3 biological replicates plus assay blank and calibration curve where applicable",
            "pass_rule": "Biochemical and pathway readouts converge or discordance is mechanistically explained",
            "acmg_svi_use": "Use strength only after pathway specificity and dynamic range are validated",
            "failure_mode_to_report": "Protein instability, membrane-localization artifact or pathway compensation",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "MSH2_MMR",
            "applies_to": "MSH2",
            "primary_readout": "Mismatch-repair reporter, MSI rescue, MSH6 interaction and protein stability",
            "controls_required": "Wild-type MSH2, known Lynch pathogenic, known benign and vector controls",
            "replicate_rule": "At least 3 biological replicates or a validated high-throughput repair reporter design",
            "pass_rule": "Repair rescue and protein-interaction/stability evidence support the same mechanism",
            "acmg_svi_use": "Report as functional evidence only after assay specificity to MMR is documented",
            "failure_mode_to_report": "Partner-protein expression imbalance, nuclear localization artifact or cell-cycle context",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "KRAS_GTPASE_MAPK",
            "applies_to": "KRAS",
            "primary_readout": "GTP loading/hydrolysis, effector binding and ERK/MAPK pathway output",
            "controls_required": "Wild-type KRAS, activating hotspot, inactive control and pathway inhibitor controls",
            "replicate_rule": "At least 3 biological replicates plus nucleotide-loading QC for purified assays",
            "pass_rule": "Biochemical GTPase/effector result and pathway signal match the predicted mechanism",
            "acmg_svi_use": "Cancer functional interpretation only; avoid overclaiming germline clinical classification without context",
            "failure_mode_to_report": "Cell-type dependency, expression-level artifact or feedback pathway compensation",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "GCK_ENZYMATIC",
            "applies_to": "GCK",
            "primary_readout": "Glucokinase kinetics, thermal stability and glucose-response effect",
            "controls_required": "Wild-type GCK, MODY loss-of-function, activating control and assay blank",
            "replicate_rule": "At least 3 biochemical replicates with substrate titration and fitted kinetic parameters",
            "pass_rule": "Kinetic shift or stability loss agrees with sealed pathogenicity/mechanism hypothesis",
            "acmg_svi_use": "Quantitative enzymology may support functional evidence if controls and disease mechanism align",
            "failure_mode_to_report": "Purification instability, allosteric-state ambiguity or substrate-range limitation",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "F9_COAGULATION",
            "applies_to": "F9",
            "primary_readout": "FIX activity, secretion/antigen level and activation/coagulation readout",
            "controls_required": "Wild-type FIX, hemophilia B pathogenic variant, benign control and secretion-positive control",
            "replicate_rule": "At least 3 biological replicates plus assay calibration against reference standard where feasible",
            "pass_rule": "Activity/secretion defect matches predicted mechanism and is not solely transfection variability",
            "acmg_svi_use": "Functional evidence requires clinically interpretable activity calibration",
            "failure_mode_to_report": "Secretion bottleneck, vitamin-K modification context or assay-standard mismatch",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "STRUCTURAL_BIOPHYSICS",
            "applies_to": "Any prioritized structural mechanism",
            "primary_readout": "DSF/nanoDSF/CD/SEC-MALS, SPR/BLI/ITC, HDX-MS, cryo-EM/X-ray/NMR when feasible",
            "controls_required": "Wild-type domain, known destabilizing/binding-disruptive variant and buffer/ligand controls",
            "replicate_rule": "At least 2 orthogonal structural/biophysical readouts or one high-resolution structure plus QC",
            "pass_rule": "Observed stability, binding or conformational effect supports the sealed structural hypothesis",
            "acmg_svi_use": "Structural evidence is mechanistic support; clinical strength requires functional/clinical calibration",
            "failure_mode_to_report": "AlphaFold uncertainty, protonation/oligomeric-state ambiguity, purification artifact or non-native domain boundary",
            "status": "template_ready_lab_required",
        },
        {
            "criterion_id": "COMPUTATIONAL_REPRODUCIBILITY",
            "applies_to": "All PrimeVarClass prospective runs",
            "primary_readout": "Frozen model hash, feature schema, source checksums, thresholds, environment and command log",
            "controls_required": "Baseline comparator models, prime-ablation controls and unchanged thresholds",
            "replicate_rule": "Independent rerun from manifest must reproduce score files within numerical tolerance",
            "pass_rule": "No hidden retuning, no label leakage and all exclusions are declared before final analysis",
            "acmg_svi_use": "Supports credibility of computational evidence but does not replace functional validation",
            "failure_mode_to_report": "Data leakage, source drift, unmapped variants, seed sensitivity or unavailable external data",
            "status": "software_ready",
        },
    ]
    return pd.DataFrame(rows)


def _build_partner_handoff(queue: pd.DataFrame) -> pd.DataFrame:
    if queue.empty:
        return pd.DataFrame(
            columns=[
                "blinding_id",
                "gene",
                "hgvs_p",
                "assay_family",
                "functional_assay",
                "structural_assay",
                "sample_material",
                "controls",
                "sop_id",
                "platform_evidence",
                "data_return_fields",
                "score_release_rule",
                "lab_status",
            ]
        )
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(queue.to_dict(orient="records"), start=1):
        blueprint = _gene_assay_blueprint(row.get("gene"))
        software_status = str(row.get("software_status") or "not_available")
        delta = row.get("paired_xtb_delta_hartree")
        delta_text = "" if pd.isna(delta) else f"; paired_xtb_delta_hartree={delta}"
        rows.append(
            {
                "blinding_id": f"PVC-BLIND-{idx:04d}",
                "gene": row.get("gene"),
                "hgvs_p": row.get("hgvs_p"),
                "assay_family": blueprint["assay_family"],
                "functional_assay": blueprint["functional_assay"],
                "structural_assay": blueprint["structural_assay"],
                "sample_material": blueprint["sample_material"],
                "controls": blueprint["controls"],
                "sop_id": blueprint["sop_id"],
                "platform_evidence": f"{row.get('priority_layer')}; software_status={software_status}{delta_text}",
                "data_return_fields": "blinding_id, raw_readout, normalized_effect, qc_status, replicate_count, control_pass, assay_version, operator_blinded",
                "score_release_rule": "Partner returns raw/QC data before PrimeVarClass score bin and mechanistic interpretation are unblinded.",
                "lab_status": row.get("lab_status") or "not_started",
            }
        )
    return pd.DataFrame(rows)


def _build_statistical_analysis_plan_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PrimeVarClass Locked Statistical Analysis Plan",
        "",
        "## Scope",
        "",
        "This plan governs the next independent/prospective validation run. It must be versioned before labels or partner assay results are opened.",
        "",
        "## Frozen assets",
        "",
        f"- Model/protocol freeze target: `{summary.get('generated_at')}`",
        "- Store model hash, feature schema hash, source checksums, command log, dependency lock and output manifest.",
        "- Do not retune thresholds, feature transforms or prime-derived encodings after the cohort lock.",
        "",
        "## Primary endpoints",
        "",
        "- ClinVar/BRCA temporal validation: AUROC, AUPRC, MCC, balanced accuracy, calibration slope/intercept and Brier score.",
        "- Functional validation: rank enrichment and concordance with quantitative MaveDB/wet-lab functional effect.",
        "- Structural validation: concordance between sealed structural hypothesis and experimental stability, binding or conformational readout.",
        "",
        "## Comparators",
        "",
        "- PrimeVarClass full model.",
        "- Prime-ablation model with the same non-prime features.",
        "- Non-prime initialization/control for quantum/VQE structural prioritization where applicable.",
        "- External predictors when locally available, such as AlphaMissense, REVEL, EVE or CADD, reported without cherry-picking.",
        "",
        "## Inference and uncertainty",
        "",
        "- Report 95% confidence intervals using bootstrap or paired resampling; use paired tests for comparator deltas.",
        "- Report calibration curves, decision-curve style net benefit and precision at top-K for experimental triage.",
        "- Stratify by gene, label confidence, evidence density, ancestry/frequency bins when population data are used, and variant domain.",
        "",
        "## Leakage and missingness",
        "",
        "- Exclude rows that were used for training, threshold choice or manual hypothesis tuning.",
        "- Publish all unmapped variants, failed assays, ambiguous labels and source-coordinate exceptions.",
        "- Any post-hoc exploratory analysis must be clearly separated from the locked primary analysis.",
        "",
        "## Success rules",
        "",
        "- The platform is considered prospectively credible if the frozen full model beats locked baselines on primary metrics without calibration collapse.",
        "- The prime-number contribution is considered supported if prime-ablation or non-prime controls underperform on the same locked cohort/fragment set.",
        "- Therapeutic claims remain hypothesis-generating until binding, rescue, toxicity and disease-relevant cellular evidence are complete.",
    ]
    return "\n".join(lines).strip()


def _build_partner_packet_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    handoff = payload.get("partner_handoff_sheet")
    handoff_df = handoff if isinstance(handoff, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass External Partner Handoff Packet",
        "",
        "## Purpose",
        "",
        "PrimeVarClass is ready for research-use-only shadow validation with blinded external functional and structural confirmation. This packet tells a partner lab what to run, what to return, and what must stay blinded.",
        "",
        "## Current validation status",
        "",
        f"- Prospective readiness: `{summary.get('prospective_validation_readiness_percent', 0)}%`",
        f"- Experimental completion: `{summary.get('experimental_confirmation_completed_percent', 0)}%`",
        f"- Final scientific proof cap: `{summary.get('final_scientific_proof_cap_percent', 0)}%`",
        f"- Partner handoff variants: `{len(handoff_df)}`",
        "",
        "## Partner rules",
        "",
        "- Use only blinded IDs until raw assay/QC outputs are returned.",
        "- Do not use the model score to choose assay thresholds after the run starts.",
        "- Return raw readouts, normalized effects, replicate counts, QC status, failed variants and protocol deviations.",
        "- Treat outputs as research evidence until clinical validation, regulatory review and disease-specific evidence standards are met.",
        "",
        "## First targets",
        "",
    ]
    if handoff_df.empty:
        lines.append("- No handoff targets generated yet.")
    else:
        for row in handoff_df.head(12).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('blinding_id')}: {row.get('gene')} {row.get('hgvs_p')} | "
                f"{row.get('assay_family')} | SOP `{row.get('sop_id')}`"
            )
    lines.extend(
        [
            "",
            "## Minimum data return",
            "",
            "- `blinding_id`, `gene`, `hgvs_p`, `assay_version`, `raw_readout`, `normalized_effect`, `qc_status`, `replicate_count`, `control_pass`, `operator_blinded`, `notes`.",
        ]
    )
    return "\n".join(lines).strip()


def _sop_template_specs() -> list[dict[str, str]]:
    return [
        {"sop_id": "SOP_BRCA1_HDR_SGE", "gene": "BRCA1", "filename": "SOP_BRCA1_HDR_SGE.md", "title": "BRCA1 HDR/SGE Functional Confirmation"},
        {"sop_id": "SOP_TP53_transactivation", "gene": "TP53", "filename": "SOP_TP53_transactivation.md", "title": "TP53 Transactivation Confirmation"},
        {"sop_id": "SOP_PTEN_phosphatase_AKT", "gene": "PTEN", "filename": "SOP_PTEN_phosphatase_AKT.md", "title": "PTEN Phosphatase and AKT Pathway Confirmation"},
        {"sop_id": "SOP_MSH2_mismatch_repair", "gene": "MSH2", "filename": "SOP_MSH2_mismatch_repair.md", "title": "MSH2 Mismatch-Repair Confirmation"},
        {"sop_id": "SOP_KRAS_GTPase_MAPK", "gene": "KRAS", "filename": "SOP_KRAS_GTPase_MAPK.md", "title": "KRAS GTPase and MAPK Confirmation"},
        {"sop_id": "SOP_GCK_enzymatic", "gene": "GCK", "filename": "SOP_GCK_enzymatic.md", "title": "GCK Enzymatic Confirmation"},
        {"sop_id": "SOP_F9_coagulation", "gene": "F9", "filename": "SOP_F9_coagulation.md", "title": "F9 Coagulation Confirmation"},
        {"sop_id": "SOP_structural_biophysics", "gene": "ALL", "filename": "SOP_structural_biophysics.md", "title": "Structural and Biophysical Confirmation"},
        {"sop_id": "SOP_blinded_scoring_and_data_return", "gene": "ALL", "filename": "SOP_blinded_scoring_and_data_return.md", "title": "Blinded Scoring and Data Return"},
    ]


def _render_gene_sop(spec: dict[str, str]) -> str:
    gene = spec["gene"]
    blueprint = _gene_assay_blueprint(gene)
    if gene == "ALL" and spec["sop_id"] == "SOP_structural_biophysics":
        return "\n".join(
            [
                f"# {spec['title']}",
                "",
                "## Objective",
                "",
                "Confirm whether a PrimeVarClass structural hypothesis is supported by orthogonal stability, binding or conformational evidence.",
                "",
                "## Minimum workflow",
                "",
                "1. Freeze the variant list, model score bins, protein/domain boundaries and structural hypothesis before experimental design.",
                "2. Review AlphaFold/PDB confidence, domain context, protonation, oligomeric state and interface assumptions.",
                "3. Select at least one stability assay such as DSF, nanoDSF, CD or SEC-MALS when protein material is available.",
                "4. Select a binding/conformation readout such as SPR, BLI, ITC, HDX-MS, cryo-EM, X-ray or NMR when the mechanism requires it.",
                "5. Return failed constructs, aggregation, poor expression and ambiguous biophysics as explicit outcomes.",
                "",
                "## Acceptance criteria",
                "",
                "- Wild-type and control variants pass assay QC.",
                "- Experimental readout supports or falsifies the sealed mechanism without changing the hypothesis after unblinding.",
                "- Structural evidence is interpreted as mechanistic support, not as a standalone therapeutic or clinical claim.",
            ]
        ).strip()
    if gene == "ALL":
        return "\n".join(
            [
                f"# {spec['title']}",
                "",
                "## Objective",
                "",
                "Prevent data leakage and preserve independent validation credibility during partner execution.",
                "",
                "## Procedure",
                "",
                "1. PrimeVarClass generates a blinded handoff sheet with `PVC-BLIND-*` IDs.",
                "2. The partner lab runs assays without seeing score bins, rank, predicted class or mechanistic interpretation.",
                "3. The partner returns raw readouts, normalized effects, QC flags, replicate counts and protocol deviations.",
                "4. The analysis team joins results to frozen scores only after raw/QC data are sealed.",
                "5. Every failed, unmapped or discordant variant remains in the audit trail.",
                "",
                "## Required return fields",
                "",
                "`blinding_id`, `assay_version`, `raw_readout`, `normalized_effect`, `qc_status`, `replicate_count`, `control_pass`, `operator_blinded`, `notes`.",
            ]
        ).strip()
    return "\n".join(
        [
            f"# {spec['title']}",
            "",
            "## Objective",
            "",
            f"Confirm PrimeVarClass predictions for `{gene}` variants with assays matched to the gene's disease biology.",
            "",
            "## Recommended assay family",
            "",
            f"- Functional readout: {blueprint['functional_assay']}.",
            f"- Structural/biophysical readout: {blueprint['structural_assay']}.",
            f"- Sample/material: {blueprint['sample_material']}.",
            f"- Required controls: {blueprint['controls']}.",
            "",
            "## Minimum procedure",
            "",
            "1. Use blinded IDs and frozen variant definitions from the partner handoff sheet.",
            "2. Confirm construct identity, expression/stability and assay dynamic range before variant interpretation.",
            "3. Run required controls and at least 3 biological replicates unless a validated pooled assay design is used.",
            "4. Return raw readouts, normalized effect, QC status, replicate count, assay version and notes before unblinding.",
            "5. Interpret concordant and discordant results against the locked statistical analysis plan.",
            "",
            "## Stop conditions",
            "",
            "- Control separation fails.",
            "- Construct identity or expression cannot be verified.",
            "- The readout does not measure the disease-relevant mechanism.",
        ]
    ).strip()


def _write_sop_templates(sop_dir: Path) -> pd.DataFrame:
    sop_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for spec in _sop_template_specs():
        path = sop_dir / spec["filename"]
        path.write_text(_render_gene_sop(spec), encoding="utf-8")
        rows.append(
            {
                "sop_id": spec["sop_id"],
                "gene": spec["gene"],
                "title": spec["title"],
                "path": str(path),
                "status": "template_ready_partner_review_required",
            }
        )
    return pd.DataFrame(rows)


def _build_protocol_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    gates = payload.get("validation_gates")
    gate_df = gates if isinstance(gates, pd.DataFrame) else pd.DataFrame()
    cohorts = payload.get("prospective_cohort_plan")
    cohort_df = cohorts if isinstance(cohorts, pd.DataFrame) else pd.DataFrame()
    criteria = payload.get("experimental_confirmation_criteria")
    criteria_df = criteria if isinstance(criteria, pd.DataFrame) else pd.DataFrame()
    handoff = payload.get("partner_handoff_sheet")
    handoff_df = handoff if isinstance(handoff, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Prospective and Experimental Validation Protocol",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Prospective validation readiness: `{summary.get('prospective_validation_readiness_percent', 0)}%`",
        f"- Experimental confirmation completion: `{summary.get('experimental_confirmation_completed_percent', 0)}%`",
        f"- Final scientific proof cap: `{summary.get('final_scientific_proof_cap_percent', 0)}%`",
        "",
        "## Locked gates",
        "",
    ]
    if gate_df.empty:
        lines.append("- No gates were generated.")
    else:
        for row in gate_df.to_dict(orient="records"):
            lines.append(
                "- "
                f"{row['title']}: {row['score_percent']}% ({row['status']}) - {row['remaining_action']}"
            )
    lines.extend(
        [
            "",
            "## Execution rule",
            "",
            "- Freeze public-source releases and model parameters before scoring the next independent/prospective cohort.",
            "- Report all variants, not only winners, and preserve failure modes as part of the scientific record.",
            "- Treat computational outputs as prioritization until orthogonal functional or structural experiments confirm the mechanism.",
            "",
            "## Cohort lock plan",
            "",
        ]
    )
    if cohort_df.empty:
        lines.append("- No cohort plan generated.")
    else:
        for row in cohort_df.to_dict(orient="records"):
            lines.append(
                "- "
                f"{row['cohort_id']}: {row['role']} | {row['status']} | primary endpoint: {row['primary_endpoint']}"
            )
    lines.extend(
        [
            "",
            "## Experimental confirmation criteria",
            "",
        ]
    )
    if criteria_df.empty:
        lines.append("- No confirmation criteria generated.")
    else:
        for row in criteria_df.to_dict(orient="records"):
            lines.append(
                "- "
                f"{row['criterion_id']}: {row['applies_to']} | {row['primary_readout']}"
            )
    lines.extend(
        [
            "",
            "## Blinded partner handoff",
            "",
            f"- Handoff targets generated: `{len(handoff_df)}`",
            "- Blinded IDs must be used until raw assay/QC outputs are sealed.",
            "- Therapeutic claims remain hypothesis-only until binding, rescue, toxicity and disease-relevant cellular evidence are complete.",
        ]
    )
    return "\n".join(lines).strip()


def build_prospective_validation_closure_package(
    *,
    multigene_annotation_enrichment_manifest_path: str,
    brca1_engine_execution_manifest_path: str,
    validation_credibility_closure_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    max_queue_rows: int = 12,
) -> dict[str, Any]:
    annotation_manifest = _load_json(multigene_annotation_enrichment_manifest_path)
    engine_manifest = _load_json(brca1_engine_execution_manifest_path)
    validation_manifest = _load_json(validation_credibility_closure_manifest_path)
    public_sync_manifest = _load_json(public_sync_closure_manifest_path)
    paired_mutant_manifest = _load_json(brca1_paired_mutant_execution_manifest_path)
    mutant_geometry_qc_manifest = _load_json(brca1_mutant_geometry_qc_manifest_path)
    annotation_summary = annotation_manifest.get("summary") or {}
    engine_summary = engine_manifest.get("summary") or {}
    validation_summary = validation_manifest.get("summary") or {}
    public_sync_summary = public_sync_manifest.get("summary") or {}
    paired_mutant_summary = paired_mutant_manifest.get("summary") or {}
    mutant_geometry_qc_summary = mutant_geometry_qc_manifest.get("summary") or {}
    annotation_matrix = _read_table(annotation_manifest.get("variant_annotation_matrix_path"))
    engine_queue = _read_table(engine_manifest.get("execution_queue_path"))
    paired_mutant_table = _read_table(paired_mutant_manifest.get("paired_mutant_table_path"))
    effective_annotation_readiness = max(
        _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 0),
        _percent(public_sync_summary.get("effective_line_level_annotation_readiness_percent"), 0),
    )
    effective_structural_readiness = max(
        _percent(engine_summary.get("execution_readiness_percent"), 0),
        _percent(paired_mutant_summary.get("paired_mutant_execution_readiness_percent"), 0),
        _percent(mutant_geometry_qc_summary.get("mutant_geometry_qc_readiness_percent"), 0),
    )

    gates = pd.DataFrame(
        _build_gates(
            annotation_summary=annotation_summary,
            public_sync_summary=public_sync_summary,
            engine_summary=engine_summary,
            paired_mutant_summary=paired_mutant_summary,
            mutant_geometry_qc_summary=mutant_geometry_qc_summary,
            validation_summary=validation_summary,
        )
    )
    queue = _experimental_queue(
        annotation_matrix=annotation_matrix,
        engine_queue=engine_queue,
        paired_mutant_table=paired_mutant_table,
        max_rows=max_queue_rows,
    )
    cohort_plan = _build_cohort_plan(
        annotation_summary=annotation_summary,
        public_sync_summary=public_sync_summary,
        validation_summary=validation_summary,
    )
    confirmation_criteria = _build_confirmation_criteria()
    partner_handoff = _build_partner_handoff(queue)
    gate_mean = _percent(gates["score_percent"].mean() if not gates.empty else 0)
    prospective_readiness = min(
        88,
        _percent(
            gate_mean * 0.55
            + effective_annotation_readiness * 0.20
            + effective_structural_readiness * 0.15
            + min(len(queue), max_queue_rows) / max(max_queue_rows, 1) * 10
        ),
    )
    experimental_completed = 0
    if not queue.empty and "lab_status" in queue.columns:
        experimental_completed = _percent(queue["lab_status"].astype(str).eq("completed").mean() * 100)
    artifact_readiness = 100 if len(cohort_plan) and len(confirmation_criteria) and len(partner_handoff) else 80
    summary = {
        "generated_at": _now_utc(),
        "prospective_validation_readiness_percent": prospective_readiness,
        "experimental_package_artifact_readiness_percent": artifact_readiness,
        "experimental_confirmation_completed_percent": experimental_completed,
        "functional_structural_confirmation_queue_count": int(len(queue)),
        "prospective_cohort_plan_count": int(len(cohort_plan)),
        "experimental_confirmation_criteria_count": int(len(confirmation_criteria)),
        "partner_handoff_variant_count": int(len(partner_handoff)),
        "sop_template_count": int(len(_sop_template_specs())),
        "validation_gate_count": int(len(gates)),
        "closed_or_strong_gate_count": int(gates["score_percent"].ge(80).sum()) if not gates.empty else 0,
        "final_scientific_proof_cap_percent": 88 if experimental_completed == 0 else 96,
        "ready_for_definitive_scientific_claims": experimental_completed >= 70 and prospective_readiness >= 90,
        "ready_for_definitive_therapeutic_claims": False,
        "ready_for_irb_or_partner_handoff": bool(len(partner_handoff) and prospective_readiness >= 75),
        "external_execution_status": "partner_lab_required",
        "why_not_100_percent": "Prospective independent scoring and wet-lab/biophysical confirmation still require external execution; this package locks the protocol and queue.",
        "source_manifests": {
            "multigene_annotation_enrichment_manifest_path": str(Path(multigene_annotation_enrichment_manifest_path).expanduser().resolve()),
            "brca1_engine_execution_manifest_path": str(Path(brca1_engine_execution_manifest_path).expanduser().resolve()),
            "validation_credibility_closure_manifest_path": (
                str(Path(validation_credibility_closure_manifest_path).expanduser().resolve())
                if validation_credibility_closure_manifest_path
                else None
            ),
            "public_sync_closure_manifest_path": (
                str(Path(public_sync_closure_manifest_path).expanduser().resolve())
                if public_sync_closure_manifest_path
                else None
            ),
            "brca1_paired_mutant_execution_manifest_path": (
                str(Path(brca1_paired_mutant_execution_manifest_path).expanduser().resolve())
                if brca1_paired_mutant_execution_manifest_path
                else None
            ),
            "brca1_mutant_geometry_qc_manifest_path": (
                str(Path(brca1_mutant_geometry_qc_manifest_path).expanduser().resolve())
                if brca1_mutant_geometry_qc_manifest_path
                else None
            ),
        },
    }
    payload = {
        "summary": summary,
        "validation_gates": gates,
        "experimental_confirmation_queue": queue,
        "prospective_cohort_plan": cohort_plan,
        "experimental_confirmation_criteria": confirmation_criteria,
        "partner_handoff_sheet": partner_handoff,
    }
    payload["markdown_report"] = _build_protocol_markdown(payload)
    payload["html_report"] = _render_markdown_html(payload["markdown_report"], "PrimeVarClass Prospective and Experimental Validation Protocol")
    payload["statistical_analysis_plan_markdown"] = _build_statistical_analysis_plan_markdown(payload)
    payload["external_partner_packet_markdown"] = _build_partner_packet_markdown(payload)
    payload["statistical_analysis_plan_html"] = _render_markdown_html(payload["statistical_analysis_plan_markdown"], "PrimeVarClass Statistical Analysis Plan")
    payload["external_partner_packet_html"] = _render_markdown_html(payload["external_partner_packet_markdown"], "PrimeVarClass External Partner Handoff")
    return payload


def export_prospective_validation_closure_package(
    *,
    multigene_annotation_enrichment_manifest_path: str,
    brca1_engine_execution_manifest_path: str,
    output_dir: str,
    validation_credibility_closure_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    max_queue_rows: int = 12,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_prospective_validation_closure_package(
        multigene_annotation_enrichment_manifest_path=multigene_annotation_enrichment_manifest_path,
        brca1_engine_execution_manifest_path=brca1_engine_execution_manifest_path,
        validation_credibility_closure_manifest_path=validation_credibility_closure_manifest_path,
        public_sync_closure_manifest_path=public_sync_closure_manifest_path,
        brca1_paired_mutant_execution_manifest_path=brca1_paired_mutant_execution_manifest_path,
        brca1_mutant_geometry_qc_manifest_path=brca1_mutant_geometry_qc_manifest_path,
        max_queue_rows=max_queue_rows,
    )

    gates_path = output_root / "prospective_validation_gates.csv"
    queue_path = output_root / "functional_structural_confirmation_queue.csv"
    cohort_plan_path = output_root / "prospective_validation_cohort_plan.csv"
    confirmation_criteria_path = output_root / "experimental_confirmation_criteria.csv"
    partner_handoff_path = output_root / "partner_lab_handoff_sheet.csv"
    statistical_plan_path = output_root / "statistical_analysis_plan.md"
    statistical_plan_html_path = output_root / "statistical_analysis_plan.html"
    partner_packet_path = output_root / "external_partner_handoff_packet.md"
    partner_packet_html_path = output_root / "external_partner_handoff_packet.html"
    sop_dir = output_root / "sop_templates"
    sop_manifest_path = output_root / "sop_template_manifest.csv"
    markdown_path = output_root / "prospective_validation_protocol.md"
    html_path = output_root / "prospective_validation_protocol.html"
    manifest_path = output_root / "prospective_validation_closure_manifest.json"

    gates = payload.get("validation_gates")
    (gates if isinstance(gates, pd.DataFrame) else pd.DataFrame()).to_csv(gates_path, index=False)
    queue = payload.get("experimental_confirmation_queue")
    (queue if isinstance(queue, pd.DataFrame) else pd.DataFrame()).to_csv(queue_path, index=False)
    cohort_plan = payload.get("prospective_cohort_plan")
    (cohort_plan if isinstance(cohort_plan, pd.DataFrame) else pd.DataFrame()).to_csv(cohort_plan_path, index=False)
    confirmation_criteria = payload.get("experimental_confirmation_criteria")
    (confirmation_criteria if isinstance(confirmation_criteria, pd.DataFrame) else pd.DataFrame()).to_csv(confirmation_criteria_path, index=False)
    partner_handoff = payload.get("partner_handoff_sheet")
    (partner_handoff if isinstance(partner_handoff, pd.DataFrame) else pd.DataFrame()).to_csv(partner_handoff_path, index=False)
    sop_manifest = _write_sop_templates(sop_dir)
    sop_manifest.to_csv(sop_manifest_path, index=False)
    markdown_path.write_text(str(payload.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(payload.get("html_report") or ""), encoding="utf-8")
    statistical_plan_path.write_text(str(payload.get("statistical_analysis_plan_markdown") or ""), encoding="utf-8")
    statistical_plan_html_path.write_text(str(payload.get("statistical_analysis_plan_html") or ""), encoding="utf-8")
    partner_packet_path.write_text(str(payload.get("external_partner_packet_markdown") or ""), encoding="utf-8")
    partner_packet_html_path.write_text(str(payload.get("external_partner_packet_html") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": payload.get("summary") or {},
        "validation_gates_path": str(gates_path),
        "functional_structural_confirmation_queue_path": str(queue_path),
        "prospective_validation_cohort_plan_path": str(cohort_plan_path),
        "experimental_confirmation_criteria_path": str(confirmation_criteria_path),
        "partner_lab_handoff_sheet_path": str(partner_handoff_path),
        "statistical_analysis_plan_path": str(statistical_plan_path),
        "statistical_analysis_plan_html_path": str(statistical_plan_html_path),
        "external_partner_handoff_packet_path": str(partner_packet_path),
        "external_partner_handoff_packet_html_path": str(partner_packet_html_path),
        "sop_templates_dir": str(sop_dir),
        "sop_template_manifest_path": str(sop_manifest_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "prospective_validation_closure": payload,
        "prospective_validation_closure_manifest_path": str(manifest_path),
        "prospective_validation_gates_path": str(gates_path),
        "functional_structural_confirmation_queue_path": str(queue_path),
        "prospective_validation_cohort_plan_path": str(cohort_plan_path),
        "experimental_confirmation_criteria_path": str(confirmation_criteria_path),
        "partner_lab_handoff_sheet_path": str(partner_handoff_path),
        "statistical_analysis_plan_path": str(statistical_plan_path),
        "statistical_analysis_plan_html_path": str(statistical_plan_html_path),
        "external_partner_handoff_packet_path": str(partner_packet_path),
        "external_partner_handoff_packet_html_path": str(partner_packet_html_path),
        "sop_templates_dir": str(sop_dir),
        "sop_template_manifest_path": str(sop_manifest_path),
        "prospective_validation_protocol_markdown_path": str(markdown_path),
        "prospective_validation_protocol_html_path": str(html_path),
    }
