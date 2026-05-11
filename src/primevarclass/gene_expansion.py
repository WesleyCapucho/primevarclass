from __future__ import annotations

import json
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .real_data_preparation import (
    _extract_any_hgvs_protein,
    _jsonify,
    _normalize_label,
    _now_utc,
    _render_markdown_html,
    _review_status_rank,
)


def _iter_clinvar_gene_support(variant_summary_path: Path) -> dict[str, dict[str, int]]:
    candidate_columns = {
        "GeneSymbol",
        "Gene",
        "gene",
        "gene_symbol",
        "Protein change",
        "protein_change",
        "HGVS_p",
        "protein",
        "ClinicalSignificance",
        "clinical_significance",
        "label",
        "ReviewStatus",
        "review_status",
        "Name",
        "name",
    }
    suffixes = [part.lower() for part in variant_summary_path.suffixes]
    read_kwargs = {
        "sep": "\t",
        "low_memory": False,
        "usecols": lambda column_name: str(column_name) in candidate_columns,
        "chunksize": 50000,
    }
    if suffixes[-2:] == [".txt", ".gz"] or suffixes[-2:] == [".tsv", ".gz"]:
        reader = pd.read_csv(variant_summary_path, compression="gzip", **read_kwargs)
    else:
        reader = pd.read_csv(variant_summary_path, **read_kwargs)

    counters: defaultdict[str, Counter] = defaultdict(Counter)
    total_rows = 0
    selected_rows = 0
    for raw_chunk in reader:
        total_rows += int(len(raw_chunk))
        work = raw_chunk.copy()

        gene_series = None
        for column in ["GeneSymbol", "Gene", "gene", "gene_symbol"]:
            if column in work.columns:
                current = work[column].astype("string")
                gene_series = current if gene_series is None else gene_series.fillna(current)
        work["gene"] = gene_series.str.upper() if gene_series is not None else pd.Series(dtype="string")

        hgvs_series = None
        for column in ["Protein change", "protein_change", "HGVS_p", "protein", "Name", "name"]:
            if column in work.columns:
                extracted = work[column].map(_extract_any_hgvs_protein)
                hgvs_series = extracted if hgvs_series is None else hgvs_series.fillna(extracted)
        work["hgvs_p"] = hgvs_series

        label_series = None
        for column in ["ClinicalSignificance", "clinical_significance", "label"]:
            if column in work.columns:
                current = work[column].map(_normalize_label)
                label_series = current if label_series is None else label_series.fillna(current)
        work["label"] = label_series

        review_series = None
        for column in ["ReviewStatus", "review_status"]:
            if column in work.columns:
                current = work[column].astype("string")
                review_series = current if review_series is None else review_series.fillna(current)
        work["review_status"] = review_series.fillna("ClinVar") if review_series is not None else "ClinVar"
        work["review_rank"] = work["review_status"].map(_review_status_rank)

        selected = work[work["gene"].notna() & work["hgvs_p"].notna() & work["label"].notna()].copy()
        if selected.empty:
            continue
        selected_rows += int(len(selected))
        for gene_name, gene_df in selected.groupby("gene"):
            counter = counters[str(gene_name)]
            counter["clinvar_labeled_rows"] += int(len(gene_df))
            counter["clinvar_positive_rows"] += int(
                gene_df["label"].astype(str).str.contains("Pathogenic", case=False, na=False).sum()
            )
            counter["clinvar_negative_rows"] += int(
                gene_df["label"].astype(str).str.contains("Benign", case=False, na=False).sum()
            )
            counter["clinvar_expert_rows"] += int((gene_df["review_rank"] >= 4).sum())
            counter["clinvar_reviewed_rows"] += int((gene_df["review_rank"] >= 2).sum())
            counter["clinvar_unique_hgvs_rows"] += int(gene_df["hgvs_p"].astype(str).nunique())

    summary = {gene_name: dict(counter) for gene_name, counter in counters.items()}
    summary["__meta__"] = {
        "input_path": str(variant_summary_path.resolve()),
        "raw_rows": int(total_rows),
        "selected_rows": int(selected_rows),
        "gene_count": int(len(counters)),
    }
    return summary


def _iter_mavedb_score_sets(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    score_sets: list[dict[str, Any]] = []
    for experiment_set in metadata.get("experimentSets", []):
        experiments = experiment_set.get("experiments") or []
        for experiment in experiments:
            experiment_title = str(experiment.get("title") or experiment.get("shortDescription") or "").strip()
            experiment_targets = [
                str(target.get("name") or target.get("mappedHgncName") or "").upper()
                for target in (experiment.get("targetGenes") or [])
                if str(target.get("name") or target.get("mappedHgncName") or "").strip()
            ]
            for score_set in experiment.get("scoreSets") or []:
                targets = [
                    str(target.get("name") or target.get("mappedHgncName") or "").upper()
                    for target in (score_set.get("targetGenes") or [])
                    if str(target.get("name") or target.get("mappedHgncName") or "").strip()
                ]
                if not targets:
                    targets = list(experiment_targets)
                score_sets.append(
                    {
                        "urn": str(score_set.get("urn") or "").strip(),
                        "assay_name": str(score_set.get("title") or experiment_title or "").strip(),
                        "processing_state": str(score_set.get("processingState") or "").strip(),
                        "target_genes": [gene for gene in targets if gene],
                    }
                )
    return score_sets


def _load_mavedb_gene_support(
    mavedb_dump_path: Path,
    *,
    candidate_genes: set[str] | None = None,
) -> dict[str, Any]:
    with zipfile.ZipFile(mavedb_dump_path) as archive:
        with archive.open("main.json") as handle:
            metadata = json.load(handle)
        score_sets = _iter_mavedb_score_sets(metadata)

        gene_to_score_sets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in score_sets:
            if not item["urn"] or item["processing_state"].lower() == "failed":
                continue
            for gene_name in set(item["target_genes"]):
                if candidate_genes and gene_name not in candidate_genes:
                    continue
                gene_to_score_sets[gene_name].append(item)

        row_counts: dict[str, int] = {}
        if candidate_genes:
            for gene_name in sorted(candidate_genes):
                total_rows = 0
                seen_entries: set[str] = set()
                for item in gene_to_score_sets.get(gene_name, []):
                    entry_name = f"csv/{item['urn'].replace(':', '-')}.scores.csv"
                    if entry_name in seen_entries or entry_name not in archive.namelist():
                        continue
                    seen_entries.add(entry_name)
                    with archive.open(entry_name) as handle:
                        total_rows += max(sum(1 for _ in handle) - 1, 0)
                row_counts[gene_name] = int(total_rows)

    gene_support: dict[str, dict[str, Any]] = {}
    for gene_name, items in gene_to_score_sets.items():
        gene_support[gene_name] = {
            "mavedb_score_set_count": int(len(items)),
            "mavedb_score_rows": int(row_counts.get(gene_name, 0)),
            "mavedb_assays": sorted({str(item["assay_name"]) for item in items if item["assay_name"]}),
            "mavedb_score_set_urns": sorted({str(item["urn"]) for item in items if item["urn"]}),
        }
    return {
        "gene_support": gene_support,
        "summary": {
            "input_path": str(mavedb_dump_path.resolve()),
            "score_set_count": int(len(score_sets)),
            "supported_gene_count": int(len(gene_support)),
            "row_counted_gene_count": int(len(candidate_genes or [])),
        },
    }


def _scaled_log(value: int | float) -> float:
    numeric = max(float(value or 0.0), 0.0)
    return 0.0 if numeric <= 0.0 else float(math.log1p(numeric))


def _normalize_series(values: pd.Series) -> pd.Series:
    if values.empty:
        return values.astype(float)
    minimum = float(values.min())
    maximum = float(values.max())
    if maximum <= minimum:
        return pd.Series([1.0] * len(values), index=values.index, dtype=float)
    return ((values.astype(float) - minimum) / (maximum - minimum)).astype(float)


def _build_panel_template(recommended_genes: list[str]) -> str:
    quoted_genes = ", ".join(f'"{gene}"' for gene in recommended_genes)
    return "\n".join(
        [
            "[panel]",
            'name = "PrimeVarClass Generalization Expansion Candidates"',
            f"genes = [{quoted_genes}]",
            'training_strategy = "ClinVar primary training + ClinVar expert holdout + external cohorts when available"',
            'annotation_strategy = "gnomAD direct API + MaveDB score sets"',
            'notes = "Gerado automaticamente a partir do overlap ClinVar x MaveDB para expansao multicohorte/multigene"',
            "",
        ]
    )


def _build_gene_expansion_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    top_candidates = bundle.get("top_candidates") or []
    lines = [
        "# PrimeVarClass Gene Expansion Assessment",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Overlap genes with ClinVar + MaveDB support: {summary.get('overlap_gene_count')}",
        f"- Recommended candidate genes: {summary.get('recommended_gene_count')}",
        f"- Excluded genes: {', '.join(summary.get('excluded_genes') or []) or 'none'}",
        "",
        "## Top expansion candidates",
        "",
    ]
    for item in top_candidates[:10]:
        lines.append(
            "- "
            f"{item.get('gene')}: priority={item.get('expansion_priority_percent')}%, "
            f"ClinVar={item.get('clinvar_labeled_rows')}, "
            f"expert={item.get('clinvar_expert_rows')}, "
            f"MaveDB score sets={item.get('mavedb_score_set_count')}, "
            f"MaveDB rows={item.get('mavedb_score_rows')}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This package ranks genes that are already supported by labeled ClinVar missense evidence and by at least one MaveDB functional assay.",
            "The resulting panel is a practical next step for expanding PrimeVarClass beyond the current BRCA benchmark while preserving real-data rigor.",
        ]
    )
    return "\n".join(lines).strip()


def build_gene_expansion_assessment(
    *,
    clinvar_variant_summary_path: str,
    mavedb_dump_path: str,
    exclude_genes: list[str] | None = None,
    top_k: int = 12,
) -> dict[str, Any]:
    excluded = {str(gene).strip().upper() for gene in (exclude_genes or ["BRCA1", "BRCA2"]) if str(gene).strip()}
    clinvar_support = _iter_clinvar_gene_support(Path(clinvar_variant_summary_path))
    clinvar_meta = dict(clinvar_support.pop("__meta__", {}))

    preliminary_candidates = {
        gene_name
        for gene_name, payload in clinvar_support.items()
        if int(payload.get("clinvar_labeled_rows", 0)) > 0 and gene_name not in excluded
    }
    mavedb_payload = _load_mavedb_gene_support(Path(mavedb_dump_path))
    initial_mavedb_support = dict(mavedb_payload.get("gene_support") or {})

    overlap_genes = sorted(preliminary_candidates.intersection(initial_mavedb_support.keys()))
    ranked_seed = []
    for gene_name in overlap_genes:
        clinvar_rows = int((clinvar_support.get(gene_name) or {}).get("clinvar_labeled_rows", 0))
        expert_rows = int((clinvar_support.get(gene_name) or {}).get("clinvar_expert_rows", 0))
        mavedb_sets = int((initial_mavedb_support.get(gene_name) or {}).get("mavedb_score_set_count", 0))
        ranked_seed.append(
            {
                "gene": gene_name,
                "preliminary_score": (2.5 * clinvar_rows) + (4.0 * expert_rows) + (25.0 * mavedb_sets),
            }
        )
    ranked_seed = sorted(ranked_seed, key=lambda item: (-item["preliminary_score"], item["gene"]))
    row_count_genes = {item["gene"] for item in ranked_seed[: max(top_k * 3, 20)]}

    rowcount_payload = _load_mavedb_gene_support(
        Path(mavedb_dump_path),
        candidate_genes=row_count_genes,
    )
    rowcount_support = dict(rowcount_payload.get("gene_support") or {})

    rows: list[dict[str, Any]] = []
    for gene_name in overlap_genes:
        clinvar_payload = dict(clinvar_support.get(gene_name) or {})
        mavedb_gene_payload = {
            **dict(initial_mavedb_support.get(gene_name) or {}),
            **dict(rowcount_support.get(gene_name) or {}),
        }
        rows.append(
            {
                "gene": gene_name,
                "clinvar_labeled_rows": int(clinvar_payload.get("clinvar_labeled_rows", 0)),
                "clinvar_unique_hgvs_rows": int(clinvar_payload.get("clinvar_unique_hgvs_rows", 0)),
                "clinvar_positive_rows": int(clinvar_payload.get("clinvar_positive_rows", 0)),
                "clinvar_negative_rows": int(clinvar_payload.get("clinvar_negative_rows", 0)),
                "clinvar_expert_rows": int(clinvar_payload.get("clinvar_expert_rows", 0)),
                "clinvar_reviewed_rows": int(clinvar_payload.get("clinvar_reviewed_rows", 0)),
                "mavedb_score_set_count": int(mavedb_gene_payload.get("mavedb_score_set_count", 0)),
                "mavedb_score_rows": int(mavedb_gene_payload.get("mavedb_score_rows", 0)),
                "gnomad_direct_api_ready": True,
            }
        )

    candidate_table = pd.DataFrame(rows)
    if candidate_table.empty:
        candidate_table = pd.DataFrame(
            columns=[
                "gene",
                "clinvar_labeled_rows",
                "clinvar_unique_hgvs_rows",
                "clinvar_positive_rows",
                "clinvar_negative_rows",
                "clinvar_expert_rows",
                "clinvar_reviewed_rows",
                "mavedb_score_set_count",
                "mavedb_score_rows",
                "gnomad_direct_api_ready",
            ]
        )
    else:
        candidate_table["clinvar_signal_score"] = _normalize_series(
            candidate_table["clinvar_labeled_rows"].map(_scaled_log)
        )
        candidate_table["expert_signal_score"] = _normalize_series(
            candidate_table["clinvar_expert_rows"].map(_scaled_log)
        )
        candidate_table["mavedb_set_score"] = _normalize_series(
            candidate_table["mavedb_score_set_count"].map(_scaled_log)
        )
        candidate_table["mavedb_row_score"] = _normalize_series(
            candidate_table["mavedb_score_rows"].map(_scaled_log)
        )
        candidate_table["expansion_priority_score"] = (
            0.45 * candidate_table["clinvar_signal_score"]
            + 0.2 * candidate_table["expert_signal_score"]
            + 0.2 * candidate_table["mavedb_set_score"]
            + 0.15 * candidate_table["mavedb_row_score"]
        )
        candidate_table["expansion_priority_percent"] = (
            candidate_table["expansion_priority_score"].fillna(0.0) * 100.0
        ).round(1)
        candidate_table = candidate_table.sort_values(
            ["expansion_priority_score", "clinvar_labeled_rows", "mavedb_score_set_count", "gene"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        candidate_table["priority_band"] = pd.cut(
            candidate_table["expansion_priority_percent"],
            bins=[-0.1, 50, 70, 85, 100],
            labels=["emerging", "promising", "strong", "ready"],
        ).astype("string")

    recommended = candidate_table.head(top_k).copy().reset_index(drop=True)
    panel_template = _build_panel_template(recommended["gene"].astype(str).tolist())
    summary = {
        "generated_at": _now_utc(),
        "clinvar_gene_count": int(clinvar_meta.get("gene_count", 0)),
        "mavedb_gene_count": int(mavedb_payload.get("summary", {}).get("supported_gene_count", 0)),
        "overlap_gene_count": int(len(candidate_table)),
        "recommended_gene_count": int(len(recommended)),
        "excluded_genes": sorted(excluded),
        "top_candidate_genes": recommended["gene"].astype(str).tolist(),
    }
    bundle = {
        "summary": summary,
        "candidate_table": candidate_table,
        "top_candidates": recommended.to_dict(orient="records"),
        "clinvar_summary": clinvar_meta,
        "mavedb_summary": {
            **dict(mavedb_payload.get("summary") or {}),
            "row_counted_gene_count": int(rowcount_payload.get("summary", {}).get("row_counted_gene_count", 0)),
        },
        "panel_template": panel_template,
    }
    bundle["markdown_report"] = _build_gene_expansion_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(
        bundle["markdown_report"],
        "PrimeVarClass Gene Expansion Assessment",
    )
    return bundle


def export_gene_expansion_assessment(
    *,
    clinvar_variant_summary_path: str,
    mavedb_dump_path: str,
    output_dir: str,
    exclude_genes: list[str] | None = None,
    top_k: int = 12,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_gene_expansion_assessment(
        clinvar_variant_summary_path=clinvar_variant_summary_path,
        mavedb_dump_path=mavedb_dump_path,
        exclude_genes=exclude_genes,
        top_k=top_k,
    )
    markdown_path = output_root / "gene_expansion_report.md"
    html_path = output_root / "gene_expansion_report.html"
    manifest_path = output_root / "gene_expansion_manifest.json"
    candidates_path = output_root / "gene_expansion_candidates.csv"
    panel_template_path = output_root / "gene_expansion_panel_template.toml"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")
    candidate_table = bundle.get("candidate_table")
    if isinstance(candidate_table, pd.DataFrame):
        candidate_table.to_csv(candidates_path, index=False)
    else:
        pd.DataFrame().to_csv(candidates_path, index=False)
    panel_template_path.write_text(str(bundle.get("panel_template") or ""), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "top_candidates": _jsonify(bundle.get("top_candidates") or []),
        "clinvar_summary": _jsonify(bundle.get("clinvar_summary") or {}),
        "mavedb_summary": _jsonify(bundle.get("mavedb_summary") or {}),
        "candidate_csv_path": str(candidates_path),
        "panel_template_path": str(panel_template_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(
        json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "gene_expansion_assessment": bundle,
        "gene_expansion_manifest_path": str(manifest_path),
        "gene_expansion_report_markdown_path": str(markdown_path),
        "gene_expansion_report_html_path": str(html_path),
        "gene_expansion_candidates_path": str(candidates_path),
        "gene_expansion_panel_template_path": str(panel_template_path),
    }
