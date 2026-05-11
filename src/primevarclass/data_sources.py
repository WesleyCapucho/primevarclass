from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from .core import REQUIRED_DATASET_COLUMNS, prepare_training_dataframe, run_full_training_pipeline_from_dataframe
from .public_sources import build_public_source_catalog_assessment
from .public_sync import build_public_source_sync_plan
from .source_presets import PRESET_REGISTRY, apply_source_preset
from .versioning import export_data_release_manifest

DEFAULT_JOIN_KEYS = ["gene", "hgvs_p"]
DEFAULT_DEDUPLICATE_KEYS = ["gene", "hgvs_p", "label"]
SUPPORTED_SOURCE_TYPES = {"file", "sqlite", "http"}
SUPPORTED_SOURCE_KINDS = {"cohort", "annotation"}
SUPPORTED_PRESETS = set(PRESET_REGISTRY)
SOURCE_METADATA_COLUMNS = {"source", "source_name", "source_kind", "source_type"}


@dataclass
class DataSourceSpec:
    name: str
    kind: str
    source_type: str
    format: str = "csv"
    path: str | None = None
    url: str | None = None
    query: str | None = None
    table: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    timeout_seconds: int = 60
    http_method: str = "GET"
    body_json: Dict[str, Any] = field(default_factory=dict)
    column_map: Dict[str, str] = field(default_factory=dict)
    static_fields: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    select_columns: List[str] = field(default_factory=list)
    join_on: List[str] = field(default_factory=lambda: DEFAULT_JOIN_KEYS.copy())
    gene_allowlist: List[str] = field(default_factory=list)
    preset: str = "none"
    records_path: str | None = None
    release_version: str | None = None
    release_date: str | None = None


@dataclass
class SourceLoadReport:
    name: str
    kind: str
    source_type: str
    rows_loaded: int
    rows_normalized: int
    columns_loaded: int
    columns_normalized: int
    join_on: str


@dataclass
class SourceCatalog:
    sources: List[DataSourceSpec]
    deduplicate_on: List[str] = field(default_factory=lambda: DEFAULT_DEDUPLICATE_KEYS.copy())
    prefer_annotation_values: bool = True


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str | None) -> str | None:
    if not value:
        return None
    return _sha256_bytes(value.encode("utf-8"))


def _file_fingerprint(path: str | None) -> dict | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    payload = candidate.read_bytes()
    stat = candidate.stat()
    return {
        "path": str(candidate.resolve()),
        "size_bytes": int(stat.st_size),
        "sha256": _sha256_bytes(payload),
        "modified_at_epoch": float(stat.st_mtime),
    }


def _preview_text(value: str | None, max_chars: int = 160) -> str | None:
    if not value:
        return None
    compact = " ".join(str(value).split())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[: max_chars - 3]}..."


def _safe_header_names(headers: Dict[str, str]) -> list[str]:
    return sorted(str(key) for key in (headers or {}).keys())


def _base_provenance(spec: DataSourceSpec) -> dict:
    return {
        "captured_at": _now_utc(),
        "source_name": spec.name,
        "source_type": spec.source_type,
        "format": spec.format.lower(),
        "preset": spec.preset,
        "join_on": list(spec.join_on or []),
    }


def _normalize_source_type(value: str) -> str:
    source_type = str(value).strip().lower()
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"Tipo de fonte nao suportado: {value}")
    return source_type


def _normalize_source_kind(value: str | None) -> str:
    kind = str(value or "cohort").strip().lower()
    if kind not in SUPPORTED_SOURCE_KINDS:
        raise ValueError(f"Kind de fonte nao suportado: {value}")
    return kind


def _normalize_preset(value: str | None) -> str:
    preset = str(value or "none").strip().lower()
    if preset not in SUPPORTED_PRESETS:
        raise ValueError(f"Preset nao suportado: {value}")
    return preset


def _extract_records(data: Any, records_path: str | None = None) -> List[dict]:
    if records_path:
        current = data
        for part in records_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
            if current is None:
                return []
        data = current

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for candidate_key in ["results", "items", "records", "data"]:
            candidate = data.get(candidate_key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return [data]
    raise ValueError("O payload JSON nao contem uma lista de registros compativel.")


def _read_file_source(spec: DataSourceSpec) -> tuple[pd.DataFrame, dict]:
    if not spec.path:
        raise ValueError(f"A fonte '{spec.name}' precisa de um caminho local.")
    path = Path(spec.path)
    format_name = spec.format.lower()

    if format_name == "csv":
        dataframe = pd.read_csv(path, sep=spec.delimiter, encoding=spec.encoding)
    elif format_name == "tsv":
        dataframe = pd.read_csv(path, sep="\t", encoding=spec.encoding)
    elif format_name in {"json", "jsonl", "ndjson"}:
        if format_name in {"jsonl", "ndjson"}:
            records = []
            with path.open("r", encoding=spec.encoding) as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            dataframe = pd.DataFrame(records)
        else:
            payload = json.loads(path.read_text(encoding=spec.encoding))
            dataframe = pd.DataFrame(_extract_records(payload, records_path=spec.records_path))
    else:
        raise ValueError(f"Formato de arquivo nao suportado: {spec.format}")

    provenance = _base_provenance(spec)
    provenance.update(
        {
            "path": str(path.resolve()),
            "encoding": spec.encoding,
            "records_path": spec.records_path,
            "file_fingerprint": _file_fingerprint(spec.path),
        }
    )
    return dataframe, provenance


def _read_sqlite_source(spec: DataSourceSpec) -> tuple[pd.DataFrame, dict]:
    if not spec.path:
        raise ValueError(f"A fonte '{spec.name}' precisa de um caminho para SQLite.")
    query = spec.query
    if not query:
        if not spec.table:
            raise ValueError(f"A fonte '{spec.name}' precisa informar 'query' ou 'table'.")
        query = f"SELECT * FROM {spec.table}"
    connection = sqlite3.connect(spec.path)
    try:
        dataframe = pd.read_sql_query(query, connection, params=spec.params or None)
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        sqlite_version = connection.execute("SELECT sqlite_version()").fetchone()
    finally:
        connection.close()
    provenance = _base_provenance(spec)
    provenance["sqlite"] = {
        "database_path": str(Path(spec.path).resolve()),
        "database_fingerprint": _file_fingerprint(spec.path),
        "table": spec.table,
        "tables": [str(row[0]) for row in table_rows],
        "query_sha256": _sha256_text(query),
        "query_preview": _preview_text(query),
        "params_keys": sorted(str(key) for key in (spec.params or {}).keys()),
        "row_count_raw": int(len(dataframe)),
        "sqlite_version": str(sqlite_version[0]) if sqlite_version else None,
    }
    return dataframe, provenance


def _read_http_source(spec: DataSourceSpec) -> tuple[pd.DataFrame, dict]:
    if not spec.url:
        raise ValueError(f"A fonte '{spec.name}' precisa de uma URL.")
    url = spec.url
    if spec.params:
        encoded_params = urlencode(spec.params, doseq=True)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{encoded_params}"

    method = str(spec.http_method or "GET").upper()
    headers = dict(spec.headers or {})
    payload_body = None
    if spec.body_json:
        payload_body = json.dumps(spec.body_json).encode(spec.encoding)
        headers.setdefault("Content-Type", "application/json")

    request = Request(url, data=payload_body, headers=headers, method=method)
    with urlopen(request, timeout=spec.timeout_seconds) as response:
        payload = response.read()
        encoding = response.headers.get_content_charset() or spec.encoding
        content_length_header = response.headers.get("Content-Length")
        try:
            content_length = int(content_length_header) if content_length_header else int(len(payload))
        except ValueError:
            content_length = int(len(payload))
        http_response = {
            "status_code": int(getattr(response, "status", 200)),
            "final_url": str(response.geturl()),
            "content_type": response.headers.get("Content-Type"),
            "content_length": content_length,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "payload_bytes": int(len(payload)),
            "payload_sha256": _sha256_bytes(payload),
        }

    format_name = spec.format.lower()
    if format_name == "csv":
        dataframe = pd.read_csv(io.BytesIO(payload), sep=spec.delimiter, encoding=encoding)
    elif format_name == "tsv":
        dataframe = pd.read_csv(io.BytesIO(payload), sep="\t", encoding=encoding)
    elif format_name == "json":
        parsed = json.loads(payload.decode(encoding))
        dataframe = pd.DataFrame(_extract_records(parsed, records_path=spec.records_path))
    else:
        raise ValueError(f"Formato HTTP nao suportado: {spec.format}")

    provenance = _base_provenance(spec)
    provenance["http"] = {
        "request": {
            "method": method,
            "configured_url": spec.url,
            "resolved_url": url,
            "timeout_seconds": int(spec.timeout_seconds),
            "header_names": _safe_header_names(headers),
            "param_keys": sorted(str(key) for key in (spec.params or {}).keys()),
            "body_keys": sorted(str(key) for key in (spec.body_json or {}).keys()),
            "body_sha256": _sha256_bytes(payload_body) if payload_body else None,
        },
        "response": http_response,
    }
    return dataframe, provenance


def load_raw_source_dataframe(spec: DataSourceSpec) -> tuple[pd.DataFrame, dict]:
    if spec.source_type == "file":
        return _read_file_source(spec)
    if spec.source_type == "sqlite":
        return _read_sqlite_source(spec)
    if spec.source_type == "http":
        return _read_http_source(spec)
    raise ValueError(f"Tipo de fonte nao suportado: {spec.source_type}")


def normalize_source_dataframe(df: pd.DataFrame, spec: DataSourceSpec) -> pd.DataFrame:
    normalized = apply_source_preset(df.copy(), spec.preset)

    if spec.column_map:
        rename_map = {source_col: canonical_col for canonical_col, source_col in spec.column_map.items() if source_col in normalized.columns}
        normalized = normalized.rename(columns=rename_map)

    for field_name, field_value in spec.static_fields.items():
        normalized[field_name] = field_value

    if "source" not in normalized.columns:
        normalized["source"] = spec.name

    if spec.select_columns:
        keep_cols = [column for column in spec.select_columns if column in normalized.columns]
        for join_column in spec.join_on:
            if join_column in normalized.columns and join_column not in keep_cols:
                keep_cols.append(join_column)
        normalized = normalized[keep_cols].copy()

    if "gene" in normalized.columns and spec.gene_allowlist:
        allowed = {str(gene).upper() for gene in spec.gene_allowlist}
        normalized["gene"] = normalized["gene"].astype(str).str.upper()
        normalized = normalized[normalized["gene"].isin(allowed)].copy()

    normalized["source_name"] = spec.name
    normalized["source_kind"] = spec.kind
    normalized["source_type"] = spec.source_type
    return normalized.reset_index(drop=True)


def load_source_dataframe(spec: DataSourceSpec) -> tuple[pd.DataFrame, SourceLoadReport, dict]:
    raw_df, provenance = load_raw_source_dataframe(spec)
    normalized_df = normalize_source_dataframe(raw_df, spec)
    provenance["schema"] = {
        "raw_columns": [str(column) for column in raw_df.columns],
        "normalized_columns": [str(column) for column in normalized_df.columns],
        "rows_loaded": int(len(raw_df)),
        "rows_normalized": int(len(normalized_df)),
    }
    report = SourceLoadReport(
        name=spec.name,
        kind=spec.kind,
        source_type=spec.source_type,
        rows_loaded=int(len(raw_df)),
        rows_normalized=int(len(normalized_df)),
        columns_loaded=int(len(raw_df.columns)),
        columns_normalized=int(len(normalized_df.columns)),
        join_on=",".join(spec.join_on),
    )
    return normalized_df, report, provenance


def load_source_catalog(config_path: str) -> SourceCatalog:
    with open(config_path, "rb") as handle:
        raw = tomllib.load(handle)

    sources_payload = raw.get("sources", [])
    if not sources_payload:
        raise ValueError("O arquivo TOML precisa conter pelo menos uma entrada em [[sources]].")

    ingestion_payload = raw.get("ingestion", {})
    deduplicate_on = ingestion_payload.get("deduplicate_on", DEFAULT_DEDUPLICATE_KEYS)
    prefer_annotation_values = bool(ingestion_payload.get("prefer_annotation_values", True))

    sources: List[DataSourceSpec] = []
    for item in sources_payload:
        sources.append(
            DataSourceSpec(
                name=str(item["name"]),
                kind=_normalize_source_kind(item.get("kind")),
                source_type=_normalize_source_type(item.get("type", "file")),
                format=str(item.get("format", "csv")),
                path=item.get("path"),
                url=item.get("url"),
                query=item.get("query"),
                table=item.get("table"),
                delimiter=str(item.get("delimiter", ",")),
                encoding=str(item.get("encoding", "utf-8")),
                timeout_seconds=int(item.get("timeout_seconds", 60)),
                http_method=str(item.get("http_method", "GET")),
                body_json=dict(item.get("body_json", {})),
                column_map=dict(item.get("column_map", {})),
                static_fields=dict(item.get("static_fields", {})),
                headers=dict(item.get("headers", {})),
                params=dict(item.get("params", {})),
                select_columns=list(item.get("select_columns", [])),
                join_on=list(item.get("join_on", DEFAULT_JOIN_KEYS)),
                gene_allowlist=list(item.get("gene_allowlist") or []),
                preset=_normalize_preset(item.get("preset")),
                records_path=item.get("records_path"),
                release_version=item.get("release_version"),
                release_date=item.get("release_date"),
            )
        )

    return SourceCatalog(
        sources=sources,
        deduplicate_on=list(deduplicate_on),
        prefer_annotation_values=prefer_annotation_values,
    )


def _merge_annotation_dataframe(base_df: pd.DataFrame, annotation_df: pd.DataFrame, join_on: List[str], prefer_annotation_values: bool = True) -> pd.DataFrame:
    if annotation_df.empty:
        return base_df
    for join_column in join_on:
        if join_column not in base_df.columns:
            raise ValueError(f"A base principal nao possui a coluna de juncao '{join_column}'.")
        if join_column not in annotation_df.columns:
            raise ValueError(f"A fonte de anotacao nao possui a coluna de juncao '{join_column}'.")

    deduplicated_annotation = annotation_df.drop_duplicates(subset=join_on, keep="first").copy()
    merged = base_df.merge(deduplicated_annotation, on=join_on, how="left", suffixes=("", "__incoming"))

    for column in deduplicated_annotation.columns:
        if column in join_on or column in SOURCE_METADATA_COLUMNS:
            continue
        incoming_column = f"{column}__incoming"
        if incoming_column not in merged.columns:
            continue
        if column in base_df.columns:
            if column.startswith("meta_"):
                merged[column] = merged[column].combine_first(merged[incoming_column])
            elif prefer_annotation_values:
                merged[column] = merged[incoming_column].combine_first(merged[column])
            else:
                merged[column] = merged[column].combine_first(merged[incoming_column])
        else:
            merged[column] = merged[incoming_column]
        merged = merged.drop(columns=[incoming_column])

    cleanup_columns = [f"{column}__incoming" for column in SOURCE_METADATA_COLUMNS if f"{column}__incoming" in merged.columns]
    if cleanup_columns:
        merged = merged.drop(columns=cleanup_columns)

    return merged


def build_integrated_training_table(catalog: SourceCatalog) -> tuple[pd.DataFrame, pd.DataFrame]:
    reports: List[SourceLoadReport] = []
    provenance_rows: List[dict] = []
    cohort_frames: List[pd.DataFrame] = []
    annotation_specs: List[tuple[DataSourceSpec, pd.DataFrame]] = []

    for spec in catalog.sources:
        normalized_df, report, provenance = load_source_dataframe(spec)
        reports.append(report)
        provenance_rows.append(provenance)
        if spec.kind == "cohort":
            missing_columns = [column for column in REQUIRED_DATASET_COLUMNS if column not in normalized_df.columns]
            if missing_columns:
                raise ValueError(f"A fonte de coorte '{spec.name}' nao contem as colunas obrigatorias: {missing_columns}")
            cohort_frames.append(normalized_df)
        else:
            annotation_specs.append((spec, normalized_df))

    if not cohort_frames:
        raise ValueError("E necessario informar pelo menos uma fonte do tipo 'cohort'.")

    integrated_df = pd.concat(cohort_frames, ignore_index=True, sort=False)
    deduplicate_on = [column for column in catalog.deduplicate_on if column in integrated_df.columns]
    if deduplicate_on:
        integrated_df = integrated_df.drop_duplicates(subset=deduplicate_on, keep="first").reset_index(drop=True)

    for spec, annotation_df in annotation_specs:
        integrated_df = _merge_annotation_dataframe(
            base_df=integrated_df,
            annotation_df=annotation_df,
            join_on=spec.join_on,
            prefer_annotation_values=catalog.prefer_annotation_values,
        )

    report_df = pd.DataFrame([asdict(report) for report in reports])
    report_df.attrs["source_provenance"] = provenance_rows
    return integrated_df.reset_index(drop=True), report_df


def ingest_sources_from_config(config_path: str, output_dir: str | None = None) -> dict:
    catalog = load_source_catalog(config_path)
    integrated_df, report_df = build_integrated_training_table(catalog)
    source_provenance = list(report_df.attrs.get("source_provenance", []))
    public_source_assessment = build_public_source_catalog_assessment(
        config_path=config_path,
        catalog=catalog,
        source_provenance=source_provenance,
    )
    public_source_sync_plan = build_public_source_sync_plan(
        config_path=config_path,
        public_source_assessment=public_source_assessment,
    )

    output_paths: Dict[str, str] = {}
    if output_dir:
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        integrated_path = output_root / "integrated_sources.csv"
        report_path = output_root / "source_ingestion_report.csv"
        integrated_df.to_csv(integrated_path, index=False)
        report_df.to_csv(report_path, index=False)
        output_paths["integrated_sources"] = str(integrated_path)
        output_paths["source_ingestion_report"] = str(report_path)
        public_json_path = output_root / "public_source_catalog_report.json"
        public_md_path = output_root / "public_source_catalog_report.md"
        public_json_path.write_text(json.dumps(public_source_assessment, indent=2, ensure_ascii=False), encoding="utf-8")
        public_md_path.write_text(str(public_source_assessment.get("markdown_report") or ""), encoding="utf-8")
        output_paths["public_source_catalog_report_json"] = str(public_json_path)
        output_paths["public_source_catalog_report_markdown"] = str(public_md_path)
        public_sync_json_path = output_root / "public_source_sync_plan.json"
        public_sync_md_path = output_root / "public_source_sync_plan.md"
        public_sync_json_path.write_text(json.dumps(public_source_sync_plan, indent=2, ensure_ascii=False), encoding="utf-8")
        public_sync_md_path.write_text(str(public_source_sync_plan.get("markdown_report") or ""), encoding="utf-8")
        output_paths["public_source_sync_plan_json"] = str(public_sync_json_path)
        output_paths["public_source_sync_plan_markdown"] = str(public_sync_md_path)
        output_paths.update(
            export_data_release_manifest(
                config_path=config_path,
                catalog=catalog,
                integrated_df=integrated_df,
                source_report=report_df,
                source_provenance=source_provenance,
                public_source_assessment=public_source_assessment,
                public_source_sync_plan=public_source_sync_plan,
                output_paths=output_paths,
                output_dir=output_dir,
            )
        )

    return {
        "catalog": catalog,
        "integrated_dataframe": integrated_df,
        "source_report": report_df,
        "source_provenance": source_provenance,
        "public_source_assessment": public_source_assessment,
        "public_source_sync_plan": public_source_sync_plan,
        "output_paths": output_paths,
    }


def train_from_source_config(
    config_path: str,
    output_dir: str = "primevarclass_results",
    mode: str = "hybrid",
    keep_metadata: bool = True,
    high_confidence_only: bool = False,
    model_families: list[str] | None = None,
) -> dict:
    ingestion = ingest_sources_from_config(config_path=config_path, output_dir=output_dir)
    results = run_full_training_pipeline_from_dataframe(
        raw_df=ingestion["integrated_dataframe"],
        mode=mode,
        output_dir=output_dir,
        keep_metadata=keep_metadata,
        high_confidence_only=high_confidence_only,
        model_families=model_families,
    )
    results["source_ingestion_report"] = ingestion["source_report"]
    results["source_provenance"] = ingestion["source_provenance"]
    results["public_source_assessment"] = ingestion["public_source_assessment"]
    results["public_source_sync_plan"] = ingestion["public_source_sync_plan"]
    results["source_ingestion_output_paths"] = ingestion["output_paths"]
    return results


def build_dataset_from_source_config(
    config_path: str,
    mode: str = "hybrid",
    keep_metadata: bool = True,
    high_confidence_only: bool = False,
    source_output_dir: str | None = None,
) -> tuple[pd.DataFrame, Any, pd.DataFrame]:
    ingestion = ingest_sources_from_config(config_path=config_path, output_dir=source_output_dir)
    built_df, build_report = prepare_training_dataframe(
        raw_df=ingestion["integrated_dataframe"],
        mode=mode,
        keep_metadata=keep_metadata,
        high_confidence_only=high_confidence_only,
    )
    return built_df, build_report, ingestion["source_report"]
