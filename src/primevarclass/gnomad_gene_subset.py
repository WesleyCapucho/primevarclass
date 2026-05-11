from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


GNOMAD_ENDPOINT = "https://gnomad.broadinstitute.org/api"
DEFAULT_TARGET_GENES = ["TP53", "PTEN", "MSH2", "KRAS", "GCK", "F9"]

GENE_VARIANTS_QUERY = """
query GeneVariants($gene: String!, $dataset: DatasetId!) {
  gene(gene_symbol: $gene, reference_genome: GRCh38) {
    symbol
    gene_id
    chrom
    start
    stop
    variants(dataset: $dataset) {
      variant_id
      chrom
      pos
      ref
      alt
      consequence
      hgvsp
      flags
      exome { ac an af }
      genome { ac an af }
    }
  }
}
"""


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


def _post_graphql(query: str, variables: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(GNOMAD_ENDPOINT, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _variant_rows_from_gene_payload(gene_payload: dict[str, Any]) -> list[dict[str, Any]]:
    gene = gene_payload or {}
    variants = gene.get("variants") or []
    rows: list[dict[str, Any]] = []
    for variant in variants:
        exome = variant.get("exome") or {}
        genome = variant.get("genome") or {}
        flags = variant.get("flags") or []
        rows.append(
            {
                "gene": gene.get("symbol"),
                "gene_id": gene.get("gene_id"),
                "gene_chrom": gene.get("chrom"),
                "gene_start": gene.get("start"),
                "gene_stop": gene.get("stop"),
                "variant_id": variant.get("variant_id"),
                "gnomad_variant_id": variant.get("variant_id"),
                "chrom": variant.get("chrom"),
                "pos": variant.get("pos"),
                "ref": variant.get("ref"),
                "alt": variant.get("alt"),
                "consequence": variant.get("consequence"),
                "hgvsp": variant.get("hgvsp"),
                "flags": ";".join(str(flag) for flag in flags),
                "AF": exome.get("af") if exome else genome.get("af"),
                "AC": exome.get("ac") if exome else genome.get("ac"),
                "AN": exome.get("an") if exome else genome.get("an"),
                "exome_af": exome.get("af"),
                "exome_ac": exome.get("ac"),
                "exome_an": exome.get("an"),
                "genome_af": genome.get("af"),
                "genome_ac": genome.get("ac"),
                "genome_an": genome.get("an"),
                "source_dataset": "gnomad_r4",
                "source_endpoint": GNOMAD_ENDPOINT,
                "fetched_at": _now_utc(),
            }
        )
    return rows


def _fetch_gene_variants(gene: str, dataset: str, timeout_sec: int, max_retries: int, sleep_seconds: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    last_error = ""
    for attempt in range(max(1, max_retries) + 1):
        try:
            response = _post_graphql(GENE_VARIANTS_QUERY, {"gene": gene, "dataset": dataset}, timeout_sec=timeout_sec)
            if response.get("errors"):
                last_error = json.dumps(response.get("errors"))[:1000]
                if "429" in last_error or "Too Many Requests" in last_error:
                    time.sleep(max(sleep_seconds, 1) * (attempt + 1))
                    continue
                return pd.DataFrame(), {"gene": gene, "status": "graphql_error", "variant_count": 0, "error": last_error}
            gene_payload = (response.get("data") or {}).get("gene") or {}
            rows = _variant_rows_from_gene_payload(gene_payload)
            return (
                pd.DataFrame(rows),
                {
                    "gene": gene,
                    "status": "found" if rows else "not_found_or_empty",
                    "variant_count": len(rows),
                    "gene_id": gene_payload.get("gene_id"),
                    "chrom": gene_payload.get("chrom"),
                    "start": gene_payload.get("start"),
                    "stop": gene_payload.get("stop"),
                    "error": "",
                },
            )
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}"
            if exc.code == 429:
                time.sleep(max(sleep_seconds, 1) * (attempt + 1))
                continue
        except Exception as exc:
            last_error = str(exc)
            time.sleep(max(sleep_seconds, 0))
    return pd.DataFrame(), {"gene": gene, "status": "query_error", "variant_count": 0, "error": last_error}


def _build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# PrimeVarClass gnomAD Gene Subset",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Dataset: `{summary.get('dataset')}`",
        f"- Genes requested: `{summary.get('gene_count_requested')}`",
        f"- Genes fetched: `{summary.get('gene_count_fetched')}`",
        f"- Variant rows: `{summary.get('variant_row_count')}`",
        f"- Query success: `{summary.get('query_success_percent')}%`",
        "",
        "## Scope",
        "",
        "- This is a broad local subset for the target genes, fetched from the public gnomAD GraphQL API.",
        "- It is not the full 1.4 TB gnomAD v4 short-variant release.",
        "- It is designed to close row-level population-frequency evidence for PrimeVarClass without forcing a full release download.",
    ]
    return "\n".join(lines).strip()


def build_gnomad_gene_subset(
    *,
    target_genes: list[str] | tuple[str, ...] | None = None,
    dataset: str = "gnomad_r4",
    timeout_sec: int = 120,
    max_retries: int = 2,
    sleep_seconds: float = 1.0,
) -> dict[str, Any]:
    genes = [str(gene).strip().upper() for gene in (target_genes or DEFAULT_TARGET_GENES) if str(gene).strip()]
    frames: list[pd.DataFrame] = []
    gene_status: list[dict[str, Any]] = []
    for gene in genes:
        frame, status = _fetch_gene_variants(
            gene,
            dataset=dataset,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            sleep_seconds=sleep_seconds,
        )
        if not frame.empty:
            frame["source_dataset"] = dataset
            frames.append(frame)
        gene_status.append(status)
        time.sleep(max(sleep_seconds, 0))
    variants = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not variants.empty:
        variants = variants.drop_duplicates(subset=["gene", "variant_id"], keep="first")
    status_table = pd.DataFrame(gene_status)
    fetched = int(status_table["status"].eq("found").sum()) if not status_table.empty else 0
    summary = {
        "generated_at": _now_utc(),
        "dataset": dataset,
        "gene_count_requested": len(genes),
        "gene_count_fetched": fetched,
        "query_success_percent": _percent((fetched / len(genes)) * 100 if genes else 0),
        "variant_row_count": int(len(variants)),
        "target_genes": genes,
        "gnomad_endpoint": GNOMAD_ENDPOINT,
        "scope": "gene_level_public_api_subset",
        "full_release_downloaded": False,
        "full_release_note": "Full gnomAD v4 exomes+genomes VCFs are much larger; this subset fetches all public browser variants for the selected genes.",
    }
    return {
        "summary": summary,
        "variants": variants,
        "gene_status": status_table,
        "markdown_report": _build_markdown(summary),
    }


def export_gnomad_gene_subset(
    *,
    output_dir: str,
    target_genes: list[str] | tuple[str, ...] | None = None,
    dataset: str = "gnomad_r4",
    timeout_sec: int = 120,
    max_retries: int = 2,
    sleep_seconds: float = 1.0,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_gnomad_gene_subset(
        target_genes=target_genes,
        dataset=dataset,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        sleep_seconds=sleep_seconds,
    )
    variants_path = output_root / "gnomad_gene_subset_variants.tsv"
    status_path = output_root / "gnomad_gene_subset_status.csv"
    manifest_path = output_root / "gnomad_gene_subset_manifest.json"
    markdown_path = output_root / "gnomad_gene_subset_report.md"
    html_path = output_root / "gnomad_gene_subset_report.html"

    variants = payload.get("variants")
    (variants if isinstance(variants, pd.DataFrame) else pd.DataFrame()).to_csv(variants_path, sep="\t", index=False)
    status = payload.get("gene_status")
    (status if isinstance(status, pd.DataFrame) else pd.DataFrame()).to_csv(status_path, index=False)
    markdown_path.write_text(str(payload.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(
        _render_markdown_html(str(payload.get("markdown_report") or ""), "PrimeVarClass gnomAD Gene Subset"),
        encoding="utf-8",
    )
    manifest = {
        "generated_at": _now_utc(),
        "summary": payload.get("summary") or {},
        "gnomad_gene_subset_variants_path": str(variants_path),
        "gnomad_gene_subset_status_path": str(status_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "gnomad_gene_subset": payload,
        "gnomad_gene_subset_manifest_path": str(manifest_path),
        "gnomad_gene_subset_variants_path": str(variants_path),
        "gnomad_gene_subset_status_path": str(status_path),
        "gnomad_gene_subset_report_markdown_path": str(markdown_path),
        "gnomad_gene_subset_report_html_path": str(html_path),
    }
