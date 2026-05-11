from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .real_data_preparation import _jsonify, _now_utc, _render_markdown_html, _review_status_rank


HGVS_POSITION_PATTERN = re.compile(r"p\.[A-Za-z\*]+(\d+)[A-Za-z\*]+$")
POSITIVE_LABELS = {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
NEGATIVE_LABELS = {"Benign", "Likely benign", "Benign/Likely benign"}
HIGH_CONFIDENCE_SOURCES = {"clinvar_expert", "enigma_curated", "brca_exchange_external"}


def _extract_position(hgvs_p: Any) -> int | None:
    match = HGVS_POSITION_PATTERN.match(str(hgvs_p or "").strip())
    if not match:
        return None
    return int(match.group(1))


def _normalize_clinical_table(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "label",
                "review_status",
                "review_rank",
                "variant_id",
                "variant_name",
                "source_name",
                "position",
            ]
        )
    work = df.copy()
    rename_map = {
        "GeneSymbol": "gene",
        "Protein change": "hgvs_p",
        "ClinicalSignificance": "label",
        "ReviewStatus": "review_status",
        "VariationID": "variant_id",
        "Name": "variant_name",
    }
    work = work.rename(columns={key: value for key, value in rename_map.items() if key in work.columns})
    work["gene"] = work["gene"].astype(str).str.upper()
    work["hgvs_p"] = work["hgvs_p"].astype(str)
    if "review_status" not in work.columns:
        work["review_status"] = ""
    if "variant_id" not in work.columns:
        work["variant_id"] = ""
    if "variant_name" not in work.columns:
        work["variant_name"] = ""
    work["review_status"] = work["review_status"].fillna("").astype(str)
    work["review_rank"] = work["review_status"].map(_review_status_rank)
    work["source_name"] = source_name
    work["position"] = work["hgvs_p"].map(_extract_position)
    return work[
        ["gene", "hgvs_p", "label", "review_status", "review_rank", "variant_id", "variant_name", "source_name", "position"]
    ].copy()


def _label_group(value: Any) -> str | None:
    text = str(value or "").strip()
    if text in POSITIVE_LABELS:
        return "positive"
    if text in NEGATIVE_LABELS:
        return "negative"
    return None


def _clinical_priority(row: pd.Series) -> tuple:
    source_name = str(row.get("source_name") or "")
    is_high_confidence = int(source_name in HIGH_CONFIDENCE_SOURCES)
    return (
        is_high_confidence,
        int(row.get("review_rank") or 0),
        source_name,
    )


def _build_clinical_reference(*tables: pd.DataFrame) -> pd.DataFrame:
    frames = [table.copy() for table in tables if isinstance(table, pd.DataFrame) and not table.empty]
    if not frames:
        return _normalize_clinical_table(pd.DataFrame(), "empty")
    merged = pd.concat(frames, ignore_index=True)
    merged["label_group"] = merged["label"].map(_label_group)
    merged = merged[merged["label_group"].notna() & merged["position"].notna()].copy()
    merged["priority_key"] = merged.apply(_clinical_priority, axis=1)
    merged = merged.sort_values(
        by=["gene", "hgvs_p", "priority_key"],
        ascending=[True, True, False],
        kind="stable",
    )
    return merged.drop_duplicates(subset=["gene", "hgvs_p"], keep="first").reset_index(drop=True)


def _build_gene_orientation_map(
    clinical_reference: pd.DataFrame,
    mavedb_scores: pd.DataFrame,
) -> tuple[dict[str, str], pd.DataFrame]:
    merged = clinical_reference.merge(
        mavedb_scores[["gene", "hgvs_p", "score", "score_set_urn", "assay_name"]],
        on=["gene", "hgvs_p"],
        how="inner",
    )
    if merged.empty:
        orientation_table = pd.DataFrame(
            columns=[
                "gene",
                "score_set_urn",
                "assay_name",
                "damaging_direction",
                "overlap_rows",
                "positive_rows",
                "negative_rows",
                "orientation_confidence_percent",
            ]
        )
        return {}, orientation_table

    gene_defaults: dict[str, str] = {}
    for gene_name, gene_df in merged.groupby("gene"):
        positive = gene_df.loc[gene_df["label_group"] == "positive", "score"]
        negative = gene_df.loc[gene_df["label_group"] == "negative", "score"]
        if len(positive) >= 3 and len(negative) >= 3 and float(positive.median()) != float(negative.median()):
            gene_defaults[str(gene_name)] = "lower" if float(positive.median()) < float(negative.median()) else "higher"
        else:
            gene_defaults[str(gene_name)] = "lower"

    rows: list[dict[str, Any]] = []
    for (gene_name, score_set_urn), score_set_df in merged.groupby(["gene", "score_set_urn"], dropna=False):
        positive = score_set_df.loc[score_set_df["label_group"] == "positive", "score"]
        negative = score_set_df.loc[score_set_df["label_group"] == "negative", "score"]
        if len(positive) >= 3 and len(negative) >= 3 and float(positive.median()) != float(negative.median()):
            direction = "lower" if float(positive.median()) < float(negative.median()) else "higher"
            confidence = min(100.0, abs(float(positive.median()) - float(negative.median())) * 100.0)
        else:
            direction = gene_defaults.get(str(gene_name), "lower")
            confidence = 35.0
        rows.append(
            {
                "gene": str(gene_name),
                "score_set_urn": str(score_set_urn),
                "assay_name": str(score_set_df["assay_name"].dropna().astype(str).iloc[0]) if score_set_df["assay_name"].notna().any() else "",
                "damaging_direction": direction,
                "overlap_rows": int(len(score_set_df)),
                "positive_rows": int(len(positive)),
                "negative_rows": int(len(negative)),
                "orientation_confidence_percent": round(float(confidence), 1),
            }
        )
    orientation_table = pd.DataFrame(rows).sort_values(
        ["gene", "orientation_confidence_percent", "score_set_urn"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    orientation_map = {
        f"{row['gene']}::{row['score_set_urn']}": row["damaging_direction"]
        for row in orientation_table.to_dict(orient="records")
    }
    return orientation_map, orientation_table


def _apply_functional_damage_scores(
    mavedb_scores: pd.DataFrame,
    orientation_map: dict[str, str],
) -> pd.DataFrame:
    if mavedb_scores.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "score",
                "score_set_urn",
                "assay_name",
                "functional_damage_score",
            ]
        )
    frames: list[pd.DataFrame] = []
    for (gene_name, score_set_urn), score_set_df in mavedb_scores.groupby(["gene", "score_set_urn"], dropna=False):
        work = score_set_df.copy()
        direction = orientation_map.get(f"{gene_name}::{score_set_urn}", "lower")
        ascending = direction == "lower"
        work["functional_damage_score"] = work["score"].rank(method="average", pct=True, ascending=ascending)
        work["functional_damage_score"] = 1.0 - work["functional_damage_score"] + (1.0 / max(len(work), 1))
        work["functional_damage_score"] = work["functional_damage_score"].clip(0.0, 1.0)
        frames.append(work)
    return pd.concat(frames, ignore_index=True)


def _aggregate_functional_scores(functional_scores: pd.DataFrame) -> pd.DataFrame:
    if functional_scores.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "functional_damage_score",
                "score_set_support",
                "assay_support",
                "median_mave_score",
            ]
        )
    return (
        functional_scores.groupby(["gene", "hgvs_p"], as_index=False)
        .agg(
            functional_damage_score=("functional_damage_score", "mean"),
            score_set_support=("score_set_urn", pd.Series.nunique),
            assay_support=("assay_name", pd.Series.nunique),
            median_mave_score=("score", "median"),
        )
        .reset_index(drop=True)
    )


def _rarity_score(popmax_af: Any) -> float:
    if pd.isna(popmax_af):
        return 0.5
    value = max(float(popmax_af), 1e-8)
    return float(np.clip(((-math.log10(value)) - 2.0) / 4.0, 0.0, 1.0))


def _build_hotspot_tables(variant_table: pd.DataFrame, window_size: int = 50) -> tuple[pd.DataFrame, pd.DataFrame]:
    labeled = variant_table[variant_table["label_group"].notna() & variant_table["position"].notna()].copy()
    if labeled.empty:
        empty = pd.DataFrame(
            columns=[
                "gene",
                "window_label",
                "window_start",
                "window_end",
                "variant_count",
                "positive_rate",
                "mean_functional_damage_score",
                "median_popmax_af",
                "hotspot_score_percent",
            ]
        )
        return empty, empty.copy()

    labeled["window_start"] = (((labeled["position"].astype(int) - 1) // int(window_size)) * int(window_size)) + 1
    labeled["window_end"] = labeled["window_start"] + int(window_size) - 1
    labeled["is_positive"] = (labeled["label_group"] == "positive").astype(int)
    labeled["hotspot_score"] = (
        0.5 * labeled["is_positive"].astype(float)
        + 0.35 * labeled["functional_damage_score"].fillna(0.5)
        + 0.15 * labeled["rarity_score"].fillna(0.5)
    )
    grouped = (
        labeled.groupby(["gene", "window_start", "window_end"], as_index=False)
        .agg(
            variant_count=("hgvs_p", "nunique"),
            positive_rate=("is_positive", "mean"),
            mean_functional_damage_score=("functional_damage_score", "mean"),
            median_popmax_af=("popmax_af", "median"),
            hotspot_score=("hotspot_score", "mean"),
        )
        .reset_index(drop=True)
    )
    grouped["window_label"] = grouped.apply(
        lambda row: f"{row['gene']}:{int(row['window_start'])}-{int(row['window_end'])}",
        axis=1,
    )
    grouped["hotspot_score_percent"] = (grouped["hotspot_score"] * 100.0).round(1)

    hotspots = grouped[
        (grouped["variant_count"] >= 4)
        & (grouped["positive_rate"] >= 0.65)
        & (grouped["mean_functional_damage_score"] >= 0.65)
    ].copy()
    hotspots = hotspots.sort_values(
        ["hotspot_score", "variant_count", "gene", "window_start"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    tolerant = grouped[
        (grouped["variant_count"] >= 4)
        & (grouped["positive_rate"] <= 0.2)
        & (grouped["mean_functional_damage_score"] <= 0.35)
    ].copy()
    tolerant["tolerant_score_percent"] = (
        (
            0.5 * (1.0 - tolerant["positive_rate"])
            + 0.35 * (1.0 - tolerant["mean_functional_damage_score"])
            + 0.15 * (1.0 - tolerant["median_popmax_af"].fillna(0.0).clip(upper=1.0))
        )
        * 100.0
    ).round(1)
    tolerant = tolerant.sort_values(
        ["tolerant_score_percent", "variant_count", "gene", "window_start"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    return hotspots, tolerant


def _build_review_upgrade_candidates(variant_table: pd.DataFrame) -> pd.DataFrame:
    candidates = variant_table.copy()
    candidates["review_rank"] = candidates["review_rank"].fillna(0).astype(int)
    candidates["evidence_score"] = np.nan

    positive_mask = (
        (candidates["label_group"] == "positive")
        & (candidates["review_rank"] <= 2)
        & (candidates["functional_damage_score"].fillna(0.0) >= 0.8)
        & (candidates["rarity_score"].fillna(0.0) >= 0.7)
    )
    benign_mask = (
        (candidates["label_group"] == "negative")
        & (candidates["review_rank"] <= 2)
        & (candidates["functional_damage_score"].fillna(1.0) <= 0.2)
        & (candidates["popmax_af"].fillna(0.0) >= 1e-5)
    )
    candidates.loc[positive_mask, "candidate_kind"] = "pathogenic_review_upgrade"
    candidates.loc[benign_mask, "candidate_kind"] = "benign_review_upgrade"
    candidates["candidate_kind"] = candidates["candidate_kind"].fillna("")
    candidates = candidates[candidates["candidate_kind"] != ""].copy()
    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "label",
                "review_status",
                "candidate_kind",
                "functional_damage_score",
                "popmax_af",
                "evidence_score_percent",
            ]
        )
    candidates["evidence_score"] = (
        0.5 * candidates["functional_damage_score"].fillna(0.5)
        + 0.25 * candidates["rarity_score"].fillna(0.5)
        + 0.25 * (1.0 - (candidates["review_rank"].clip(lower=0, upper=4) / 4.0))
    )
    candidates["evidence_score_percent"] = (candidates["evidence_score"] * 100.0).round(1)
    return candidates.sort_values(
        ["evidence_score", "gene", "hgvs_p"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def _build_hypothesis_variants(variant_table: pd.DataFrame) -> pd.DataFrame:
    hypotheses = variant_table[
        variant_table["label_group"].isna()
        & variant_table["functional_damage_score"].fillna(0.0).ge(0.85)
        & variant_table["score_set_support"].fillna(0).ge(1)
        & (
            variant_table["popmax_af"].isna()
            | variant_table["popmax_af"].fillna(1.0).le(1e-5)
        )
    ].copy()
    if hypotheses.empty:
        return pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "functional_damage_score",
                "score_set_support",
                "popmax_af",
                "hypothesis_score_percent",
            ]
        )
    hypotheses["hypothesis_score"] = (
        0.7 * hypotheses["functional_damage_score"].fillna(0.0)
        + 0.3 * hypotheses["rarity_score"].fillna(0.5)
    )
    hypotheses["hypothesis_score_percent"] = (hypotheses["hypothesis_score"] * 100.0).round(1)
    return hypotheses.sort_values(
        ["hypothesis_score", "score_set_support", "gene", "hgvs_p"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)


def _load_real_data_artifacts(real_data_manifest_path: Path) -> dict[str, str]:
    payload = json.loads(real_data_manifest_path.read_text(encoding="utf-8"))
    return dict(payload.get("artifact_paths") or {})


def _load_table(path: str | None, sep: str = "\t") -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    candidate = Path(path)
    if not candidate.exists():
        return pd.DataFrame()
    if candidate.suffix.lower() == ".csv":
        return pd.read_csv(candidate, low_memory=False)
    return pd.read_csv(candidate, sep=sep, low_memory=False)


def _build_biological_discovery_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    hotspots_payload = bundle.get("hotspots")
    tolerant_payload = bundle.get("tolerant_regions")
    upgrades_payload = bundle.get("review_upgrade_candidates")
    hypotheses_payload = bundle.get("hypothesis_variants")
    hotspots = hotspots_payload if isinstance(hotspots_payload, pd.DataFrame) else pd.DataFrame()
    tolerant = tolerant_payload if isinstance(tolerant_payload, pd.DataFrame) else pd.DataFrame()
    upgrades = upgrades_payload if isinstance(upgrades_payload, pd.DataFrame) else pd.DataFrame()
    hypotheses = hypotheses_payload if isinstance(hypotheses_payload, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Biological Discovery Package",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Genes profiled: {summary.get('gene_count')}",
        f"- Clinically labeled variants with functional support: {summary.get('clinical_functional_overlap_rows')}",
        f"- Mechanistic hotspot windows: {summary.get('hotspot_count')}",
        f"- Tolerant windows: {summary.get('tolerant_region_count')}",
        f"- Review-upgrade candidates: {summary.get('review_upgrade_candidate_count')}",
        f"- Hypothesis variants: {summary.get('hypothesis_variant_count')}",
        "",
        "## Top hotspot windows",
        "",
    ]
    for row in hotspots.head(8).to_dict(orient="records"):
        lines.append(
            "- "
            f"{row.get('window_label')}: score={row.get('hotspot_score_percent')}%, "
            f"positive_rate={round(float(row.get('positive_rate', 0.0)) * 100.0, 1)}%, "
            f"variants={row.get('variant_count')}"
        )
    lines.extend(["", "## Review-upgrade candidates", ""])
    for row in upgrades.head(8).to_dict(orient="records"):
        lines.append(
            "- "
            f"{row.get('gene')} {row.get('hgvs_p')} ({row.get('candidate_kind')}): "
            f"evidence={row.get('evidence_score_percent')}%, "
            f"review={row.get('review_status')}"
        )
    lines.extend(["", "## Hypothesis variants", ""])
    for row in hypotheses.head(8).to_dict(orient="records"):
        lines.append(
            "- "
            f"{row.get('gene')} {row.get('hgvs_p')}: "
            f"hypothesis={row.get('hypothesis_score_percent')}%, "
            f"functional_damage={round(float(row.get('functional_damage_score', 0.0)) * 100.0, 1)}%, "
            f"score_sets={row.get('score_set_support')}"
        )
    if tolerant.empty:
        lines.extend(["", "## Tolerant windows", "", "- No tolerant windows passed the current threshold."])
    else:
        lines.extend(["", "## Tolerant windows", ""])
        for row in tolerant.head(6).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('window_label')}: tolerant_score={row.get('tolerant_score_percent')}%, "
                f"variants={row.get('variant_count')}"
            )
    return "\n".join(lines).strip()


def build_biological_discovery_package(
    *,
    real_data_manifest_path: str,
) -> dict[str, Any]:
    artifact_paths = _load_real_data_artifacts(Path(real_data_manifest_path))
    training_df = _normalize_clinical_table(
        _load_table(artifact_paths.get("training_table")),
        "clinvar_training",
    )
    clinvar_expert_df = _normalize_clinical_table(
        _load_table(artifact_paths.get("clinvar_expert_table")),
        "clinvar_expert",
    )
    external_df = _normalize_clinical_table(
        _load_table(artifact_paths.get("external_table")),
        "brca_exchange_external",
    )
    enigma_df = _normalize_clinical_table(
        _load_table(artifact_paths.get("enigma_table")),
        "enigma_curated",
    )
    gnomad_df = _load_table(artifact_paths.get("gnomad_table"))
    mavedb_df = _load_table(artifact_paths.get("mavedb_table"))

    clinical_reference = _build_clinical_reference(training_df, clinvar_expert_df, external_df, enigma_df)
    orientation_map, orientation_table = _build_gene_orientation_map(clinical_reference, mavedb_df)
    functional_scores = _apply_functional_damage_scores(mavedb_df, orientation_map)
    functional_variant_table = _aggregate_functional_scores(functional_scores)

    gnomad_subset = gnomad_df[["gene", "hgvs_p", "af", "ac", "an", "popmax_af"]].copy() if not gnomad_df.empty else pd.DataFrame(
        columns=["gene", "hgvs_p", "af", "ac", "an", "popmax_af"]
    )

    clinical_variants = clinical_reference.merge(
        functional_variant_table,
        on=["gene", "hgvs_p"],
        how="outer",
    )
    variant_table = clinical_variants.merge(
        gnomad_subset,
        on=["gene", "hgvs_p"],
        how="left",
    )
    variant_table["position"] = variant_table["position"].fillna(variant_table["hgvs_p"].map(_extract_position))
    variant_table["label_group"] = variant_table["label"].map(_label_group)
    variant_table["review_rank"] = variant_table["review_rank"].fillna(0).astype(int)
    variant_table["rarity_score"] = variant_table["popmax_af"].map(_rarity_score)

    hotspots, tolerant_regions = _build_hotspot_tables(variant_table)
    review_upgrade_candidates = _build_review_upgrade_candidates(variant_table)
    hypothesis_variants = _build_hypothesis_variants(variant_table)

    summary = {
        "generated_at": _now_utc(),
        "gene_count": int(variant_table["gene"].dropna().astype(str).nunique()),
        "clinical_functional_overlap_rows": int(
            (
                variant_table["label_group"].notna()
                & variant_table["functional_damage_score"].notna()
            ).sum()
        ),
        "hotspot_count": int(len(hotspots)),
        "tolerant_region_count": int(len(tolerant_regions)),
        "review_upgrade_candidate_count": int(len(review_upgrade_candidates)),
        "hypothesis_variant_count": int(len(hypothesis_variants)),
        "top_hotspot_genes": hotspots["gene"].astype(str).head(5).tolist() if not hotspots.empty else [],
        "top_hypothesis_variants": hypothesis_variants["hgvs_p"].astype(str).head(5).tolist() if not hypothesis_variants.empty else [],
    }
    bundle = {
        "summary": summary,
        "hotspots": hotspots,
        "tolerant_regions": tolerant_regions,
        "review_upgrade_candidates": review_upgrade_candidates,
        "hypothesis_variants": hypothesis_variants,
        "orientation_table": orientation_table,
        "variant_table": variant_table,
        "artifact_paths": artifact_paths,
    }
    bundle["markdown_report"] = _build_biological_discovery_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(
        bundle["markdown_report"],
        "PrimeVarClass Biological Discovery Package",
    )
    return bundle


def export_biological_discovery_package(
    *,
    real_data_manifest_path: str,
    output_dir: str,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_biological_discovery_package(real_data_manifest_path=real_data_manifest_path)

    markdown_path = output_root / "biological_discovery_report.md"
    html_path = output_root / "biological_discovery_report.html"
    manifest_path = output_root / "biological_discovery_manifest.json"
    hotspots_path = output_root / "biological_discovery_hotspots.csv"
    tolerant_path = output_root / "biological_discovery_tolerant_regions.csv"
    upgrades_path = output_root / "biological_discovery_review_upgrade_candidates.csv"
    hypotheses_path = output_root / "biological_discovery_hypothesis_variants.csv"
    orientations_path = output_root / "biological_discovery_orientations.csv"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or ""), encoding="utf-8")
    for payload, path in [
        (bundle.get("hotspots"), hotspots_path),
        (bundle.get("tolerant_regions"), tolerant_path),
        (bundle.get("review_upgrade_candidates"), upgrades_path),
        (bundle.get("hypothesis_variants"), hypotheses_path),
        (bundle.get("orientation_table"), orientations_path),
    ]:
        if isinstance(payload, pd.DataFrame):
            payload.to_csv(path, index=False)
        else:
            pd.DataFrame().to_csv(path, index=False)

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "artifact_paths": bundle.get("artifact_paths") or {},
        "hotspots_path": str(hotspots_path),
        "tolerant_regions_path": str(tolerant_path),
        "review_upgrade_candidates_path": str(upgrades_path),
        "hypothesis_variants_path": str(hypotheses_path),
        "orientations_path": str(orientations_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(
        json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "biological_discovery_package": bundle,
        "biological_discovery_manifest_path": str(manifest_path),
        "biological_discovery_report_markdown_path": str(markdown_path),
        "biological_discovery_report_html_path": str(html_path),
        "biological_discovery_hotspots_path": str(hotspots_path),
        "biological_discovery_tolerant_regions_path": str(tolerant_path),
        "biological_discovery_review_upgrade_candidates_path": str(upgrades_path),
        "biological_discovery_hypothesis_variants_path": str(hypotheses_path),
        "biological_discovery_orientations_path": str(orientations_path),
    }
