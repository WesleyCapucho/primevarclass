from __future__ import annotations

import json
import gzip
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

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


def _read_table(path_value: str | Path | None) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _canonical_chrom(value: Any) -> str:
    chrom = str(value or "").strip()
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    return chrom


def _variant_id_from_parts(chrom: Any, pos: Any, ref: Any, alt: Any) -> str:
    try:
        pos_text = str(int(float(str(pos).strip())))
    except Exception:
        pos_text = str(pos or "").strip()
    parts = [_canonical_chrom(chrom), pos_text, str(ref or "").strip(), str(alt or "").strip()]
    return "-".join(parts) if all(parts) else ""


def _pick_column(df: pd.DataFrame, *names: str) -> str | None:
    normalized = {str(column).strip().lower(): column for column in df.columns}
    for name in names:
        match = normalized.get(name.lower())
        if match is not None:
            return str(match)
    return None


def _first_info_value(info: str, key: str) -> str:
    for entry in str(info or "").split(";"):
        if entry.startswith(f"{key}="):
            return entry.split("=", 1)[1].split(",", 1)[0]
    return ""


def _local_gnomad_cache_from_frame(frame: pd.DataFrame, target_ids: set[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    variant_col = _pick_column(work, "gnomad_variant_id", "variant_id", "variant id", "variant")
    if variant_col:
        work["gnomad_variant_id"] = work[variant_col].astype(str)
    else:
        chrom_col = _pick_column(work, "chrom", "chromosome", "#chrom", "#CHROM")
        pos_col = _pick_column(work, "pos", "position", "start")
        ref_col = _pick_column(work, "ref", "reference", "allele_ref")
        alt_col = _pick_column(work, "alt", "alternate", "allele_alt")
        if not all([chrom_col, pos_col, ref_col, alt_col]):
            return pd.DataFrame()
        work["gnomad_variant_id"] = [
            _variant_id_from_parts(chrom, pos, ref, alt)
            for chrom, pos, ref, alt in zip(work[chrom_col], work[pos_col], work[ref_col], work[alt_col])
        ]
    work = work.loc[work["gnomad_variant_id"].astype(str).isin(target_ids)].copy()
    if work.empty:
        return pd.DataFrame()
    af_col = _pick_column(work, "af", "AF", "allele_frequency", "gnomad_af", "live_gnomad_af")
    ac_col = _pick_column(work, "ac", "AC", "allele_count", "gnomad_ac", "live_gnomad_ac")
    an_col = _pick_column(work, "an", "AN", "allele_number", "gnomad_an", "live_gnomad_an")
    info_col = _pick_column(work, "info", "INFO")
    if info_col and not af_col:
        work["live_gnomad_af"] = work[info_col].apply(lambda value: _first_info_value(str(value), "AF"))
    else:
        work["live_gnomad_af"] = work[af_col] if af_col else ""
    if info_col and not ac_col:
        work["live_gnomad_ac"] = work[info_col].apply(lambda value: _first_info_value(str(value), "AC"))
    else:
        work["live_gnomad_ac"] = work[ac_col] if ac_col else ""
    if info_col and not an_col:
        work["live_gnomad_an"] = work[info_col].apply(lambda value: _first_info_value(str(value), "AN"))
    else:
        work["live_gnomad_an"] = work[an_col] if an_col else ""
    work["status"] = "found"
    work["error"] = ""
    work["cached_at"] = _now_utc()
    keep = ["gnomad_variant_id", "status", "live_gnomad_af", "live_gnomad_ac", "live_gnomad_an", "error", "cached_at"]
    return work[keep].drop_duplicates(subset=["gnomad_variant_id"], keep="first")


def _read_local_gnomad_release_cache(path_value: str | Path | None, target_ids: set[str]) -> pd.DataFrame:
    if not path_value or not target_ids:
        return pd.DataFrame()
    path = Path(path_value).expanduser()
    if not path.exists():
        return pd.DataFrame()
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".vcf") or suffixes.endswith(".vcf.gz") or suffixes.endswith(".vcf.bgz"):
        opener = gzip.open if suffixes.endswith((".gz", ".bgz")) else open
        rows: list[dict[str, Any]] = []
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("##"):
                        continue
                    if line.startswith("#"):
                        continue
                    fields = line.rstrip("\n").split("\t")
                    if len(fields) < 8:
                        continue
                    variant_id = _variant_id_from_parts(fields[0], fields[1], fields[3], fields[4].split(",", 1)[0])
                    if variant_id not in target_ids:
                        continue
                    info = fields[7]
                    rows.append(
                        {
                            "gnomad_variant_id": variant_id,
                            "status": "found",
                            "live_gnomad_af": _first_info_value(info, "AF"),
                            "live_gnomad_ac": _first_info_value(info, "AC"),
                            "live_gnomad_an": _first_info_value(info, "AN"),
                            "error": "",
                            "cached_at": _now_utc(),
                        }
                    )
        except Exception:
            return pd.DataFrame()
        return pd.DataFrame(rows).drop_duplicates(subset=["gnomad_variant_id"], keep="first") if rows else pd.DataFrame()
    sep = "," if ".csv" in suffixes else "\t"
    frames: list[pd.DataFrame] = []
    try:
        for chunk in pd.read_csv(path, sep=sep, compression="infer", chunksize=100_000):
            matched = _local_gnomad_cache_from_frame(chunk, target_ids)
            if not matched.empty:
                frames.append(matched)
    except Exception:
        return pd.DataFrame()
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["gnomad_variant_id"], keep="first")


def _local_gene_subset_scope(path_value: str | Path | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value).expanduser()
    manifest_path = path.with_name("gnomad_gene_subset_manifest.json")
    if not manifest_path.exists():
        return {}
    manifest = _load_json(str(manifest_path))
    summary = manifest.get("summary") or {}
    is_complete_gene_subset = (
        str(summary.get("scope") or "") == "gene_level_public_api_subset"
        and _percent(summary.get("query_success_percent"), 0) >= 100
        and int(summary.get("gene_count_requested") or 0) == int(summary.get("gene_count_fetched") or -1)
    )
    return {
        "is_complete_gene_subset": bool(is_complete_gene_subset),
        "manifest_path": str(manifest_path.resolve()),
        "dataset": summary.get("dataset"),
        "target_genes": summary.get("target_genes") or [],
        "variant_row_count": int(summary.get("variant_row_count") or 0),
        "scope": summary.get("scope"),
    }


def _local_absence_cache_from_gene_subset(target_ids: set[str], found_cache: pd.DataFrame, scope: dict[str, Any]) -> pd.DataFrame:
    if not target_ids or not scope.get("is_complete_gene_subset"):
        return pd.DataFrame()
    found_ids = set()
    if not found_cache.empty and "gnomad_variant_id" in found_cache.columns:
        found_ids = set(found_cache["gnomad_variant_id"].dropna().astype(str))
    absent_ids = sorted(variant_id for variant_id in target_ids if variant_id and variant_id not in found_ids)
    if not absent_ids:
        return pd.DataFrame()
    now = _now_utc()
    return pd.DataFrame(
        [
            {
                "gnomad_variant_id": variant_id,
                "status": "not_found",
                "live_gnomad_af": "",
                "live_gnomad_ac": "",
                "live_gnomad_an": "",
                "error": "exact_variant_id_not_observed_in_complete_gene_level_public_api_subset",
                "cached_at": now,
            }
            for variant_id in absent_ids
        ]
    )


def _column_or_default(df: pd.DataFrame, column: str, default: Any = "") -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def _as_bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    series = _column_or_default(df, column, False)
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes", "sim"})


def _normalize_gnomad_status(row: pd.Series) -> str:
    status = str(row.get("status") or "").strip()
    error = str(row.get("error") or "").strip()
    if status == "graphql_error" and "Variant not found" in error:
        return "not_found"
    return status


def _build_gnomad_cache(live_queries: pd.DataFrame, existing_cache: pd.DataFrame | None = None) -> pd.DataFrame:
    frames = []
    if existing_cache is not None and not existing_cache.empty:
        frames.append(existing_cache.copy())
    if live_queries is not None and not live_queries.empty:
        frames.append(live_queries.copy().rename(columns={"variant_id": "gnomad_variant_id"}))
    if not frames:
        return pd.DataFrame(
            columns=[
                "gnomad_variant_id",
                "status",
                "gene",
                "hgvs_p",
                "variation_id",
                "live_gnomad_af",
                "live_gnomad_ac",
                "live_gnomad_an",
                "error",
                "cached_at",
            ]
        )
    cache = pd.concat(frames, ignore_index=True, sort=False)
    for column in ["gnomad_variant_id", "status", "gene", "hgvs_p", "variation_id", "error"]:
        if column not in cache.columns:
            cache[column] = ""
    for column in ["live_gnomad_af", "live_gnomad_ac", "live_gnomad_an"]:
        if column not in cache.columns:
            cache[column] = np.nan
    if "cached_at" not in cache.columns:
        cache["cached_at"] = ""
    cache["cached_at"] = cache["cached_at"].fillna("").astype(str)
    cache.loc[cache["cached_at"].eq(""), "cached_at"] = _now_utc()
    cache["status"] = cache.apply(_normalize_gnomad_status, axis=1)
    cache["is_rate_limited"] = cache["error"].astype(str).str.contains("429|Too Many Requests", case=False, na=False)
    status_priority = cache["status"].map({"found": 5, "not_found": 4, "graphql_error": 3, "query_error": 2}).fillna(0)
    retry_penalty = cache["is_rate_limited"].astype(int)
    cache["status_priority"] = status_priority
    cache = cache.sort_values(
        ["gnomad_variant_id", "status_priority", "is_rate_limited", "cached_at"],
        ascending=[True, False, True, False],
        kind="stable",
    )
    keep_columns = [
        "gnomad_variant_id",
        "status",
        "gene",
        "hgvs_p",
        "variation_id",
        "live_gnomad_af",
        "live_gnomad_ac",
        "live_gnomad_an",
        "error",
        "is_rate_limited",
        "cached_at",
    ]
    return cache[keep_columns].drop_duplicates(subset=["gnomad_variant_id"], keep="first")


def _build_sync_queue(matrix: pd.DataFrame, cache: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    queue = matrix.copy()
    queue["gnomad_variant_id"] = (
        _column_or_default(queue, "gnomad_variant_id")
        .fillna("")
        .astype(str)
        .str.strip()
        .replace({"nan": "", "None": "", "NaN": ""})
    )
    queue["coordinate_ready"] = _as_bool_series(queue, "coordinate_ready") | queue["gnomad_variant_id"].ne("")
    queue["mavedb_line_available"] = _as_bool_series(queue, "mavedb_line_available")
    queue["source_trace_ready"] = _as_bool_series(queue, "source_trace_ready")
    queue["source_cohort_kind"] = _column_or_default(queue, "source_cohort_kind").astype(str)

    if not cache.empty:
        cache_compact = cache.rename(
            columns={
                "status": "cached_gnomad_status",
                "live_gnomad_af": "cached_gnomad_af",
                "live_gnomad_ac": "cached_gnomad_ac",
                "live_gnomad_an": "cached_gnomad_an",
                "error": "cached_gnomad_error",
            }
        )
        queue = queue.merge(
            cache_compact[
                [
                    "gnomad_variant_id",
                    "cached_gnomad_status",
                    "cached_gnomad_af",
                    "cached_gnomad_ac",
                    "cached_gnomad_an",
                    "cached_gnomad_error",
                    "is_rate_limited",
                    "cached_at",
                ]
            ],
            on="gnomad_variant_id",
            how="left",
        )
        for column in ["cached_gnomad_status", "cached_gnomad_error", "cached_at"]:
            queue[column] = queue[column].fillna("")
        for column in ["cached_gnomad_af", "cached_gnomad_ac", "cached_gnomad_an"]:
            queue[column] = pd.to_numeric(queue[column], errors="coerce")
        queue["is_rate_limited"] = queue["is_rate_limited"].fillna(False).astype(bool)
    else:
        queue["cached_gnomad_status"] = ""
        queue["cached_gnomad_af"] = np.nan
        queue["cached_gnomad_ac"] = np.nan
        queue["cached_gnomad_an"] = np.nan
        queue["cached_gnomad_error"] = ""
        queue["is_rate_limited"] = False
        queue["cached_at"] = ""

    queue["gnomad_sync_status"] = np.select(
        [
            ~queue["coordinate_ready"],
            queue["cached_gnomad_status"].eq("found"),
            queue["cached_gnomad_status"].eq("not_found"),
            queue["is_rate_limited"].fillna(False).astype(bool),
            queue["cached_gnomad_status"].eq("graphql_error"),
            queue["cached_gnomad_status"].astype(str).ne(""),
        ],
        [
            "coordinate_missing",
            "cached_found",
            "cached_not_found",
            "rate_limited_retry_later",
            "graphql_error_retry_later",
            "cached_error_retry_later",
        ],
        default="pending_query",
    )
    external_priority = queue["source_cohort_kind"].str.contains("external", case=False, na=False).astype(int) * 25
    mavedb_priority = queue["mavedb_line_available"].astype(int) * 20
    trace_priority = queue["source_trace_ready"].astype(int) * 10
    pending_priority = queue["gnomad_sync_status"].eq("pending_query").astype(int) * 35
    retry_priority = queue["gnomad_sync_status"].str.contains("retry", na=False).astype(int) * 20
    queue["sync_priority_score"] = external_priority + mavedb_priority + trace_priority + pending_priority + retry_priority
    keep_columns = [
        "gene",
        "hgvs_p",
        "variation_id",
        "clinical_significance",
        "review_status",
        "source_cohort_kind",
        "gnomad_variant_id",
        "coordinate_ready",
        "mavedb_line_available",
        "source_trace_ready",
        "cached_gnomad_status",
        "cached_gnomad_af",
        "cached_gnomad_ac",
        "cached_gnomad_an",
        "cached_gnomad_error",
        "is_rate_limited",
        "gnomad_sync_status",
        "sync_priority_score",
    ]
    keep = [column for column in keep_columns if column in queue.columns]
    return queue[keep].sort_values(["sync_priority_score", "gene", "hgvs_p"], ascending=[False, True, True], kind="stable")


def _build_status_by_gene(queue: pd.DataFrame) -> pd.DataFrame:
    if queue.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "variant_count",
                "cached_found_count",
                "cached_not_found_count",
                "retryable_count",
                "pending_query_count",
                "definitive_cached_percent",
            ]
        )
    work = queue.copy()
    work["gene"] = _column_or_default(work, "gene", "unknown").fillna("unknown").astype(str)
    work["gnomad_sync_status"] = _column_or_default(work, "gnomad_sync_status", "").fillna("").astype(str)
    grouped = work.groupby("gene", dropna=False)
    status = grouped.agg(
        variant_count=("gnomad_sync_status", "size"),
        cached_found_count=("gnomad_sync_status", lambda values: int((values == "cached_found").sum())),
        cached_not_found_count=("gnomad_sync_status", lambda values: int((values == "cached_not_found").sum())),
        retryable_count=("gnomad_sync_status", lambda values: int(values.isin(["graphql_error_retry_later", "cached_error_retry_later", "rate_limited_retry_later"]).sum())),
        pending_query_count=("gnomad_sync_status", lambda values: int((values == "pending_query").sum())),
    ).reset_index()
    definitive = status["cached_found_count"] + status["cached_not_found_count"]
    status["definitive_cached_percent"] = np.where(
        status["variant_count"].gt(0),
        np.round((definitive / status["variant_count"]) * 100).astype(int),
        0,
    )
    status["needs_more_sync_count"] = status["retryable_count"] + status["pending_query_count"]
    return status.sort_values(["needs_more_sync_count", "gene"], ascending=[False, True], kind="stable")


def _build_mavedb_reconciliation(matrix: pd.DataFrame) -> pd.DataFrame:
    if matrix.empty:
        return pd.DataFrame()
    work = matrix.copy()
    work["mavedb_line_available"] = _as_bool_series(work, "mavedb_line_available")
    work["live_mavedb_score_set_urn"] = _column_or_default(work, "live_mavedb_score_set_urn").astype(str)
    work["local_mavedb_score_set_urn"] = _column_or_default(work, "local_mavedb_score_set_urn").astype(str)
    work["score_set_urn"] = work["live_mavedb_score_set_urn"]
    work.loc[work["score_set_urn"].eq(""), "score_set_urn"] = work.loc[work["score_set_urn"].eq(""), "local_mavedb_score_set_urn"]
    work["reconciliation_status"] = np.select(
        [
            work["mavedb_line_available"] & work["score_set_urn"].ne(""),
            work["mavedb_line_available"],
        ],
        [
            "protein_hgvs_join_with_score_set",
            "protein_hgvs_join_missing_score_set_metadata",
        ],
        default="missing_mavedb_line",
    )
    work["next_precision_step"] = np.select(
        [
            work["reconciliation_status"].eq("protein_hgvs_join_with_score_set"),
            work["reconciliation_status"].eq("protein_hgvs_join_missing_score_set_metadata"),
        ],
        [
            "Fetch mapped-variants for the score set and reconcile VRS/genomic identity.",
            "Resolve score set URN before VRS/genomic reconciliation.",
        ],
        default="Search MaveDB for a matching score set or mark as no public MAVE evidence.",
    )
    columns = [
        "gene",
        "hgvs_p",
        "variation_id",
        "score_set_urn",
        "live_mavedb_assay_name",
        "reconciliation_status",
        "next_precision_step",
    ]
    return work[[column for column in columns if column in work.columns]].drop_duplicates(
        subset=["gene", "hgvs_p", "variation_id"],
        keep="first",
    )


def _build_coordinate_exception_review(queue: pd.DataFrame) -> pd.DataFrame:
    if queue.empty or "gnomad_sync_status" not in queue.columns:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "variation_id",
                "exception_type",
                "review_status",
                "evidence",
                "next_resolution_step",
            ]
        )
    missing = queue.loc[queue["gnomad_sync_status"].astype(str).eq("coordinate_missing")].copy()
    if missing.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "variation_id",
                "exception_type",
                "review_status",
                "evidence",
                "next_resolution_step",
            ]
        )
    rows: list[dict[str, Any]] = []
    for _, row in missing.iterrows():
        rows.append(
            {
                "gene": row.get("gene"),
                "hgvs_p": row.get("hgvs_p"),
                "variation_id": row.get("variation_id"),
                "exception_type": "legacy_protein_only_or_non_precise_clinvar_record",
                "review_status": "documented_exception_not_row_level_gnomad_queryable",
                "evidence": "ClinVar local row lacks GRCh38 chrom/position/ref/alt; gnomAD exact variant query cannot be formed.",
                "next_resolution_step": "Resolve nucleotide HGVS/SPDI from submitter records, expert curation, or transcript-to-genome remapping before population-frequency claims.",
            }
        )
    return pd.DataFrame(rows)


def _write_resume_script(path: Path, queue_path: Path, cache_path: Path, batch_size: int, sleep_seconds: int) -> None:
    path.write_text(
        "\n".join(
            [
                '"""Resume capped gnomAD GraphQL sync for PrimeVarClass.',
                "",
                "This script is intentionally conservative. It reads the pending queue,",
                "queries a small batch, appends a cache file, and stops on rate limits.",
                '"""',
                "from __future__ import annotations",
                "",
                "import csv",
                "import json",
                "import time",
                "import urllib.request",
                "from pathlib import Path",
                "",
                f"QUEUE_PATH = Path(r'''{queue_path}''')",
                f"CACHE_PATH = Path(r'''{cache_path}''')",
                f"BATCH_SIZE = {int(batch_size)}",
                f"SLEEP_SECONDS = {int(sleep_seconds)}",
                f"ENDPOINT = {GNOMAD_ENDPOINT!r}",
                "",
                "QUERY = '''",
                "query Variant($variantId: String!, $dataset: DatasetId!) {",
                "  variant(variantId: $variantId, dataset: $dataset) {",
                "    variant_id reference_genome exome { ac an af } genome { ac an af }",
                "  }",
                "}",
                "'''",
                "",
                "def post(payload):",
                "    body = json.dumps(payload).encode('utf-8')",
                "    req = urllib.request.Request(ENDPOINT, data=body, headers={'Content-Type': 'application/json'})",
                "    with urllib.request.urlopen(req, timeout=25) as response:",
                "        return json.loads(response.read().decode('utf-8'))",
                "",
                "rows = list(csv.DictReader(QUEUE_PATH.open('r', encoding='utf-8')))",
                "cached_ids = set()",
                "if CACHE_PATH.exists():",
                "    with CACHE_PATH.open('r', encoding='utf-8', newline='') as cache_handle:",
                "        for cached in csv.DictReader(cache_handle):",
                "            if cached.get('gnomad_variant_id') and cached.get('status') in {'found', 'not_found'}:",
                "                cached_ids.add(cached.get('gnomad_variant_id'))",
                "retry_statuses = {'pending_query', 'graphql_error_retry_later', 'cached_error_retry_later', 'rate_limited_retry_later'}",
                "pending = [row for row in rows if row.get('gnomad_variant_id') not in cached_ids and row.get('gnomad_sync_status') in retry_statuses]",
                "CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)",
                "write_header = not CACHE_PATH.exists()",
                "with CACHE_PATH.open('a', encoding='utf-8', newline='') as handle:",
                "    writer = csv.DictWriter(handle, fieldnames=['gnomad_variant_id','status','gene','hgvs_p','variation_id','live_gnomad_af','live_gnomad_ac','live_gnomad_an','error','cached_at'])",
                "    if write_header:",
                "        writer.writeheader()",
                "    for row in pending[:BATCH_SIZE]:",
                "        variant_id = row.get('gnomad_variant_id') or ''",
                "        if not variant_id:",
                "            continue",
                "        try:",
                "            payload = {'query': QUERY, 'variables': {'variantId': variant_id, 'dataset': 'gnomad_r4'}}",
                "            response = post(payload)",
                "            if response.get('errors'):",
                "                error = json.dumps(response.get('errors'))[:500]",
                "                status = 'not_found' if 'Variant not found' in error else 'graphql_error'",
                "                ac = an = af = ''",
                "            else:",
                "                variant = (response.get('data') or {}).get('variant') or {}",
                "                exome = variant.get('exome') or {}",
                "                genome = variant.get('genome') or {}",
                "                preferred = exome if exome.get('an') else genome",
                "                status = 'found' if variant else 'not_found'",
                "                ac, an, af = preferred.get('ac',''), preferred.get('an',''), preferred.get('af','')",
                "                error = ''",
                "        except Exception as exc:",
                "            error = str(exc)",
                "            status = 'query_error'",
                "            ac = an = af = ''",
                "        writer.writerow({'gnomad_variant_id': variant_id, 'status': status, 'gene': row.get('gene'), 'hgvs_p': row.get('hgvs_p'), 'variation_id': row.get('variation_id'), 'live_gnomad_af': af, 'live_gnomad_ac': ac, 'live_gnomad_an': an, 'error': error, 'cached_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})",
                "        handle.flush()",
                "        if '429' in error or 'Too Many Requests' in error:",
                "            break",
                "        time.sleep(SLEEP_SECONDS)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _build_markdown(payload: dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PrimeVarClass Public Sync Closure",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Variant rows: `{summary.get('variant_row_count', 0)}`",
        f"- gnomAD queryable rows: `{summary.get('gnomad_queryable_percent', 0)}%`",
        f"- gnomAD cached attempts: `{summary.get('gnomad_cached_attempt_percent', 0)}%`",
        f"- Local gnomAD release rows matched: `{summary.get('local_gnomad_release_rows_matched', 0)}`",
        f"- gnomAD cached found rows: `{summary.get('gnomad_cached_found_count', 0)}`",
        f"- gnomAD definitive cached rows: `{summary.get('gnomad_definitive_cached_percent', 0)}%`",
        f"- Effective line-level annotation readiness: `{summary.get('effective_line_level_annotation_readiness_percent', 0)}%`",
        f"- gnomAD retryable rows: `{summary.get('gnomad_retryable_error_count', 0)}`",
        f"- MaveDB protein-HGVS coverage: `{summary.get('mavedb_line_evidence_percent', 0)}%`",
        f"- Sync infrastructure readiness: `{summary.get('sync_infrastructure_readiness_percent', 0)}%`",
        f"- Public sync closure percent: `{summary.get('public_sync_closure_percent', 0)}%`",
        "",
        "## Honest closure statement",
        "",
        "- The platform now has a resumable public sync lane instead of one-off live requests.",
        "- gnomAD evidence is not complete until the queue is resumed or a release table is staged locally.",
        "- MaveDB protein-HGVS evidence is strong, but publication-grade precision still benefits from mapped-variant/VRS reconciliation.",
    ]
    return "\n".join(lines).strip()


def build_public_sync_closure_package(
    *,
    multigene_annotation_enrichment_manifest_path: str,
    existing_gnomad_cache_path: str | None = None,
    gnomad_release_table_path: str | None = None,
    gnomad_batch_size: int = 25,
    gnomad_sleep_seconds: int = 6,
) -> dict[str, Any]:
    annotation_manifest = _load_json(multigene_annotation_enrichment_manifest_path)
    matrix = _read_table(annotation_manifest.get("variant_annotation_matrix_path"))
    live_queries = _read_table(annotation_manifest.get("gnomad_live_query_results_path"))
    existing_cache = _read_table(existing_gnomad_cache_path)
    target_ids = set(_column_or_default(matrix, "gnomad_variant_id").dropna().astype(str))
    target_ids.discard("")
    local_release_cache = _read_local_gnomad_release_cache(gnomad_release_table_path, target_ids)
    local_gene_subset_scope = _local_gene_subset_scope(gnomad_release_table_path)
    local_absence_cache = _local_absence_cache_from_gene_subset(target_ids, local_release_cache, local_gene_subset_scope)
    cache = _build_gnomad_cache(live_queries, existing_cache=existing_cache)
    if not local_release_cache.empty:
        cache = _build_gnomad_cache(local_release_cache, existing_cache=cache)
    if not local_absence_cache.empty:
        cache = _build_gnomad_cache(local_absence_cache, existing_cache=cache)
    queue = _build_sync_queue(matrix, cache)
    status_by_gene = _build_status_by_gene(queue)
    mavedb_reconciliation = _build_mavedb_reconciliation(matrix)
    coordinate_exceptions = _build_coordinate_exception_review(queue)
    row_count = int(len(matrix))
    queryable = _percent((queue["coordinate_ready"].astype(bool).mean() * 100) if not queue.empty else 0)
    cached_attempt = _percent((queue["cached_gnomad_status"].fillna("").astype(str).ne("").mean() * 100) if not queue.empty else 0)
    cached_found_count = int(queue["gnomad_sync_status"].eq("cached_found").sum()) if not queue.empty else 0
    cached_not_found_count = int(queue["gnomad_sync_status"].eq("cached_not_found").sum()) if not queue.empty else 0
    cached_found_percent = _percent((cached_found_count / row_count) * 100 if row_count else 0)
    definitive_cached_percent = _percent(((cached_found_count + cached_not_found_count) / row_count) * 100 if row_count else 0)
    retryable_error_count = int(
        queue["gnomad_sync_status"].isin(
            ["graphql_error_retry_later", "cached_error_retry_later", "rate_limited_retry_later"]
        ).sum()
    ) if not queue.empty else 0
    pending_count = int(
        queue["gnomad_sync_status"].isin(
            ["pending_query", "graphql_error_retry_later", "cached_error_retry_later", "rate_limited_retry_later"]
        ).sum()
    ) if not queue.empty else 0
    coordinate_missing_count = int(queue["gnomad_sync_status"].eq("coordinate_missing").sum()) if not queue.empty else 0
    coordinate_exception_reviewed_count = int(len(coordinate_exceptions))
    mavedb_percent = _percent((queue["mavedb_line_available"].astype(bool).mean() * 100) if not queue.empty else 0)
    source_trace_percent = _percent((queue["source_trace_ready"].astype(bool).mean() * 100) if "source_trace_ready" in queue.columns and not queue.empty else 0)
    effective_line_level_annotation = _percent(
        queryable * 0.25
        + definitive_cached_percent * 0.30
        + mavedb_percent * 0.25
        + source_trace_percent * 0.20
    )
    infrastructure = _percent(
        (100 if not queue.empty else 0) * 0.25
        + (100 if not cache.empty else 0) * 0.20
        + (100 if not mavedb_reconciliation.empty else 0) * 0.20
        + queryable * 0.20
        + mavedb_percent * 0.15
    )
    local_release_bonus = 15 if not local_release_cache.empty else 0
    closure = _percent(
        queryable * 0.15
        + mavedb_percent * 0.20
        + definitive_cached_percent * 0.25
        + cached_attempt * 0.10
        + infrastructure * 0.20
        + local_release_bonus
    )
    if definitive_cached_percent < 80:
        closure = min(closure, 89)
    if coordinate_missing_count > 0:
        closure = min(closure, 99)
    summary = {
        "generated_at": _now_utc(),
        "variant_row_count": row_count,
        "gnomad_queryable_percent": queryable,
        "gnomad_cached_attempt_percent": cached_attempt,
        "gnomad_cache_row_count": int(len(cache)),
        "local_gnomad_release_rows_matched": int(len(local_release_cache)),
        "local_gnomad_release_absent_inferred_count": int(len(local_absence_cache)),
        "local_gnomad_gene_subset_scope": local_gene_subset_scope,
        "gnomad_cached_found_count": cached_found_count,
        "gnomad_cached_not_found_count": cached_not_found_count,
        "gnomad_cached_found_percent": cached_found_percent,
        "gnomad_definitive_cached_percent": definitive_cached_percent,
        "effective_gnomad_line_evidence_percent": definitive_cached_percent,
        "gnomad_retryable_error_count": retryable_error_count,
        "gnomad_pending_or_retry_count": pending_count,
        "gnomad_coordinate_missing_count": coordinate_missing_count,
        "coordinate_exception_reviewed_count": coordinate_exception_reviewed_count,
        "mavedb_line_evidence_percent": mavedb_percent,
        "source_trace_coverage_percent": source_trace_percent,
        "effective_line_level_annotation_readiness_percent": effective_line_level_annotation,
        "mavedb_reconciliation_rows": int(len(mavedb_reconciliation)),
        "local_gnomad_release_bonus_percent": local_release_bonus,
        "sync_infrastructure_readiness_percent": infrastructure,
        "public_sync_closure_percent": closure,
        "ready_for_public_sync_completion": infrastructure >= 80 and pending_count > 0,
        "ready_for_full_row_level_claim": definitive_cached_percent >= 95 and mavedb_percent >= 80 and coordinate_missing_count == 0,
        "ready_for_row_level_claim_with_documented_exceptions": (
            definitive_cached_percent >= 95
            and mavedb_percent >= 80
            and coordinate_missing_count == coordinate_exception_reviewed_count
            and coordinate_missing_count <= 2
        ),
        "public_sources": {
            "gnomad_graphql_endpoint": GNOMAD_ENDPOINT,
            "mavedb_api_base": MAVEDB_API_BASE,
        },
        "source_manifest_path": str(Path(multigene_annotation_enrichment_manifest_path).expanduser().resolve()),
        "existing_gnomad_cache_path": str(Path(existing_gnomad_cache_path).expanduser().resolve()) if existing_gnomad_cache_path else None,
        "gnomad_release_table_path": str(Path(gnomad_release_table_path).expanduser().resolve()) if gnomad_release_table_path else None,
    }
    payload = {
        "summary": summary,
        "gnomad_cache": cache,
        "gnomad_sync_queue": queue,
        "gnomad_status_by_gene": status_by_gene,
        "mavedb_reconciliation": mavedb_reconciliation,
        "coordinate_exception_review": coordinate_exceptions,
        "gnomad_batch_size": int(gnomad_batch_size),
        "gnomad_sleep_seconds": int(gnomad_sleep_seconds),
    }
    payload["markdown_report"] = _build_markdown(payload)
    payload["html_report"] = _render_markdown_html(payload["markdown_report"], "PrimeVarClass Public Sync Closure")
    return payload


def export_public_sync_closure_package(
    *,
    multigene_annotation_enrichment_manifest_path: str,
    output_dir: str,
    existing_gnomad_cache_path: str | None = None,
    gnomad_release_table_path: str | None = None,
    gnomad_batch_size: int = 25,
    gnomad_sleep_seconds: int = 6,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cache_path = output_root / "gnomad_sync_cache.csv"
    resolved_existing_cache_path = existing_gnomad_cache_path
    if resolved_existing_cache_path is None and cache_path.exists():
        resolved_existing_cache_path = str(cache_path)
    payload = build_public_sync_closure_package(
        multigene_annotation_enrichment_manifest_path=multigene_annotation_enrichment_manifest_path,
        existing_gnomad_cache_path=resolved_existing_cache_path,
        gnomad_release_table_path=gnomad_release_table_path,
        gnomad_batch_size=gnomad_batch_size,
        gnomad_sleep_seconds=gnomad_sleep_seconds,
    )

    queue_path = output_root / "gnomad_sync_queue.csv"
    status_by_gene_path = output_root / "gnomad_sync_status_by_gene.csv"
    mavedb_reconciliation_path = output_root / "mavedb_reconciliation_queue.csv"
    coordinate_exception_path = output_root / "coordinate_exception_review.csv"
    resume_script_path = output_root / "resume_gnomad_sync.py"
    markdown_path = output_root / "public_sync_closure_report.md"
    html_path = output_root / "public_sync_closure_report.html"
    manifest_path = output_root / "public_sync_closure_manifest.json"

    cache = payload.get("gnomad_cache")
    (cache if isinstance(cache, pd.DataFrame) else pd.DataFrame()).to_csv(cache_path, index=False)
    queue = payload.get("gnomad_sync_queue")
    (queue if isinstance(queue, pd.DataFrame) else pd.DataFrame()).to_csv(queue_path, index=False)
    status_by_gene = payload.get("gnomad_status_by_gene")
    (status_by_gene if isinstance(status_by_gene, pd.DataFrame) else pd.DataFrame()).to_csv(status_by_gene_path, index=False)
    reconciliation = payload.get("mavedb_reconciliation")
    (reconciliation if isinstance(reconciliation, pd.DataFrame) else pd.DataFrame()).to_csv(mavedb_reconciliation_path, index=False)
    coordinate_exceptions = payload.get("coordinate_exception_review")
    (coordinate_exceptions if isinstance(coordinate_exceptions, pd.DataFrame) else pd.DataFrame()).to_csv(coordinate_exception_path, index=False)
    _write_resume_script(
        resume_script_path,
        queue_path,
        cache_path,
        batch_size=int(payload.get("gnomad_batch_size") or gnomad_batch_size),
        sleep_seconds=int(payload.get("gnomad_sleep_seconds") or gnomad_sleep_seconds),
    )
    markdown_path.write_text(str(payload.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(payload.get("html_report") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": payload.get("summary") or {},
        "gnomad_sync_cache_path": str(cache_path),
        "gnomad_sync_queue_path": str(queue_path),
        "gnomad_sync_status_by_gene_path": str(status_by_gene_path),
        "mavedb_reconciliation_queue_path": str(mavedb_reconciliation_path),
        "coordinate_exception_review_path": str(coordinate_exception_path),
        "resume_gnomad_sync_script_path": str(resume_script_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "public_sync_closure": payload,
        "public_sync_closure_manifest_path": str(manifest_path),
        "gnomad_sync_cache_path": str(cache_path),
        "gnomad_sync_queue_path": str(queue_path),
        "gnomad_sync_status_by_gene_path": str(status_by_gene_path),
        "mavedb_reconciliation_queue_path": str(mavedb_reconciliation_path),
        "coordinate_exception_review_path": str(coordinate_exception_path),
        "resume_gnomad_sync_script_path": str(resume_script_path),
        "public_sync_closure_report_markdown_path": str(markdown_path),
        "public_sync_closure_report_html_path": str(html_path),
    }
