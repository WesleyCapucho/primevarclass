from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


SYNC_RECIPES: dict[str, dict] = {
    "clinvar": {
        "automation_level": "automatable",
        "sync_strategy": "direct_download",
        "preferred_channel": "ftp_tsv",
        "official_entrypoints": [
            {
                "label": "ClinVar downloads overview",
                "url": "https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/",
                "notes": "ClinVar documents weekly updates and monthly archived releases for XML, VCF, and TSV.",
            },
            {
                "label": "ClinVar TSV directory",
                "url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/",
                "notes": "Recommended for variant_summary-based ingestion into PrimeVarClass.",
            },
        ],
        "recommended_artifacts": [
            "variant_summary.txt.gz",
            "variant_summary.txt.gz.md5",
        ],
        "notes": [
            "Prefer the TSV summary file for cohort assembly.",
            "Capture the archived monthly release when building a publication cohort.",
        ],
    },
    "gnomad": {
        "automation_level": "semi_automatable",
        "sync_strategy": "download_or_toolbox_query",
        "preferred_channel": "downloads_page",
        "official_entrypoints": [
            {
                "label": "gnomAD downloads",
                "url": "https://gnomad.broadinstitute.org/downloads",
                "notes": "Use the official downloads page for release files and browser tables.",
            },
            {
                "label": "gnomAD toolbox announcement",
                "url": "https://gnomad.broadinstitute.org/news/2025-01-gnomad-toolbox/",
                "notes": "Recommended when full downloads are too large for local handling.",
            },
        ],
        "recommended_artifacts": [
            "browser variants Hail Table or release table export",
            "gene-filtered BRCA annotation subset",
        ],
        "notes": [
            "gnomAD short-variant downloads can be extremely large.",
            "For BRCA-focused work, prefer gene-filtered extraction or toolbox-assisted queries.",
        ],
    },
    "mavedb": {
        "automation_level": "automatable",
        "sync_strategy": "api_or_bulk_download",
        "preferred_channel": "api",
        "official_entrypoints": [
            {
                "label": "MaveDB API",
                "url": "https://www.mavedb.org/docs/mavedb/api/index.html",
                "notes": "Use for score set metadata and programmatic access.",
            },
            {
                "label": "MaveDB bulk downloads",
                "url": "https://www.mavedb.org/docs/mavedb/bulk_downloads.html",
                "notes": "Zenodo-backed archival releases updated twice yearly.",
            },
        ],
        "recommended_artifacts": [
            "score set metadata JSON",
            "mapped variants JSON",
            "score CSV per public score set (optional or bulk release)",
        ],
        "notes": [
            "Prefer stable public URNs for publication-grade reproducibility.",
            "Bulk releases are a strong option when many score sets are needed.",
            "When release_version stores a public URN, PrimeVarClass can stage score-set metadata and mapped variants directly via the official API.",
        ],
    },
    "enigma": {
        "automation_level": "manual_assisted",
        "sync_strategy": "manual_curated_import",
        "preferred_channel": "curated_manual_import",
        "official_entrypoints": [
            {
                "label": "ENIGMA consortium",
                "url": "https://enigmaconsortium.org/",
                "notes": "Primary consortium site and curation context.",
            },
            {
                "label": "ENIGMA useful links",
                "url": "https://enigmaconsortium.org/library/useful-links/",
                "notes": "Points users to ClinVar expert panel and BRCA Exchange resources.",
            },
        ],
        "recommended_artifacts": [
            "curated ENIGMA-derived BRCA classification table",
        ],
        "notes": [
            "The official ENIGMA site points users to linked resources such as ClinVar expert-panel records and BRCA Exchange.",
            "Treat this source as curated import unless a stable direct export is available for your study.",
        ],
    },
    "uniprot": {
        "automation_level": "automatable",
        "sync_strategy": "rest_api_or_tab_export",
        "preferred_channel": "rest_api",
        "official_entrypoints": [
            {
                "label": "UniProt API documentation",
                "url": "https://www.uniprot.org/api-documentation",
                "notes": "Use REST queries or reviewed tab exports to annotate sequence, domain, and protein-function context.",
            },
            {
                "label": "UniProt REST root",
                "url": "https://rest.uniprot.org/",
                "notes": "Primary REST endpoint for search and field-specific retrieval.",
            },
        ],
        "recommended_artifacts": [
            "reviewed entry metadata JSON or TSV",
            "gene to UniProt accession mapping table",
        ],
        "notes": [
            "Use reviewed human entries when building publication-grade protein context annotations.",
            "Keep accession mapping frozen per study release to avoid silent protein-model drift.",
        ],
    },
    "alphafold_db": {
        "automation_level": "semi_automatable",
        "sync_strategy": "api_by_uniprot_accession",
        "preferred_channel": "prediction_api",
        "official_entrypoints": [
            {
                "label": "AlphaFold DB",
                "url": "https://alphafold.ebi.ac.uk/",
                "notes": "Primary portal for AlphaFold protein structure predictions.",
            },
            {
                "label": "AlphaFold prediction API",
                "url": "https://alphafold.ebi.ac.uk/api/",
                "notes": "Use accession-specific prediction endpoints after resolving UniProt accessions.",
            },
        ],
        "recommended_artifacts": [
            "prediction metadata JSON",
            "model coordinate file URL list",
            "PAE or confidence metadata",
        ],
        "notes": [
            "Best used after a stable UniProt accession mapping layer is established.",
            "Refresh structural context without promoting a new clinical model unless benchmark performance is preserved.",
        ],
    },
    "pdb": {
        "automation_level": "semi_automatable",
        "sync_strategy": "data_api_or_search_export",
        "preferred_channel": "data_api",
        "official_entrypoints": [
            {
                "label": "RCSB PDB APIs overview",
                "url": "https://www.rcsb.org/docs/programmatic-access/web-apis-overview",
                "notes": "Use Data API or Search API for structure metadata and accession cross-references.",
            },
            {
                "label": "RCSB Data API",
                "url": "https://data.rcsb.org/",
                "notes": "Primary endpoint for experimental structure metadata.",
            },
        ],
        "recommended_artifacts": [
            "structure metadata JSON",
            "gene or accession to PDB mapping table",
            "resolution and method summary table",
        ],
        "notes": [
            "Use PDB as an experimental-structure overlay rather than as a label source.",
            "Prioritize structures with human sequence alignment and adequate local coverage around the residue of interest.",
        ],
    },
    "civic": {
        "automation_level": "automatable",
        "sync_strategy": "api_or_nightly_export",
        "preferred_channel": "api",
        "official_entrypoints": [
            {
                "label": "CIViC API documentation",
                "url": "https://docs.civicdb.org/en/latest/api.html",
                "notes": "Use the API for translational and actionability evidence linked to variants and genes.",
            },
            {
                "label": "CIViC portal",
                "url": "https://civicdb.org/",
                "notes": "Primary knowledgebase portal for curated cancer variant interpretation.",
            },
        ],
        "recommended_artifacts": [
            "variant evidence JSON",
            "therapy and disease evidence summary table",
        ],
        "notes": [
            "Treat CIViC as translational evidence enrichment, not as the primary pathogenicity supervision layer.",
            "Freeze evidence snapshots before manuscript-grade benchmarking or external comparison.",
        ],
    },
    "clingen_erepo": {
        "automation_level": "automatable",
        "sync_strategy": "api_or_table_download",
        "preferred_channel": "api",
        "official_entrypoints": [
            {
                "label": "ClinGen Evidence Repository",
                "url": "https://erepo.clinicalgenome.org/evrepo/",
                "notes": "FDA-recognized expert variant classifications with download and API entrypoints.",
            },
            {
                "label": "ClinGen ERepo API docs",
                "url": "https://erepo.genome.network/",
                "notes": "Use for programmatic classification and provenance retrieval.",
            },
        ],
        "recommended_artifacts": [
            "gene-filtered expert classification TSV",
            "classification provenance JSON",
        ],
        "notes": [
            "Use as independent expert validation, not as leaked labels inside the same training split.",
            "Preserve expert panel and CAID metadata for auditability.",
        ],
    },
    "cbioportal": {
        "automation_level": "semi_automatable",
        "sync_strategy": "datahub_study_download",
        "preferred_channel": "datahub_git_lfs_or_study_zip",
        "official_entrypoints": [
            {
                "label": "cBioPortal public Datahub",
                "url": "https://github.com/cBioPortal/datahub",
                "notes": "Study staging files can be downloaded per study, for example public/brca_tcga.",
            },
            {
                "label": "cBioPortal public portal",
                "url": "https://www.cbioportal.org/",
                "notes": "Use for cancer cohort exploration and study-level downloads.",
            },
        ],
        "recommended_artifacts": [
            "study mutation MAF or data_mutations_extended.txt",
            "clinical sample table",
            "study metadata",
        ],
        "notes": [
            "Strong for somatic/translational generalization in cancer genes.",
            "Do not treat tumor recurrence as germline pathogenicity without a separate biological question.",
        ],
    },
    "gdc": {
        "automation_level": "semi_automatable",
        "sync_strategy": "api_or_transfer_tool",
        "preferred_channel": "gdc_api",
        "official_entrypoints": [
            {
                "label": "NCI GDC access data",
                "url": "https://gdc.cancer.gov/access-data",
                "notes": "GDC provides portal, API, and transfer tooling with open and controlled data tiers.",
            },
            {
                "label": "GDC API",
                "url": "https://gdc.cancer.gov/content/gdc-api",
                "notes": "Use for open MAF, clinical, project, and file metadata queries.",
            },
        ],
        "recommended_artifacts": [
            "open-access MAF tables",
            "project and clinical metadata",
            "controlled-access request record when needed",
        ],
        "notes": [
            "Some GDC files require dbGaP authorization; keep open and controlled lanes separate.",
            "Best used for independent cancer-context validation and translational analysis.",
        ],
    },
    "gwas_catalog": {
        "automation_level": "automatable",
        "sync_strategy": "rest_api_or_tsv_download",
        "preferred_channel": "rest_api",
        "official_entrypoints": [
            {
                "label": "GWAS Catalog REST API",
                "url": "https://www.ebi.ac.uk/gwas/rest/api/v2/docs",
                "notes": "Literature-curated top associations and metadata are available programmatically.",
            },
            {
                "label": "GWAS Catalog",
                "url": "https://www.ebi.ac.uk/gwas/",
                "notes": "Use for disease/trait association context and independent genetic-association evidence.",
            },
        ],
        "recommended_artifacts": [
            "gene or variant association table",
            "trait mapping metadata",
        ],
        "notes": [
            "Association evidence is not a direct pathogenicity label.",
            "Use as external biological plausibility and disease-context evidence.",
        ],
    },
    "opentargets": {
        "automation_level": "automatable",
        "sync_strategy": "graphql_api_or_bulk_download",
        "preferred_channel": "graphql_api",
        "official_entrypoints": [
            {
                "label": "Open Targets Platform",
                "url": "https://platform.opentargets.org/",
                "notes": "Integrates genetic, functional, drug, pathway, and literature evidence for target-disease associations.",
            },
            {
                "label": "Open Targets Platform docs",
                "url": "https://platform-docs.opentargets.org/variant",
                "notes": "Variant data are mapped to GRCh38 and enriched with functional annotation.",
            },
        ],
        "recommended_artifacts": [
            "target-disease evidence table",
            "variant-to-phenotype summary",
        ],
        "notes": [
            "Use for translational prioritization and target-discovery context.",
            "Keep source-level evidence provenance when using aggregate association scores.",
        ],
    },
    "alphamissense": {
        "automation_level": "semi_automatable",
        "sync_strategy": "bulk_download_or_gene_subset",
        "preferred_channel": "bulk_tsv",
        "official_entrypoints": [
            {
                "label": "AlphaMissense README",
                "url": "https://storage.googleapis.com/dm_alphamissense/README.pdf",
                "notes": "Describes hg19/hg38 and amino-acid substitution score files, columns, thresholds, and CC-BY licensing.",
            },
            {
                "label": "AlphaMissense storage bucket",
                "url": "https://console.cloud.google.com/storage/browser/dm_alphamissense",
                "notes": "Use gene-filtered extraction locally when full files are too large.",
            },
        ],
        "recommended_artifacts": [
            "AlphaMissense_hg38.tsv.gz subset",
            "AlphaMissense_aa_substitutions.tsv.gz subset",
        ],
        "notes": [
            "Use as an independent predictor/comparator and functional prior, not as a ground-truth label.",
            "Freeze transcript and genome-build mapping before benchmark comparisons.",
        ],
    },
    "pharmgkb": {
        "automation_level": "automatable",
        "sync_strategy": "api_or_tsv_download",
        "preferred_channel": "api",
        "official_entrypoints": [
            {
                "label": "ClinPGx API",
                "url": "https://api.pharmgkb.org/",
                "notes": "REST API for PharmGKB, CPIC, and PharmCAT data including annotations, genes, chemicals, and variants.",
            },
            {
                "label": "PharmGKB downloads",
                "url": "https://www.pharmgkb.org/downloads",
                "notes": "Use where bulk academic-use terms are suitable for the study.",
            },
        ],
        "recommended_artifacts": [
            "variant-drug clinical annotation table",
            "gene-drug guideline metadata",
        ],
        "notes": [
            "Best for pharmacogenomic/translational layers rather than germline pathogenicity supervision.",
            "Respect request limits and data usage terms.",
        ],
    },
    "lovd": {
        "automation_level": "manual_assisted",
        "sync_strategy": "gene_database_export",
        "preferred_channel": "curated_lovd_export",
        "official_entrypoints": [
            {
                "label": "LOVD public installation list",
                "url": "https://www.lovd.nl/2.0/index_list.php",
                "notes": "Find gene-centered public LOVD installations and download/export data where supported.",
            },
            {
                "label": "Global Variome shared LOVD",
                "url": "https://databases.lovd.nl/shared/",
                "notes": "Use only after checking field definitions and database-specific submission policies.",
            },
        ],
        "recommended_artifacts": [
            "gene-specific variant export",
            "submission/individual metadata when allowed",
        ],
        "notes": [
            "LOVD instances are heterogeneous; normalize carefully and do not mix observations with expert labels blindly.",
            "Use as supplementary external evidence after field-level QC.",
        ],
    },
}

MAVEDB_URN_PATTERN = re.compile(r"(urn:mavedb:[A-Za-z0-9._:-]+)", flags=re.IGNORECASE)


def _default_local_path(profile_id: str, source_name: str, release_value: str | None) -> str:
    release_slug = str(release_value or "unversioned").replace(":", "_").replace("/", "_").replace("\\", "_")
    return str((Path("data") / "raw" / profile_id / f"{source_name}_{release_slug}").as_posix())


def _extract_mavedb_urn(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        match = MAVEDB_URN_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def _build_sync_item(source: dict) -> dict:
    profile_id = str(source.get("profile_id") or "")
    recipe = dict(SYNC_RECIPES.get(profile_id, {}))
    source_name = str(source.get("source_name") or profile_id or "source")
    suggested_local_path = source.get("path") or _default_local_path(profile_id or "public", source_name, source.get("release_value"))
    automation_level = str(recipe.get("automation_level") or "manual_assisted")
    can_auto_sync = automation_level in {"automatable", "semi_automatable"}
    resolved_mavedb_urn = _extract_mavedb_urn(
        source.get("release_value"),
        source.get("path"),
        source.get("url"),
        source.get("source_name"),
    )
    local_source_path = str(source.get("path") or "").strip() or None
    local_source_exists = bool(local_source_path and Path(local_source_path).exists())

    next_action = {
        "automatable": "Pode ser automatizada com download/API e versionamento local.",
        "semi_automatable": "Automatize a descoberta e o recorte BRCA; trate downloads grandes com cuidado.",
        "manual_assisted": "Exige curadoria assistida e importacao manual versionada.",
    }.get(automation_level, "Requer avaliacao manual antes da sincronizacao.")
    if profile_id == "mavedb" and not resolved_mavedb_urn:
        next_action = "Informe release_version com o URN publico do score set para habilitar sync automatico via API."
    if profile_id == "gnomad":
        if local_source_exists:
            next_action = "Pode executar recorte BRCA local a partir da tabela gnomAD ja baixada e versionada."
        else:
            next_action = "Forneca uma tabela gnomAD local exportada para habilitar recorte BRCA controlado no bootstrap."
    if profile_id == "enigma":
        if local_source_exists:
            next_action = "Pode executar staging auditavel da importacao curada ENIGMA a partir do arquivo local versionado."
        else:
            next_action = "Forneca um arquivo local curado ENIGMA para habilitar staging auditavel no bootstrap."

    return {
        "source_name": source_name,
        "profile_id": profile_id,
        "display_name": source.get("display_name"),
        "release_value": source.get("release_value"),
        "release_method": source.get("release_method"),
        "readiness_percent": source.get("readiness_percent", 0),
        "schema_coverage_percent": source.get("schema_coverage_percent", 0),
        "automation_level": automation_level,
        "can_auto_sync": can_auto_sync,
        "sync_strategy": recipe.get("sync_strategy"),
        "preferred_channel": recipe.get("preferred_channel"),
        "official_entrypoints": list(recipe.get("official_entrypoints") or []),
        "recommended_artifacts": list(recipe.get("recommended_artifacts") or []),
        "suggested_local_path": suggested_local_path,
        "notes": list(recipe.get("notes") or []),
        "next_action": next_action,
        "source_path": source.get("path"),
        "source_url": source.get("url"),
        "source_format": source.get("source_format"),
        "gene_allowlist": list(source.get("gene_allowlist") or []),
        "local_source_exists": local_source_exists,
        "resolved_mavedb_urn": resolved_mavedb_urn,
    }


def build_public_source_sync_plan(
    *,
    config_path: str,
    public_source_assessment: dict | None = None,
) -> dict:
    assessment = dict(public_source_assessment or {})
    sources = list(assessment.get("sources") or [])
    recognized_sources = [source for source in sources if source.get("recognized_public_source")]
    sync_items = [_build_sync_item(source) for source in recognized_sources]

    summary = {
        "config_path": str(Path(config_path).resolve()),
        "n_sync_candidates": int(len(sync_items)),
        "n_automatable_sources": int(sum(1 for item in sync_items if item.get("automation_level") == "automatable")),
        "n_semi_automatable_sources": int(sum(1 for item in sync_items if item.get("automation_level") == "semi_automatable")),
        "n_manual_sources": int(sum(1 for item in sync_items if item.get("automation_level") == "manual_assisted")),
        "overall_readiness_percent": int((assessment.get("summary") or {}).get("overall_readiness_percent") or 0),
        "recommended_next_step": "Usar ClinVar, ClinGen, gnomAD, MaveDB, ENIGMA/BRCA Exchange, CIViC/cBioPortal/GDC e fontes proteicas em staging versionado antes dos benchmarks finais.",
    }

    markdown_lines = [
        "# Public Source Sync Plan",
        "",
        f"- Config path: {summary['config_path']}",
        f"- Sync candidates: {summary['n_sync_candidates']}",
        f"- Automatable: {summary['n_automatable_sources']}",
        f"- Semi-automatable: {summary['n_semi_automatable_sources']}",
        f"- Manual-assisted: {summary['n_manual_sources']}",
        f"- Catalog readiness: {summary['overall_readiness_percent']}%",
        f"- Recommended next step: {summary['recommended_next_step']}",
        "",
        "## Sync Items",
        "",
    ]

    for item in sync_items:
        markdown_lines.extend(
            [
                f"### {item['display_name']} - {item['source_name']}",
                "",
                f"- Release: {item.get('release_value') or '-'}",
                f"- Automation level: {item.get('automation_level')}",
                f"- Sync strategy: {item.get('sync_strategy')}",
                f"- Preferred channel: {item.get('preferred_channel')}",
                f"- Suggested local path: {item.get('suggested_local_path')}",
                f"- Readiness: {item.get('readiness_percent', 0)}%",
                f"- Next action: {item.get('next_action')}",
                "",
            ]
        )
        for entrypoint in item.get("official_entrypoints") or []:
            markdown_lines.append(f"- Official entrypoint: {entrypoint.get('label')} -> {entrypoint.get('url')}")
        for artifact in item.get("recommended_artifacts") or []:
            markdown_lines.append(f"- Expected artifact: {artifact}")
        for note in item.get("notes") or []:
            markdown_lines.append(f"- Note: {note}")
        markdown_lines.append("")

    return {
        "summary": summary,
        "sync_items": sync_items,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }
