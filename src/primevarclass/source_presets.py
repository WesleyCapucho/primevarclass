from __future__ import annotations

import re
from typing import Callable, Dict

import pandas as pd

from .core import normalize_clinvar_dataframe, normalize_gene, normalize_hgvs_protein

PROTEIN_CHANGE_PATTERN = re.compile(r"p\.([A-Za-z]{1,3}\d+[A-Za-z]{1,3}|[A-Za-z]{1,3}\d+\*)")


def _rename_first_available(df: pd.DataFrame, target: str, candidates: list[str]) -> pd.DataFrame:
    renamed = df.copy()
    if target in renamed.columns:
        return renamed
    for candidate in candidates:
        if candidate in renamed.columns:
            renamed = renamed.rename(columns={candidate: target})
            break
    return renamed


def _extract_protein_change(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    match = PROTEIN_CHANGE_PATTERN.search(text)
    if match:
        return f"p.{match.group(1)}"
    return text if text.startswith("p.") else None


def canonicalize_variant_keys(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    if "gene" in normalized.columns:
        normalized["gene"] = normalized["gene"].apply(lambda value: normalize_gene(value) if pd.notna(value) else None)

    if "hgvs_p" in normalized.columns:
        normalized["hgvs_p"] = normalized.apply(
            lambda row: normalize_hgvs_protein(row.get("hgvs_p"), gene=row.get("gene")),
            axis=1,
        )

    return normalized


def preset_none(df: pd.DataFrame) -> pd.DataFrame:
    return canonicalize_variant_keys(df)


def preset_clinvar(df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_clinvar_dataframe(df)
    normalized = _rename_first_available(normalized, "protein_change_raw", ["Name", "name"])
    if "hgvs_p" not in normalized.columns and "protein_change_raw" in normalized.columns:
        normalized["hgvs_p"] = normalized["protein_change_raw"].apply(_extract_protein_change)
    normalized["meta_dataset"] = "clinvar"
    return canonicalize_variant_keys(normalized)


def preset_clinvar_variant_summary(df: pd.DataFrame) -> pd.DataFrame:
    normalized = preset_clinvar(df)
    normalized = _rename_first_available(normalized, "meta_clinvar_accession", ["AlleleID", "allele_id"])
    normalized = _rename_first_available(normalized, "meta_clinvar_variation_id", ["VariationID", "variation_id"])
    normalized = _rename_first_available(normalized, "meta_clinvar_type", ["Type", "type"])
    normalized = _rename_first_available(normalized, "meta_clinvar_name", ["Name", "name"])
    return normalized


def preset_gnomad_variant_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "gene_symbol", "Gene", "symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "hgvsp", "HGVSp", "hgvs_pro", "protein_change"])

    alias_map = {
        "feature_gnomad_af": ["af", "AF", "joint_af", "genome_af"],
        "feature_gnomad_ac": ["ac", "AC"],
        "feature_gnomad_an": ["an", "AN"],
        "feature_gnomad_nhomalt": ["nhomalt", "n_homalt", "hom_alt"],
        "feature_gnomad_popmax_af": ["popmax_af", "AF_popmax", "faf95_popmax"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "gnomad")
    return canonicalize_variant_keys(normalized)


def preset_mavedb_score_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "target_gene", "Gene"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "hgvs_pro", "hgvsp", "protein_variant"])

    alias_map = {
        "feature_mave_score": ["score", "functional_score", "score_value"],
        "feature_mave_se": ["score_se", "se", "standard_error"],
        "feature_mave_qvalue": ["q_value", "qvalue", "q_val"],
        "feature_mave_pvalue": ["p_value", "pvalue"],
        "feature_mave_annotation": ["annotation", "functional_class", "consequence"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized = _rename_first_available(normalized, "meta_mavedb_urn", ["urn", "score_set_urn"])
    normalized = _rename_first_available(normalized, "meta_assay_name", ["title", "assay_name", "experiment_title"])
    normalized["meta_dataset"] = normalized.get("meta_dataset", "mavedb")
    return canonicalize_variant_keys(normalized)


def preset_enigma_brca(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "gene_symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "protein_change", "Protein change", "hgvsp"])
    normalized = _rename_first_available(normalized, "label", ["classification", "Classification", "clinical_significance"])
    normalized["meta_dataset"] = normalized.get("meta_dataset", "enigma")
    return canonicalize_variant_keys(normalized)


def preset_uniprot_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene Names (primary)", "gene_primary", "gene_symbol"])
    normalized = _rename_first_available(normalized, "meta_uniprot_accession", ["accession", "Entry", "primaryAccession", "uniprot_accession"])

    alias_map = {
        "feature_uniprot_sequence_length": ["length", "Sequence length", "sequence_length"],
        "feature_uniprot_reviewed": ["reviewed", "Reviewed", "entryType"],
        "feature_uniprot_domain_count": ["domain_count", "domains_count", "feature_domain_count"],
        "feature_uniprot_disease_annotation_count": ["disease_annotation_count", "disease_count"],
        "feature_uniprot_keyword_count": ["keyword_count", "keywords_count"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "uniprot")
    return canonicalize_variant_keys(normalized)


def preset_alphafold_model_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "gene_symbol", "Gene"])
    normalized = _rename_first_available(normalized, "meta_uniprot_accession", ["uniprot_accession", "uniprotAccession", "entryId", "accession"])

    alias_map = {
        "feature_alphafold_model_url": ["model_url", "modelUrl", "cifUrl", "bcifUrl"],
        "feature_alphafold_pae_url": ["pae_url", "paeDocUrl", "predicted_aligned_error_url"],
        "feature_alphafold_plddt_mean": ["plddt_mean", "confidenceScore", "mean_plddt"],
        "feature_alphafold_fragment_start": ["fragment_start", "uniprotStart"],
        "feature_alphafold_fragment_end": ["fragment_end", "uniprotEnd"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "alphafold_db")
    return canonicalize_variant_keys(normalized)


def preset_pdb_structure_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "gene_symbol", "Gene"])
    normalized = _rename_first_available(normalized, "meta_pdb_id", ["pdb_id", "rcsb_id", "entry_id", "id"])

    alias_map = {
        "feature_pdb_experimental_method": ["experimental_method", "method", "exptl.method"],
        "feature_pdb_resolution": ["resolution", "rcsb_entry_info.resolution_combined"],
        "feature_pdb_chain_count": ["chain_count", "polymer_entity_count", "rcsb_entry_info.polymer_entity_count"],
        "feature_pdb_ligand_count": ["ligand_count", "nonpolymer_entity_count", "rcsb_entry_info.nonpolymer_entity_count"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "pdb")
    return canonicalize_variant_keys(normalized)


def preset_civic_variant_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "gene_symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "protein_change", "variant", "name"])

    alias_map = {
        "feature_civic_evidence_count": ["evidence_count", "assertion_count", "evidence_items"],
        "feature_civic_level": ["evidence_level", "level", "evidence_level_label"],
        "feature_civic_rating": ["rating", "trust_rating", "average_rating"],
        "feature_civic_disease": ["disease", "disease_name"],
        "feature_civic_drug": ["drug", "drugs", "therapy"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "civic")
    return canonicalize_variant_keys(normalized)


def preset_clingen_erepo_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "gene_symbol", "Gene Symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "HGVS", "hgvsp", "protein_change"])
    normalized = _rename_first_available(normalized, "label", ["classification", "Classification", "clinical_significance"])

    alias_map = {
        "meta_clingen_caid": ["caid", "CAID", "canonical_allele_id"],
        "meta_clingen_expert_panel": ["expert_panel", "Expert Panel", "affiliation", "affiliation_name"],
        "meta_clingen_assertion_id": ["assertion_id", "classification_id", "id"],
        "meta_clinvar_variation_id": ["clinvar_variation_id", "ClinVar Variation ID", "variation_id"],
        "feature_clingen_evidence_strength": ["evidence_strength", "criteria_summary", "evidence_summary"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "clingen_erepo")
    return canonicalize_variant_keys(normalized)


def preset_cbioportal_mutation_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "Hugo_Symbol", "hugo_gene_symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "HGVSp_Short", "HGVSp", "protein_change", "Amino_Acid_Change"])

    alias_map = {
        "feature_cbioportal_mutation_count": ["mutation_count", "count", "case_count", "num_samples"],
        "feature_cbioportal_sample_frequency": ["sample_frequency", "mutation_frequency", "frequency"],
        "feature_cbioportal_cancer_type": ["cancer_type", "Cancer Type", "cancer_type_detailed"],
        "meta_cbioportal_study_id": ["study_id", "cancer_study_identifier", "Cancer Study"],
        "meta_cbioportal_sample_id": ["sample_id", "Tumor_Sample_Barcode", "sample"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "cbioportal")
    return canonicalize_variant_keys(normalized)


def preset_gdc_maf_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "Hugo_Symbol", "symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "HGVSp_Short", "HGVSp", "Protein_Change"])

    alias_map = {
        "feature_gdc_variant_classification": ["Variant_Classification", "variant_classification"],
        "feature_gdc_variant_type": ["Variant_Type", "variant_type"],
        "feature_gdc_tumor_vaf": ["t_alt_count", "tumor_vaf", "vaf"],
        "meta_gdc_project_id": ["Project", "project_id", "cases.project.project_id"],
        "meta_gdc_case_id": ["case_id", "Case_ID", "case_submitter_id"],
        "meta_gdc_sample_id": ["Tumor_Sample_Barcode", "sample_id"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "gdc")
    return canonicalize_variant_keys(normalized)


def preset_gwas_catalog_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "mapped_gene", "MAPPED_GENE", "reported_gene"])

    alias_map = {
        "meta_gwas_rsid": ["rsid", "SNPS", "variant_id", "strongest_snp_risk_allele"],
        "feature_gwas_pvalue": ["pvalue", "P-VALUE", "p_value"],
        "feature_gwas_or_beta": ["or_beta", "OR or BETA", "beta", "odds_ratio"],
        "feature_gwas_trait": ["trait", "DISEASE/TRAIT", "mapped_trait"],
        "feature_gwas_initial_sample_size": ["initial_sample_size", "INITIAL SAMPLE SIZE"],
        "meta_gwas_study_accession": ["study_accession", "STUDY ACCESSION"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "gwas_catalog")
    return canonicalize_variant_keys(normalized)


def preset_opentargets_variant_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "symbol", "approvedSymbol", "target_symbol"])

    alias_map = {
        "meta_opentargets_variant_id": ["variant_id", "variantId", "id"],
        "feature_opentargets_association_score": ["association_score", "score", "overallScore"],
        "feature_opentargets_disease": ["disease", "disease_name", "trait_reported"],
        "feature_opentargets_evidence_count": ["evidence_count", "count"],
        "meta_opentargets_target_id": ["target_id", "targetId", "ensembl_id"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "opentargets")
    return canonicalize_variant_keys(normalized)


def preset_alphamissense_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "gene_symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "protein_variant", "Protein_variant"])
    normalized = _rename_first_available(normalized, "meta_uniprot_accession", ["uniprot_id", "uniprot", "accession"])

    alias_map = {
        "feature_alphamissense_pathogenicity": ["am_pathogenicity", "alphamissense_pathogenicity", "score"],
        "feature_alphamissense_class": ["am_class", "alphamissense_class", "classification"],
        "meta_alphamissense_transcript_id": ["transcript_id", "ensembl_transcript_id"],
        "meta_genome_build": ["genome", "genome_build"],
        "meta_chrom": ["CHROM", "chrom"],
        "meta_pos": ["POS", "pos"],
        "meta_ref": ["REF", "ref"],
        "meta_alt": ["ALT", "alt"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "alphamissense")
    return canonicalize_variant_keys(normalized)


def preset_pharmgkb_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "gene_symbol", "genes"])

    alias_map = {
        "meta_pharmgkb_variant_id": ["variant_id", "Variant ID", "id"],
        "meta_pharmgkb_annotation_id": ["annotation_id", "Clinical Annotation ID"],
        "feature_pharmgkb_level": ["level_of_evidence", "Level of Evidence", "evidence_level"],
        "feature_pharmgkb_drug": ["drug", "Drug(s)", "chemicals"],
        "feature_pharmgkb_phenotype": ["phenotype", "Phenotype Category", "phenotypes"],
        "feature_pharmgkb_significance": ["significance", "clinical_significance"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "pharmgkb")
    return canonicalize_variant_keys(normalized)


def preset_lovd_variant_table(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized = _rename_first_available(normalized, "gene", ["gene", "Gene", "symbol", "gene_symbol"])
    normalized = _rename_first_available(normalized, "hgvs_p", ["hgvs_p", "Protein", "protein", "effect_reported"])
    normalized = _rename_first_available(normalized, "label", ["classification", "effect", "clinical_significance"])

    alias_map = {
        "meta_lovd_variant_id": ["variant_id", "Variant ID", "id"],
        "meta_lovd_individual_id": ["individual_id", "Individual ID"],
        "feature_lovd_origin": ["origin", "Origin"],
        "feature_lovd_disease": ["disease", "Disease", "phenotype"],
        "feature_lovd_frequency": ["frequency", "Frequency"],
    }
    for target, candidates in alias_map.items():
        normalized = _rename_first_available(normalized, target, candidates)

    normalized["meta_dataset"] = normalized.get("meta_dataset", "lovd")
    return canonicalize_variant_keys(normalized)


PRESET_REGISTRY: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "none": preset_none,
    "clinvar": preset_clinvar,
    "clinvar_variant_summary": preset_clinvar_variant_summary,
    "gnomad_variant_table": preset_gnomad_variant_table,
    "mavedb_score_table": preset_mavedb_score_table,
    "enigma_brca": preset_enigma_brca,
    "uniprot_feature_table": preset_uniprot_feature_table,
    "alphafold_model_table": preset_alphafold_model_table,
    "pdb_structure_table": preset_pdb_structure_table,
    "civic_variant_table": preset_civic_variant_table,
    "clingen_erepo_table": preset_clingen_erepo_table,
    "cbioportal_mutation_table": preset_cbioportal_mutation_table,
    "gdc_maf_table": preset_gdc_maf_table,
    "gwas_catalog_table": preset_gwas_catalog_table,
    "opentargets_variant_table": preset_opentargets_variant_table,
    "alphamissense_table": preset_alphamissense_table,
    "pharmgkb_table": preset_pharmgkb_table,
    "lovd_variant_table": preset_lovd_variant_table,
}


def apply_source_preset(df: pd.DataFrame, preset_name: str | None) -> pd.DataFrame:
    preset_key = str(preset_name or "none").strip().lower()
    if preset_key not in PRESET_REGISTRY:
        raise ValueError(f"Preset nao suportado: {preset_name}")
    return PRESET_REGISTRY[preset_key](df)
