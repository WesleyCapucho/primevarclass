from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BASE_STUDY_CONFIG = Path("configs/jovem_cientista_brca_evidence_quick.toml")
BASE_SOURCE_CONFIGS = {
    "public_brca_training": Path("configs/public_brca_real.toml"),
    "clinvar_expert_external_validation_brca1": Path("configs/public_brca_external_real_clinvar_expert_brca1.toml"),
    "clinvar_expert_external_validation_brca2": Path("configs/public_brca_external_real_clinvar_expert_brca2.toml"),
    "bridges_like_external_validation_brca1": Path("configs/public_brca_external_real_brca1.toml"),
    "bridges_like_external_validation_brca2": Path("configs/public_brca_external_real_brca2.toml"),
}
ALPHAMISSENSE_LOCAL_SUBSET = Path("data/raw/alphamissense/target_gene_alphamissense.tsv")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: str | Path | None) -> dict:
    if not path:
        return {}
    resolved = Path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def _read_table(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    resolved = Path(path)
    if not resolved.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(resolved, sep="\t" if resolved.suffix.lower() == ".tsv" else ",")
    except Exception:
        return pd.DataFrame()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    return default if math.isnan(numeric) or math.isinf(numeric) else numeric


def _alpha_source_block(alpha_subset_path: Path = ALPHAMISSENSE_LOCAL_SUBSET) -> str:
    return "\n".join(
        [
            "",
            "[[sources]]",
            'name = "alphamissense_priority_variant_scores"',
            'kind = "annotation"',
            'type = "file"',
            'format = "tsv"',
            f'path = "{_display_path(alpha_subset_path)}"',
            'preset = "alphamissense_table"',
            'join_on = ["gene", "hgvs_p"]',
            'gene_allowlist = ["BRCA1", "BRCA2"]',
            'release_version = "AlphaMissense_v2023_priority_sparse_50_variant_overlay"',
            "",
        ]
    )


def _write_alpha_source_configs(output_root: Path) -> dict[str, str]:
    config_dir = output_root / "alphamissense_sparse_source_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    alpha_block = _alpha_source_block()
    for cohort_name, source_path in BASE_SOURCE_CONFIGS.items():
        base_text = source_path.read_text(encoding="utf-8")
        target_path = config_dir / f"{cohort_name}_alphamissense_sparse.toml"
        target_path.write_text(base_text.rstrip() + "\n" + alpha_block, encoding="utf-8")
        written[cohort_name] = _display_path(target_path)
    return written


def _write_alpha_study_config(output_root: Path, source_configs: dict[str, str]) -> str:
    study_path = output_root / "jovem_cientista_brca_evidence_quick_alphamissense_sparse.toml"
    lines = [
        "[study]",
        'name = "Jovem Cientista BRCA Real Evidence Quick Pass AlphaMissense Sparse Overlay"',
        'mode = "hybrid"',
        "high_confidence_only = false",
        "keep_metadata = true",
        'primary_metric = "auc_roc"',
        'baseline_experiment = "external_predictors_only"',
        "n_bootstrap = 20",
        'model_families = ["logistic_regression"]',
        "",
    ]
    roles = {
        "public_brca_training": "train",
        "clinvar_expert_external_validation_brca1": "external_test",
        "clinvar_expert_external_validation_brca2": "external_test",
        "bridges_like_external_validation_brca1": "external_test",
        "bridges_like_external_validation_brca2": "external_test",
    }
    for cohort_name, role in roles.items():
        lines.extend(
            [
                "[[cohorts]]",
                f'name = "{cohort_name}"',
                f'role = "{role}"',
                f'source_config = "{source_configs[cohort_name]}"',
                "",
            ]
        )
    study_path.write_text("\n".join(lines), encoding="utf-8")
    return _display_path(study_path)


def _build_alpha_benchmark_plan(alpha_manifest: dict, study_config_path: str) -> pd.DataFrame:
    benchmark = alpha_manifest.get("priority_benchmark", {}) or {}
    return pd.DataFrame(
        [
            {
                "step_id": "A1",
                "step": "Priority AlphaMissense overlay already extracted and scored",
                "status": "complete" if alpha_manifest.get("status") == "ready_to_benchmark" else "partial",
                "evidence": f"{alpha_manifest.get('matched_alphamissense_count', 0)}/{alpha_manifest.get('target_count', 0)} priority variants; AUC-ROC={benchmark.get('best_auc_roc')}",
                "claim_unlocked": "Functional evidence on priority error queue",
                "remaining_risk": "Not yet full-cohort AlphaMissense validation",
            },
            {
                "step_id": "A2",
                "step": "Sparse BRCA study config with AlphaMissense annotation source",
                "status": "staged",
                "evidence": study_config_path,
                "claim_unlocked": "Runnable benchmark path without changing frozen original configs",
                "remaining_risk": "Sparse 50-variant overlay may not affect every cohort row",
            },
            {
                "step_id": "A3",
                "step": "Full BRCA1/BRCA2 AlphaMissense target-gene subset",
                "status": "required_next",
                "evidence": "Use official AlphaMissense amino-acid substitution table and BRCA1/BRCA2 protein targets; stream only matching rows",
                "claim_unlocked": "Full-cohort functional-predictor validation",
                "remaining_risk": "Large official file requires controlled streaming or CI/HPC execution",
            },
            {
                "step_id": "A4",
                "step": "Frozen comparison against current quick pass",
                "status": "required_next",
                "evidence": "Compare external AUC-ROC/AUC-PR/MCC, calibration safety and BRCA1 LOVD errors",
                "claim_unlocked": "Defensible statement about whether AlphaMissense improves weak external cohort behavior",
                "remaining_risk": "Must preserve non-diagnostic, retrospective research-use framing",
            },
        ]
    )


def _build_prime_figure_ready(ablation_matrix: pd.DataFrame) -> pd.DataFrame:
    if ablation_matrix.empty:
        return pd.DataFrame()
    work = ablation_matrix.copy()
    order = {
        "external_predictors_only": 1,
        "biochemical_only": 2,
        "prime_only": 3,
        "hybrid": 4,
        "hybrid_plus_conservation": 5,
        "hybrid_plus_conservation_structure": 6,
        "hybrid_plus_external": 7,
        "gene_balanced_specialist": 8,
    }
    work["visual_order"] = work["feature_set"].map(order).fillna(99).astype(int)
    work["contains_prime_features"] = work["feature_set"].astype(str).str.contains("prime|hybrid", case=False, regex=True)
    work["recommended_plot_label"] = work["feature_set"].astype(str).str.replace("_", " ", regex=False).str.title()
    external_baseline = _safe_float(
        work.loc[work["feature_set"].astype(str).eq("external_predictors_only"), "training_auc_roc"].max(),
        0.0,
    )
    biochemical_baseline = _safe_float(
        work.loc[work["feature_set"].astype(str).eq("biochemical_only"), "training_auc_roc"].max(),
        0.0,
    )
    work["training_auc_delta_vs_external_only"] = (pd.to_numeric(work["training_auc_roc"], errors="coerce") - external_baseline).round(4)
    work["training_auc_delta_vs_biochemical_only"] = (pd.to_numeric(work["training_auc_roc"], errors="coerce") - biochemical_baseline).round(4)
    work["jury_message"] = work.apply(_prime_jury_message, axis=1)
    return work.sort_values("visual_order").reset_index(drop=True)


def _prime_jury_message(row: pd.Series) -> str:
    feature_set = str(row.get("feature_set") or "")
    if feature_set == "prime_only":
        return "Prime-only is the originality control: useful signal exists, but it is not overclaimed alone."
    if feature_set == "hybrid":
        return "Hybrid shows prime encoding gains credibility when fused with biochemical context."
    if feature_set == "hybrid_plus_external":
        return "Best final story: original prime-aware features plus independent public biological evidence."
    if feature_set == "external_predictors_only":
        return "External-only comparator prevents the project from being judged as merely repackaging public predictors."
    if feature_set == "biochemical_only":
        return "Biochemical-only baseline is the fair non-prime biological control."
    return "Supportive control for robustness and presentation."


def _build_mechanistic_protocols(discordance: pd.DataFrame) -> pd.DataFrame:
    if discordance.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for row in discordance.to_dict(orient="records"):
        gene = str(row.get("gene") or "").upper()
        variant = str(row.get("variant") or "")
        rows.append(
            {
                "variant": variant,
                "gene": gene,
                "hypothesis_priority": row.get("hypothesis_priority"),
                "alignment": row.get("alphamissense_label_alignment"),
                "primevarclass_locked_score": row.get("locked_calibrated_score"),
                "alphamissense_score": row.get("feature_alphamissense_pathogenicity"),
                "alphamissense_class": row.get("feature_alphamissense_class"),
                "primary_hypothesis": _primary_hypothesis(row),
                "recommended_assay": _recommended_assay(gene),
                "required_controls": _required_controls(gene),
                "functional_readout": _functional_readout(gene),
                "structural_workup": "AlphaFold local environment review; map residue neighborhood; compare with MAVE/gnomAD when available; nominate xTB/DFT only as mechanistic support.",
                "go_no_go_rule": "Advance only if public label provenance, AlphaMissense, population frequency and assay feasibility can be reconciled without post-hoc score tuning.",
                "submission_use": "Use as mechanistic hypothesis and future experimental validation plan, not as confirmed discovery.",
            }
        )
    return pd.DataFrame(rows)


def _primary_hypothesis(row: dict[str, Any]) -> str:
    alignment = str(row.get("alphamissense_label_alignment") or "")
    if alignment.startswith("discordant_am_pathogenic"):
        return "Protein-level damage signal conflicts with benign label; investigate curation, isoform, low-frequency evidence and local structural disruption."
    if alignment.startswith("discordant_am_benign"):
        return "Clinical/pathogenic label conflicts with benign protein-level predictor; investigate label provenance, nonlocal BRCA mechanism or missing assay context."
    if alignment == "ambiguous_functional_signal":
        return "Functional predictor is uncertain; variant is useful as a calibration and assay-prioritization stress test."
    return "Prioritized for orthogonal mechanistic review."


def _recommended_assay(gene: str) -> str:
    if gene == "BRCA1":
        return "Saturation genome editing or HDR reporter; protein stability/localization; BRCA1 interaction-domain review."
    if gene == "BRCA2":
        return "HDR/RAD51 functional readout; conservation review; BRCA2 domain-context interpretation."
    return "Matched gene-specific functional assay plus protein stability readout."


def _required_controls(gene: str) -> str:
    if gene in {"BRCA1", "BRCA2"}:
        return "Known benign control, known pathogenic control, synonymous/neutral construct, assay batch replicate, blinded score bin."
    return "Known benign and pathogenic controls, neutral construct, biological replicate, blinded score bin."


def _functional_readout(gene: str) -> str:
    if gene == "BRCA1":
        return "HDR efficiency, cell viability under DNA damage, protein abundance/localization and interaction-context consistency."
    if gene == "BRCA2":
        return "HDR efficiency, RAD51-related repair context, protein-domain consistency and variant-specific rescue behavior."
    return "Gene-specific repair/function readout and protein abundance/localization."


def _build_submission_checklist(jury_manifest: dict, closure_readiness: float) -> pd.DataFrame:
    rows = [
        ("scientific_validation", "Retrospective BRCA external validation and locked calibration", "ready", "competition_evidence_summary.md"),
        ("functional_overlay", "AlphaMissense priority overlay with discordance hypotheses", "ready", "alphamissense_priority_enrichment_manifest.json"),
        ("full_alpha_benchmark", "Full BRCA AlphaMissense-enriched benchmark", "staged_not_complete", "full_brca_alphamissense_benchmark_plan.csv"),
        ("prime_originality", "Prime-number ablation figure and safe narrative", "ready_for_manuscript", "prime_ablation_figure_ready.csv"),
        ("mechanistic_validation", "Functional/structural protocols for top discordant variants", "protocol_ready", "mechanistic_validation_protocols.csv"),
        ("public_good", "Common-good impact narrative and responsible-AI boundary", "ready_for_submission", "public_good_impact_narrative.md"),
        ("product_demo", "Bilingual multiuser public demo and feedback workflow", "needs_final_ui_smoke", "launch readiness and UI smoke test"),
        ("paper", "Portuguese 20-25 page submission manuscript", "needs_draft", "future LaTeX/PJC manuscript package"),
    ]
    return pd.DataFrame(
        [
            {
                "item_id": item_id,
                "submission_item": label,
                "status": status,
                "evidence_or_next_file": evidence,
                "blocks_first_place_if_missing": status in {"staged_not_complete", "needs_final_ui_smoke", "needs_draft"},
                "closure_readiness_percent": closure_readiness,
                "current_jury_points": jury_manifest.get("estimated_jury_points"),
            }
            for item_id, label, status, evidence in rows
        ]
    )


def _closure_readiness(jury_manifest: dict, alpha_manifest: dict, protocols: pd.DataFrame, figure_ready: pd.DataFrame) -> float:
    jury_points = _safe_float(jury_manifest.get("estimated_jury_points"))
    alpha_bonus = 1.2 if (alpha_manifest.get("priority_benchmark") or {}).get("status") == "priority_overlay_evaluated" else 0.0
    protocol_bonus = 1.0 if not protocols.empty else 0.0
    figure_bonus = 0.8 if not figure_ready.empty else 0.0
    return round(min(97.0, jury_points + alpha_bonus + protocol_bonus + figure_bonus), 2)


def _render_report(
    closure_readiness: float,
    alpha_plan: pd.DataFrame,
    checklist: pd.DataFrame,
    protocols: pd.DataFrame,
) -> str:
    open_blockers = int(checklist["blocks_first_place_if_missing"].sum()) if not checklist.empty else 0
    lines = [
        "# PrimeVarClass competition closure package",
        "",
        f"- Generated at: `{_now_utc()}`",
        f"- Closure readiness estimate: `{closure_readiness}%`",
        f"- Remaining first-place blockers: `{open_blockers}`",
        "",
        "## What this package closes",
        "",
        "- Converts the jury audit into concrete closure artifacts.",
        "- Stages an AlphaMissense-enriched BRCA benchmark config without modifying frozen original configs.",
        "- Produces a figure-ready prime-number ablation table and safe narrative.",
        "- Turns AlphaMissense discordances into functional/structural validation protocols.",
        "- Builds a submission checklist for the Prêmio Jovem Cientista dossier.",
        "",
        "## AlphaMissense benchmark plan",
        "",
    ]
    for row in alpha_plan.to_dict(orient="records"):
        lines.append(f"- {row['step_id']} ({row['status']}): {row['step']} -> {row['claim_unlocked']}")
    lines.extend(["", "## Mechanistic protocols", ""])
    if protocols.empty:
        lines.append("- No protocols were generated because no discordance table was available.")
    else:
        for row in protocols.head(4).to_dict(orient="records"):
            lines.append(f"- {row['variant']}: {row['recommended_assay']}")
    lines.extend(
        [
            "",
            "## Conservative claim boundary",
            "",
            "This package strengthens competition readiness, but it does not convert the platform into a clinical diagnostic tool. Full prospective validation and experimental confirmation remain required before definitive clinical claims.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_markdown_html(markdown: str, title: str) -> str:
    blocks: list[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("- "):
            blocks.append("<ul>" + "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines()) + "</ul>")
        else:
            blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;color:#132238;background:#f8fbff}"
        "h1{color:#102a43}h2{color:#2155d9}ul{background:#fff;border:1px solid #d9e2ec;border-radius:14px;padding:16px 24px}</style>"
        "</head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def build_competition_closure_package(campaign_root: str, output_dir: str | None = None) -> dict:
    campaign_path = Path(campaign_root).resolve()
    if not campaign_path.exists():
        raise FileNotFoundError(f"Campaign root not found: {campaign_path}")
    output_root = Path(output_dir).resolve() if output_dir else campaign_path / "competition_closure"
    output_root.mkdir(parents=True, exist_ok=True)

    jury_manifest = _read_json(campaign_path / "competition_jury_audit" / "competition_jury_audit_manifest.json")
    alpha_manifest = _read_json(campaign_path / "alphamissense_priority_enrichment" / "alphamissense_priority_enrichment_manifest.json")
    ablation_matrix = _read_table(campaign_path / "competition_jury_audit" / "prime_ablation_matrix.csv")
    discordance = _read_table(campaign_path / "alphamissense_priority_enrichment" / "alphamissense_priority_discordance_hypotheses.csv")

    source_configs = _write_alpha_source_configs(output_root)
    study_config_path = _write_alpha_study_config(output_root, source_configs)
    alpha_plan = _build_alpha_benchmark_plan(alpha_manifest, study_config_path)
    figure_ready = _build_prime_figure_ready(ablation_matrix)
    protocols = _build_mechanistic_protocols(discordance)
    closure_readiness = _closure_readiness(jury_manifest, alpha_manifest, protocols, figure_ready)
    checklist = _build_submission_checklist(jury_manifest, closure_readiness)
    report = _render_report(closure_readiness, alpha_plan, checklist, protocols)

    alpha_plan_path = output_root / "full_brca_alphamissense_benchmark_plan.csv"
    figure_ready_path = output_root / "prime_ablation_figure_ready.csv"
    protocols_path = output_root / "mechanistic_validation_protocols.csv"
    checklist_path = output_root / "submission_readiness_checklist.csv"
    report_path = output_root / "competition_closure_report.md"
    html_path = output_root / "competition_closure_report.html"
    manifest_path = output_root / "competition_closure_manifest.json"

    alpha_plan.to_csv(alpha_plan_path, index=False)
    figure_ready.to_csv(figure_ready_path, index=False)
    protocols.to_csv(protocols_path, index=False)
    checklist.to_csv(checklist_path, index=False)
    report_path.write_text(report, encoding="utf-8")
    html_path.write_text(_render_markdown_html(report, "PrimeVarClass Competition Closure"), encoding="utf-8")

    manifest = {
        "generated_at": _now_utc(),
        "campaign_root": _display_path(campaign_path),
        "closure_readiness_percent": closure_readiness,
        "starting_jury_points": jury_manifest.get("estimated_jury_points"),
        "remaining_first_place_blockers": int(checklist["blocks_first_place_if_missing"].sum()) if not checklist.empty else 0,
        "alphamissense_sparse_study_config_path": study_config_path,
        "alphamissense_sparse_source_config_paths": source_configs,
        "alpha_plan_status_counts": alpha_plan["status"].value_counts().to_dict() if not alpha_plan.empty else {},
        "prime_figure_rows": int(len(figure_ready)),
        "mechanistic_protocol_count": int(len(protocols)),
        "submission_checklist_items": int(len(checklist)),
        "claim_boundary": "Research-use prioritization and hypothesis generation only; not a clinical diagnostic claim.",
        "full_brca_alphamissense_benchmark_plan_path": _display_path(alpha_plan_path),
        "prime_ablation_figure_ready_path": _display_path(figure_ready_path),
        "mechanistic_validation_protocols_path": _display_path(protocols_path),
        "submission_readiness_checklist_path": _display_path(checklist_path),
        "markdown_path": _display_path(report_path),
        "html_path": _display_path(html_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "competition_closure": manifest,
        "competition_closure_manifest_path": str(manifest_path),
        "full_brca_alphamissense_benchmark_plan_path": str(alpha_plan_path),
        "prime_ablation_figure_ready_path": str(figure_ready_path),
        "mechanistic_validation_protocols_path": str(protocols_path),
        "submission_readiness_checklist_path": str(checklist_path),
        "competition_closure_report_markdown_path": str(report_path),
        "competition_closure_report_html_path": str(html_path),
    }


def export_competition_closure_package(campaign_root: str, output_dir: str | None = None) -> dict:
    return build_competition_closure_package(campaign_root=campaign_root, output_dir=output_dir)
