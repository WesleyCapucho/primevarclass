from __future__ import annotations

import csv
import json
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .independent_data_expansion import DEFAULT_EXPANSION_GENES


GENE_UNIPROT_ACCESSIONS: dict[str, str] = {
    "BRCA1": "P38398",
    "BRCA2": "P51587",
    "TP53": "P04637",
    "PTEN": "P60484",
    "MSH2": "P43246",
    "KRAS": "P01116",
    "GCK": "P35557",
    "F9": "P00740",
}

GENE_ENSEMBL_IDS: dict[str, str] = {
    "BRCA1": "ENSG00000012048",
    "BRCA2": "ENSG00000139618",
    "TP53": "ENSG00000141510",
    "PTEN": "ENSG00000171862",
    "MSH2": "ENSG00000095002",
    "KRAS": "ENSG00000133703",
    "GCK": "ENSG00000106633",
    "F9": "ENSG00000101981",
}

GENE_ENTREZ_IDS: dict[str, int] = {
    "BRCA1": 672,
    "BRCA2": 675,
    "TP53": 7157,
    "PTEN": 5728,
    "MSH2": 4436,
    "KRAS": 3845,
    "GCK": 2645,
    "F9": 2158,
}

OPEN_SOURCE_TARGETS = [
    "clingen_erepo",
    "uniprot",
    "alphafold_db",
    "pdb",
    "civic",
    "cbioportal",
    "gdc",
    "gwas_catalog",
    "opentargets",
    "pharmgkb",
]


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


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout_sec: int = 20,
    headers: dict[str, str] | None = None,
) -> dict | list:
    body = None
    request_headers = {"Accept": "application/json", "User-Agent": "PrimeVarClass/independent-autostager"}
    request_headers.update(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_file(url: str, path: Path, *, timeout_sec: int = 120) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "PrimeVarClass/independent-autostager"})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response, path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return {"path": str(path), "size_bytes": int(path.stat().st_size), "url": url}


def _write_tsv(path: Path, rows: list[dict[str, Any]]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return {"path": str(path), "size_bytes": int(path.stat().st_size), "row_count": int(len(rows))}


def _safe_count(items: Any, predicate: str | None = None) -> int:
    if not isinstance(items, list):
        return 0
    if predicate is None:
        return len(items)
    return sum(1 for item in items if str((item or {}).get("type") or "").upper() == predicate.upper())


def _stage_clingen_erepo(root: Path, *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "clingen_erepo" / "clingen_erepo_classifications.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "clingen_erepo", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    result = _download_file(
        "https://erepo.clinicalgenome.org/evrepo/api/summary/classifications/download",
        path,
        timeout_sec=max(timeout_sec, 60),
    )
    return {"source_id": "clingen_erepo", "status": "staged", **result}


def _stage_uniprot(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "uniprot" / "target_gene_features.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "uniprot", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        accession = GENE_UNIPROT_ACCESSIONS.get(gene)
        if not accession:
            continue
        payload = _http_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json", timeout_sec=timeout_sec)
        comments = payload.get("comments") if isinstance(payload, dict) else []
        keywords = payload.get("keywords") if isinstance(payload, dict) else []
        features = payload.get("features") if isinstance(payload, dict) else []
        rows.append(
            {
                "gene": gene,
                "accession": payload.get("primaryAccession", accession),
                "reviewed": payload.get("entryType", ""),
                "length": ((payload.get("sequence") or {}).get("length") if isinstance(payload, dict) else ""),
                "domain_count": _safe_count(features, "Domain"),
                "disease_annotation_count": _safe_count(comments, "DISEASE"),
                "keyword_count": _safe_count(keywords),
                "source_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        )
    result = _write_tsv(path, rows)
    return {"source_id": "uniprot", "status": "staged", **result}


def _stage_alphafold(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "alphafold" / "target_gene_models.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "alphafold_db", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    skipped_genes: list[str] = []
    for gene in genes:
        accession = GENE_UNIPROT_ACCESSIONS.get(gene)
        if not accession:
            continue
        try:
            payload = _http_json(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}", timeout_sec=timeout_sec)
        except urllib.error.HTTPError:
            skipped_genes.append(gene)
            continue
        records = payload if isinstance(payload, list) else []
        for record in records[:1]:
            rows.append(
                {
                    "gene": gene,
                    "uniprot_accession": accession,
                    "model_url": record.get("cifUrl") or record.get("bcifUrl") or record.get("pdbUrl"),
                    "pae_url": record.get("paeDocUrl"),
                    "plddt_mean": record.get("confidenceScore"),
                    "fragment_start": record.get("uniprotStart"),
                    "fragment_end": record.get("uniprotEnd"),
                    "model_created_date": record.get("modelCreatedDate"),
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "alphafold_db", "status": "staged", "skipped_genes": ";".join(skipped_genes), **result}


def _rcsb_search(accession: str, *, timeout_sec: int, max_rows: int) -> list[str]:
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                "operator": "exact_match",
                "value": accession,
            },
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": max_rows}},
    }
    payload = _http_json("https://search.rcsb.org/rcsbsearch/v2/query", method="POST", payload=query, timeout_sec=timeout_sec)
    return [str(item.get("identifier")) for item in (payload.get("result_set") or []) if item.get("identifier")]


def _stage_pdb(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int, max_pdb_per_gene: int) -> dict:
    path = root / "data" / "raw" / "pdb" / "target_gene_structures.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "pdb", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        accession = GENE_UNIPROT_ACCESSIONS.get(gene)
        if not accession:
            continue
        for pdb_id in _rcsb_search(accession, timeout_sec=timeout_sec, max_rows=max_pdb_per_gene):
            try:
                entry = _http_json(f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}", timeout_sec=timeout_sec)
            except Exception:
                entry = {}
            info = entry.get("rcsb_entry_info") if isinstance(entry, dict) else {}
            rows.append(
                {
                    "gene": gene,
                    "pdb_id": pdb_id,
                    "experimental_method": ";".join(entry.get("experimental_method") or []),
                    "resolution": ";".join(str(item) for item in (info.get("resolution_combined") or [])),
                    "chain_count": info.get("polymer_entity_count"),
                    "ligand_count": info.get("nonpolymer_entity_count"),
                    "source_url": f"https://www.rcsb.org/structure/{pdb_id}",
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "pdb", "status": "staged", **result}


def _stage_civic(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "civic" / "target_gene_civic.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "civic", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    query = (
        "query Genes($symbols: [String!]) { "
        "genes(entrezSymbols: $symbols, first: 100) { nodes { id name description variants { totalCount } } } }"
    )
    payload = _http_json(
        "https://civicdb.org/api/graphql",
        method="POST",
        payload={"query": query, "variables": {"symbols": genes}},
        timeout_sec=timeout_sec,
    )
    nodes = (((payload or {}).get("data") or {}).get("genes") or {}).get("nodes") or []
    rows = [
        {
            "gene": node.get("name"),
            "evidence_count": ((node.get("variants") or {}).get("totalCount")),
            "disease": "",
            "drug": "",
            "description": node.get("description"),
            "source_url": f"https://civicdb.org/links/genes/{node.get('id')}",
        }
        for node in nodes
    ]
    result = _write_tsv(path, rows)
    return {"source_id": "civic", "status": "staged", **result}


def _stage_cbioportal(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "cbioportal" / "brca_tcga_pan_can_mutations.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "cbioportal", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        entrez_id = GENE_ENTREZ_IDS.get(gene)
        if not entrez_id:
            continue
        try:
            payload = _http_json(
                "https://www.cbioportal.org/api/molecular-profiles/brca_tcga_pan_can_atlas_2018_mutations/mutations/fetch?projection=SUMMARY",
                method="POST",
                payload={"entrezGeneIds": [entrez_id], "sampleListId": "brca_tcga_pan_can_atlas_2018_all"},
                timeout_sec=timeout_sec,
            )
        except urllib.error.HTTPError:
            payload = []
        for item in payload if isinstance(payload, list) else []:
            rows.append(
                {
                    "gene": gene,
                    "Hugo_Symbol": gene,
                    "HGVSp_Short": item.get("proteinChange"),
                    "Amino_Acid_Change": item.get("proteinChange"),
                    "mutationType": item.get("mutationType"),
                    "sampleId": item.get("sampleId"),
                    "studyId": item.get("studyId"),
                    "keyword": item.get("keyword"),
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "cbioportal", "status": "staged", **result}


def _stage_gdc(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "gdc" / "target_gene_metadata.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "gdc", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        ensembl_id = GENE_ENSEMBL_IDS.get(gene)
        if not ensembl_id:
            continue
        payload = _http_json(f"https://api.gdc.cancer.gov/genes/{ensembl_id}", timeout_sec=timeout_sec)
        data = (payload or {}).get("data") or {}
        rows.append(
            {
                "gene": gene,
                "gene_id": data.get("gene_id") or ensembl_id,
                "symbol": data.get("symbol") or gene,
                "name": data.get("name"),
                "biotype": data.get("biotype"),
                "source_url": f"https://api.gdc.cancer.gov/genes/{ensembl_id}",
            }
        )
    result = _write_tsv(path, rows)
    return {"source_id": "gdc", "status": "staged", **result}


def _stage_gwas(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int, max_gwas_per_gene: int) -> dict:
    path = root / "data" / "raw" / "gwas_catalog" / "target_gene_associations.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "gwas_catalog", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        url = "https://www.ebi.ac.uk/gwas/rest/api/v2/associations?" + urllib.parse.urlencode(
            {"mapped_gene": gene, "size": max_gwas_per_gene}
        )
        payload = _http_json(url, timeout_sec=timeout_sec)
        associations = (((payload or {}).get("_embedded") or {}).get("associations") or [])
        for item in associations:
            allele = (item.get("snp_allele") or [{}])[0] if isinstance(item.get("snp_allele"), list) else {}
            traits = item.get("efo_traits") or [{}]
            rows.append(
                {
                    "gene": gene,
                    "rsid": allele.get("rs_id"),
                    "pvalue": item.get("p_value"),
                    "or_beta": item.get("beta") or item.get("or_per_copy_number"),
                    "trait": traits[0].get("efo_trait") if traits else "",
                    "study_accession": item.get("accession_id"),
                    "pubmed_id": item.get("pubmed_id"),
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "gwas_catalog", "status": "staged", **result}


def _stage_opentargets(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "opentargets" / "target_disease_associations.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "opentargets", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    query = (
        "query Target($ensemblId: String!) { target(ensemblId: $ensemblId) { id approvedSymbol "
        "associatedDiseases(page: { index: 0, size: 5 }) { count rows { score disease { id name } } } } }"
    )
    rows: list[dict[str, Any]] = []
    for gene in genes:
        ensembl_id = GENE_ENSEMBL_IDS.get(gene)
        if not ensembl_id:
            continue
        payload = _http_json(
            "https://api.platform.opentargets.org/api/v4/graphql",
            method="POST",
            payload={"query": query, "variables": {"ensemblId": ensembl_id}},
            timeout_sec=timeout_sec,
        )
        target = (((payload or {}).get("data") or {}).get("target") or {})
        associated = (target.get("associatedDiseases") or {})
        for item in associated.get("rows") or []:
            disease = item.get("disease") or {}
            rows.append(
                {
                    "gene": gene,
                    "target_id": target.get("id") or ensembl_id,
                    "association_score": item.get("score"),
                    "disease": disease.get("name"),
                    "disease_id": disease.get("id"),
                    "evidence_count": associated.get("count"),
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "opentargets", "status": "staged", **result}


def _stage_pharmgkb(root: Path, genes: list[str], *, refresh: bool, timeout_sec: int) -> dict:
    path = root / "data" / "raw" / "pharmgkb" / "target_gene_pharmgkb.tsv"
    if path.exists() and path.stat().st_size > 512 and not refresh:
        return {"source_id": "pharmgkb", "status": "retained_existing", "path": str(path), "size_bytes": path.stat().st_size}
    rows: list[dict[str, Any]] = []
    for gene in genes:
        url = "https://api.pharmgkb.org/data/gene?" + urllib.parse.urlencode({"symbol": gene})
        payload = _http_json(url, timeout_sec=timeout_sec)
        for item in (payload.get("data") or []) if isinstance(payload, dict) else []:
            rows.append(
                {
                    "gene": item.get("symbol") or gene,
                    "variant_id": item.get("id"),
                    "level_of_evidence": item.get("vipTier"),
                    "drug": "",
                    "phenotype": item.get("alleleType"),
                    "significance": "cpic_gene" if item.get("cpicGene") else "",
                    "name": item.get("name"),
                    "source_url": f"https://www.pharmgkb.org/gene/{item.get('id')}",
                }
            )
    result = _write_tsv(path, rows)
    return {"source_id": "pharmgkb", "status": "staged", **result}


def build_independent_open_source_autostage_package(
    *,
    workspace_root: str | Path | None = None,
    target_genes: Iterable[str] | None = None,
    refresh: bool = False,
    timeout_sec: int = 20,
    max_gwas_per_gene: int = 8,
    max_pdb_per_gene: int = 8,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(workspace_root or Path.cwd()).resolve()
    genes = _normalize_genes(target_genes)
    staged: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    tasks = [
        lambda: _stage_clingen_erepo(root, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_uniprot(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_alphafold(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_pdb(root, genes, refresh=refresh, timeout_sec=timeout_sec, max_pdb_per_gene=max_pdb_per_gene),
        lambda: _stage_civic(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_cbioportal(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_gdc(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_gwas(root, genes, refresh=refresh, timeout_sec=timeout_sec, max_gwas_per_gene=max_gwas_per_gene),
        lambda: _stage_opentargets(root, genes, refresh=refresh, timeout_sec=timeout_sec),
        lambda: _stage_pharmgkb(root, genes, refresh=refresh, timeout_sec=timeout_sec),
    ]
    for task in tasks:
        try:
            staged.append(task())
        except Exception as exc:
            errors.append({"source_id": "unknown", "status": "failed", "error": str(exc)})

    staged_count = sum(
        1
        for item in staged
        if int(item.get("row_count") or 0) > 0 or int(item.get("size_bytes") or 0) > 512
    )
    summary = {
        "workspace_root": str(root),
        "target_genes": genes,
        "attempted_source_count": len(OPEN_SOURCE_TARGETS),
        "staged_source_count": int(staged_count),
        "failed_source_count": int(len(errors)),
        "total_staged_size_bytes": int(sum(int(item.get("size_bytes") or 0) for item in staged)),
        "autostaging_readiness_percent": int(round((staged_count / max(len(OPEN_SOURCE_TARGETS), 1)) * 100)),
        "ready_for_staging_closure_refresh": staged_count >= 7,
    }
    return {
        "generated_at": _now_utc(),
        "summary": summary,
        "staged_sources": staged,
        "errors": errors,
        "report_context": dict(report_context or {}),
    }


def export_independent_open_source_autostage_package(
    *,
    output_dir: str,
    workspace_root: str | Path | None = None,
    target_genes: Iterable[str] | None = None,
    refresh: bool = False,
    timeout_sec: int = 20,
    max_gwas_per_gene: int = 8,
    max_pdb_per_gene: int = 8,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    package = build_independent_open_source_autostage_package(
        workspace_root=workspace_root,
        target_genes=target_genes,
        refresh=refresh,
        timeout_sec=timeout_sec,
        max_gwas_per_gene=max_gwas_per_gene,
        max_pdb_per_gene=max_pdb_per_gene,
        report_context=report_context,
    )
    manifest_path = output_root / "independent_open_source_autostage_manifest.json"
    status_path = output_root / "independent_open_source_autostage_status.csv"
    error_path = output_root / "independent_open_source_autostage_errors.csv"
    _write_tsv(status_path, list(package["staged_sources"]))
    _write_tsv(error_path, list(package["errors"]))
    manifest_path.write_text(json.dumps(_jsonify(package), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "independent_open_source_autostage_manifest_path": str(manifest_path),
        "independent_open_source_autostage_status_path": str(status_path),
        "independent_open_source_autostage_errors_path": str(error_path),
        "summary": package["summary"],
        "staged_sources": package["staged_sources"],
        "errors": package["errors"],
    }
