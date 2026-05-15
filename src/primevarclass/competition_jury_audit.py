from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OFFICIAL_PJC_SOURCE_URL = "https://jovemcientista.cnpq.br/projeto/premio-jovem-cientista"
OFFICIAL_PJC_EDITAL_URL = "https://midia.frm.org.br/drupal/public/media/documento/2026-03/SEI_CNPq%20-%202625129%20-%20Edital_0.pdf"
OFFICIAL_RUBRIC = [
    {
        "criterion": "Scientific merit and relevance",
        "official_points": 30,
        "judge_question": "Does the work advance Brazilian science and technology with credible validation?",
    },
    {
        "criterion": "Practical application and final results",
        "official_points": 30,
        "judge_question": "Does the work solve a concrete theme-related problem with usable final results?",
    },
    {
        "criterion": "Originality and contribution to knowledge",
        "official_points": 25,
        "judge_question": "Is the core idea original, defensible and useful beyond a demo?",
    },
    {
        "criterion": "Text, clarity and presentation quality",
        "official_points": 15,
        "judge_question": "Can a multidisciplinary jury understand the problem, method, evidence and impact quickly?",
    },
]


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _score_value(scorecard: pd.DataFrame, area: str, default: float = 0.0) -> float:
    if scorecard.empty or "area" not in scorecard.columns:
        return default
    match = scorecard[scorecard["area"].astype(str).eq(area)]
    if match.empty:
        return default
    return _safe_float(match.iloc[0].get("score_percent"), default)


def _weighted_percent(items: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in items)
    if total_weight <= 0:
        return 0.0
    return max(0.0, min(100.0, sum(max(0.0, min(100.0, value)) * weight for value, weight in items) / total_weight))


def _load_campaign_inputs(campaign_root: Path) -> dict[str, Any]:
    evidence_manifest = _read_json(campaign_root / "competition_evidence_manifest.json")
    readiness = _read_json(campaign_root / "competition_readiness" / "competition_readiness_manifest.json")
    alpha = _read_json(campaign_root / "alphamissense_priority_enrichment" / "alphamissense_priority_enrichment_manifest.json")
    validation = _read_json(campaign_root / "brca_real_quick" / "study_validation_lock_manifest.json")
    claim = _read_json(campaign_root / "brca_real_quick" / "claim_strength_manifest.json")
    publication = _read_json(campaign_root / "brca_real_quick" / "publication_readiness_manifest.json")
    robustness = _read_json(campaign_root / "brca_real_quick" / "external_robustness_manifest.json")
    launch = _read_json(Path("primevarclass_launch_readiness_results") / "launch_readiness_manifest.json")
    prospective = _read_json(Path("primevarclass_prospective_validation_closure_results") / "prospective_validation_closure_manifest.json")
    return {
        "evidence_manifest": evidence_manifest,
        "readiness": readiness,
        "alpha": alpha,
        "validation": validation.get("summary", validation),
        "claim": claim.get("summary", claim),
        "publication": publication.get("summary", publication),
        "robustness": robustness.get("summary", robustness),
        "launch": launch.get("summary", launch),
        "prospective": prospective.get("summary", prospective),
        "scorecard": _read_table(campaign_root / "competition_evidence_scorecard.csv"),
        "external_best": _read_table(campaign_root / "competition_external_best_metrics.csv"),
        "training_metrics": _read_table(campaign_root / "brca_real_quick" / "study_training_metrics.csv"),
        "external_metrics": _read_table(campaign_root / "brca_real_quick" / "study_external_evaluation.csv"),
        "alpha_discordance": _read_table(
            campaign_root / "alphamissense_priority_enrichment" / "alphamissense_priority_discordance_hypotheses.csv"
        ),
        "alpha_metrics": _read_table(
            campaign_root / "alphamissense_priority_enrichment" / "alphamissense_priority_benchmark_metrics.csv"
        ),
        "strategy_exists": (campaign_root / "competition_first_place_strategy.md").exists(),
        "summary_exists": (campaign_root / "competition_evidence_summary.md").exists(),
    }


def _build_jury_scorecard(inputs: dict[str, Any]) -> pd.DataFrame:
    scorecard = inputs["scorecard"]
    readiness = inputs["readiness"]
    launch = inputs["launch"]
    alpha = inputs["alpha"]
    alpha_benchmark = alpha.get("priority_benchmark", {}) or {}
    tests = 100.0
    total_tests = _safe_int(inputs["evidence_manifest"].get("total_targeted_tests"))
    if total_tests:
        tests = 100.0 * _safe_float(inputs["evidence_manifest"].get("passed_targeted_tests")) / max(total_tests, 1)

    scientific_percent = _weighted_percent(
        [
            (_safe_float(readiness.get("paper_readiness_percent")), 0.24),
            (_score_value(scorecard, "Validation lock"), 0.20),
            (_score_value(scorecard, "AlphaMissense priority benchmark"), 0.18),
            (_score_value(scorecard, "External robustness"), 0.18),
            (tests, 0.20),
        ]
    )
    application_percent = _weighted_percent(
        [
            (_safe_float(readiness.get("competition_readiness_percent")), 0.26),
            (_safe_float(readiness.get("web_launch_scientific_readiness_percent")), 0.22),
            (_score_value(scorecard, "Calibration rescue"), 0.16),
            (_score_value(scorecard, "Locked calibration holdout"), 0.16),
            (_safe_float(inputs["prospective"].get("prospective_validation_readiness_percent"), 88.0), 0.10),
            (100.0 if inputs["strategy_exists"] else 0.0, 0.10),
        ]
    )
    originality_percent = _weighted_percent(
        [
            (_score_value(scorecard, "Baseline and ablation"), 0.30),
            (_score_value(scorecard, "Claim strength"), 0.25),
            (_safe_float(alpha_benchmark.get("functional_support_rate_percent")), 0.20),
            (100.0 if not inputs["alpha_discordance"].empty else 0.0, 0.15),
            (_score_value(scorecard, "AlphaMissense priority benchmark"), 0.10),
        ]
    )
    clarity_percent = _weighted_percent(
        [
            (100.0 if inputs["strategy_exists"] else 0.0, 0.22),
            (100.0 if inputs["summary_exists"] else 0.0, 0.22),
            (tests, 0.18),
            (_safe_float(inputs["publication"].get("overall_readiness_percent")), 0.18),
            (_safe_float(inputs["launch"].get("documentation_readiness_percent"), 82.0), 0.10),
            (_safe_float(inputs["launch"].get("web_launch_percent"), 78.0), 0.10),
        ]
    )

    percents = {
        "Scientific merit and relevance": scientific_percent,
        "Practical application and final results": application_percent,
        "Originality and contribution to knowledge": originality_percent,
        "Text, clarity and presentation quality": clarity_percent,
    }
    rows = []
    for item in OFFICIAL_RUBRIC:
        percent = percents[item["criterion"]]
        awarded = round(item["official_points"] * percent / 100.0, 2)
        rows.append(
            {
                **item,
                "evidence_percent": round(percent, 1),
                "estimated_points": awarded,
                "remaining_points": round(item["official_points"] - awarded, 2),
                "jury_verdict": _verdict(percent),
            }
        )
    return pd.DataFrame(rows)


def _verdict(percent: float) -> str:
    if percent >= 94:
        return "excellent"
    if percent >= 88:
        return "competitive_but_attackable"
    if percent >= 80:
        return "solid_with_visible_gaps"
    return "major_gap"


def _build_risk_register(inputs: dict[str, Any]) -> pd.DataFrame:
    alpha_benchmark = (inputs["alpha"].get("priority_benchmark") or {})
    risks = [
        {
            "risk_id": "R1",
            "criterion": "Scientific merit and relevance",
            "risk": "Priority AlphaMissense overlay is strong, but the full BRCA benchmark has not yet been rerun with AlphaMissense as a cohort-level feature.",
            "severity": "high",
            "point_loss_if_unresolved": 4.0,
            "evidence_now": f"Priority overlay AUC-ROC={alpha_benchmark.get('best_auc_roc')}; local coverage={inputs['alpha'].get('local_subset_coverage_percent')}%.",
            "closure_action": "Run or stage a full AlphaMissense-enriched BRCA benchmark and compare against the frozen quick pass.",
        },
        {
            "risk_id": "R2",
            "criterion": "Originality and contribution to knowledge",
            "risk": "Prime-number contribution can be misunderstood as decorative unless the ablation narrative is explicit and visual.",
            "severity": "high",
            "point_loss_if_unresolved": 3.5,
            "evidence_now": f"Baseline and ablation score={_score_value(inputs['scorecard'], 'Baseline and ablation')}%.",
            "closure_action": "Include prime-only, biochemical-only, external-only, hybrid and hybrid-plus-external comparisons in the application.",
        },
        {
            "risk_id": "R3",
            "criterion": "Practical application and final results",
            "risk": "The platform is not yet a polished public multiuser release with a submission-grade demo flow.",
            "severity": "high",
            "point_loss_if_unresolved": 3.0,
            "evidence_now": f"Web-launch scientific readiness={inputs['readiness'].get('web_launch_scientific_readiness_percent')}%.",
            "closure_action": "Finalize the clean module-by-module interface, registration flow, bilingual UX, feedback area and exportable report.",
        },
        {
            "risk_id": "R4",
            "criterion": "Scientific merit and relevance",
            "risk": "Prospective independent validation and wet-lab functional or structural confirmation remain future work.",
            "severity": "high",
            "point_loss_if_unresolved": 4.5,
            "evidence_now": f"Prospective readiness={inputs['prospective'].get('prospective_validation_readiness_percent', 'not_available')}%.",
            "closure_action": "Frame this honestly as research-use evidence and attach a blinded prospective protocol with top targets.",
        },
        {
            "risk_id": "R5",
            "criterion": "Text, clarity and presentation quality",
            "risk": "The competition requires a concise 20-25 page Portuguese scientific work for undergraduate submission.",
            "severity": "medium",
            "point_loss_if_unresolved": 2.5,
            "evidence_now": "Evidence package exists, but final Portuguese submission manuscript is not yet assembled.",
            "closure_action": "Convert evidence assets into a 20-25 page paper with figures, limitations and a non-diagnostic claim boundary.",
        },
        {
            "risk_id": "R6",
            "criterion": "Practical application and final results",
            "risk": "A judge may challenge ethical AI, clinical safety and overclaiming if boundaries are not visible.",
            "severity": "medium",
            "point_loss_if_unresolved": 2.0,
            "evidence_now": "Claims boundary exists in competition readiness package.",
            "closure_action": "Put research-use-only, privacy, uncertainty and human-review safeguards in the demo and paper abstract.",
        },
    ]
    return pd.DataFrame(risks)


def _build_action_plan(risk_register: pd.DataFrame) -> pd.DataFrame:
    rows = []
    priority_order = {"high": 0, "medium": 1, "low": 2}
    for index, row in risk_register.sort_values(
        by=["severity", "point_loss_if_unresolved"],
        key=lambda series: series.map(priority_order).fillna(series) if series.name == "severity" else series,
        ascending=[True, False],
    ).reset_index(drop=True).iterrows():
        rows.append(
            {
                "rank": index + 1,
                "risk_id": row["risk_id"],
                "action": row["closure_action"],
                "owner_mode": "PrimeVarClass development",
                "expected_jury_gain_points": row["point_loss_if_unresolved"],
                "acceptance_evidence": _acceptance_evidence(row["risk_id"]),
            }
        )
    return pd.DataFrame(rows)


def _acceptance_evidence(risk_id: str) -> str:
    mapping = {
        "R1": "AlphaMissense-enriched BRCA comparison table or explicit staged benchmark plan with runnable configs.",
        "R2": "Prime ablation matrix and narrative included in final paper figures.",
        "R3": "Public demo smoke test, registration path and bilingual interface checklist.",
        "R4": "Blinded prospective protocol plus mechanistic target queue.",
        "R5": "Portuguese 20-25 page manuscript draft following PJC structure.",
        "R6": "Claims boundary and responsible-AI safeguards visible in paper and UI.",
    }
    return mapping.get(str(risk_id), "Documented closure evidence.")


def _build_ablation_matrix(inputs: dict[str, Any]) -> pd.DataFrame:
    training = inputs["training_metrics"].copy()
    external = inputs["external_metrics"].copy()
    if training.empty:
        return pd.DataFrame()
    rows = []
    external_combined = external[external.get("evaluation_group", pd.Series(dtype=str)).astype(str).eq("combined")].copy() if not external.empty else pd.DataFrame()
    if external_combined.empty:
        external_combined = external
    for feature_set, group in training.groupby("feature_set", sort=True):
        best_train = group.sort_values(["auc_roc", "auc_pr"], ascending=[False, False], kind="stable").iloc[0]
        external_group = (
            external_combined[external_combined["feature_set"].astype(str).eq(str(feature_set))]
            if not external_combined.empty and "feature_set" in external_combined.columns
            else pd.DataFrame()
        )
        rows.append(
            {
                "feature_set": feature_set,
                "best_training_experiment": best_train.get("experiment"),
                "training_auc_roc": round(_safe_float(best_train.get("auc_roc")), 4),
                "training_auc_pr": round(_safe_float(best_train.get("auc_pr")), 4),
                "training_mcc": round(_safe_float(best_train.get("mcc")), 4),
                "best_external_auc_roc": round(_safe_float(external_group["auc_roc"].max()) if not external_group.empty else 0.0, 4),
                "mean_external_auc_roc": round(_safe_float(external_group["auc_roc"].mean()) if not external_group.empty else 0.0, 4),
                "external_cohort_count": int(external_group["cohort"].nunique()) if not external_group.empty and "cohort" in external_group.columns else 0,
                "jury_interpretation": _ablation_interpretation(str(feature_set)),
            }
        )
    matrix = pd.DataFrame(rows)
    if not matrix.empty:
        matrix = matrix.sort_values(["training_auc_roc", "best_external_auc_roc"], ascending=[False, False]).reset_index(drop=True)
    return matrix


def _ablation_interpretation(feature_set: str) -> str:
    if feature_set == "prime_only":
        return "Isolates the prime-number signal; useful for originality, but must not be overclaimed alone."
    if feature_set == "hybrid":
        return "Shows the prime representation works best when fused with biochemical context."
    if feature_set == "hybrid_plus_external":
        return "Best competition story: prime-aware model plus public biological evidence."
    if feature_set == "external_predictors_only":
        return "Baseline comparator; proves the project is not just repackaging external predictors."
    if feature_set == "biochemical_only":
        return "Non-prime biological baseline for judging the added value of prime features."
    return "Supportive ablation layer for robustness and interpretability."


def _render_prime_ablation_narrative(matrix: pd.DataFrame) -> str:
    lines = [
        "# Prime-number ablation narrative",
        "",
        "## Jury-facing message",
        "",
        "Prime numbers are not presented as a mystical biological law. They are used as a transparent, reproducible feature-engineering lens that maps amino-acid substitutions into discrete mathematical relationships. The ablation story is strongest when the prime-only signal is compared against biochemical-only, external-only and hybrid models on the same frozen data.",
        "",
        "## Evidence table",
        "",
    ]
    if matrix.empty:
        lines.append("- Ablation matrix was not available in this run.")
    else:
        lines.append("| Feature set | Training AUC-ROC | Best external AUC-ROC | Jury interpretation |")
        lines.append("|---|---:|---:|---|")
        for row in matrix.to_dict(orient="records"):
            lines.append(
                f"| {row['feature_set']} | {row['training_auc_roc']} | {row['best_external_auc_roc']} | {row['jury_interpretation']} |"
            )
    lines.extend(
        [
            "",
            "## Safe claim",
            "",
            "The prime-number component is a defensible originality layer because it is explicit, testable and ablated against non-prime controls. The final paper should claim that prime-aware features improve the platform as part of a hybrid biological AI workflow, not that prime numbers alone prove pathogenicity.",
            "",
            "## Figure recommendation",
            "",
            "Create one figure with five bars: prime-only, biochemical-only, external-only, hybrid, and hybrid-plus-external. Add a callout showing that the prime signal becomes most valuable when fused with biochemical and public-data evidence.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _case_hypothesis(row: dict[str, Any]) -> str:
    alignment = str(row.get("alphamissense_label_alignment") or "")
    if alignment.startswith("discordant_am_pathogenic"):
        return "AlphaMissense suggests protein-level damage despite a benign external label; review isoform mapping, curation context, population frequency and protein-domain evidence."
    if alignment.startswith("discordant_am_benign"):
        return "Clinical/external evidence suggests risk while AlphaMissense is benign; investigate nonlocal mechanisms, clinical assertion strength, splicing-adjacent context and label provenance."
    if alignment == "ambiguous_functional_signal":
        return "Functional signal is unresolved; combine MAVE, gnomAD, structure and targeted assays before using the variant as a strong claim."
    return "Use as a supporting mechanistic hypothesis, not as a definitive finding."


def _case_assay(row: dict[str, Any]) -> str:
    gene = str(row.get("gene") or "").upper()
    if gene == "BRCA1":
        return "Prioritize saturation genome editing or HDR assay, protein stability/localization, BRCA1 interaction context and AlphaFold local-structure review."
    if gene == "BRCA2":
        return "Prioritize homology-directed repair readout, RAD51-related functional context, conservation review and AlphaFold local-structure review."
    return "Prioritize matched functional assay, protein stability and local structural review."


def _render_mechanistic_case_studies(discordance: pd.DataFrame) -> str:
    lines = [
        "# Mechanistic case studies for judges",
        "",
        "These are not claimed as confirmed biological discoveries yet. They are high-value hypotheses generated by combining PrimeVarClass, AlphaMissense, public labels and evidence gaps.",
        "",
    ]
    if discordance.empty:
        lines.append("- No AlphaMissense discordance or ambiguity cases were available.")
        return "\n".join(lines).strip() + "\n"
    for index, row in enumerate(discordance.head(8).to_dict(orient="records"), start=1):
        lines.extend(
            [
                f"## Case {index}: {row.get('variant')}",
                "",
                f"- External label: `{row.get('label')}`",
                f"- PrimeVarClass locked score: `{row.get('locked_calibrated_score')}`",
                f"- AlphaMissense score/class: `{row.get('feature_alphamissense_pathogenicity')}` / `{row.get('feature_alphamissense_class')}`",
                f"- Alignment: `{row.get('alphamissense_label_alignment')}`",
                f"- Priority: `{row.get('hypothesis_priority')}`",
                f"- Evidence gap: `{row.get('evidence_gap')}`",
                f"- Mechanistic hypothesis: {_case_hypothesis(row)}",
                f"- Confirmation route: {_case_assay(row)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _render_public_good_narrative(jury_scorecard: pd.DataFrame, inputs: dict[str, Any]) -> str:
    total = round(float(jury_scorecard["estimated_points"].sum()), 2) if not jury_scorecard.empty else 0.0
    return "\n".join(
        [
            "# Public-good impact narrative",
            "",
            "PrimeVarClass addresses the Prêmio Jovem Cientista 2026 theme, Artificial Intelligence for the Common Good, by turning public biomedical data into an accessible, reproducible and interpretable research workflow for missense variant prioritization.",
            "",
            "The common-good value is not only prediction accuracy. The platform teaches users why a variant is difficult, shows which evidence is missing, exposes model uncertainty, and nominates variants for functional or structural confirmation. This is important for Brazil because genomic interpretation tools are often expensive, opaque, English-only or difficult for students and smaller research groups to reproduce.",
            "",
            f"Current estimated jury score: `{total}/100`.",
            f"Competition readiness: `{inputs['readiness'].get('competition_readiness_percent')}%`.",
            f"AlphaMissense priority overlay AUC-ROC: `{(inputs['alpha'].get('priority_benchmark') or {}).get('best_auc_roc')}`.",
            "",
            "The final application should emphasize responsible use: PrimeVarClass is a research and education platform, not a standalone clinical diagnostic system. Human expert review, prospective validation and experimental confirmation remain required for clinical decisions.",
        ]
    ).strip() + "\n"


def _render_report(jury_scorecard: pd.DataFrame, risk_register: pd.DataFrame, action_plan: pd.DataFrame) -> str:
    total = round(float(jury_scorecard["estimated_points"].sum()), 2) if not jury_scorecard.empty else 0.0
    remaining = round(100.0 - total, 2)
    lines = [
        "# PrimeVarClass competition jury audit",
        "",
        f"- Generated at: `{_now_utc()}`",
        f"- Estimated official-rubric score: `{total}/100`",
        f"- Estimated points still attackable: `{remaining}`",
        f"- Official rubric source: `{OFFICIAL_PJC_SOURCE_URL}`",
        f"- Official edital source: `{OFFICIAL_PJC_EDITAL_URL}`",
        "",
        "## Rubric scorecard",
        "",
    ]
    for row in jury_scorecard.to_dict(orient="records"):
        lines.append(
            f"- {row['criterion']}: {row['estimated_points']}/{row['official_points']} points, {row['jury_verdict']}."
        )
    lines.extend(["", "## Highest-risk objections", ""])
    for row in risk_register.head(6).to_dict(orient="records"):
        lines.append(f"- {row['risk_id']} ({row['severity']}): {row['risk']}")
    lines.extend(["", "## Immediate closure plan", ""])
    for row in action_plan.head(6).to_dict(orient="records"):
        lines.append(f"- {row['rank']}. {row['action']}")
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
        elif stripped.startswith("|"):
            rows = [line for line in stripped.splitlines() if not set(line.replace("|", "").strip()) <= {"-", ":"}]
            table_rows = []
            for row_index, line in enumerate(rows):
                cells = [html.escape(cell.strip()) for cell in line.strip("|").split("|")]
                tag = "th" if row_index == 0 else "td"
                table_rows.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
            blocks.append("<table>" + "".join(table_rows) + "</table>")
        else:
            blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;max-width:980px;margin:0 auto;padding:32px;line-height:1.65;color:#132238;background:#f8fbff}"
        "h1{color:#102a43}h2{color:#2155d9}ul,table{background:#fff;border:1px solid #d9e2ec;border-radius:14px;padding:16px 24px}"
        "table{border-collapse:collapse;width:100%;padding:0}td,th{border:1px solid #d9e2ec;padding:8px;text-align:left}</style>"
        "</head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def build_competition_jury_audit_package(campaign_root: str, output_dir: str | None = None) -> dict:
    campaign_path = Path(campaign_root).resolve()
    if not campaign_path.exists():
        raise FileNotFoundError(f"Campaign root not found: {campaign_path}")
    output_root = Path(output_dir).resolve() if output_dir else campaign_path / "competition_jury_audit"
    output_root.mkdir(parents=True, exist_ok=True)
    inputs = _load_campaign_inputs(campaign_path)

    jury_scorecard = _build_jury_scorecard(inputs)
    risk_register = _build_risk_register(inputs)
    action_plan = _build_action_plan(risk_register)
    ablation_matrix = _build_ablation_matrix(inputs)
    prime_narrative = _render_prime_ablation_narrative(ablation_matrix)
    case_studies = _render_mechanistic_case_studies(inputs["alpha_discordance"])
    impact_narrative = _render_public_good_narrative(jury_scorecard, inputs)
    report = _render_report(jury_scorecard, risk_register, action_plan)

    scorecard_path = output_root / "competition_jury_scorecard.csv"
    risk_path = output_root / "competition_jury_risk_register.csv"
    action_path = output_root / "competition_jury_action_plan.csv"
    ablation_path = output_root / "prime_ablation_matrix.csv"
    prime_narrative_path = output_root / "prime_ablation_narrative.md"
    case_studies_path = output_root / "mechanistic_case_studies.md"
    impact_path = output_root / "public_good_impact_narrative.md"
    report_path = output_root / "competition_jury_audit_report.md"
    html_path = output_root / "competition_jury_audit_report.html"
    manifest_path = output_root / "competition_jury_audit_manifest.json"

    jury_scorecard.to_csv(scorecard_path, index=False)
    risk_register.to_csv(risk_path, index=False)
    action_plan.to_csv(action_path, index=False)
    ablation_matrix.to_csv(ablation_path, index=False)
    prime_narrative_path.write_text(prime_narrative, encoding="utf-8")
    case_studies_path.write_text(case_studies, encoding="utf-8")
    impact_path.write_text(impact_narrative, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    html_path.write_text(_render_markdown_html(report, "PrimeVarClass Competition Jury Audit"), encoding="utf-8")

    total_points = round(float(jury_scorecard["estimated_points"].sum()), 2) if not jury_scorecard.empty else 0.0
    high_risk_count = int(risk_register["severity"].astype(str).eq("high").sum()) if not risk_register.empty else 0
    manifest = {
        "generated_at": _now_utc(),
        "campaign_root": _display_path(campaign_path),
        "official_theme": "Artificial Intelligence for the Common Good",
        "target_category": "Estudante do Ensino Superior",
        "official_rubric_total_points": 100,
        "estimated_jury_points": total_points,
        "estimated_remaining_attackable_points": round(100.0 - total_points, 2),
        "high_risk_objection_count": high_risk_count,
        "top_risks": risk_register.head(3).get("risk_id", pd.Series(dtype=str)).astype(str).tolist(),
        "official_source_url": OFFICIAL_PJC_SOURCE_URL,
        "official_edital_url": OFFICIAL_PJC_EDITAL_URL,
        "scorecard_path": _display_path(scorecard_path),
        "risk_register_path": _display_path(risk_path),
        "action_plan_path": _display_path(action_path),
        "prime_ablation_matrix_path": _display_path(ablation_path),
        "prime_ablation_narrative_path": _display_path(prime_narrative_path),
        "mechanistic_case_studies_path": _display_path(case_studies_path),
        "public_good_impact_narrative_path": _display_path(impact_path),
        "markdown_path": _display_path(report_path),
        "html_path": _display_path(html_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "competition_jury_audit": manifest,
        "competition_jury_audit_manifest_path": str(manifest_path),
        "competition_jury_scorecard_path": str(scorecard_path),
        "competition_jury_risk_register_path": str(risk_path),
        "competition_jury_action_plan_path": str(action_path),
        "prime_ablation_matrix_path": str(ablation_path),
        "prime_ablation_narrative_path": str(prime_narrative_path),
        "mechanistic_case_studies_path": str(case_studies_path),
        "public_good_impact_narrative_path": str(impact_path),
        "competition_jury_audit_report_markdown_path": str(report_path),
        "competition_jury_audit_report_html_path": str(html_path),
    }


def export_competition_jury_audit_package(campaign_root: str, output_dir: str | None = None) -> dict:
    return build_competition_jury_audit_package(campaign_root=campaign_root, output_dir=output_dir)
