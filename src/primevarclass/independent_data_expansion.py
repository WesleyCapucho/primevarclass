from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .source_presets import PRESET_REGISTRY


DEFAULT_EXPANSION_GENES = ("BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9")


INDEPENDENT_DATABASE_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "source_id": "clinvar",
        "display_name": "ClinVar",
        "evidence_lane": "clinical_labels",
        "recommended_use": "training_and_external_holdout",
        "independence_role": "core clinical supervision plus release-frozen expert-panel holdout",
        "source_kind": "cohort",
        "preset": "clinvar_variant_summary",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/",
        "download_url_hint": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
        "local_stage_path": "data/raw/clinvar/variant_summary.txt.gz",
        "join_on": "gene,hgvs_p",
        "priority": "critical",
        "validation_value": "Release-frozen clinical labels, review status, expert-panel separation, and prospective release cutoffs.",
        "caveat": "Avoid leakage: expert or newest releases should be locked away from training when used as validation.",
    },
    {
        "source_id": "clingen_erepo",
        "display_name": "ClinGen Evidence Repository",
        "evidence_lane": "expert_curation",
        "recommended_use": "independent_validation",
        "independence_role": "FDA-recognized expert assertions for adjudication and holdout checks",
        "source_kind": "cohort",
        "preset": "clingen_erepo_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://erepo.clinicalgenome.org/evrepo/",
        "download_url_hint": "https://erepo.genome.network/",
        "local_stage_path": "data/raw/clingen_erepo/clingen_erepo_gene_panel.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "critical",
        "validation_value": "Independent expert assertions and provenance can verify whether PrimeVarClass generalizes beyond ClinVar-only labels.",
        "caveat": "Use as external validation unless a deliberate, versioned training release is created.",
    },
    {
        "source_id": "brca_exchange_enigma",
        "display_name": "BRCA Exchange / ENIGMA",
        "evidence_lane": "expert_brca_curation",
        "recommended_use": "brca_external_validation",
        "independence_role": "BRCA-specific expert adjudication and conflict resolution",
        "source_kind": "cohort",
        "preset": "enigma_brca",
        "format": "tsv",
        "access_level": "open_or_curated_public_release",
        "automation_level": "manual_assisted",
        "official_url": "https://enigmaconsortium.org/",
        "download_url_hint": "stage BRCA Exchange or ENIGMA-derived release file locally",
        "local_stage_path": "data/raw/brca_exchange/brca_exchange_enigma_curated.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "critical",
        "validation_value": "Strong BRCA-specific independent expert source for the first high-impact disease area.",
        "caveat": "Confirm redistribution and release terms before bundling raw tables.",
    },
    {
        "source_id": "gnomad",
        "display_name": "gnomAD",
        "evidence_lane": "population_frequency",
        "recommended_use": "annotation_and_calibration",
        "independence_role": "population rarity, ancestry-aware frequency, and constraint control",
        "source_kind": "annotation",
        "preset": "gnomad_variant_table",
        "format": "tsv",
        "access_level": "open_public_with_large_files",
        "automation_level": "semi_automatable",
        "official_url": "https://gnomad.broadinstitute.org/downloads",
        "download_url_hint": "use gene-filtered browser table, Hail table, or GraphQL/toolbox extraction",
        "local_stage_path": "data/raw/gnomad/target_gene_missense_annotations.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "critical",
        "validation_value": "Population allele frequency is essential for pathogenicity calibration and rare-variant plausibility.",
        "caveat": "Full files are large; freeze release and ancestry fields before publication claims.",
    },
    {
        "source_id": "mavedb",
        "display_name": "MaveDB",
        "evidence_lane": "functional_assay",
        "recommended_use": "functional_validation",
        "independence_role": "experimental variant-effect evidence for mechanism and calibration",
        "source_kind": "annotation",
        "preset": "mavedb_score_table",
        "format": "csv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://www.mavedb.org/",
        "download_url_hint": "use public score-set CSVs, mapped variants, or bulk release dump",
        "local_stage_path": "data/raw/mavedb/target_gene_function_scores.csv",
        "join_on": "gene,hgvs_p",
        "priority": "critical",
        "validation_value": "Direct functional effect data helps discover mechanism and evaluate predictions beyond labels.",
        "caveat": "Assays differ by gene, domain, and cellular context; benchmark by assay family when possible.",
    },
    {
        "source_id": "alphamissense",
        "display_name": "AlphaMissense",
        "evidence_lane": "external_predictor",
        "recommended_use": "baseline_comparator_and_disagreement_discovery",
        "independence_role": "independent proteome-wide missense prior for comparator analyses",
        "source_kind": "annotation",
        "preset": "alphamissense_table",
        "format": "tsv",
        "access_level": "open_public_cc_by",
        "automation_level": "semi_automatable",
        "official_url": "https://storage.googleapis.com/dm_alphamissense/README.pdf",
        "download_url_hint": "stage AlphaMissense_hg38.tsv.gz or amino-acid substitution subset",
        "local_stage_path": "data/raw/alphamissense/target_gene_alphamissense.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "high",
        "validation_value": "Useful for head-to-head comparison and cases where prime features disagree with a strong external predictor.",
        "caveat": "Do not use predictor scores as ground truth labels.",
    },
    {
        "source_id": "uniprot",
        "display_name": "UniProt",
        "evidence_lane": "protein_context",
        "recommended_use": "protein_annotation",
        "independence_role": "reviewed sequence, accession, domain, and function backbone",
        "source_kind": "annotation",
        "preset": "uniprot_feature_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://www.uniprot.org/api-documentation",
        "download_url_hint": "REST reviewed human gene/accession export",
        "local_stage_path": "data/raw/uniprot/target_gene_uniprot_features.tsv",
        "join_on": "gene",
        "priority": "high",
        "validation_value": "Protein context anchors structural, proteomic, and quantum modules to stable accessions.",
        "caveat": "Freeze accession and isoform mapping for each benchmark release.",
    },
    {
        "source_id": "alphafold_db",
        "display_name": "AlphaFold DB",
        "evidence_lane": "predicted_structure",
        "recommended_use": "structure_prior",
        "independence_role": "3D model prior for residue environment, fragments, and quantum target selection",
        "source_kind": "annotation",
        "preset": "alphafold_model_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "semi_automatable",
        "official_url": "https://alphafold.ebi.ac.uk/",
        "download_url_hint": "stage accession-specific model metadata and coordinate URLs",
        "local_stage_path": "data/raw/alphafold/target_gene_alphafold_models.tsv",
        "join_on": "gene",
        "priority": "high",
        "validation_value": "Connects variant predictions to 3D residue neighborhoods and protein-fragment engines.",
        "caveat": "Predicted structures are not experimental validation; use PDB or lab confirmation when possible.",
    },
    {
        "source_id": "pdb",
        "display_name": "RCSB PDB",
        "evidence_lane": "experimental_structure",
        "recommended_use": "structural_validation_overlay",
        "independence_role": "experimental structural evidence around domains, interfaces, and ligands",
        "source_kind": "annotation",
        "preset": "pdb_structure_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "semi_automatable",
        "official_url": "https://www.rcsb.org/",
        "download_url_hint": "stage Data API/Search API structure metadata by accession/gene",
        "local_stage_path": "data/raw/pdb/target_gene_pdb_structures.tsv",
        "join_on": "gene",
        "priority": "high",
        "validation_value": "Experimental structures strengthen mechanistic interpretation and drug-discovery target selection.",
        "caveat": "Coverage can be fragmentary; require residue/domain overlap checks.",
    },
    {
        "source_id": "civic",
        "display_name": "CIViC",
        "evidence_lane": "translational_oncology",
        "recommended_use": "translational_validation",
        "independence_role": "curated disease, therapy, and evidence items for cancer variants",
        "source_kind": "annotation",
        "preset": "civic_variant_table",
        "format": "tsv",
        "access_level": "open_public_research_use",
        "automation_level": "automatable",
        "official_url": "https://docs.civicdb.org/en/latest/using/data_releases.html",
        "download_url_hint": "nightly or historical monthly TSV/VCF release",
        "local_stage_path": "data/raw/civic/target_gene_civic_evidence.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "high",
        "validation_value": "Adds translational oncology actionability without turning actionability into a pathogenicity label.",
        "caveat": "Research use only; do not present as clinical medical advice.",
    },
    {
        "source_id": "cbioportal",
        "display_name": "cBioPortal Datahub",
        "evidence_lane": "somatic_cancer_cohorts",
        "recommended_use": "cancer_context_external_validation",
        "independence_role": "independent tumor cohorts and study-level cancer mutation context",
        "source_kind": "annotation",
        "preset": "cbioportal_mutation_table",
        "format": "tsv",
        "access_level": "open_public_with_study_licenses",
        "automation_level": "semi_automatable",
        "official_url": "https://github.com/cBioPortal/datahub",
        "download_url_hint": "download selected public study folders, e.g. public/brca_tcga",
        "local_stage_path": "data/raw/cbioportal/target_gene_cbioportal_mutations.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "high",
        "validation_value": "Tests cross-context signal in tumor cohorts for cancer genes such as BRCA1, TP53, PTEN, MSH2, and KRAS.",
        "caveat": "Somatic recurrence is a different endpoint from germline pathogenicity.",
    },
    {
        "source_id": "gdc",
        "display_name": "NCI Genomic Data Commons",
        "evidence_lane": "tcga_gdc_cancer_cohorts",
        "recommended_use": "open_cancer_context_validation",
        "independence_role": "large cancer-genomics cohort context and clinical metadata",
        "source_kind": "annotation",
        "preset": "gdc_maf_table",
        "format": "tsv",
        "access_level": "open_plus_controlled_tiers",
        "automation_level": "semi_automatable",
        "official_url": "https://gdc.cancer.gov/access-data",
        "download_url_hint": "use open MAF/project metadata via GDC API; controlled files require dbGaP",
        "local_stage_path": "data/raw/gdc/target_gene_gdc_open_maf.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "high",
        "validation_value": "Adds an independent, clinically annotated cancer-context layer for translational claims.",
        "caveat": "Keep controlled-access and open-access cohorts separated in all manifests.",
    },
    {
        "source_id": "gwas_catalog",
        "display_name": "GWAS Catalog",
        "evidence_lane": "genetic_association",
        "recommended_use": "disease_trait_context",
        "independence_role": "literature-curated associations for gene/variant plausibility",
        "source_kind": "annotation",
        "preset": "gwas_catalog_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://www.ebi.ac.uk/gwas/rest/api/v2/docs",
        "download_url_hint": "REST API by trait, variant, study, or mapped gene",
        "local_stage_path": "data/raw/gwas_catalog/target_gene_gwas_associations.tsv",
        "join_on": "gene",
        "priority": "medium",
        "validation_value": "Supports biological plausibility, disease breadth, and target-discovery narratives.",
        "caveat": "Association evidence is not functional causality or variant pathogenicity.",
    },
    {
        "source_id": "opentargets",
        "display_name": "Open Targets Platform",
        "evidence_lane": "target_disease_evidence",
        "recommended_use": "translational_target_prioritization",
        "independence_role": "multi-evidence target-disease and variant-to-phenotype context",
        "source_kind": "annotation",
        "preset": "opentargets_variant_table",
        "format": "tsv",
        "access_level": "open_public",
        "automation_level": "automatable",
        "official_url": "https://platform-docs.opentargets.org/variant",
        "download_url_hint": "GraphQL API or bulk data filtered by target/disease/variant",
        "local_stage_path": "data/raw/opentargets/target_gene_opentargets_evidence.tsv",
        "join_on": "gene",
        "priority": "medium",
        "validation_value": "Strengthens translational target selection and mechanism-to-disease mapping.",
        "caveat": "Aggregate scores require source-level evidence audit for strong scientific claims.",
    },
    {
        "source_id": "pharmgkb",
        "display_name": "PharmGKB / ClinPGx",
        "evidence_lane": "pharmacogenomics",
        "recommended_use": "drug_response_context",
        "independence_role": "variant-drug and gene-drug actionability evidence",
        "source_kind": "annotation",
        "preset": "pharmgkb_table",
        "format": "tsv",
        "access_level": "public_with_data_usage_terms",
        "automation_level": "automatable",
        "official_url": "https://api.pharmgkb.org/",
        "download_url_hint": "ClinPGx API or PharmGKB bulk downloads under applicable terms",
        "local_stage_path": "data/raw/pharmgkb/target_gene_pharmgkb_annotations.tsv",
        "join_on": "gene",
        "priority": "medium",
        "validation_value": "Adds drug-response and pharmacogenomic context for translational reports.",
        "caveat": "Often not disease-pathogenicity evidence; keep as a separate translational lane.",
    },
    {
        "source_id": "lovd",
        "display_name": "LOVD",
        "evidence_lane": "locus_specific_variation",
        "recommended_use": "supplemental_external_validation",
        "independence_role": "gene-centered observations and curated locus-specific repositories",
        "source_kind": "cohort",
        "preset": "lovd_variant_table",
        "format": "tsv",
        "access_level": "public_heterogeneous",
        "automation_level": "manual_assisted",
        "official_url": "https://www.lovd.nl/2.0/index_list.php",
        "download_url_hint": "stage gene-specific export after database-level QC",
        "local_stage_path": "data/raw/lovd/target_gene_lovd_variants.tsv",
        "join_on": "gene,hgvs_p",
        "priority": "conditional",
        "validation_value": "Can expose population- or locus-specific evidence not captured in broad aggregators.",
        "caveat": "Different LOVD installations have different schemas and curation depth.",
    },
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_genes(target_genes: Iterable[str] | None) -> list[str]:
    genes: list[str] = []
    seen: set[str] = set()
    for value in target_genes or DEFAULT_EXPANSION_GENES:
        gene = str(value or "").strip().upper()
        if gene and gene not in seen:
            seen.add(gene)
            genes.append(gene)
    return genes or list(DEFAULT_EXPANSION_GENES)


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


def _readiness_for_source(row: dict[str, Any]) -> int:
    preset_ready = str(row.get("preset") or "") in PRESET_REGISTRY
    automation = str(row.get("automation_level") or "")
    access = str(row.get("access_level") or "")
    score = 55
    if preset_ready:
        score += 25
    if automation == "automatable":
        score += 15
    elif automation == "semi_automatable":
        score += 10
    elif automation == "manual_assisted":
        score += 4
    if "controlled" in access:
        score -= 8
    if str(row.get("priority")) in {"critical", "high"}:
        score += 4
    return max(0, min(100, int(score)))


def _has_local_stage(row: dict[str, Any]) -> bool:
    configured_path = Path(str(row.get("local_stage_path") or ""))
    if configured_path.exists():
        return True
    source_id = str(row.get("source_id") or "")
    fallback_dirs = {
        "brca_exchange_enigma": [Path("data/raw/brca_exchange")],
        "clinvar": [Path("data/raw/clinvar")],
        "gnomad": [Path("data/raw/gnomad")],
        "mavedb": [Path("data/raw/mavedb")],
    }.get(source_id, [Path("data/raw") / source_id])
    for directory in fallback_dirs:
        if directory.exists() and any(path.is_file() for path in directory.rglob("*")):
            return True
    return False


def _materialize_registry_rows(target_genes: list[str], include_restricted_sources: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in INDEPENDENT_DATABASE_REGISTRY:
        access = str(item.get("access_level") or "")
        if not include_restricted_sources and access == "controlled_only":
            continue
        row = dict(item)
        row["target_genes"] = ";".join(target_genes)
        row["supported_preset"] = str(row.get("preset") or "") in PRESET_REGISTRY
        row["readiness_percent"] = _readiness_for_source(row)
        row["local_stage_exists"] = _has_local_stage(row)
        row["claim_safe_role"] = (
            "label_or_holdout"
            if row.get("source_kind") == "cohort" and row.get("recommended_use") in {"training_and_external_holdout", "independent_validation", "brca_external_validation", "supplemental_external_validation"}
            else "annotation_or_mechanistic_evidence"
        )
        row["should_train_as_label"] = row.get("recommended_use") in {"training_and_external_holdout"} and row.get("source_id") == "clinvar"
        row["should_validate_independently"] = row.get("recommended_use") in {
            "independent_validation",
            "brca_external_validation",
            "cancer_context_external_validation",
            "open_cancer_context_validation",
            "functional_validation",
            "supplemental_external_validation",
        }
        rows.append(row)
    return rows


def _build_training_validation_plan(registry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes = [
        {
            "phase": "01_sync_freeze",
            "objective": "Download or stage every source into a versioned, hashed local release.",
            "sources": "all",
            "success_criterion": "Manifest has source URL, release, hash, row count, schema preset, and access terms.",
            "claim_boundary": "No model claim yet; this is data governance.",
        },
        {
            "phase": "02_supervised_training",
            "objective": "Train only on allowed clinical-label cohorts and separate expert/newer releases.",
            "sources": "ClinVar training split",
            "success_criterion": "Training labels are release-frozen and leakage checks pass against external holdouts.",
            "claim_boundary": "Computational model claim only; no clinical-use claim.",
        },
        {
            "phase": "03_independent_validation",
            "objective": "Evaluate held-out expert, BRCA-specific, locus-specific, and prospective release cohorts.",
            "sources": "ClinGen ERepo; BRCA Exchange/ENIGMA; LOVD; newest ClinVar release",
            "success_criterion": "AUC/PR/MCC/calibration hold across sources and genes without training contamination.",
            "claim_boundary": "Supports scientific credibility if confidence intervals and no-regression gates pass.",
        },
        {
            "phase": "04_functional_mechanistic_validation",
            "objective": "Triangulate predictions with MAVE, structural, protein, and quantum evidence.",
            "sources": "MaveDB; AlphaMissense; UniProt; AlphaFold DB; RCSB PDB",
            "success_criterion": "High-risk predictions show consistent functional/structural signal or explainable disagreement.",
            "claim_boundary": "Mechanistic insight is hypothesis-generating until lab-confirmed.",
        },
        {
            "phase": "05_translational_generalization",
            "objective": "Test disease breadth and actionability without using actionability as pathogenicity labels.",
            "sources": "CIViC; cBioPortal; GDC; GWAS Catalog; Open Targets; PharmGKB",
            "success_criterion": "Cancer, disease, and drug-evidence layers improve prioritization and reporting traceability.",
            "claim_boundary": "Translational prioritization claim only; not treatment recommendation.",
        },
        {
            "phase": "06_prospective_lock",
            "objective": "Lock a model, wait for new public releases, then evaluate unseen variants prospectively.",
            "sources": "future ClinVar/ClinGen/MaveDB/gnomAD releases",
            "success_criterion": "Pre-registered endpoints pass on variants absent from the locked training timestamp.",
            "claim_boundary": "This is the strongest route toward publication-grade independent validation.",
        },
    ]
    rows: list[dict[str, Any]] = []
    for lane in lanes:
        source_count = len(registry_rows) if lane["sources"] == "all" else sum(1 for item in registry_rows if str(item.get("display_name") or "").split()[0] in lane["sources"])
        row = dict(lane)
        row["source_count_hint"] = source_count
        rows.append(row)
    return rows


def _build_gene_matrix(registry_rows: list[dict[str, Any]], target_genes: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cancer_genes = {"BRCA1", "BRCA2", "TP53", "PTEN", "MSH2", "KRAS"}
    brca_genes = {"BRCA1", "BRCA2"}
    for gene in target_genes:
        for source in registry_rows:
            source_id = str(source.get("source_id") or "")
            recommended = True
            if source_id == "brca_exchange_enigma" and gene not in brca_genes:
                recommended = False
            if source_id in {"civic", "cbioportal", "gdc"} and gene not in cancer_genes:
                recommended = False
            rows.append(
                {
                    "gene": gene,
                    "source_id": source_id,
                    "display_name": source.get("display_name"),
                    "evidence_lane": source.get("evidence_lane"),
                    "recommended_for_gene": recommended,
                    "recommended_use": source.get("recommended_use"),
                    "join_on": source.get("join_on"),
                    "readiness_percent": source.get("readiness_percent"),
                    "next_step": (
                        "stage_source_and_include_in_benchmark"
                        if recommended and source.get("should_validate_independently")
                        else "stage_as_annotation_or_context"
                        if recommended
                        else "optional_after_primary_gene_scope"
                    ),
                }
            )
    return rows


def _toml_array(values: Iterable[str]) -> str:
    return "[" + ", ".join(json.dumps(str(value)) for value in values) + "]"


def _build_source_template_toml(registry_rows: list[dict[str, Any]], target_genes: list[str]) -> str:
    lines = [
        "# PrimeVarClass independent public-source template",
        "# Stage the listed files locally, confirm release/licensing, then run with --source-config.",
        "",
        "[ingestion]",
        'deduplicate_on = ["gene", "hgvs_p", "label"]',
        "prefer_annotation_values = true",
        "",
    ]
    for row in registry_rows:
        lines.extend(
            [
                "[[sources]]",
                f'name = "{row["source_id"]}_staged"',
                f'kind = "{row["source_kind"]}"',
                'type = "file"',
                f'format = "{row["format"]}"',
                f'path = "{row["local_stage_path"]}"',
                f'preset = "{row["preset"]}"',
                f'gene_allowlist = {_toml_array(target_genes)}',
                f'join_on = {_toml_array(str(row["join_on"]).split(","))}',
                f'release_version = "{row["source_id"]}_release_to_freeze"',
                f'# official_url = "{row["official_url"]}"',
                f'# download_url_hint = "{row["download_url_hint"]}"',
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_markdown_report(summary: dict, registry_rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]]) -> str:
    critical_sources = [row["display_name"] for row in registry_rows if row.get("priority") == "critical"]
    high_sources = [row["display_name"] for row in registry_rows if row.get("priority") == "high"]
    lines = [
        "# Independent Real-Data Expansion",
        "",
        f"- Target genes: {', '.join(summary['target_genes'])}",
        f"- Public/independent databases mapped: {summary['database_count']}",
        f"- Supported ingestion presets: {summary['supported_preset_count']}/{summary['database_count']}",
        f"- Automatable or semi-automatable sources: {summary['automatable_or_semi_automatable_count']}",
        f"- Connector/template readiness: {summary['connector_template_readiness_percent']}%",
        f"- Locally staged line-level sources: {summary['locally_staged_source_count']}/{summary['database_count']}",
        f"- Independent data expansion readiness: {summary['independent_data_expansion_percent']}%",
        "",
        "## Critical sources",
        "",
        "- " + "; ".join(critical_sources),
        "",
        "## High-value expansion sources",
        "",
        "- " + "; ".join(high_sources),
        "",
        "## Validation plan",
        "",
    ]
    for item in plan_rows:
        lines.append(f"- {item['phase']}: {item['objective']} Success: {item['success_criterion']}")
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This package expands real-data readiness and source interoperability. It does not by itself prove clinical validity. Strong claims still require frozen independent benchmarks, prospective validation, and functional/structural confirmation for prioritized targets.",
        ]
    )
    return "\n".join(lines)


def build_independent_data_expansion_package(
    *,
    target_genes: Iterable[str] | None = None,
    include_restricted_sources: bool = False,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    genes = _normalize_genes(target_genes)
    registry_rows = _materialize_registry_rows(genes, include_restricted_sources=include_restricted_sources)
    plan_rows = _build_training_validation_plan(registry_rows)
    gene_matrix_rows = _build_gene_matrix(registry_rows, genes)

    supported_count = sum(1 for row in registry_rows if row.get("supported_preset"))
    automatable_count = sum(1 for row in registry_rows if row.get("automation_level") in {"automatable", "semi_automatable"})
    independent_validation_count = sum(1 for row in registry_rows if row.get("should_validate_independently"))
    functional_count = sum(1 for row in registry_rows if row.get("evidence_lane") in {"functional_assay", "external_predictor", "protein_context", "predicted_structure", "experimental_structure"})
    translational_count = sum(1 for row in registry_rows if row.get("evidence_lane") in {"translational_oncology", "somatic_cancer_cohorts", "tcga_gdc_cancer_cohorts", "target_disease_evidence", "pharmacogenomics"})
    locally_staged_count = sum(1 for row in registry_rows if row.get("local_stage_exists"))
    mean_readiness = int(round(sum(int(row.get("readiness_percent") or 0) for row in registry_rows) / max(len(registry_rows), 1)))
    connector_template_readiness_percent = max(0, min(100, mean_readiness + (8 if supported_count == len(registry_rows) else 0)))
    line_level_real_data_execution_percent = int(round((locally_staged_count / max(len(registry_rows), 1)) * 100))
    independent_data_expansion_percent = min(
        connector_template_readiness_percent,
        92 + int(round(line_level_real_data_execution_percent * 0.08)),
    )

    summary = {
        "target_genes": genes,
        "database_count": int(len(registry_rows)),
        "supported_preset_count": int(supported_count),
        "automatable_or_semi_automatable_count": int(automatable_count),
        "independent_validation_source_count": int(independent_validation_count),
        "functional_or_structural_source_count": int(functional_count),
        "translational_source_count": int(translational_count),
        "locally_staged_source_count": int(locally_staged_count),
        "mean_source_readiness_percent": int(mean_readiness),
        "connector_template_readiness_percent": int(connector_template_readiness_percent),
        "line_level_real_data_execution_percent": int(line_level_real_data_execution_percent),
        "independent_data_expansion_percent": int(independent_data_expansion_percent),
        "ready_for_more_real_data_training": bool(supported_count >= 8 and independent_validation_count >= 4),
        "strong_claim_requires": [
            "line-level staged files downloaded and hashed",
            "locked train/validation separation by source and release date",
            "prospective release holdout after model freeze",
            "functional or structural confirmation for top targets",
        ],
    }

    return {
        "generated_at": _now_utc(),
        "summary": summary,
        "registry": registry_rows,
        "training_validation_plan": plan_rows,
        "gene_source_matrix": gene_matrix_rows,
        "source_template_toml": _build_source_template_toml(registry_rows, genes),
        "report_context": dict(report_context or {}),
    }


def export_independent_data_expansion_package(
    *,
    output_dir: str,
    target_genes: Iterable[str] | None = None,
    include_restricted_sources: bool = False,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    package = build_independent_data_expansion_package(
        target_genes=target_genes,
        include_restricted_sources=include_restricted_sources,
        report_context=report_context,
    )

    registry_path = output_root / "independent_public_database_registry.csv"
    plan_path = output_root / "independent_training_validation_plan.csv"
    gene_matrix_path = output_root / "independent_gene_source_matrix.csv"
    source_template_path = output_root / "independent_source_templates.toml"
    manifest_path = output_root / "independent_data_expansion_manifest.json"
    markdown_path = output_root / "independent_data_expansion_report.md"
    html_path = output_root / "independent_data_expansion_report.html"

    _write_csv(registry_path, list(package["registry"]))
    _write_csv(plan_path, list(package["training_validation_plan"]))
    _write_csv(gene_matrix_path, list(package["gene_source_matrix"]))
    source_template_path.write_text(str(package["source_template_toml"]), encoding="utf-8")

    markdown = _build_markdown_report(
        dict(package["summary"]),
        list(package["registry"]),
        list(package["training_validation_plan"]),
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, title="Independent Real-Data Expansion"), encoding="utf-8")

    manifest = {
        "generated_at": package["generated_at"],
        "summary": package["summary"],
        "artifact_paths": {
            "registry_csv": str(registry_path),
            "training_validation_plan_csv": str(plan_path),
            "gene_source_matrix_csv": str(gene_matrix_path),
            "source_template_toml": str(source_template_path),
            "markdown_report": str(markdown_path),
            "html_report": str(html_path),
        },
        "registry": package["registry"],
        "training_validation_plan": package["training_validation_plan"],
        "report_context": package["report_context"],
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "independent_data_expansion_manifest_path": str(manifest_path),
        "independent_public_database_registry_path": str(registry_path),
        "independent_training_validation_plan_path": str(plan_path),
        "independent_gene_source_matrix_path": str(gene_matrix_path),
        "independent_source_templates_path": str(source_template_path),
        "independent_data_expansion_report_markdown_path": str(markdown_path),
        "independent_data_expansion_report_html_path": str(html_path),
        "summary": package["summary"],
    }
