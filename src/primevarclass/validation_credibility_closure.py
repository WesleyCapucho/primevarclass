from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def _first_existing(*paths: str) -> str | None:
    for path in paths:
        if Path(path).exists():
            return path
    return None


def _percent(value: Any, default: int = 0) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return default


def _criterion(
    criterion_id: str,
    title: str,
    score_percent: int,
    evidence: str,
    remaining_action: str,
    proof_layer: str,
    critical: bool = False,
) -> dict[str, Any]:
    score = _percent(score_percent)
    if score >= 90:
        status = "closed"
    elif score >= 75:
        status = "strong_but_not_final"
    elif score >= 55:
        status = "partial"
    else:
        status = "gap"
    return {
        "criterion_id": criterion_id,
        "title": title,
        "score_percent": score,
        "status": status,
        "proof_layer": proof_layer,
        "critical": bool(critical),
        "evidence": evidence,
        "remaining_action": remaining_action,
    }


def _build_criteria(
    *,
    prime_manifest: dict[str, Any],
    biological_manifest: dict[str, Any],
    protein_manifest: dict[str, Any],
    quantum_manifest: dict[str, Any],
    multigene_manifest: dict[str, Any],
    claim_manifest: dict[str, Any],
    quantum_benchmark_manifest: dict[str, Any],
    structural_manifest: dict[str, Any],
    brca1_engine_execution_manifest: dict[str, Any],
    brca1_fragment_preparation_manifest: dict[str, Any],
    brca1_paired_mutant_execution_manifest: dict[str, Any],
    brca1_mutant_geometry_qc_manifest: dict[str, Any],
    multigene_annotation_manifest: dict[str, Any],
    public_sync_closure_manifest: dict[str, Any],
    prospective_validation_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    prime_summary = prime_manifest.get("summary") or {}
    biological_summary = biological_manifest.get("summary") or {}
    protein_summary = protein_manifest.get("summary") or {}
    quantum_summary = quantum_manifest.get("summary") or {}
    multigene_summary = multigene_manifest.get("summary") or {}
    claim_summary = claim_manifest.get("summary") or {}
    quantum_benchmark_summary = quantum_benchmark_manifest.get("summary") or {}
    structural_summary = structural_manifest.get("summary") or {}
    engine_execution_summary = brca1_engine_execution_manifest.get("summary") or {}
    fragment_preparation_summary = brca1_fragment_preparation_manifest.get("summary") or {}
    paired_mutant_summary = brca1_paired_mutant_execution_manifest.get("summary") or {}
    mutant_geometry_qc_summary = brca1_mutant_geometry_qc_manifest.get("summary") or {}
    annotation_summary = multigene_annotation_manifest.get("summary") or {}
    public_sync_summary = public_sync_closure_manifest.get("summary") or {}
    prospective_summary = prospective_validation_manifest.get("summary") or {}
    effective_annotation_readiness = max(
        _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 0),
        _percent(public_sync_summary.get("effective_line_level_annotation_readiness_percent"), 0),
    )
    effective_gnomad_evidence = max(
        _percent(annotation_summary.get("gnomad_line_evidence_coverage_percent"), 0),
        _percent(public_sync_summary.get("effective_gnomad_line_evidence_percent"), 0),
    )

    claim_score = 0
    if claim_summary:
        claim_score = 95 if str(claim_summary.get("claim_tier") or "").lower() == "strong" else 80
        claim_score = max(claim_score, _percent(claim_summary.get("claim_strength_percent"), 0))

    biological_score = min(
        100,
        50
        + min(int(biological_summary.get("hotspot_count") or 0), 5) * 6
        + min(int(biological_summary.get("hypothesis_variant_count") or 0), 50),
    )
    protein_score = min(
        100,
        20
        + min(int(protein_summary.get("modeling_queue_count") or 0), 25) * 1.2
        + int(_percent(protein_summary.get("modeling_queue_prime_alignment_percent"), 0) * 0.12)
        + int(_percent(structural_summary.get("campaign_readiness_percent"), 0) * 0.15)
        + int(_percent(engine_execution_summary.get("execution_readiness_percent"), 0) * 0.14)
        + int(_percent(fragment_preparation_summary.get("fragment_preparation_readiness_percent"), 0) * 0.09)
        + int(_percent(paired_mutant_summary.get("paired_mutant_execution_readiness_percent"), 0) * 0.02)
        + int(_percent(mutant_geometry_qc_summary.get("mutant_geometry_qc_readiness_percent"), 0) * 0.01)
        + int(_percent(structural_summary.get("mean_surrogate_structural_signal_percent"), 0) * 0.08),
    )
    quantum_score = min(
        100,
        20
        + min(int(quantum_summary.get("quantum_target_count") or 0), 12) * 3
        + min(int(quantum_summary.get("vqe_target_count") or 0), 12) * 2
        + int(_percent(quantum_summary.get("mean_vqe_readiness_score_percent"), 0) * 0.12)
        + int(_percent(quantum_benchmark_summary.get("benchmark_support_percent"), 0) * 0.18),
    )
    prime_quantum_bridge_score = min(
        100,
        20
        + int(_percent(quantum_summary.get("mean_prime_quantum_coupling_score_percent"), 0) * 0.25)
        + int(_percent(quantum_benchmark_summary.get("prime_guided_win_rate_percent"), 0) * 0.35)
        + int(_percent(quantum_benchmark_summary.get("strong_win_rate_percent"), 0) * 0.15)
        + int(_percent(quantum_benchmark_summary.get("mean_overall_advantage_percent_points"), 0) * 0.20),
    )
    if int(multigene_summary.get("gene_count") or 0) > 0:
        multigene_score = min(
            100,
            10
            + min(int(multigene_summary.get("gene_count") or 0), 6) * 3
            + min(int(multigene_summary.get("completed_gene_count") or 0), 6) * 4
            + int(_percent(multigene_summary.get("mean_gene_progress_percent"), 0) * 0.20)
            + int(_percent(multigene_summary.get("mean_external_balanced_score_percent"), 0) * 0.15)
            + int(effective_annotation_readiness * 0.25),
        )
    else:
        multigene_score = 90 if int(multigene_summary.get("phase_1_gene_count") or 0) > 0 else 45

    return [
        _criterion(
            "external_validation_claim",
            "Frozen external validation and claim strength",
            claim_score,
            f"Claim summary: {claim_summary or 'not provided'}",
            "Keep the frozen external benchmark immutable; add independent prospective and multigene external cohorts before final clinical claims.",
            "clinical_statistical",
            critical=True,
        ),
        _criterion(
            "prime_methodological_differentiator",
            "Prime-number methodological signal",
            _percent(prime_summary.get("overall_prime_intelligence_percent"), 0),
            f"Prime intelligence summary: {prime_summary or 'not provided'}",
            "Preserve prime-only/hybrid ablations in every new gene/disease benchmark.",
            "methodological",
            critical=True,
        ),
        _criterion(
            "prime_quantum_bridge",
            "Prime-quantum coupling and prime-guided VQE design",
            prime_quantum_bridge_score,
            f"Mean prime-quantum coupling={quantum_summary.get('mean_prime_quantum_coupling_score_percent')}%; paired win rate={quantum_benchmark_summary.get('prime_guided_win_rate_percent')}%; benchmark support={quantum_benchmark_summary.get('benchmark_support_percent')}%",
            "Convert the paired proxy benchmark into physical fragment/Hamiltonian runs while keeping the prime vs non-prime ablation frozen.",
            "methodological_translation",
        ),
        _criterion(
            "biological_discovery",
            "Functional biological discovery layer",
            biological_score,
            f"Hotspots={biological_summary.get('hotspot_count')}; hypotheses={biological_summary.get('hypothesis_variant_count')}; review upgrades={biological_summary.get('review_upgrade_candidate_count')}",
            "Validate top hotspots with orthogonal functional assays and expert variant curation.",
            "functional_biology",
        ),
        _criterion(
            "protein_impact",
            "Proteomic/3D mechanistic prioritization and BRCA1 execution campaign",
            protein_score,
            f"Modeling queue={protein_summary.get('modeling_queue_count')}; BRCA1 campaign readiness={structural_summary.get('campaign_readiness_percent')}%; engine execution readiness={engine_execution_summary.get('execution_readiness_percent')}; xTB baseline fragments={fragment_preparation_summary.get('xtb_completed_count')}; paired mutant xTB={paired_mutant_summary.get('paired_xtb_completed_count')}; geometry QC={mutant_geometry_qc_summary.get('mutant_geometry_qc_readiness_percent')}",
            "Upgrade automated geometry QC into expert protonation/domain review and DFT/OpenMM/Vina controls.",
            "structural_biology",
        ),
        _criterion(
            "quantum_vqe_engine",
            "Quantum proteomics, VQE, QM/MM, MD, and docking readiness",
            quantum_score,
            f"Quantum targets={quantum_summary.get('quantum_target_count')}; VQE targets={quantum_summary.get('vqe_target_count')}; mean VQE readiness={quantum_summary.get('mean_vqe_readiness_score_percent')}%; paired benchmark support={quantum_benchmark_summary.get('benchmark_support_percent')}",
            "Populate the strongest targets with reviewed coordinates and real fragment controls before interpreting VQE as anything more than a refinement layer.",
            "computational_chemistry",
        ),
        _criterion(
            "multigene_generalization",
            "Multigene generalization plan",
            multigene_score,
            f"Gene count={multigene_summary.get('gene_count')}; mean external balanced score={multigene_summary.get('mean_external_balanced_score_percent')}; row-level annotation={effective_annotation_readiness}",
            "Complete full gnomAD/MaveDB sync and extend beyond the first 6 genes.",
            "generalization",
            critical=True,
        ),
        _criterion(
            "row_level_public_evidence",
            "Line-level public annotation evidence",
            int(
                round(
                    effective_annotation_readiness * 0.60
                    + _percent(public_sync_summary.get("public_sync_closure_percent"), 0) * 0.40
                )
            ) if public_sync_summary else _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 45),
            f"Coordinate coverage={annotation_summary.get('genomic_coordinate_coverage_percent')}; gnomAD evidence={effective_gnomad_evidence}; MaveDB evidence={annotation_summary.get('mavedb_line_evidence_coverage_percent')}; public sync closure={public_sync_summary.get('public_sync_closure_percent')}",
            "Resume the gnomAD sync queue or stage a release table locally, then complete VRS/coordinate reconciliation.",
            "public_data_traceability",
            critical=True,
        ),
        _criterion(
            "prospective_experimental_closure",
            "Prospective and experimental validation closure",
            _percent(prospective_summary.get("prospective_validation_readiness_percent"), 45),
            f"Queue count={prospective_summary.get('functional_structural_confirmation_queue_count')}; experimental completion={prospective_summary.get('experimental_confirmation_completed_percent')}",
            "Run the locked next-release benchmark and complete orthogonal wet-lab/biophysical confirmation for top variants.",
            "prospective_experimental",
            critical=True,
        ),
        _criterion(
            "therapeutic_translation_guardrails",
            "Drug-discovery translation guardrails",
            88 if quantum_summary and protein_summary else 45,
            "The platform now separates hypothesis generation from therapeutic efficacy claims.",
            "Add experimental binding/functional rescue assays before any therapeutic or patent claim about drug efficacy.",
            "translation",
        ),
    ]


def _build_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    criteria = payload["criteria"]
    actions = payload["remaining_actions"]
    lines = [
        "# PrimeVarClass Validation and Credibility Closure",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Software evidence closure: `{summary['software_evidence_closure_percent']}%`",
        f"- Scientific credibility score: `{summary['scientific_credibility_percent']}%`",
        f"- Final proof cap: `{summary['final_proof_cap_percent']}%`",
        f"- Ready for stronger external validation: `{summary['ready_for_stronger_external_validation']}`",
        f"- Ready for definitive therapeutic claims: `{summary['ready_for_definitive_therapeutic_claims']}`",
        "",
        "## Criteria",
        "",
    ]
    for row in criteria:
        lines.append(
            "- "
            f"{row['title']}: {row['score_percent']}% ({row['status']}) - {row['remaining_action']}"
        )
    lines.extend(["", "## Remaining actions to reach final proof", ""])
    for action in actions:
        lines.append(f"- {action}")
    return "\n".join(lines).strip()


def build_validation_credibility_closure(
    *,
    prime_intelligence_manifest_path: str | None = None,
    biological_discovery_manifest_path: str | None = None,
    protein_impact_manifest_path: str | None = None,
    quantum_proteomics_manifest_path: str | None = None,
    multigene_rollout_manifest_path: str | None = None,
    claim_strength_manifest_path: str | None = None,
    quantum_vqe_benchmark_manifest_path: str | None = None,
    brca1_structural_campaign_manifest_path: str | None = None,
    brca1_engine_execution_manifest_path: str | None = None,
    brca1_fragment_preparation_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    multigene_real_benchmark_manifest_path: str | None = None,
    multigene_annotation_enrichment_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
) -> dict[str, Any]:
    prime_path = prime_intelligence_manifest_path or _first_existing(
        "primevarclass_study_results_real_multicohort_robust/prime_intelligence_manifest.json",
        "primevarclass_study_results_real_multicohort_pooled/prime_intelligence_manifest.json",
    )
    biological_path = biological_discovery_manifest_path or _first_existing(
        "primevarclass_biological_discovery_results/biological_discovery_manifest.json"
    )
    protein_path = protein_impact_manifest_path or _first_existing(
        "primevarclass_protein_impact_results/protein_impact_manifest.json"
    )
    quantum_path = quantum_proteomics_manifest_path or _first_existing(
        "primevarclass_quantum_proteomics_results/quantum_proteomics_manifest.json"
    )
    multigene_path = multigene_real_benchmark_manifest_path or multigene_rollout_manifest_path or _first_existing(
        "primevarclass_multigene_real_benchmark_results/multigene_real_benchmark_manifest.json",
        "primevarclass_multigene_rollout_results/multigene_rollout_manifest.json"
    )
    claim_path = claim_strength_manifest_path or _first_existing(
        "primevarclass_study_results_real_multicohort_robust/claim_strength_manifest.json",
        "primevarclass_study_results_real_multicohort_pooled/claim_strength_manifest.json",
    )
    quantum_benchmark_path = quantum_vqe_benchmark_manifest_path or _first_existing(
        "primevarclass_quantum_vqe_benchmark_results/quantum_vqe_benchmark_manifest.json"
    )
    structural_path = brca1_structural_campaign_manifest_path or _first_existing(
        "primevarclass_brca1_structural_campaign_results/brca1_structural_campaign_manifest.json"
    )
    engine_execution_path = brca1_engine_execution_manifest_path or _first_existing(
        "primevarclass_brca1_engine_execution_results/brca1_engine_execution_manifest.json"
    )
    fragment_preparation_path = brca1_fragment_preparation_manifest_path or _first_existing(
        "primevarclass_brca1_fragment_preparation_results/brca1_fragment_preparation_manifest.json"
    )
    paired_mutant_path = brca1_paired_mutant_execution_manifest_path or _first_existing(
        "primevarclass_brca1_paired_mutant_execution_results/brca1_paired_mutant_execution_manifest.json"
    )
    mutant_geometry_qc_path = brca1_mutant_geometry_qc_manifest_path or _first_existing(
        "primevarclass_brca1_mutant_geometry_qc_results/brca1_mutant_geometry_qc_manifest.json"
    )
    annotation_path = multigene_annotation_enrichment_manifest_path or _first_existing(
        "primevarclass_multigene_annotation_enrichment_results/multigene_annotation_enrichment_manifest.json"
    )
    public_sync_path = public_sync_closure_manifest_path or _first_existing(
        "primevarclass_public_sync_closure_results/public_sync_closure_manifest.json"
    )
    prospective_path = prospective_validation_closure_manifest_path or _first_existing(
        "primevarclass_prospective_validation_closure_results/prospective_validation_closure_manifest.json"
    )

    criteria = _build_criteria(
        prime_manifest=_load_json(prime_path),
        biological_manifest=_load_json(biological_path),
        protein_manifest=_load_json(protein_path),
        quantum_manifest=_load_json(quantum_path),
        multigene_manifest=_load_json(multigene_path),
        claim_manifest=_load_json(claim_path),
        quantum_benchmark_manifest=_load_json(quantum_benchmark_path),
        structural_manifest=_load_json(structural_path),
        brca1_engine_execution_manifest=_load_json(engine_execution_path),
        brca1_fragment_preparation_manifest=_load_json(fragment_preparation_path),
        brca1_paired_mutant_execution_manifest=_load_json(paired_mutant_path),
        brca1_mutant_geometry_qc_manifest=_load_json(mutant_geometry_qc_path),
        multigene_annotation_manifest=_load_json(annotation_path),
        public_sync_closure_manifest=_load_json(public_sync_path),
        prospective_validation_manifest=_load_json(prospective_path),
    )
    criteria_df = pd.DataFrame(criteria)
    software_evidence = _percent(criteria_df["score_percent"].mean() if not criteria_df.empty else 0)
    critical_scores = criteria_df.loc[criteria_df["critical"], "score_percent"].tolist() if not criteria_df.empty else []
    critical_floor = min(critical_scores) if critical_scores else 0
    scientific_credibility = int(round((software_evidence * 0.7) + (critical_floor * 0.3)))
    prospective_summary = (_load_json(prospective_path).get("summary") or {}) if prospective_path else {}
    prospective_cap = _percent(prospective_summary.get("final_scientific_proof_cap_percent"), 92)
    final_proof_cap = min(92, prospective_cap) if prospective_summary else 92
    capped_scientific = min(scientific_credibility, final_proof_cap)
    remaining_actions = [
        "Complete full scheduled gnomAD/MaveDB row-level sync for every multigene benchmark variant while preserving frozen external splits.",
        "Generate reviewed mutant side-chain coordinates and run paired reference-vs-mutant xTB/DFT/OpenMM/Vina/Qiskit-Nature logs.",
        "Run xTB/DFT controls before interpreting VQE outputs; VQE remains a hypothesis-refinement layer, not standalone proof.",
        "Upgrade the prime-guided vs non-prime benchmark from paired proxy evidence to real fragment/Hamiltonian execution on identical curated fragments.",
        "Validate top mechanistic hypotheses with orthogonal biochemical or cellular assays.",
        "Only advance drug-development or patent-strength therapeutic claims after experimental rescue, binding, or functional evidence.",
    ]
    summary = {
        "generated_at": _now_utc(),
        "software_evidence_closure_percent": software_evidence,
        "scientific_credibility_percent": capped_scientific,
        "uncapped_scientific_credibility_percent": scientific_credibility,
        "final_proof_cap_percent": final_proof_cap,
        "ready_for_stronger_external_validation": software_evidence >= 85 and critical_floor >= 75,
        "ready_for_definitive_therapeutic_claims": False,
        "why_not_100_percent": "Definitive scientific and therapeutic proof still requires prospective/multigene external validation plus experimental structural/functional confirmation.",
        "resolved_manifest_paths": {
            "prime_intelligence_manifest_path": prime_path,
            "biological_discovery_manifest_path": biological_path,
            "protein_impact_manifest_path": protein_path,
            "quantum_proteomics_manifest_path": quantum_path,
            "multigene_rollout_manifest_path": multigene_path,
            "claim_strength_manifest_path": claim_path,
            "quantum_vqe_benchmark_manifest_path": quantum_benchmark_path,
            "brca1_structural_campaign_manifest_path": structural_path,
            "brca1_engine_execution_manifest_path": engine_execution_path,
            "brca1_fragment_preparation_manifest_path": fragment_preparation_path,
            "brca1_paired_mutant_execution_manifest_path": paired_mutant_path,
            "brca1_mutant_geometry_qc_manifest_path": mutant_geometry_qc_path,
            "multigene_annotation_enrichment_manifest_path": annotation_path,
            "public_sync_closure_manifest_path": public_sync_path,
            "prospective_validation_closure_manifest_path": prospective_path,
        },
    }
    payload = {
        "summary": summary,
        "criteria": criteria,
        "remaining_actions": remaining_actions,
    }
    payload["markdown_report"] = _build_markdown(payload)
    payload["html_report"] = _render_markdown_html(payload["markdown_report"], "PrimeVarClass Validation and Credibility Closure")
    return payload


def export_validation_credibility_closure(
    *,
    output_dir: str,
    prime_intelligence_manifest_path: str | None = None,
    biological_discovery_manifest_path: str | None = None,
    protein_impact_manifest_path: str | None = None,
    quantum_proteomics_manifest_path: str | None = None,
    multigene_rollout_manifest_path: str | None = None,
    claim_strength_manifest_path: str | None = None,
    quantum_vqe_benchmark_manifest_path: str | None = None,
    brca1_structural_campaign_manifest_path: str | None = None,
    brca1_engine_execution_manifest_path: str | None = None,
    brca1_fragment_preparation_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    multigene_real_benchmark_manifest_path: str | None = None,
    multigene_annotation_enrichment_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_validation_credibility_closure(
        prime_intelligence_manifest_path=prime_intelligence_manifest_path,
        biological_discovery_manifest_path=biological_discovery_manifest_path,
        protein_impact_manifest_path=protein_impact_manifest_path,
        quantum_proteomics_manifest_path=quantum_proteomics_manifest_path,
        multigene_rollout_manifest_path=multigene_rollout_manifest_path,
        claim_strength_manifest_path=claim_strength_manifest_path,
        quantum_vqe_benchmark_manifest_path=quantum_vqe_benchmark_manifest_path,
        brca1_structural_campaign_manifest_path=brca1_structural_campaign_manifest_path,
        brca1_engine_execution_manifest_path=brca1_engine_execution_manifest_path,
        brca1_fragment_preparation_manifest_path=brca1_fragment_preparation_manifest_path,
        brca1_paired_mutant_execution_manifest_path=brca1_paired_mutant_execution_manifest_path,
        brca1_mutant_geometry_qc_manifest_path=brca1_mutant_geometry_qc_manifest_path,
        multigene_real_benchmark_manifest_path=multigene_real_benchmark_manifest_path,
        multigene_annotation_enrichment_manifest_path=multigene_annotation_enrichment_manifest_path,
        public_sync_closure_manifest_path=public_sync_closure_manifest_path,
        prospective_validation_closure_manifest_path=prospective_validation_closure_manifest_path,
    )
    manifest_path = output_root / "validation_credibility_closure_manifest.json"
    criteria_path = output_root / "validation_credibility_criteria.csv"
    actions_path = output_root / "validation_credibility_remaining_actions.csv"
    markdown_path = output_root / "validation_credibility_closure_report.md"
    html_path = output_root / "validation_credibility_closure_report.html"

    pd.DataFrame(payload["criteria"]).to_csv(criteria_path, index=False)
    pd.DataFrame({"remaining_action": payload["remaining_actions"]}).to_csv(actions_path, index=False)
    markdown_path.write_text(payload["markdown_report"], encoding="utf-8")
    html_path.write_text(payload["html_report"], encoding="utf-8")
    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": payload["summary"],
        "criteria_path": str(criteria_path),
        "remaining_actions_path": str(actions_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "validation_credibility_closure": payload,
        "validation_credibility_closure_manifest_path": str(manifest_path),
        "validation_credibility_criteria_path": str(criteria_path),
        "validation_credibility_remaining_actions_path": str(actions_path),
        "validation_credibility_report_markdown_path": str(markdown_path),
        "validation_credibility_report_html_path": str(html_path),
    }
