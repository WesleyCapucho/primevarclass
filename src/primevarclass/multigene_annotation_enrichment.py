from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .multigene_real_benchmark import DEFAULT_TARGET_GENES
from .real_data_preparation import _jsonify, _render_markdown_html


GNOMAD_ENDPOINT = "https://gnomad.broadinstitute.org/api"
MAVEDB_API_BASE = "https://api.mavedb.org/api/v1"


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


def _read_table(path_value: str | Path | None, *, sep: str | None = None) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        read_sep = sep
        if read_sep is None:
            read_sep = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
        return pd.read_csv(path, sep=read_sep)
    except Exception:
        return pd.DataFrame()


def _string(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "na", "<na>"}:
        return ""
    return text


def _normalize_gene(value: Any) -> str:
    return _string(value).upper()


def _normalize_hgvs(value: Any) -> str:
    text = _string(value)
    if not text:
        return ""
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    return text.replace(" ", "")


def _column_or_default(df: pd.DataFrame, column: str, default: Any = "") -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _cohort_kind_from_path(path: Path) -> str:
    name = path.name.lower()
    if "combined_external" in name:
        return "combined_external"
    if "secondary_external" in name:
        return "secondary_external"
    if "clinical_external" in name:
        return "clinical_external"
    if "training" in name:
        return "training"
    return "unknown"


def _target_gene_list(manifest: dict[str, Any], target_genes: Iterable[str] | None) -> list[str]:
    if target_genes:
        genes = [_normalize_gene(gene) for gene in target_genes if _normalize_gene(gene)]
    else:
        summary = manifest.get("summary") or {}
        genes = [_normalize_gene(gene) for gene in summary.get("target_genes") or DEFAULT_TARGET_GENES]
    return sorted(set(genes))


def _source_multigene_root(manifest: dict[str, Any], fallback: str | Path | None) -> Path:
    if fallback:
        return Path(fallback).expanduser()
    variant_path = _string((manifest.get("summary") or {}).get("variant_summary_input_path"))
    if variant_path:
        candidate = Path(variant_path).expanduser().parent.parent / "multigene"
        if candidate.exists():
            return candidate
    return Path("data/raw/multigene")


def _collect_multigene_variants(
    *,
    multigene_root: Path,
    target_genes: Iterable[str],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for gene in target_genes:
        gene_dir = multigene_root / gene
        if not gene_dir.exists():
            gene_dir = multigene_root / gene.upper()
        if not gene_dir.exists():
            gene_dir = multigene_root / gene.lower()
        if not gene_dir.exists():
            continue
        for path in sorted(gene_dir.glob("*.tsv")):
            raw = _read_table(path, sep="\t")
            if raw.empty:
                continue
            work = pd.DataFrame(
                {
                    "gene": raw.get("GeneSymbol", gene),
                    "hgvs_p": raw.get("Protein change", ""),
                    "clinical_significance": raw.get("ClinicalSignificance", ""),
                    "review_status": raw.get("ReviewStatus", ""),
                    "variation_id": raw.get("VariationID", ""),
                    "variant_name": raw.get("Name", ""),
                    "last_evaluated": raw.get("LastEvaluated", ""),
                }
            )
            work["gene"] = work["gene"].map(_normalize_gene)
            work["hgvs_p"] = work["hgvs_p"].map(_normalize_hgvs)
            work["variation_id"] = work["variation_id"].map(_string)
            work["source_cohort_kind"] = _cohort_kind_from_path(path)
            work["source_cohort_path"] = str(path.resolve())
            frames.append(work)
    if not frames:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "clinical_significance",
                "review_status",
                "variation_id",
                "variant_name",
                "last_evaluated",
                "source_cohort_kind",
                "source_cohort_path",
            ]
        )
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.loc[(combined["gene"] != "") & (combined["hgvs_p"] != "")].copy()
    combined["source_priority"] = combined["source_cohort_kind"].map(
        {
            "combined_external": 4,
            "clinical_external": 3,
            "secondary_external": 2,
            "training": 1,
        }
    ).fillna(0)
    combined["last_evaluated_sort"] = pd.to_datetime(combined["last_evaluated"], errors="coerce")
    combined = combined.sort_values(
        ["gene", "hgvs_p", "variation_id", "source_priority", "last_evaluated_sort"],
        ascending=[True, True, True, False, False],
        kind="stable",
    )
    return combined.drop_duplicates(subset=["gene", "hgvs_p", "variation_id"], keep="first").drop(
        columns=["source_priority", "last_evaluated_sort"],
        errors="ignore",
    )


def _variant_summary_path(manifest: dict[str, Any], explicit_path: str | Path | None) -> Path | None:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        return path if path.exists() else None
    summary_path = _string((manifest.get("summary") or {}).get("variant_summary_input_path"))
    if summary_path and Path(summary_path).expanduser().exists():
        return Path(summary_path).expanduser()
    for candidate in [
        Path("data/raw/clinvar/variant_summary.txt"),
        Path("data/raw/clinvar/variant_summary.txt.gz"),
    ]:
        if candidate.exists():
            return candidate
    return None


def _required_clinvar_columns() -> set[str]:
    return {
        "GeneSymbol",
        "Assembly",
        "Chromosome",
        "Start",
        "Stop",
        "ReferenceAllele",
        "AlternateAllele",
        "VariationID",
        "PositionVCF",
        "ReferenceAlleleVCF",
        "AlternateAlleleVCF",
        "RS# (dbSNP)",
    }


def _scan_clinvar_coordinate_metadata(
    *,
    variant_summary_path: Path | None,
    variation_ids: Iterable[str],
    target_genes: Iterable[str],
    chunk_size: int = 150000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ids = {_string(value) for value in variation_ids if _string(value)}
    genes = {_normalize_gene(value) for value in target_genes if _normalize_gene(value)}
    if not variant_summary_path or not variant_summary_path.exists() or not ids:
        return pd.DataFrame(), {
            "variant_summary_path": str(variant_summary_path) if variant_summary_path else None,
            "variation_ids_requested": len(ids),
            "coordinate_rows_found": 0,
            "raw_rows_scanned": 0,
            "status": "missing_input",
        }

    read_kwargs = {
        "sep": "\t",
        "low_memory": False,
        "usecols": lambda column_name: str(column_name) in _required_clinvar_columns(),
        "chunksize": int(chunk_size),
    }
    suffixes = [suffix.lower() for suffix in variant_summary_path.suffixes]
    if suffixes[-2:] in [[".txt", ".gz"], [".tsv", ".gz"]]:
        reader = pd.read_csv(variant_summary_path, compression="gzip", **read_kwargs)
    else:
        reader = pd.read_csv(variant_summary_path, **read_kwargs)

    frames: list[pd.DataFrame] = []
    raw_rows = 0
    for chunk in reader:
        raw_rows += int(len(chunk))
        work = chunk.copy()
        if "VariationID" not in work.columns:
            continue
        work["variation_id"] = work["VariationID"].map(_string)
        if "GeneSymbol" in work.columns:
            work["gene"] = work["GeneSymbol"].map(_normalize_gene)
            mask = work["variation_id"].isin(ids) & work["gene"].isin(genes)
        else:
            mask = work["variation_id"].isin(ids)
        selected = work.loc[mask].copy()
        if not selected.empty:
            frames.append(selected)

    if not frames:
        return pd.DataFrame(), {
            "variant_summary_path": str(variant_summary_path.resolve()),
            "variation_ids_requested": len(ids),
            "coordinate_rows_found": 0,
            "raw_rows_scanned": raw_rows,
            "status": "no_matches",
        }

    metadata = pd.concat(frames, ignore_index=True)
    metadata["gene"] = _column_or_default(metadata, "GeneSymbol").map(_normalize_gene)
    metadata["variation_id"] = _column_or_default(metadata, "VariationID").map(_string)
    metadata["assembly"] = _column_or_default(metadata, "Assembly").map(_string)
    metadata["chromosome"] = _column_or_default(metadata, "Chromosome").map(_string)
    metadata["position_vcf"] = _column_or_default(metadata, "PositionVCF").map(_string)
    metadata["reference_allele_vcf"] = _column_or_default(metadata, "ReferenceAlleleVCF").map(_string)
    metadata["alternate_allele_vcf"] = _column_or_default(metadata, "AlternateAlleleVCF").map(_string)
    metadata["rsid"] = _column_or_default(metadata, "RS# (dbSNP)").map(_string)
    metadata["has_grch38_coordinate"] = (
        metadata["assembly"].str.upper().eq("GRCH38")
        & metadata["chromosome"].ne("")
        & metadata["position_vcf"].ne("")
        & metadata["reference_allele_vcf"].ne("")
        & metadata["alternate_allele_vcf"].ne("")
    )
    metadata["assembly_priority"] = np.select(
        [
            metadata["assembly"].str.upper().eq("GRCH38"),
            metadata["assembly"].str.upper().eq("GRCH37"),
        ],
        [2, 1],
        default=0,
    )
    metadata = metadata.sort_values(
        ["variation_id", "has_grch38_coordinate", "assembly_priority"],
        ascending=[True, False, False],
        kind="stable",
    )
    metadata = metadata.drop_duplicates(subset=["variation_id"], keep="first")

    columns = [
        "gene",
        "variation_id",
        "assembly",
        "chromosome",
        "Start",
        "Stop",
        "ReferenceAllele",
        "AlternateAllele",
        "position_vcf",
        "reference_allele_vcf",
        "alternate_allele_vcf",
        "rsid",
        "has_grch38_coordinate",
    ]
    compact = metadata[[column for column in columns if column in metadata.columns]].copy()
    return compact, {
        "variant_summary_path": str(variant_summary_path.resolve()),
        "variation_ids_requested": len(ids),
        "coordinate_rows_found": int(len(compact)),
        "raw_rows_scanned": raw_rows,
        "status": "completed",
    }


def _gnomad_variant_id(row: pd.Series) -> str:
    if str(row.get("has_grch38_coordinate")).lower() not in {"true", "1"}:
        return ""
    chromosome = _string(row.get("chromosome")).replace("chr", "").replace("CHR", "")
    position = _string(row.get("position_vcf"))
    reference = _string(row.get("reference_allele_vcf"))
    alternate = _string(row.get("alternate_allele_vcf"))
    if not chromosome or not position or not reference or not alternate:
        return ""
    return f"{chromosome}-{position}-{reference}-{alternate}"


def _load_local_gnomad(gnomad_dir: Path, target_genes: Iterable[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for gene in target_genes:
        path = gnomad_dir / f"{gene.lower()}_missense_annotations.tsv"
        raw = _read_table(path, sep="\t")
        if raw.empty:
            continue
        work = raw.copy()
        if "gene" not in work.columns or "hgvs_p" not in work.columns:
            continue
        work["gene"] = work["gene"].map(_normalize_gene)
        work["hgvs_p"] = work["hgvs_p"].map(_normalize_hgvs)
        work["local_gnomad_source_path"] = str(path.resolve())
        frames.append(work)
    if not frames:
        return pd.DataFrame(columns=["gene", "hgvs_p"])
    combined = pd.concat(frames, ignore_index=True)
    keep_columns = [
        column
        for column in [
            "gene",
            "hgvs_p",
            "af",
            "ac",
            "an",
            "popmax_af",
            "meta_gnomad_variant_id",
            "meta_gnomad_dataset",
            "meta_gnomad_reference_genome",
            "local_gnomad_source_path",
        ]
        if column in combined.columns
    ]
    return combined[keep_columns].drop_duplicates(subset=["gene", "hgvs_p"], keep="first")


def _load_local_mavedb(mavedb_dir: Path, target_genes: Iterable[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for gene in target_genes:
        path = mavedb_dir / f"{gene.lower()}_function_scores.csv"
        raw = _read_table(path, sep=",")
        if raw.empty:
            continue
        if "gene" not in raw.columns or "hgvs_p" not in raw.columns:
            continue
        work = raw.copy()
        work["gene"] = work["gene"].map(_normalize_gene)
        work["hgvs_p"] = work["hgvs_p"].map(_normalize_hgvs)
        work["local_mavedb_source_path"] = str(path.resolve())
        frames.append(work)
    if not frames:
        return pd.DataFrame(columns=["gene", "hgvs_p"])
    combined = pd.concat(frames, ignore_index=True)
    keep_columns = [
        column
        for column in [
            "gene",
            "hgvs_p",
            "score",
            "score_se",
            "score_set_urn",
            "assay_name",
            "local_mavedb_source_path",
        ]
        if column in combined.columns
    ]
    return combined[keep_columns].drop_duplicates(subset=["gene", "hgvs_p"], keep="first")


def _post_json(url: str, payload: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_text(url: str, timeout_sec: int) -> str:
    request = urllib.request.Request(url, headers={"Accept": "text/csv,application/json,text/plain,*/*"})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return response.read().decode("utf-8", errors="replace")


def _fetch_mavedb_scores_for_genes(
    *,
    target_genes: Iterable[str],
    max_score_sets_per_gene: int,
    timeout_sec: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    score_sets: list[dict[str, Any]] = []
    score_frames: list[pd.DataFrame] = []
    errors: list[dict[str, Any]] = []
    if max_score_sets_per_gene <= 0:
        return pd.DataFrame(), pd.DataFrame(), errors

    for gene in target_genes:
        try:
            search_payload = {"published": True, "targets": [gene], "limit": max_score_sets_per_gene, "offset": 0}
            search = _post_json(f"{MAVEDB_API_BASE}/score-sets/search", search_payload, timeout_sec)
        except Exception as exc:
            errors.append({"gene": gene, "stage": "search", "error": str(exc)})
            continue
        for score_set in search.get("scoreSets") or []:
            urn = _string(score_set.get("urn"))
            if not urn:
                continue
            title = _string(score_set.get("title"))
            score_sets.append(
                {
                    "gene": gene,
                    "score_set_urn": urn,
                    "title": title,
                    "published_date": score_set.get("publishedDate"),
                    "num_variants": score_set.get("numVariants"),
                }
            )
            try:
                encoded = urllib.parse.quote(urn, safe="")
                text = _get_text(f"{MAVEDB_API_BASE}/score-sets/{encoded}/scores", timeout_sec)
                raw_scores = pd.read_csv(io.StringIO(text))
            except Exception as exc:
                errors.append({"gene": gene, "stage": "scores", "score_set_urn": urn, "error": str(exc)})
                continue
            if raw_scores.empty:
                continue
            protein_column = next(
                (column for column in ["hgvs_pro", "hgvs_p", "hgvs_protein", "protein_change"] if column in raw_scores.columns),
                None,
            )
            if not protein_column:
                continue
            score_column = "score" if "score" in raw_scores.columns else None
            if not score_column:
                numeric_columns = raw_scores.select_dtypes(include=["number"]).columns.tolist()
                score_column = numeric_columns[0] if numeric_columns else None
            work = pd.DataFrame(
                {
                    "gene": gene,
                    "hgvs_p": raw_scores[protein_column].map(_normalize_hgvs),
                    "live_mavedb_score": raw_scores[score_column] if score_column else np.nan,
                    "live_mavedb_score_set_urn": urn,
                    "live_mavedb_assay_name": title,
                }
            )
            work = work.loc[work["hgvs_p"].ne("")].copy()
            score_frames.append(work)

    score_set_df = pd.DataFrame(score_sets)
    scores_df = pd.concat(score_frames, ignore_index=True) if score_frames else pd.DataFrame()
    if not scores_df.empty:
        scores_df["gene"] = scores_df["gene"].map(_normalize_gene)
        scores_df = scores_df.drop_duplicates(subset=["gene", "hgvs_p"], keep="first")
    return score_set_df, scores_df, errors


def _query_gnomad_variant(variant_id: str, *, dataset: str, timeout_sec: int) -> dict[str, Any]:
    query = """
    query Variant($variantId: String!, $dataset: DatasetId!) {
      variant(variantId: $variantId, dataset: $dataset) {
        variant_id
        reference_genome
        exome { ac an af }
        genome { ac an af }
      }
    }
    """
    payload = {"query": query, "variables": {"variantId": variant_id, "dataset": dataset}}
    try:
        response = _post_json(GNOMAD_ENDPOINT, payload, timeout_sec)
    except (urllib.error.URLError, TimeoutError, Exception) as exc:
        return {"variant_id": variant_id, "status": "query_error", "error": str(exc)}
    if response.get("errors"):
        return {"variant_id": variant_id, "status": "graphql_error", "error": json.dumps(response.get("errors"))[:500]}
    variant = ((response.get("data") or {}).get("variant") or {})
    if not variant:
        return {"variant_id": variant_id, "status": "not_found"}
    exome = variant.get("exome") or {}
    genome = variant.get("genome") or {}
    preferred = exome if exome.get("an") else genome
    return {
        "variant_id": variant_id,
        "status": "found",
        "reference_genome": variant.get("reference_genome"),
        "live_gnomad_ac": preferred.get("ac"),
        "live_gnomad_an": preferred.get("an"),
        "live_gnomad_af": preferred.get("af"),
        "live_gnomad_exome_af": exome.get("af"),
        "live_gnomad_genome_af": genome.get("af"),
    }


def _run_live_gnomad_queries(
    matrix: pd.DataFrame,
    *,
    max_queries: int,
    max_queries_per_gene: int,
    dataset: str,
    timeout_sec: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if matrix.empty or max_queries <= 0:
        return matrix, pd.DataFrame()

    work = matrix.copy()
    default_values = {
        "live_gnomad_attempted": False,
        "live_gnomad_status": "",
        "live_gnomad_af": np.nan,
        "live_gnomad_ac": np.nan,
        "live_gnomad_an": np.nan,
        "live_gnomad_reference_genome": "",
        "live_gnomad_error": "",
    }
    for column, default_value in default_values.items():
        if column not in work.columns:
            work[column] = default_value

    candidates = work.loc[work["gnomad_variant_id"].astype(str).ne("")].copy()
    if candidates.empty:
        return work, pd.DataFrame()
    candidates = (
        candidates.sort_values(["gene", "source_cohort_kind", "hgvs_p"], ascending=[True, True, True], kind="stable")
        .groupby("gene", group_keys=False)
        .head(max_queries_per_gene)
        .head(max_queries)
    )
    query_records: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        gnomad_variant = _string(row.get("gnomad_variant_id"))
        result = _query_gnomad_variant(gnomad_variant, dataset=dataset, timeout_sec=timeout_sec)
        result["gene"] = row.get("gene")
        result["hgvs_p"] = row.get("hgvs_p")
        result["variation_id"] = row.get("variation_id")
        query_records.append(result)
        mask = (
            work["gene"].eq(row.get("gene"))
            & work["hgvs_p"].eq(row.get("hgvs_p"))
            & work["variation_id"].astype(str).eq(_string(row.get("variation_id")))
        )
        work.loc[mask, "live_gnomad_attempted"] = True
        work.loc[mask, "live_gnomad_status"] = result.get("status", "")
        work.loc[mask, "live_gnomad_af"] = result.get("live_gnomad_af", np.nan)
        work.loc[mask, "live_gnomad_ac"] = result.get("live_gnomad_ac", np.nan)
        work.loc[mask, "live_gnomad_an"] = result.get("live_gnomad_an", np.nan)
        work.loc[mask, "live_gnomad_reference_genome"] = result.get("reference_genome", "")
        work.loc[mask, "live_gnomad_error"] = result.get("error", "")
    return work, pd.DataFrame(query_records)


def _build_matrix(
    *,
    variants: pd.DataFrame,
    coordinates: pd.DataFrame,
    local_gnomad: pd.DataFrame,
    local_mavedb: pd.DataFrame,
    live_mavedb_scores: pd.DataFrame,
) -> pd.DataFrame:
    matrix = variants.copy()
    if not coordinates.empty:
        matrix = matrix.merge(coordinates, on=["gene", "variation_id"], how="left", suffixes=("", "_clinvar"))
    else:
        matrix["assembly"] = ""
        matrix["chromosome"] = ""
        matrix["position_vcf"] = ""
        matrix["reference_allele_vcf"] = ""
        matrix["alternate_allele_vcf"] = ""
        matrix["rsid"] = ""
        matrix["has_grch38_coordinate"] = False
    matrix["has_grch38_coordinate"] = matrix["has_grch38_coordinate"].fillna(False).astype(bool)
    matrix["gnomad_variant_id"] = matrix.apply(_gnomad_variant_id, axis=1)

    if not local_gnomad.empty:
        local = local_gnomad.rename(
            columns={
                "af": "local_gnomad_af",
                "ac": "local_gnomad_ac",
                "an": "local_gnomad_an",
                "popmax_af": "local_gnomad_popmax_af",
            }
        )
        matrix = matrix.merge(local, on=["gene", "hgvs_p"], how="left")
    else:
        matrix["local_gnomad_af"] = np.nan
        matrix["local_gnomad_ac"] = np.nan
        matrix["local_gnomad_an"] = np.nan
    matrix["local_gnomad_available"] = matrix.get("local_gnomad_af", pd.Series(dtype=float)).notna()

    if not local_mavedb.empty:
        local_mave = local_mavedb.rename(
            columns={
                "score": "local_mavedb_score",
                "score_set_urn": "local_mavedb_score_set_urn",
                "assay_name": "local_mavedb_assay_name",
            }
        )
        matrix = matrix.merge(local_mave, on=["gene", "hgvs_p"], how="left")
    else:
        matrix["local_mavedb_score"] = np.nan
    matrix["local_mavedb_available"] = matrix.get("local_mavedb_score", pd.Series(dtype=float)).notna()

    if not live_mavedb_scores.empty:
        matrix = matrix.merge(live_mavedb_scores, on=["gene", "hgvs_p"], how="left")
    else:
        matrix["live_mavedb_score"] = np.nan
        matrix["live_mavedb_score_set_urn"] = ""
        matrix["live_mavedb_assay_name"] = ""
    matrix["live_mavedb_available"] = matrix.get("live_mavedb_score", pd.Series(dtype=float)).notna()
    matrix["mavedb_line_available"] = matrix["local_mavedb_available"] | matrix["live_mavedb_available"]

    matrix["source_trace_ready"] = (
        matrix["variation_id"].astype(str).ne("")
        & matrix["variant_name"].astype(str).ne("")
        & matrix["review_status"].astype(str).ne("")
    )
    matrix["coordinate_ready"] = matrix["gnomad_variant_id"].astype(str).ne("")
    matrix["gnomad_line_available"] = matrix["local_gnomad_available"]
    matrix["annotation_status"] = np.select(
        [
            matrix["coordinate_ready"] & matrix["gnomad_line_available"] & matrix["mavedb_line_available"],
            matrix["coordinate_ready"] & matrix["gnomad_line_available"],
            matrix["coordinate_ready"] & matrix["mavedb_line_available"],
            matrix["coordinate_ready"],
        ],
        [
            "coordinate_gnomad_mavedb_complete",
            "coordinate_gnomad_complete_mavedb_missing",
            "coordinate_mavedb_complete_gnomad_missing",
            "coordinate_ready_annotation_missing",
        ],
        default="needs_coordinate_reconciliation",
    )
    return matrix


def _coverage_table(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    rows = []
    for gene, group in matrix.groupby("gene", dropna=False):
        row_count = len(group)
        rows.append(
            {
                "gene": gene,
                "variant_rows": int(row_count),
                "coordinate_coverage_percent": _percent(group["coordinate_ready"].mean() * 100 if row_count else 0),
                "local_gnomad_line_coverage_percent": _percent(group["local_gnomad_available"].mean() * 100 if row_count else 0),
                "live_gnomad_attempt_coverage_percent": _percent(
                    (_column_or_default(group, "live_gnomad_attempted", False).astype(bool).mean() * 100) if row_count else 0
                ),
                "live_gnomad_hit_coverage_percent": _percent(
                    (_column_or_default(group, "live_gnomad_status").eq("found").mean() * 100) if row_count else 0
                ),
                "mavedb_line_coverage_percent": _percent(group["mavedb_line_available"].mean() * 100 if row_count else 0),
                "source_trace_coverage_percent": _percent(group["source_trace_ready"].mean() * 100 if row_count else 0),
            }
        )
    coverage = pd.DataFrame(rows)
    coverage["line_level_annotation_readiness_percent"] = (
        coverage["coordinate_coverage_percent"] * 0.30
        + np.maximum(coverage["local_gnomad_line_coverage_percent"], coverage["live_gnomad_hit_coverage_percent"]) * 0.35
        + coverage["mavedb_line_coverage_percent"] * 0.25
        + coverage["source_trace_coverage_percent"] * 0.10
    ).round().astype(int)
    return coverage.sort_values(["line_level_annotation_readiness_percent", "gene"], ascending=[False, True], kind="stable")


def _build_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    coverage = payload.get("coverage_by_gene")
    coverage_df = coverage if isinstance(coverage, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Multigene Row-Level Annotation Enrichment",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Target genes: `{', '.join(summary.get('target_genes') or [])}`",
        f"- Variant rows: `{summary.get('variant_row_count', 0)}`",
        f"- GRCh38 coordinate coverage: `{summary.get('genomic_coordinate_coverage_percent', 0)}%`",
        f"- gnomAD line evidence coverage: `{summary.get('gnomad_line_evidence_coverage_percent', 0)}%`",
        f"- MaveDB line evidence coverage: `{summary.get('mavedb_line_evidence_coverage_percent', 0)}%`",
        f"- Line-level annotation readiness: `{summary.get('line_level_annotation_readiness_percent', 0)}%`",
        "",
        "## Gene coverage",
        "",
    ]
    if coverage_df.empty:
        lines.append("- No coverage rows were generated.")
    else:
        lines.extend(["| Gene | Rows | Coord | gnomAD hit | MaveDB | Readiness |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in coverage_df.to_dict(orient="records"):
            lines.append(
                f"| {row['gene']} | {row['variant_rows']} | {row['coordinate_coverage_percent']}% | "
                f"{max(row['local_gnomad_line_coverage_percent'], row['live_gnomad_hit_coverage_percent'])}% | "
                f"{row['mavedb_line_coverage_percent']}% | {row['line_level_annotation_readiness_percent']}% |"
            )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- gnomAD live queries are intentionally capped to keep the benchmark reproducible and respectful of public services.",
            "- MaveDB live evidence is joined by gene and protein HGVS; genomic VRS reconciliation is queued as the next precision upgrade.",
            "- Rows without GRCh38 coordinates remain excluded from gnomAD allele-frequency interpretation until coordinate reconciliation is complete.",
        ]
    )
    return "\n".join(lines).strip()


def build_multigene_annotation_enrichment_package(
    *,
    multigene_real_benchmark_manifest_path: str,
    variant_summary_path: str | None = None,
    multigene_root: str | None = None,
    gnomad_dir: str = "data/raw/gnomad",
    mavedb_dir: str = "data/raw/mavedb",
    target_genes: Iterable[str] | None = None,
    run_live_gnomad: bool = True,
    max_live_gnomad_queries: int = 48,
    max_live_gnomad_queries_per_gene: int = 8,
    gnomad_dataset: str = "gnomad_r4",
    run_live_mavedb: bool = True,
    max_live_mavedb_score_sets_per_gene: int = 1,
    timeout_sec: int = 20,
) -> dict[str, Any]:
    manifest = _load_json(multigene_real_benchmark_manifest_path)
    genes = _target_gene_list(manifest, target_genes)
    root = _source_multigene_root(manifest, multigene_root)
    variants = _collect_multigene_variants(multigene_root=root, target_genes=genes)
    clinvar_path = _variant_summary_path(manifest, variant_summary_path)
    coordinates, coordinate_summary = _scan_clinvar_coordinate_metadata(
        variant_summary_path=clinvar_path,
        variation_ids=variants.get("variation_id", pd.Series(dtype=str)).dropna().astype(str).unique().tolist(),
        target_genes=genes,
    )
    local_gnomad = _load_local_gnomad(Path(gnomad_dir), genes)
    local_mavedb = _load_local_mavedb(Path(mavedb_dir), genes)
    live_mavedb_score_sets = pd.DataFrame()
    live_mavedb_scores = pd.DataFrame()
    live_mavedb_errors: list[dict[str, Any]] = []
    if run_live_mavedb:
        live_mavedb_score_sets, live_mavedb_scores, live_mavedb_errors = _fetch_mavedb_scores_for_genes(
            target_genes=genes,
            max_score_sets_per_gene=max_live_mavedb_score_sets_per_gene,
            timeout_sec=timeout_sec,
        )

    matrix = _build_matrix(
        variants=variants,
        coordinates=coordinates,
        local_gnomad=local_gnomad,
        local_mavedb=local_mavedb,
        live_mavedb_scores=live_mavedb_scores,
    )
    live_gnomad_queries = pd.DataFrame()
    if run_live_gnomad:
        matrix, live_gnomad_queries = _run_live_gnomad_queries(
            matrix,
            max_queries=max_live_gnomad_queries,
            max_queries_per_gene=max_live_gnomad_queries_per_gene,
            dataset=gnomad_dataset,
            timeout_sec=timeout_sec,
        )
        if "live_gnomad_status" in matrix.columns:
            matrix["gnomad_line_available"] = matrix["local_gnomad_available"] | matrix["live_gnomad_status"].eq("found")
            matrix.loc[matrix["gnomad_line_available"] & matrix["mavedb_line_available"], "annotation_status"] = (
                "coordinate_gnomad_mavedb_complete"
            )
            matrix.loc[
                matrix["coordinate_ready"] & matrix["gnomad_line_available"] & ~matrix["mavedb_line_available"],
                "annotation_status",
            ] = "coordinate_gnomad_complete_mavedb_missing"

    coverage_by_gene = _coverage_table(matrix)
    row_count = int(len(matrix))
    coordinate_coverage = _percent(matrix["coordinate_ready"].mean() * 100 if row_count else 0)
    live_gnomad_hit_coverage = _percent(
        (_column_or_default(matrix, "live_gnomad_status").eq("found").mean() * 100) if row_count else 0
    )
    local_gnomad_coverage = _percent(matrix["local_gnomad_available"].mean() * 100 if row_count else 0)
    gnomad_evidence_coverage = _percent(matrix["gnomad_line_available"].mean() * 100 if row_count else 0)
    mavedb_coverage = _percent(matrix["mavedb_line_available"].mean() * 100 if row_count else 0)
    source_trace = _percent(matrix["source_trace_ready"].mean() * 100 if row_count else 0)
    readiness = int(
        round(
            coordinate_coverage * 0.30
            + gnomad_evidence_coverage * 0.35
            + mavedb_coverage * 0.25
            + source_trace * 0.10
        )
    )
    summary = {
        "generated_at": _now_utc(),
        "target_genes": genes,
        "variant_row_count": row_count,
        "genomic_coordinate_coverage_percent": coordinate_coverage,
        "local_gnomad_line_coverage_percent": local_gnomad_coverage,
        "live_gnomad_query_count": int(len(live_gnomad_queries)),
        "live_gnomad_hit_coverage_percent": live_gnomad_hit_coverage,
        "gnomad_line_evidence_coverage_percent": gnomad_evidence_coverage,
        "mavedb_line_evidence_coverage_percent": mavedb_coverage,
        "source_trace_coverage_percent": source_trace,
        "line_level_annotation_readiness_percent": _percent(readiness),
        "live_mavedb_score_set_count": int(len(live_mavedb_score_sets)),
        "live_mavedb_score_rows_loaded": int(len(live_mavedb_scores)),
        "local_gnomad_rows_loaded": int(len(local_gnomad)),
        "local_mavedb_rows_loaded": int(len(local_mavedb)),
        "coordinate_summary": coordinate_summary,
        "public_sources": {
            "gnomad_graphql_endpoint": GNOMAD_ENDPOINT,
            "gnomad_dataset": gnomad_dataset,
            "mavedb_api_base": MAVEDB_API_BASE,
        },
        "warnings": [
            "Line-level MaveDB joins use protein HGVS and should be upgraded with VRS/coordinate reconciliation for publication-grade variant identity.",
            "gnomAD live calls are capped; full production sync should use downloaded gnomAD tables or a scheduled public sync job.",
        ],
    }
    payload = {
        "summary": summary,
        "variant_annotation_matrix": matrix,
        "coverage_by_gene": coverage_by_gene,
        "live_gnomad_queries": live_gnomad_queries,
        "live_mavedb_score_sets": live_mavedb_score_sets,
        "live_mavedb_errors": live_mavedb_errors,
    }
    payload["markdown_report"] = _build_markdown(payload)
    payload["html_report"] = _render_markdown_html(payload["markdown_report"], "PrimeVarClass Multigene Annotation Enrichment")
    return payload


def export_multigene_annotation_enrichment_package(
    *,
    multigene_real_benchmark_manifest_path: str,
    output_dir: str,
    variant_summary_path: str | None = None,
    multigene_root: str | None = None,
    gnomad_dir: str = "data/raw/gnomad",
    mavedb_dir: str = "data/raw/mavedb",
    target_genes: Iterable[str] | None = None,
    run_live_gnomad: bool = True,
    max_live_gnomad_queries: int = 48,
    max_live_gnomad_queries_per_gene: int = 8,
    gnomad_dataset: str = "gnomad_r4",
    run_live_mavedb: bool = True,
    max_live_mavedb_score_sets_per_gene: int = 1,
    timeout_sec: int = 20,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_multigene_annotation_enrichment_package(
        multigene_real_benchmark_manifest_path=multigene_real_benchmark_manifest_path,
        variant_summary_path=variant_summary_path,
        multigene_root=multigene_root,
        gnomad_dir=gnomad_dir,
        mavedb_dir=mavedb_dir,
        target_genes=target_genes,
        run_live_gnomad=run_live_gnomad,
        max_live_gnomad_queries=max_live_gnomad_queries,
        max_live_gnomad_queries_per_gene=max_live_gnomad_queries_per_gene,
        gnomad_dataset=gnomad_dataset,
        run_live_mavedb=run_live_mavedb,
        max_live_mavedb_score_sets_per_gene=max_live_mavedb_score_sets_per_gene,
        timeout_sec=timeout_sec,
    )

    matrix_path = output_root / "multigene_variant_annotation_matrix.csv"
    coverage_path = output_root / "multigene_annotation_coverage_by_gene.csv"
    live_gnomad_path = output_root / "gnomad_live_query_results.csv"
    live_mavedb_sets_path = output_root / "mavedb_live_score_sets.csv"
    live_mavedb_errors_path = output_root / "mavedb_live_errors.json"
    markdown_path = output_root / "multigene_annotation_enrichment_report.md"
    html_path = output_root / "multigene_annotation_enrichment_report.html"
    manifest_path = output_root / "multigene_annotation_enrichment_manifest.json"

    matrix = payload.get("variant_annotation_matrix")
    (matrix if isinstance(matrix, pd.DataFrame) else pd.DataFrame()).to_csv(matrix_path, index=False)
    coverage = payload.get("coverage_by_gene")
    (coverage if isinstance(coverage, pd.DataFrame) else pd.DataFrame()).to_csv(coverage_path, index=False)
    live_gnomad = payload.get("live_gnomad_queries")
    (live_gnomad if isinstance(live_gnomad, pd.DataFrame) else pd.DataFrame()).to_csv(live_gnomad_path, index=False)
    live_sets = payload.get("live_mavedb_score_sets")
    (live_sets if isinstance(live_sets, pd.DataFrame) else pd.DataFrame()).to_csv(live_mavedb_sets_path, index=False)
    live_mavedb_errors_path.write_text(json.dumps(_jsonify(payload.get("live_mavedb_errors") or []), indent=2), encoding="utf-8")
    markdown_path.write_text(str(payload.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(payload.get("html_report") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": payload.get("summary") or {},
        "variant_annotation_matrix_path": str(matrix_path),
        "coverage_by_gene_path": str(coverage_path),
        "gnomad_live_query_results_path": str(live_gnomad_path),
        "mavedb_live_score_sets_path": str(live_mavedb_sets_path),
        "mavedb_live_errors_path": str(live_mavedb_errors_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "multigene_annotation_enrichment": payload,
        "multigene_annotation_enrichment_manifest_path": str(manifest_path),
        "multigene_variant_annotation_matrix_path": str(matrix_path),
        "multigene_annotation_coverage_by_gene_path": str(coverage_path),
        "gnomad_live_query_results_path": str(live_gnomad_path),
        "mavedb_live_score_sets_path": str(live_mavedb_sets_path),
        "multigene_annotation_enrichment_report_markdown_path": str(markdown_path),
        "multigene_annotation_enrichment_report_html_path": str(html_path),
    }
