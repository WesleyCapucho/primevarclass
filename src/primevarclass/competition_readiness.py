from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


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
    if math.isnan(numeric):
        return default
    return numeric


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _summary(payload: dict) -> dict:
    return dict(payload.get("summary") or payload or {})


def _variant_parts(variant: Any, fallback_gene: Any = "") -> tuple[str, str]:
    text = str(variant or "").strip()
    if " " in text:
        gene, hgvs_p = text.split(" ", 1)
        return gene.strip() or str(fallback_gene or ""), hgvs_p.strip()
    return str(fallback_gene or "").strip(), text


def _normalise_variant_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    work = frame.copy()
    if "variant" in work.columns:
        parsed = work.apply(lambda row: _variant_parts(row.get("variant"), row.get("gene", "")), axis=1)
        work["gene"] = [item[0] for item in parsed]
        work["hgvs_p"] = [item[1] for item in parsed]
    elif "hgvs_p" in work.columns:
        work["gene"] = work.get("gene", "")
    else:
        work["gene"] = work.get("gene", "")
        work["hgvs_p"] = ""
    work["variant_key"] = work["gene"].astype(str).str.upper() + "|" + work["hgvs_p"].astype(str)
    return work


def _missing(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "None", "NA", "N/A"])


def _load_campaign_inputs(campaign_root: Path, prospective_manifest_path: str | None) -> dict[str, Any]:
    brca_dir = campaign_root / "brca_real_quick"
    locked_manifest = _read_json(campaign_root / "locked_calibration_holdout" / "locked_calibration_holdout_manifest.json")
    calibration_manifest = _read_json(campaign_root / "calibration_rescue" / "calibration_rescue_manifest.json")
    brca_error_manifest = _read_json(campaign_root / "brca1_lovd_error_analysis" / "brca1_lovd_error_analysis_manifest.json")
    alpha_manifest = _read_json(campaign_root / "alphamissense_subset_plan" / "alphamissense_subset_plan_manifest.json")
    alpha_enrichment_manifest = _read_json(campaign_root / "alphamissense_priority_enrichment" / "alphamissense_priority_enrichment_manifest.json")
    competition_manifest = _read_json(campaign_root / "competition_evidence_manifest.json")
    prospective_manifest = _read_json(
        prospective_manifest_path
        or Path("primevarclass_prospective_validation_closure_results") / "prospective_validation_closure_manifest.json"
    )
    return {
        "publication": _summary(_read_json(brca_dir / "publication_readiness_manifest.json")),
        "validation": _summary(_read_json(brca_dir / "study_validation_lock_manifest.json")),
        "claim": _summary(_read_json(brca_dir / "claim_strength_manifest.json")),
        "robustness": _summary(_read_json(brca_dir / "external_robustness_manifest.json")),
        "locked": locked_manifest,
        "calibration": calibration_manifest,
        "brca_error": brca_error_manifest,
        "alpha": alpha_manifest,
        "alpha_enrichment": alpha_enrichment_manifest,
        "competition": competition_manifest,
        "prospective": prospective_manifest,
        "locked_error_queue": _read_table(locked_manifest.get("error_queue_path")),
        "calibration_error_queue": _read_table(calibration_manifest.get("error_triage_queue_path")),
        "brca_selected_errors": _read_table(brca_error_manifest.get("selected_model_errors_path")),
        "prospective_queue": _read_table((prospective_manifest.get("functional_structural_confirmation_queue_path"))),
    }


def _build_priority_queue(inputs: dict[str, Any], max_rows: int) -> pd.DataFrame:
    locked = _normalise_variant_columns(inputs["locked_error_queue"])
    calibration = _normalise_variant_columns(inputs["calibration_error_queue"])
    brca_errors = _normalise_variant_columns(inputs["brca_selected_errors"])
    prospective_queue = _normalise_variant_columns(inputs["prospective_queue"])
    if locked.empty:
        return pd.DataFrame()
    work = locked.copy()
    calibration_keys = set(calibration.get("variant_key", pd.Series(dtype=str)).astype(str))
    brca_error_keys = set(brca_errors.get("variant_key", pd.Series(dtype=str)).astype(str))
    prospective_keys = set(prospective_queue.get("variant_key", pd.Series(dtype=str)).astype(str))
    work["in_diagnostic_rescue_queue"] = work["variant_key"].isin(calibration_keys)
    work["in_brca1_lovd_selected_errors"] = work["variant_key"].isin(brca_error_keys)
    work["in_functional_structural_queue"] = work["variant_key"].isin(prospective_keys)
    for column in ["feature_gnomad_af", "feature_mave_score", "prime_diff", "prime_ratio", "biochemical_severity_score"]:
        if column not in work.columns:
            work[column] = ""
    missing_gnomad = _missing(work["feature_gnomad_af"])
    missing_mave = _missing(work["feature_mave_score"])
    persistent = work.get("calibration_effect", pd.Series("", index=work.index)).astype(str).str.contains("persistent", case=False, na=False)
    weak_brca = work.get("cohort", pd.Series("", index=work.index)).astype(str).eq("bridges_like_external_validation_brca1")
    prime_weight = work["prime_diff"].map(lambda value: min(abs(_safe_float(value)) / 25.0, 0.4))
    biochemical_weight = work["biochemical_severity_score"].map(lambda value: min(_safe_float(value) / 20.0, 0.4))
    work["competition_priority_score"] = (
        work.get("priority_score", pd.Series(0, index=work.index)).map(_safe_float)
        + persistent.astype(int) * 0.6
        + weak_brca.astype(int) * 0.5
        + work["in_brca1_lovd_selected_errors"].astype(int) * 0.35
        + work["in_functional_structural_queue"].astype(int) * 0.5
        + missing_mave.astype(int) * 0.2
        + missing_gnomad.astype(int) * 0.15
        + prime_weight
        + biochemical_weight
    ).round(4)
    work["evidence_gap"] = "needs AlphaMissense/MAVE/structural confirmation"
    work.loc[~missing_mave & missing_gnomad, "evidence_gap"] = "needs population-frequency confirmation"
    work.loc[~missing_mave & ~missing_gnomad, "evidence_gap"] = "needs mechanistic review and threshold audit"
    work["recommended_next_action"] = "extract AlphaMissense subset; review BRCA curation; nominate for functional/structural confirmation"
    work.loc[work["in_functional_structural_queue"], "recommended_next_action"] = (
        "advance existing structural/quantum confirmation queue and link outcome to variant error analysis"
    )
    selected = [
        "competition_priority_score",
        "cohort",
        "variant",
        "gene",
        "hgvs_p",
        "label",
        "calibration_effect",
        "raw_score",
        "locked_calibrated_score",
        "baseline_score",
        "feature_gnomad_af",
        "feature_mave_score",
        "prime_diff",
        "prime_ratio",
        "biochemical_severity_score",
        "functional_domain",
        "protein_interface",
        "in_diagnostic_rescue_queue",
        "in_brca1_lovd_selected_errors",
        "in_functional_structural_queue",
        "evidence_gap",
        "recommended_next_action",
    ]
    available = [column for column in selected if column in work.columns]
    return work[available].sort_values(["competition_priority_score", "variant"], ascending=[False, True], kind="stable").head(max_rows)


def _build_strategy_matrix(inputs: dict[str, Any]) -> pd.DataFrame:
    locked = inputs["locked"]
    calibration = inputs["calibration"]
    brca_error = inputs["brca_error"]
    prospective_summary = _summary(inputs["prospective"])
    alpha = inputs["alpha"]
    alpha_enrichment = inputs["alpha_enrichment"]
    alpha_current = (
        f"{alpha_enrichment.get('target_count', 0)} priority targets; "
        f"{alpha_enrichment.get('coordinate_ready_percent', 0)}% coordinate-ready; "
        f"{alpha_enrichment.get('local_subset_coverage_percent', 0)}% local AlphaMissense coverage."
        if alpha_enrichment
        else f"AlphaMissense subset plan for {len(alpha.get('target_genes', []))} target genes."
    )
    alpha_status = alpha_enrichment.get("status") if alpha_enrichment else ("ready_to_stage" if alpha else "missing")
    rows = [
        {
            "front": "Locked external validation",
            "current_evidence": f"{locked.get('n_heldout_test_variants', 0)} held-out variants; safety {locked.get('raw_test_calibration_safety_rate_percent')}% -> {locked.get('locked_calibrated_test_safety_rate_percent')}%",
            "gap_to_close": "Repeat on full BRCA campaign and larger prospective release.",
            "action": "Freeze model, thresholds and split seed before any new labels are inspected.",
            "impact_for_prize": "Shows statistical discipline and protects against post-hoc tuning.",
            "status": locked.get("status", "missing"),
        },
        {
            "front": "Functional predictor expansion",
            "current_evidence": alpha_current,
            "gap_to_close": "Stage target-gene AlphaMissense rows and rerun benchmark with external functional predictor.",
            "action": "Use the generated priority target list and streaming extractor; do not load the full table into memory.",
            "impact_for_prize": "Adds independent functional evidence to weak BRCA1/LOVD calls.",
            "status": alpha_status,
        },
        {
            "front": "BRCA1 LOVD error mechanism",
            "current_evidence": f"{brca_error.get('selected_model_error_count', 0)} selected-model errors; gnomAD coverage {brca_error.get('feature_coverage', {}).get('gnomad_af_coverage_percent')}%; MaveDB coverage {brca_error.get('feature_coverage', {}).get('mavedb_score_coverage_percent')}%.",
            "gap_to_close": "Explain persistent false positives/negatives mechanistically.",
            "action": "Prioritize variants with high prime signal, missing MAVE and persistent locked-test errors.",
            "impact_for_prize": "Turns the weakest result into an innovation story and an experimental roadmap.",
            "status": "active_gap",
        },
        {
            "front": "Functional/structural confirmation",
            "current_evidence": f"{prospective_summary.get('functional_structural_confirmation_queue_count', 0)} queued targets; readiness {prospective_summary.get('prospective_validation_readiness_percent', 0)}%.",
            "gap_to_close": "External lab/partner assays remain required.",
            "action": "Use HDR/SGE, protein stability/localization and paired xTB/DFT/MD triage for top variants.",
            "impact_for_prize": "Connects algorithmic novelty to biological mechanism and translational value.",
            "status": "partner_lab_required",
        },
        {
            "front": "Prime-number differentiation",
            "current_evidence": f"Claim strength {inputs['claim'].get('overall_claim_strength_percent', 0)}%; prime-aware hybrid selected in current evidence package.",
            "gap_to_close": "Add final ablation narrative showing where prime features help and where they do not.",
            "action": "Report prime-only, non-prime baseline and hybrid deltas by cohort/gene.",
            "impact_for_prize": "Makes the core differentiator understandable without overstating causality.",
            "status": "needs_final_ablation_narrative",
        },
        {
            "front": "Reproducibility and public trust",
            "current_evidence": f"{inputs['competition'].get('passed_targeted_tests', 0)}/{inputs['competition'].get('total_targeted_tests', 0)} targeted tests passed; data artifacts in GitHub Release.",
            "gap_to_close": "Full suite should run in sharded CI rather than one local monolith.",
            "action": "Add CI shards for core, scientific modules, API, study benchmark and evidence package.",
            "impact_for_prize": "Makes the platform credible for judges, users and manuscript reviewers.",
            "status": "strong_with_ci_gap",
        },
    ]
    return pd.DataFrame(rows)


def _build_claims_boundary(inputs: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "claim": "PrimeVarClass is a reproducible BRCA-first platform using prime-aware features plus external biological predictors.",
                "status": "supported",
                "evidence": f"Claim strength {inputs['claim'].get('overall_claim_strength_percent', 0)}%; cohort independence {inputs['validation'].get('cohort_independence_percent', 0)}%.",
                "safe_wording": "Use as a research platform for variant-prioritization and hypothesis generation.",
            },
            {
                "claim": "Locked calibration improves safety on held-out external BRCA variants.",
                "status": "supported_with_scope_limit",
                "evidence": f"Locked holdout safety {inputs['locked'].get('raw_test_calibration_safety_rate_percent')}% -> {inputs['locked'].get('locked_calibrated_test_safety_rate_percent')}% on {inputs['locked'].get('n_heldout_test_variants')} variants.",
                "safe_wording": "Report as locked retrospective/external evidence, not as clinical deployment proof.",
            },
            {
                "claim": "The platform discovered definitive new biological mechanisms.",
                "status": "not_yet",
                "evidence": "Persistent-error queue and structural/functional plan exist, but experimental confirmation is not complete.",
                "safe_wording": "Say the platform nominates mechanistic hypotheses and prioritized variants for confirmation.",
            },
            {
                "claim": "The platform is clinically validated for diagnostic use.",
                "status": "not_yet",
                "evidence": "Prospective independent scoring and wet-lab/clinical confirmation remain open.",
                "safe_wording": "Keep all user-facing and manuscript language in research-use, non-diagnostic scope.",
            },
            {
                "claim": "The approach has high social and translational potential.",
                "status": "supported_with_caveat",
                "evidence": "External validation, prioritization queues and partner-lab handoff are in place.",
                "safe_wording": "Emphasize triage, education, reproducibility and acceleration of functional validation.",
            },
        ]
    )


def _readiness_scores(inputs: dict[str, Any]) -> dict[str, Any]:
    publication = _safe_float(inputs["publication"].get("overall_readiness_percent"))
    validation = _safe_float(inputs["validation"].get("overall_validation_lock_percent"))
    claim = _safe_float(inputs["claim"].get("overall_claim_strength_percent"))
    robustness = _safe_float(inputs["robustness"].get("overall_external_robustness_percent"))
    locked = _safe_float(inputs["locked"].get("locked_calibrated_test_safety_rate_percent"))
    tests = 100.0
    total_tests = _safe_int(inputs["competition"].get("total_targeted_tests"))
    if total_tests:
        tests = 100.0 * _safe_float(inputs["competition"].get("passed_targeted_tests")) / max(total_tests, 1)
    prospective = _safe_float(_summary(inputs["prospective"]).get("prospective_validation_readiness_percent"), 0)
    alpha_enrichment = inputs["alpha_enrichment"]
    alpha_plan = 85.0 if inputs["alpha"] else 0.0
    if alpha_enrichment:
        alpha_plan = max(
            alpha_plan,
            min(
                100.0,
                55.0
                + _safe_float(alpha_enrichment.get("coordinate_ready_percent")) * 0.25
                + _safe_float(alpha_enrichment.get("local_subset_coverage_percent")) * 0.20,
            ),
        )
    competition_readiness = min(
        96,
        round(
            publication * 0.12
            + validation * 0.14
            + claim * 0.12
            + robustness * 0.14
            + locked * 0.14
            + tests * 0.10
            + prospective * 0.14
            + alpha_plan * 0.10,
            1,
        ),
    )
    paper_readiness = min(94, round(competition_readiness - 2 if competition_readiness else 0, 1))
    web_scientific_readiness = min(92, round(competition_readiness - 4 if competition_readiness else 0, 1))
    return {
        "competition_readiness_percent": competition_readiness,
        "paper_readiness_percent": paper_readiness,
        "web_launch_scientific_readiness_percent": web_scientific_readiness,
        "ready_for_competition_dossier": competition_readiness >= 88,
        "ready_for_top_tier_submission_draft": paper_readiness >= 85,
        "ready_for_definitive_clinical_claims": False,
        "why_not_100_percent": "Full BRCA campaign, prospective independent validation and experimental functional/structural confirmation are still required.",
    }


def _build_paper_evidence_map(inputs: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_section": "Methods",
                "evidence_asset": "Frozen BRCA study, source configs, release manifests and locked calibration protocol",
                "status": "ready",
                "next_action": "Convert methods package and locked holdout protocol into LaTeX methods text.",
            },
            {
                "paper_section": "Results",
                "evidence_asset": "External BRCA metrics, claim-strength tables, calibration rescue and locked holdout",
                "status": "strong_but_needs_full_campaign",
                "next_action": "Rerun full BRCA campaign with bootstrap confidence intervals.",
            },
            {
                "paper_section": "Ablation",
                "evidence_asset": "Prime-only, external-only and hybrid comparison",
                "status": "partial",
                "next_action": "Write final prime-feature ablation narrative by cohort and gene.",
            },
            {
                "paper_section": "Mechanism",
                "evidence_asset": "BRCA1 LOVD persistent-error queue, structural/quantum queue and AlphaMissense plan",
                "status": "hypothesis_ready",
                "next_action": "Add AlphaMissense rows and run prioritized functional/structural confirmation.",
            },
            {
                "paper_section": "Limitations",
                "evidence_asset": "Claims boundary table and prospective validation protocol",
                "status": "ready",
                "next_action": "State non-diagnostic research scope and required prospective/experimental follow-up.",
            },
        ]
    )


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


def build_competition_readiness_package(
    campaign_root: str,
    output_dir: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
    max_priority_variants: int = 40,
) -> dict:
    campaign_path = Path(campaign_root).resolve()
    if not campaign_path.exists():
        raise FileNotFoundError(f"Campaign root not found: {campaign_path}")
    output_root = Path(output_dir).resolve() if output_dir else campaign_path / "competition_readiness"
    output_root.mkdir(parents=True, exist_ok=True)
    inputs = _load_campaign_inputs(campaign_path, prospective_validation_closure_manifest_path)
    priority_queue = _build_priority_queue(inputs, max_rows=max_priority_variants)
    strategy_matrix = _build_strategy_matrix(inputs)
    claims_boundary = _build_claims_boundary(inputs)
    paper_map = _build_paper_evidence_map(inputs)
    scores = _readiness_scores(inputs)
    manifest = {
        "generated_at": _now_utc(),
        "campaign_root": _display_path(campaign_path),
        **scores,
        "priority_variant_count": int(len(priority_queue)),
        "strategy_front_count": int(len(strategy_matrix)),
        "claims_boundary_count": int(len(claims_boundary)),
        "top_priority_variants": priority_queue.head(10).get("variant", pd.Series(dtype=str)).astype(str).tolist(),
        "source_evidence": {
            "locked_holdout_status": inputs["locked"].get("status"),
            "locked_holdout_test_variants": inputs["locked"].get("n_heldout_test_variants"),
            "locked_holdout_safety_percent": inputs["locked"].get("locked_calibrated_test_safety_rate_percent"),
            "diagnostic_calibration_safety_percent": inputs["calibration"].get("calibrated_safety_rate_percent"),
            "external_robustness_percent": inputs["robustness"].get("overall_external_robustness_percent"),
            "prospective_readiness_percent": _summary(inputs["prospective"]).get("prospective_validation_readiness_percent"),
            "alphamissense_target_genes": inputs["alpha"].get("target_genes", []),
            "alphamissense_priority_status": inputs["alpha_enrichment"].get("status"),
            "alphamissense_priority_coordinate_ready_percent": inputs["alpha_enrichment"].get("coordinate_ready_percent"),
            "alphamissense_priority_local_subset_coverage_percent": inputs["alpha_enrichment"].get("local_subset_coverage_percent"),
        },
    }

    queue_path = output_root / "competition_priority_variant_queue.csv"
    strategy_path = output_root / "competition_strategy_matrix.csv"
    claims_path = output_root / "scientific_claims_boundary.csv"
    paper_path = output_root / "paper_evidence_map.csv"
    manifest_path = output_root / "competition_readiness_manifest.json"
    markdown_path = output_root / "competition_readiness_report.md"
    html_path = output_root / "competition_readiness_report.html"
    priority_queue.to_csv(queue_path, index=False)
    strategy_matrix.to_csv(strategy_path, index=False)
    claims_boundary.to_csv(claims_path, index=False)
    paper_map.to_csv(paper_path, index=False)

    lines = [
        "# PrimeVarClass competition readiness package",
        "",
        f"- Generated at: `{manifest['generated_at']}`",
        f"- Competition readiness: `{scores['competition_readiness_percent']}%`",
        f"- Paper readiness: `{scores['paper_readiness_percent']}%`",
        f"- Web-launch scientific readiness: `{scores['web_launch_scientific_readiness_percent']}%`",
        f"- Ready for competition dossier: `{scores['ready_for_competition_dossier']}`",
        f"- Ready for top-tier submission draft: `{scores['ready_for_top_tier_submission_draft']}`",
        f"- Ready for definitive clinical claims: `{scores['ready_for_definitive_clinical_claims']}`",
        "",
        "## Strongest story",
        "",
        "- The project now has frozen BRCA external validation, cohort-independence evidence, locked calibration holdout support and a transparent weak-cohort error queue.",
        "- The prime-number component should be framed as a reproducible feature-engineering hypothesis that improves the hybrid methodology, not as a standalone biological proof.",
        "- The highest-impact next step is to enrich persistent BRCA1/LOVD errors with AlphaMissense and functional/structural confirmation.",
        "",
        "## Top priority variants",
        "",
    ]
    if priority_queue.empty:
        lines.append("- No priority variants were available from the locked holdout queue.")
    else:
        for row in priority_queue.head(10).to_dict(orient="records"):
            lines.append(
                f"- {row.get('variant')}: score={row.get('competition_priority_score')}, gap={row.get('evidence_gap')}, action={row.get('recommended_next_action')}"
            )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            f"- {scores['why_not_100_percent']}",
            "- Keep the language research-use and non-diagnostic until prospective independent validation and experimental confirmation are complete.",
            "",
            "## Output files",
            "",
            f"- Priority queue: `{_display_path(queue_path)}`",
            f"- Strategy matrix: `{_display_path(strategy_path)}`",
            f"- Claims boundary: `{_display_path(claims_path)}`",
            f"- Paper evidence map: `{_display_path(paper_path)}`",
        ]
    )
    markdown = "\n".join(lines).strip() + "\n"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown, "PrimeVarClass Competition Readiness"), encoding="utf-8")
    manifest.update(
        {
            "priority_queue_path": _display_path(queue_path),
            "strategy_matrix_path": _display_path(strategy_path),
            "claims_boundary_path": _display_path(claims_path),
            "paper_evidence_map_path": _display_path(paper_path),
            "markdown_path": _display_path(markdown_path),
            "html_path": _display_path(html_path),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "competition_readiness": manifest,
        "competition_readiness_manifest_path": str(manifest_path),
        "competition_readiness_report_markdown_path": str(markdown_path),
        "competition_readiness_report_html_path": str(html_path),
        "competition_priority_variant_queue_path": str(queue_path),
        "competition_strategy_matrix_path": str(strategy_path),
        "scientific_claims_boundary_path": str(claims_path),
        "paper_evidence_map_path": str(paper_path),
    }


def export_competition_readiness_package(
    campaign_root: str,
    output_dir: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
    max_priority_variants: int = 40,
) -> dict:
    return build_competition_readiness_package(
        campaign_root=campaign_root,
        output_dir=output_dir,
        prospective_validation_closure_manifest_path=prospective_validation_closure_manifest_path,
        max_priority_variants=max_priority_variants,
    )
