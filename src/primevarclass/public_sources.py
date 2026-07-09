from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List


@dataclass(frozen=True)
class PublicSourceProfile:
    profile_id: str
    display_name: str
    preset_names: tuple[str, ...]
    keywords: tuple[str, ...]
    source_roles: tuple[str, ...]
    release_patterns: tuple[str, ...]
    expected_columns: tuple[str, ...]
    citation_url: str


PUBLIC_SOURCE_PROFILES: tuple[PublicSourceProfile, ...] = (
    PublicSourceProfile(
        profile_id="clinvar",
        display_name="ClinVar",
        preset_names=("clinvar", "clinvar_variant_summary"),
        keywords=("clinvar", "variant_summary"),
        source_roles=("cohort", "annotation"),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"(20\d{6})",
            r"(20\d{2}_\d{2}_\d{2})",
        ),
        expected_columns=("gene", "hgvs_p", "label", "review_status"),
        citation_url="https://www.ncbi.nlm.nih.gov/clinvar/",
    ),
    PublicSourceProfile(
        profile_id="gnomad",
        display_name="gnomAD",
        preset_names=("gnomad_variant_table",),
        keywords=("gnomad",),
        source_roles=("annotation",),
        release_patterns=(
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
            r"(r\d+\.\d+)",
            r"(20\d{2}-\d{2}-\d{2})",
        ),
        expected_columns=("gene", "hgvs_p", "feature_gnomad_af"),
        citation_url="https://gnomad.broadinstitute.org/",
    ),
    PublicSourceProfile(
        profile_id="mavedb",
        display_name="MaveDB",
        preset_names=("mavedb_score_table",),
        keywords=("mavedb", "mave"),
        source_roles=("annotation",),
        release_patterns=(
            r"(urn:mavedb:[A-Za-z0-9._:-]+)",
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "feature_mave_score"),
        citation_url="https://www.mavedb.org/",
    ),
    PublicSourceProfile(
        profile_id="enigma",
        display_name="ENIGMA",
        preset_names=("enigma_brca",),
        keywords=("enigma",),
        source_roles=("annotation", "cohort"),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"(20\d{6})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "label"),
        citation_url="https://enigmaconsortium.org/",
    ),
    PublicSourceProfile(
        profile_id="uniprot",
        display_name="UniProt",
        preset_names=("uniprot_feature_table",),
        keywords=("uniprot", "uniprotkb", "rest.uniprot.org"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\brelease[_ -]?(\d{4}_\d+)\b",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_uniprot_accession", "feature_uniprot_sequence_length"),
        citation_url="https://www.uniprot.org/",
    ),
    PublicSourceProfile(
        profile_id="alphafold_db",
        display_name="AlphaFold DB",
        preset_names=("alphafold_model_table",),
        keywords=("alphafold", "afdb", "alphafold.ebi.ac.uk"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_uniprot_accession", "feature_alphafold_model_url"),
        citation_url="https://alphafold.ebi.ac.uk/",
    ),
    PublicSourceProfile(
        profile_id="pdb",
        display_name="RCSB PDB",
        preset_names=("pdb_structure_table",),
        keywords=("rcsb", "pdb", "data.rcsb.org"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_pdb_id", "feature_pdb_experimental_method"),
        citation_url="https://www.rcsb.org/",
    ),
    PublicSourceProfile(
        profile_id="civic",
        display_name="CIViC",
        preset_names=("civic_variant_table",),
        keywords=("civic", "civicdb"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "feature_civic_evidence_count"),
        citation_url="https://civicdb.org/",
    ),
    PublicSourceProfile(
        profile_id="clingen_erepo",
        display_name="ClinGen Evidence Repository",
        preset_names=("clingen_erepo_table",),
        keywords=("clingen", "erepo", "evidence repository", "clinicalgenome"),
        source_roles=("cohort", "annotation"),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
            r"(CA\d+)",
        ),
        expected_columns=("gene", "hgvs_p", "label", "meta_clingen_caid"),
        citation_url="https://erepo.clinicalgenome.org/evrepo/",
    ),
    PublicSourceProfile(
        profile_id="cbioportal",
        display_name="cBioPortal",
        preset_names=("cbioportal_mutation_table",),
        keywords=("cbioportal", "datahub", "brca_tcga", "tcga"),
        source_roles=("annotation", "cohort"),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\b(public/[A-Za-z0-9_.-]+)\b",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "feature_cbioportal_mutation_count"),
        citation_url="https://www.cbioportal.org/",
    ),
    PublicSourceProfile(
        profile_id="gdc",
        display_name="NCI Genomic Data Commons",
        preset_names=("gdc_maf_table",),
        keywords=("gdc", "genomic data commons", "tcga", "maf"),
        source_roles=("annotation", "cohort"),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\b(TCGA-[A-Z0-9-]+)\b",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "feature_gdc_variant_classification"),
        citation_url="https://gdc.cancer.gov/",
    ),
    PublicSourceProfile(
        profile_id="gwas_catalog",
        display_name="GWAS Catalog",
        preset_names=("gwas_catalog_table",),
        keywords=("gwas", "ebi.ac.uk/gwas", "nhgri-ebi"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_gwas_rsid", "feature_gwas_pvalue"),
        citation_url="https://www.ebi.ac.uk/gwas/",
    ),
    PublicSourceProfile(
        profile_id="opentargets",
        display_name="Open Targets Platform",
        preset_names=("opentargets_variant_table",),
        keywords=("opentargets", "open targets", "platform.opentargets"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_opentargets_variant_id", "feature_opentargets_association_score"),
        citation_url="https://platform.opentargets.org/",
    ),
    PublicSourceProfile(
        profile_id="alphamissense",
        display_name="AlphaMissense",
        preset_names=("alphamissense_table",),
        keywords=("alphamissense", "dm_alphamissense", "am_pathogenicity"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
            r"(hg19|hg38)",
        ),
        expected_columns=("hgvs_p", "feature_alphamissense_pathogenicity", "feature_alphamissense_class"),
        citation_url="https://storage.googleapis.com/dm_alphamissense/README.pdf",
    ),
    PublicSourceProfile(
        profile_id="pharmgkb",
        display_name="PharmGKB / ClinPGx",
        preset_names=("pharmgkb_table",),
        keywords=("pharmgkb", "clinpgx", "api.pharmgkb"),
        source_roles=("annotation",),
        release_patterns=(
            r"(20\d{2}-\d{2}-\d{2})",
            r"\bv?(\d+\.\d+(?:\.\d+)?)\b",
        ),
        expected_columns=("gene", "meta_pharmgkb_variant_id", "feature_pharmgkb_level"),
        citation_url="https://api.pharmgkb.org/",
    ),
    PublicSourceProfile(
        profile_id="lovd",
        display_name="LOVD",
        preset_names=("lovd_variant_table",),
        keywords=("lovd", "leiden open variation database", "databases.lovd.nl"),
        source_roles=("cohort", "annotation"),
        release_patterns=(
            r"(20\d{2}/\d{2}/\d{2})",
            r"(20\d{2}-\d{2}-\d{2})",
            r"\b(\d+\.\d+-\d+[a-z]?)\b",
        ),
        expected_columns=("gene", "hgvs_p", "label"),
        citation_url="https://www.lovd.nl/",
    ),
)


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower()


def resolve_public_source_profile(spec: Any) -> PublicSourceProfile | None:
    preset = _normalize_token(getattr(spec, "preset", None))
    name = _normalize_token(getattr(spec, "name", None))
    path = _normalize_token(getattr(spec, "path", None))
    url = _normalize_token(getattr(spec, "url", None))
    joined = " ".join(token for token in [preset, name, path, url] if token)

    for profile in PUBLIC_SOURCE_PROFILES:
        if preset in profile.preset_names:
            return profile
        if any(keyword in joined for keyword in profile.keywords):
            return profile
    return None


def _collect_release_candidates(spec: Any, provenance: dict | None) -> List[dict]:
    provenance = provenance or {}
    candidates: List[dict] = []

    def _append(label: str, value: Any) -> None:
        text = str(value or "").strip()
        if text:
            candidates.append({"label": label, "value": text})

    _append("config.release_version", getattr(spec, "release_version", None))
    _append("config.release_date", getattr(spec, "release_date", None))
    _append("config.path", getattr(spec, "path", None))
    _append("config.url", getattr(spec, "url", None))
    _append("config.name", getattr(spec, "name", None))
    _append("config.query", getattr(spec, "query", None))

    file_fingerprint = provenance.get("file_fingerprint") or {}
    _append("provenance.file.path", file_fingerprint.get("path"))

    sqlite_meta = provenance.get("sqlite") or {}
    _append("provenance.sqlite.database_path", sqlite_meta.get("database_path"))
    _append("provenance.sqlite.query_preview", sqlite_meta.get("query_preview"))

    http_meta = provenance.get("http") or {}
    request_meta = http_meta.get("request") or {}
    response_meta = http_meta.get("response") or {}
    _append("provenance.http.request.configured_url", request_meta.get("configured_url"))
    _append("provenance.http.request.resolved_url", request_meta.get("resolved_url"))
    _append("provenance.http.response.final_url", response_meta.get("final_url"))
    _append("provenance.http.response.etag", response_meta.get("etag"))
    _append("provenance.http.response.last_modified", response_meta.get("last_modified"))

    return candidates


def infer_public_source_release(spec: Any, provenance: dict | None = None) -> dict:
    profile = resolve_public_source_profile(spec)
    if profile is None:
        return {
            "recognized_public_source": False,
            "profile_id": None,
            "display_name": None,
            "release_value": None,
            "release_method": "unrecognized",
            "evidence": [],
            "coverage_percent": 0,
            "citation_url": None,
            "warnings": ["Fonte nao reconhecida como catalogo publico prioritario."],
        }

    release_version = str(getattr(spec, "release_version", "") or "").strip()
    release_date = str(getattr(spec, "release_date", "") or "").strip()
    evidence: List[dict] = []
    warnings: List[str] = []

    if release_version or release_date:
        if release_version:
            evidence.append({"label": "config.release_version", "value": release_version})
        if release_date:
            evidence.append({"label": "config.release_date", "value": release_date})
        release_value = release_version or release_date
        coverage_percent = 100 if release_version and release_date else 92
        return {
            "recognized_public_source": True,
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "release_value": release_value,
            "release_date": release_date or None,
            "release_method": "config_override",
            "evidence": evidence,
            "coverage_percent": coverage_percent,
            "citation_url": profile.citation_url,
            "warnings": warnings,
        }

    candidates = _collect_release_candidates(spec, provenance)
    for candidate in candidates:
        text = candidate["value"]
        for pattern in profile.release_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                release_value = match.group(1)
                evidence.append({"label": candidate["label"], "value": text})
                return {
                    "recognized_public_source": True,
                    "profile_id": profile.profile_id,
                    "display_name": profile.display_name,
                    "release_value": release_value,
                    "release_date": release_value if re.match(r"20\d{2}-\d{2}-\d{2}", release_value) else None,
                    "release_method": "pattern_inference",
                    "evidence": evidence,
                    "coverage_percent": 84,
                    "citation_url": profile.citation_url,
                    "warnings": warnings,
                }

    warnings.append("Release/version nao identificada automaticamente; recomenda-se preencher release_version ou release_date no catalogo.")
    return {
        "recognized_public_source": True,
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "release_value": None,
        "release_date": None,
        "release_method": "missing",
        "evidence": candidates[:5],
        "coverage_percent": 45,
        "citation_url": profile.citation_url,
        "warnings": warnings,
    }


def assess_public_source_schema(spec: Any, provenance: dict | None = None) -> dict:
    profile = resolve_public_source_profile(spec)
    provenance = provenance or {}
    schema = provenance.get("schema") or {}
    normalized_columns = [str(column) for column in (schema.get("normalized_columns") or [])]
    raw_columns = [str(column) for column in (schema.get("raw_columns") or [])]

    if profile is None:
        return {
            "schema_recognized": False,
            "schema_coverage_percent": 0,
            "expected_columns": [],
            "available_normalized_columns": normalized_columns,
            "available_raw_columns": raw_columns,
            "missing_expected_columns": [],
            "schema_ready": False,
            "schema_warnings": [],
        }

    expected_columns = list(profile.expected_columns)
    available_set = set(normalized_columns)
    missing_columns = [column for column in expected_columns if column not in available_set]
    present_count = len(expected_columns) - len(missing_columns)
    coverage_percent = int(round((present_count / len(expected_columns)) * 100)) if expected_columns else 100
    warnings: List[str] = []
    if missing_columns:
        warnings.append(f"Colunas esperadas ausentes apos normalizacao: {', '.join(missing_columns)}.")

    return {
        "schema_recognized": True,
        "schema_coverage_percent": coverage_percent,
        "expected_columns": expected_columns,
        "available_normalized_columns": normalized_columns,
        "available_raw_columns": raw_columns,
        "missing_expected_columns": missing_columns,
        "schema_ready": bool(coverage_percent >= 80),
        "schema_warnings": warnings,
    }


def build_public_source_catalog_assessment(*, config_path: str, catalog: Any, source_provenance: Iterable[dict] | None = None) -> dict:
    provenance_by_name = {
        str((item or {}).get("source_name") or (item or {}).get("name") or ""): dict(item or {})
        for item in (source_provenance or [])
    }

    assessed_sources = []
    warnings: List[str] = []
    recognized_count = 0
    coverage_total = 0
    schema_coverage_total = 0
    schema_ready_count = 0

    for spec in getattr(catalog, "sources", []) or []:
        provenance = provenance_by_name.get(str(getattr(spec, "name", "")), {})
        release_info = infer_public_source_release(spec, provenance)
        schema_info = assess_public_source_schema(spec, provenance)
        readiness_percent = int(round((int(release_info.get("coverage_percent", 0)) + int(schema_info.get("schema_coverage_percent", 0))) / 2))
        source_row = {
            "source_name": getattr(spec, "name", None),
            "kind": getattr(spec, "kind", None),
            "source_format": getattr(spec, "format", None),
            "preset": getattr(spec, "preset", None),
            "path": getattr(spec, "path", None),
            "url": getattr(spec, "url", None),
            "gene_allowlist": list(getattr(spec, "gene_allowlist", []) or []),
            **release_info,
            **schema_info,
            "readiness_percent": readiness_percent,
            "ready_for_public_use": bool(release_info["recognized_public_source"] and schema_info["schema_ready"] and release_info.get("coverage_percent", 0) >= 75),
        }
        assessed_sources.append(source_row)
        if release_info["recognized_public_source"]:
            recognized_count += 1
            coverage_total += int(release_info.get("coverage_percent", 0))
            schema_coverage_total += int(schema_info.get("schema_coverage_percent", 0))
            if schema_info.get("schema_ready"):
                schema_ready_count += 1
            warnings.extend(list(release_info.get("warnings") or []))
            warnings.extend(list(schema_info.get("schema_warnings") or []))

    coverage_percent = int(round(coverage_total / recognized_count)) if recognized_count else 0
    schema_coverage_percent = int(round(schema_coverage_total / recognized_count)) if recognized_count else 0
    overall_readiness_percent = int(round((coverage_percent + schema_coverage_percent) / 2)) if recognized_count else 0
    summary = {
        "config_path": str(Path(config_path).resolve()),
        "n_sources": int(len(assessed_sources)),
        "n_recognized_public_sources": int(recognized_count),
        "n_sources_with_release": int(sum(1 for item in assessed_sources if item.get("release_value"))),
        "release_coverage_percent": coverage_percent,
        "schema_coverage_percent": schema_coverage_percent,
        "n_schema_ready_sources": int(schema_ready_count),
        "overall_readiness_percent": overall_readiness_percent,
        "ready_for_public_benchmark": bool(recognized_count > 0 and coverage_percent >= 75 and schema_coverage_percent >= 80),
    }

    markdown_lines = [
        "# Public Source Catalog Assessment",
        "",
        f"- Config path: {summary['config_path']}",
        f"- Total sources: {summary['n_sources']}",
        f"- Recognized public sources: {summary['n_recognized_public_sources']}",
        f"- Sources with explicit or inferred release: {summary['n_sources_with_release']}",
        f"- Release coverage: {summary['release_coverage_percent']}%",
        f"- Schema coverage: {summary['schema_coverage_percent']}%",
        f"- Overall readiness: {summary['overall_readiness_percent']}%",
        f"- Ready for public benchmark: {'yes' if summary['ready_for_public_benchmark'] else 'not yet'}",
        "",
        "## Sources",
        "",
    ]

    for item in assessed_sources:
        markdown_lines.extend(
            [
                f"### {item['source_name']}",
                "",
                f"- Recognized: {'yes' if item['recognized_public_source'] else 'no'}",
                f"- Public source: {item.get('display_name') or '-'}",
                f"- Release: {item.get('release_value') or '-'}",
                f"- Release method: {item.get('release_method') or '-'}",
                f"- Release coverage: {item.get('coverage_percent', 0)}%",
                f"- Schema coverage: {item.get('schema_coverage_percent', 0)}%",
                f"- Overall readiness: {item.get('readiness_percent', 0)}%",
                f"- Citation: {item.get('citation_url') or '-'}",
                "",
            ]
        )
        for warning in [*list(item.get("warnings") or []), *list(item.get("schema_warnings") or [])]:
            markdown_lines.append(f"- Warning: {warning}")
        if item.get("warnings") or item.get("schema_warnings"):
            markdown_lines.append("")

    unique_warnings = sorted({warning for warning in warnings if warning})
    return {
        "summary": summary,
        "sources": assessed_sources,
        "warnings": unique_warnings,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }
