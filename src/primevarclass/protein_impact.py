from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .core import encode_variant_features, get_aa_props, parse_variant
from .real_data_preparation import _jsonify, _render_markdown_html


GENE_DOMAIN_PRIORS: dict[str, list[dict[str, Any]]] = {
    "BRCA1": [
        {"region_name": "RING domain", "start": 1, "end": 109, "weight": 1.0, "mechanism": "zinc_binding_or_E3_ligase_interface"},
        {"region_name": "PALB2 interaction region", "start": 1393, "end": 1424, "weight": 0.75, "mechanism": "partner_binding"},
        {"region_name": "BRCT repeat 1", "start": 1646, "end": 1736, "weight": 0.9, "mechanism": "phosphopeptide_binding"},
        {"region_name": "BRCT repeat 2", "start": 1760, "end": 1855, "weight": 0.9, "mechanism": "phosphopeptide_binding"},
    ],
    "BRCA2": [
        {"region_name": "BRC repeat region", "start": 1000, "end": 1600, "weight": 0.75, "mechanism": "RAD51_binding"},
        {"region_name": "DNA-binding domain", "start": 2479, "end": 3192, "weight": 1.0, "mechanism": "DNA_binding_or_fold_stability"},
        {"region_name": "OB fold cluster", "start": 2670, "end": 3228, "weight": 0.9, "mechanism": "single_strand_DNA_binding"},
    ],
    "TP53": [
        {"region_name": "transactivation domain", "start": 1, "end": 92, "weight": 0.65, "mechanism": "cofactor_binding"},
        {"region_name": "DNA-binding core domain", "start": 102, "end": 292, "weight": 1.0, "mechanism": "DNA_binding_or_fold_stability"},
        {"region_name": "tetramerization domain", "start": 323, "end": 356, "weight": 0.85, "mechanism": "oligomerization"},
    ],
    "PTEN": [
        {"region_name": "phosphatase domain", "start": 7, "end": 185, "weight": 1.0, "mechanism": "catalysis_or_substrate_binding"},
        {"region_name": "C2 membrane-binding domain", "start": 186, "end": 351, "weight": 0.8, "mechanism": "membrane_binding"},
    ],
    "MSH2": [
        {"region_name": "mismatch-binding domain", "start": 1, "end": 115, "weight": 0.8, "mechanism": "DNA_mismatch_recognition"},
        {"region_name": "connector domain", "start": 116, "end": 300, "weight": 0.7, "mechanism": "protein_domain_coupling"},
        {"region_name": "ATPase domain", "start": 620, "end": 934, "weight": 1.0, "mechanism": "ATPase_or_dimerization"},
    ],
    "KRAS": [
        {"region_name": "P-loop", "start": 10, "end": 17, "weight": 1.0, "mechanism": "nucleotide_binding"},
        {"region_name": "switch I", "start": 30, "end": 40, "weight": 1.0, "mechanism": "effector_binding"},
        {"region_name": "switch II", "start": 60, "end": 76, "weight": 1.0, "mechanism": "GTPase_regulation"},
    ],
    "GCK": [
        {"region_name": "glucose-binding catalytic cleft", "start": 150, "end": 460, "weight": 0.9, "mechanism": "catalysis_or_substrate_binding"},
    ],
    "F9": [
        {"region_name": "Gla domain", "start": 1, "end": 46, "weight": 0.8, "mechanism": "membrane_binding"},
        {"region_name": "EGF-like region", "start": 47, "end": 160, "weight": 0.7, "mechanism": "cofactor_binding"},
        {"region_name": "serine protease domain", "start": 181, "end": 415, "weight": 1.0, "mechanism": "catalysis_or_fold_stability"},
    ],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    if math.isnan(numeric) or math.isinf(numeric):
        return default
    return numeric


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _read_table(path_value: Any) -> pd.DataFrame:
    if not path_value:
        return pd.DataFrame()
    path = Path(str(path_value)).expanduser()
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        return pd.DataFrame()


def _load_biological_discovery_manifest(path: str) -> dict[str, Any]:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"Biological discovery manifest not found: {path}")
    return json.loads(candidate.read_text(encoding="utf-8"))


def _normalize_candidate_table(df: pd.DataFrame, source_kind: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["gene", "hgvs_p", "source_kind", "source_score_percent"])
    work = df.copy()
    if "gene" not in work.columns or "hgvs_p" not in work.columns:
        return pd.DataFrame(columns=["gene", "hgvs_p", "source_kind", "source_score_percent"])
    work["gene"] = work["gene"].astype(str).str.upper().str.strip()
    work["hgvs_p"] = work["hgvs_p"].astype(str).str.strip()
    work["source_kind"] = source_kind
    score_columns = [
        "hypothesis_score_percent",
        "evidence_score_percent",
        "hotspot_score_percent",
        "tolerant_score_percent",
        "functional_damage_score",
    ]
    score_column = next((column for column in score_columns if column in work.columns), None)
    if score_column is None:
        work["source_score_percent"] = 50.0
    elif score_column == "functional_damage_score":
        work["source_score_percent"] = work[score_column].map(lambda value: _safe_float(value) * 100.0)
    else:
        work["source_score_percent"] = work[score_column].map(lambda value: _safe_float(value, 50.0))
    return work


def _load_candidate_variants(manifest: dict[str, Any]) -> pd.DataFrame:
    frames = [
        _normalize_candidate_table(_read_table(manifest.get("hypothesis_variants_path")), "hypothesis_variant"),
        _normalize_candidate_table(_read_table(manifest.get("review_upgrade_candidates_path")), "review_upgrade"),
    ]
    combined = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else pd.DataFrame()
    if combined.empty:
        return pd.DataFrame(columns=["gene", "hgvs_p", "source_kind", "source_score_percent"])
    combined["source_rank"] = combined["source_kind"].map({"review_upgrade": 2, "hypothesis_variant": 1}).fillna(0)
    combined = combined.sort_values(
        ["gene", "hgvs_p", "source_rank", "source_score_percent"],
        ascending=[True, True, False, False],
        kind="stable",
    )
    return combined.drop_duplicates(["gene", "hgvs_p"], keep="first").reset_index(drop=True)


def _domain_context(gene: str, position: int) -> dict[str, Any]:
    regions = GENE_DOMAIN_PRIORS.get(str(gene).upper(), [])
    for region in regions:
        if int(region["start"]) <= int(position) <= int(region["end"]):
            return {
                "structural_region": region["region_name"],
                "domain_weight": float(region["weight"]),
                "domain_mechanism": region["mechanism"],
                "domain_known": True,
            }
    return {
        "structural_region": "outside_curated_domain_prior",
        "domain_weight": 0.45,
        "domain_mechanism": "context_dependent_or_unknown",
        "domain_known": False,
    }


def _mechanism_tags(features: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    aa_ref = str(features.get("aa_ref") or "")
    aa_alt = str(features.get("aa_alt") or "")
    ref_props = get_aa_props(aa_ref)
    alt_props = get_aa_props(aa_alt)
    if aa_ref == "C" or aa_alt == "C":
        tags.append("cysteine_or_disulfide_shift")
    if aa_ref == "G" or aa_alt == "G":
        tags.append("backbone_flexibility_shift")
    if aa_ref == "P" or aa_alt == "P":
        tags.append("helix_or_backbone_constraint")
    if abs(int(features.get("charge_abs_diff") or 0)) >= 1:
        tags.append("electrostatic_shift")
    if float(features.get("hydro_abs_diff") or 0.0) >= 3.0:
        tags.append("hydrophobic_core_or_surface_shift")
    if int(features.get("aromatic_switch") or 0) == 1:
        tags.append("aromatic_packing_shift")
    if ref_props.get("class_group") != alt_props.get("class_group"):
        tags.append("amino_acid_class_switch")
    if float(features.get("prime_diff") or 0.0) >= 6:
        tags.append("large_prime_displacement")
    if abs(float(features.get("prime_gap_delta") or 0.0)) >= 4.0:
        tags.append("prime_gap_rewiring")
    if float(features.get("prime_curvature_score") or 0.0) >= 1.25:
        tags.append("prime_curvature_spike")
    if str(features.get("prime_twin_transition") or "0->0") != "0->0":
        tags.append("twin_prime_context_shift")
    if str(features.get("prime_sophie_transition") or "0->0") != "0->0":
        tags.append("sophie_germain_context_shift")
    if not tags:
        tags.append("subtle_biophysical_shift")
    return tags


def _prime_mechanistic_score(features: dict[str, Any]) -> float:
    prime_diff = min(float(features.get("prime_diff") or 0.0) / 12.0, 1.0)
    prime_ratio = min(abs(float(features.get("prime_log_ratio") or 0.0)) / 1.5, 1.0)
    prime_transition = 1.0 - float(features.get("prime_mass_retention") or 0.0)
    gap_delta = min(abs(float(features.get("prime_gap_delta") or 0.0)) / 8.0, 1.0)
    curvature = min(float(features.get("prime_curvature_score") or 0.0) / 2.5, 1.0)
    density_shift = min(abs(float(features.get("prime_local_density_delta") or 0.0)) / 0.25, 1.0)
    twin_shift = float(str(features.get("prime_twin_transition") or "0->0") != "0->0")
    sophie_shift = float(str(features.get("prime_sophie_transition") or "0->0") != "0->0")
    return float(
        np.clip(
            (0.30 * prime_diff)
            + (0.22 * prime_ratio)
            + (0.14 * prime_transition)
            + (0.14 * gap_delta)
            + (0.10 * curvature)
            + (0.05 * density_shift)
            + (0.03 * twin_shift)
            + (0.02 * sophie_shift),
            0.0,
            1.0,
        )
    )


def _recommended_assays(row: dict[str, Any]) -> str:
    mechanism_text = str(row.get("mechanism_tags") or "")
    domain_mechanism = str(row.get("domain_mechanism") or "")
    assays = ["mutant_structure_modeling"]
    if "fold_stability" in domain_mechanism or "hydrophobic_core" in mechanism_text:
        assays.append("thermal_or_protease_stability")
    if "binding" in domain_mechanism or "interface" in domain_mechanism:
        assays.append("partner_binding_assay")
    if "DNA" in domain_mechanism:
        assays.append("DNA_binding_or_repair_readout")
    if "catalysis" in domain_mechanism or "ATPase" in domain_mechanism or "GTPase" in domain_mechanism:
        assays.append("enzyme_activity_assay")
    if "cysteine" in mechanism_text:
        assays.append("redox_or_metal_coordination_check")
    return ";".join(dict.fromkeys(assays))


def _modeling_plan(row: dict[str, Any]) -> str:
    gene = str(row.get("gene") or "")
    hgvs_p = str(row.get("hgvs_p") or "")
    region = str(row.get("structural_region") or "protein region")
    return (
        f"Build reference-vs-mutant model for {gene} {hgvs_p}; map residue to {region}; "
        "compare local contacts, solvent exposure, charge/hydrophobic changes, and prime-displacement rationale."
    )


def build_protein_impact_package(
    *,
    biological_discovery_manifest_path: str,
    max_modeling_variants: int = 25,
) -> dict[str, Any]:
    manifest = _load_biological_discovery_manifest(biological_discovery_manifest_path)
    candidates = _load_candidate_variants(manifest)
    if candidates.empty:
        empty = pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "source_kind",
                "protein_impact_score_percent",
                "prime_mechanistic_score_percent",
                "structural_region",
                "mechanism_tags",
                "recommended_assays",
                "modeling_plan",
            ]
        )
        summary = {
            "generated_at": _now_utc(),
            "candidate_variant_count": 0,
            "modeling_queue_count": 0,
            "high_priority_variant_count": 0,
            "high_priority_threshold_percent": 85.0,
            "prime_mechanistic_alignment_percent": 0,
            "modeling_queue_prime_alignment_percent": 0,
            "candidate_prime_mechanistic_alignment_percent": 0,
            "mean_modeling_queue_prime_score_percent": 0.0,
            "top_modeling_variants": [],
            "top_mechanism_tags": [],
        }
        return {
            "summary": summary,
            "protein_variant_triage": empty,
            "protein_modeling_queue": empty,
            "protein_region_summary": pd.DataFrame(),
            "manifest_context": manifest,
        }

    rows: list[dict[str, Any]] = []
    for _, source_row in candidates.iterrows():
        gene = str(source_row.get("gene") or "").upper()
        hgvs_p = str(source_row.get("hgvs_p") or "")
        try:
            parsed = parse_variant(f"{gene} {hgvs_p}")
            features = encode_variant_features(parsed, mode="hybrid")
        except Exception:
            continue
        domain = _domain_context(gene, int(features["position"]))
        prime_score = _prime_mechanistic_score(features)
        functional_score = _safe_float(source_row.get("functional_damage_score"), default=_safe_float(source_row.get("source_score_percent"), 50.0) / 100.0)
        source_score = _safe_float(source_row.get("source_score_percent"), 50.0) / 100.0
        biochemical_severity_value = _safe_float(features.get("biochemical_severity_score"), 0.0)
        biochemical_severity = min(biochemical_severity_value / 10.0, 1.0)
        protein_impact_score = float(
            np.clip(
                (0.32 * source_score)
                + (0.24 * functional_score)
                + (0.18 * float(domain["domain_weight"]))
                + (0.16 * biochemical_severity)
                + (0.10 * prime_score),
                0.0,
                1.0,
            )
        )
        tags = _mechanism_tags(features)
        row = {
            "gene": gene,
            "hgvs_p": hgvs_p,
            "source_kind": str(source_row.get("source_kind") or ""),
            "source_score_percent": round(source_score * 100.0, 1),
            "protein_impact_score_percent": round(protein_impact_score * 100.0, 1),
            "prime_mechanistic_score_percent": round(prime_score * 100.0, 1),
            "position": int(features["position"]),
            "aa_ref": features.get("aa_ref"),
            "aa_alt": features.get("aa_alt"),
            "prime_ref": int(features.get("prime_ref") or 0),
            "prime_alt": int(features.get("prime_alt") or 0),
            "prime_diff": float(features.get("prime_diff") or 0.0),
            "prime_ratio": round(float(features.get("prime_ratio") or 0.0), 4),
            "prime_gap_delta": round(_safe_float(features.get("prime_gap_delta")), 4),
            "prime_curvature_score": round(_safe_float(features.get("prime_curvature_score")), 4),
            "prime_local_density_delta": round(_safe_float(features.get("prime_local_density_delta")), 6),
            "prime_mod_30_transition": str(features.get("prime_mod_30_transition") or ""),
            "prime_twin_transition": str(features.get("prime_twin_transition") or ""),
            "prime_sophie_transition": str(features.get("prime_sophie_transition") or ""),
            "biochemical_severity": round(biochemical_severity_value, 4),
            "hydro_abs_diff": round(_safe_float(features.get("hydro_abs_diff")), 4),
            "charge_abs_diff": _safe_int(features.get("charge_abs_diff")),
            "mass_abs_diff": round(_safe_float(features.get("mass_abs_diff")), 4),
            "structural_region": domain["structural_region"],
            "domain_mechanism": domain["domain_mechanism"],
            "domain_known": bool(domain["domain_known"]),
            "mechanism_tags": ";".join(tags),
        }
        row["recommended_assays"] = _recommended_assays(row)
        row["modeling_plan"] = _modeling_plan(row)
        rows.append(row)

    triage = pd.DataFrame(rows)
    if triage.empty:
        empty = pd.DataFrame(
            columns=[
                "gene",
                "hgvs_p",
                "source_kind",
                "protein_impact_score_percent",
                "prime_mechanistic_score_percent",
                "structural_region",
                "mechanism_tags",
                "recommended_assays",
                "modeling_plan",
            ]
        )
        summary = {
            "generated_at": _now_utc(),
            "candidate_variant_count": 0,
            "modeling_queue_count": 0,
            "high_priority_variant_count": 0,
            "high_priority_threshold_percent": 85.0,
            "prime_mechanistic_alignment_percent": 0,
            "modeling_queue_prime_alignment_percent": 0,
            "candidate_prime_mechanistic_alignment_percent": 0,
            "mean_modeling_queue_prime_score_percent": 0.0,
            "top_modeling_variants": [],
            "top_mechanism_tags": [],
        }
        return {
            "summary": summary,
            "protein_variant_triage": empty,
            "protein_modeling_queue": empty,
            "protein_region_summary": pd.DataFrame(),
            "manifest_context": manifest,
        }
    triage = triage.sort_values(
        ["protein_impact_score_percent", "prime_mechanistic_score_percent", "gene", "position"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    queue = triage.head(max(0, int(max_modeling_variants))).copy()
    queue["queue_rank"] = list(range(1, len(queue) + 1))
    queue["model_request_id"] = queue.apply(
        lambda row: f"{row['gene']}_{str(row['hgvs_p']).replace('.', '').replace('*', 'Ter')}",
        axis=1,
    )
    high_priority_threshold = 85.0
    region_summary = (
        triage.groupby(["gene", "structural_region", "domain_mechanism"], as_index=False)
        .agg(
            variant_count=("hgvs_p", "nunique"),
            mean_protein_impact_score_percent=("protein_impact_score_percent", "mean"),
            mean_prime_mechanistic_score_percent=("prime_mechanistic_score_percent", "mean"),
            high_priority_count=("protein_impact_score_percent", lambda values: int((values >= high_priority_threshold).sum())),
        )
        .sort_values(["high_priority_count", "mean_protein_impact_score_percent"], ascending=[False, False])
        .reset_index(drop=True)
    )
    mechanism_counts: dict[str, int] = {}
    for tags in triage["mechanism_tags"].astype(str):
        for tag in [token for token in tags.split(";") if token]:
            mechanism_counts[tag] = mechanism_counts.get(tag, 0) + 1
    top_tags = [tag for tag, _ in sorted(mechanism_counts.items(), key=lambda item: (-item[1], item[0]))[:6]]
    high_priority_count = int((triage["protein_impact_score_percent"] >= high_priority_threshold).sum())
    candidate_prime_alignment = int(round(float((triage["prime_mechanistic_score_percent"] >= 50.0).mean()) * 100.0))
    queue_prime_alignment = (
        int(round(float((queue["prime_mechanistic_score_percent"] >= 50.0).mean()) * 100.0))
        if not queue.empty
        else 0
    )
    mean_queue_prime_score = round(float(queue["prime_mechanistic_score_percent"].mean()), 1) if not queue.empty else 0.0
    summary = {
        "generated_at": _now_utc(),
        "candidate_variant_count": int(len(triage)),
        "modeling_queue_count": int(len(queue)),
        "high_priority_variant_count": high_priority_count,
        "high_priority_threshold_percent": high_priority_threshold,
        "prime_mechanistic_alignment_percent": queue_prime_alignment,
        "modeling_queue_prime_alignment_percent": queue_prime_alignment,
        "candidate_prime_mechanistic_alignment_percent": candidate_prime_alignment,
        "mean_modeling_queue_prime_score_percent": mean_queue_prime_score,
        "top_modeling_variants": (queue["gene"] + " " + queue["hgvs_p"]).head(8).tolist() if not queue.empty else [],
        "top_mechanism_tags": top_tags,
    }
    bundle = {
        "summary": summary,
        "protein_variant_triage": triage,
        "protein_modeling_queue": queue,
        "protein_region_summary": region_summary,
        "manifest_context": manifest,
    }
    bundle["markdown_report"] = _build_protein_impact_markdown(bundle)
    bundle["html_report"] = _render_markdown_html(bundle["markdown_report"], "PrimeVarClass Protein Impact Package")
    return bundle


def _build_protein_impact_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    queue = bundle.get("protein_modeling_queue")
    region_summary = bundle.get("protein_region_summary")
    queue_df = queue if isinstance(queue, pd.DataFrame) else pd.DataFrame()
    region_df = region_summary if isinstance(region_summary, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Protein Impact Package",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Candidate variants triaged: `{summary.get('candidate_variant_count')}`",
        f"- 3D/proteomic modeling queue: `{summary.get('modeling_queue_count')}`",
        f"- High-priority variants: `{summary.get('high_priority_variant_count')}` at `>= {summary.get('high_priority_threshold_percent', 85.0)}%`",
        f"- Modeling-queue prime alignment: `{summary.get('modeling_queue_prime_alignment_percent', summary.get('prime_mechanistic_alignment_percent'))}%`",
        f"- Candidate-wide prime alignment: `{summary.get('candidate_prime_mechanistic_alignment_percent', summary.get('prime_mechanistic_alignment_percent'))}%`",
        f"- Mean queue prime score: `{summary.get('mean_modeling_queue_prime_score_percent', 0)}%`",
        "",
        "## Top modeling queue",
        "",
    ]
    if queue_df.empty:
        lines.append("- No protein-impact candidates passed the current input filters.")
    else:
        for row in queue_df.head(12).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('hgvs_p')}: "
                f"impact={row.get('protein_impact_score_percent')}%, "
                f"prime={row.get('prime_mechanistic_score_percent')}%, "
                f"region={row.get('structural_region')}, "
                f"tags={row.get('mechanism_tags')}"
            )
    lines.extend(["", "## Region summary", ""])
    if region_df.empty:
        lines.append("- No region-level summary available.")
    else:
        for row in region_df.head(10).to_dict(orient="records"):
            lines.append(
                "- "
                f"{row.get('gene')} {row.get('structural_region')}: "
                f"variants={row.get('variant_count')}, "
                f"mean_impact={round(float(row.get('mean_protein_impact_score_percent', 0.0)), 1)}%, "
                f"mechanism={row.get('domain_mechanism')}"
            )
    lines.extend(
        [
            "",
            "## Modeling guidance",
            "",
            "- Treat this package as a triage and hypothesis-generation layer, not as final structural proof.",
            "- For top variants, run reference-vs-mutant structure modeling, local contact analysis, and assay follow-up.",
            "- Use the prime-mechanistic score as an explanatory signal to prioritize biochemical shifts that are unusually large in the project's prime encoding space.",
        ]
    )
    return "\n".join(lines).strip()


def export_protein_impact_package(
    *,
    biological_discovery_manifest_path: str,
    output_dir: str,
    max_modeling_variants: int = 25,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_protein_impact_package(
        biological_discovery_manifest_path=biological_discovery_manifest_path,
        max_modeling_variants=max_modeling_variants,
    )
    manifest_path = output_root / "protein_impact_manifest.json"
    markdown_path = output_root / "protein_impact_report.md"
    html_path = output_root / "protein_impact_report.html"
    triage_path = output_root / "protein_variant_triage.csv"
    queue_path = output_root / "protein_modeling_queue.csv"
    region_path = output_root / "protein_region_summary.csv"

    triage = bundle.get("protein_variant_triage")
    queue = bundle.get("protein_modeling_queue")
    region_summary = bundle.get("protein_region_summary")
    (triage if isinstance(triage, pd.DataFrame) else pd.DataFrame()).to_csv(triage_path, index=False)
    (queue if isinstance(queue, pd.DataFrame) else pd.DataFrame()).to_csv(queue_path, index=False)
    (region_summary if isinstance(region_summary, pd.DataFrame) else pd.DataFrame()).to_csv(region_path, index=False)
    markdown_path.write_text(str(bundle.get("markdown_report") or _build_protein_impact_markdown(bundle)), encoding="utf-8")
    html_path.write_text(str(bundle.get("html_report") or _render_markdown_html(markdown_path.read_text(encoding="utf-8"), "PrimeVarClass Protein Impact Package")), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "source_biological_discovery_manifest_path": str(Path(biological_discovery_manifest_path).expanduser().resolve()),
        "triage_path": str(triage_path),
        "modeling_queue_path": str(queue_path),
        "region_summary_path": str(region_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "protein_impact_package": bundle,
        "protein_impact_manifest_path": str(manifest_path),
        "protein_impact_report_markdown_path": str(markdown_path),
        "protein_impact_report_html_path": str(html_path),
        "protein_variant_triage_path": str(triage_path),
        "protein_modeling_queue_path": str(queue_path),
        "protein_region_summary_path": str(region_path),
    }
