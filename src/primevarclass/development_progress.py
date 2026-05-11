from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .real_data_preparation import _jsonify, _render_markdown_html


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _first_existing(*paths: str) -> str | None:
    for path in paths:
        if path and Path(path).exists():
            return path
    return None


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


def _percent(value: Any, default: int = 0) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return default


def _status(value: int) -> str:
    if value >= 85:
        return "strong"
    if value >= 70:
        return "advancing"
    if value >= 50:
        return "partial"
    return "early"


def _area(area_id: str, title: str, progress_percent: int, evidence: str, next_gate: str) -> dict[str, Any]:
    progress = _percent(progress_percent)
    return {
        "area_id": area_id,
        "area": title,
        "progress_percent": progress,
        "remaining_percent": 100 - progress,
        "status": _status(progress),
        "evidence": evidence,
        "next_gate": next_gate,
    }


def _file_contains(path: str | Path, pattern: str) -> bool:
    candidate = Path(path)
    if not candidate.exists():
        return False
    try:
        return pattern in candidate.read_text(encoding="utf-8")
    except Exception:
        return False


def build_development_progress_dashboard(
    *,
    prime_intelligence_manifest_path: str | None = None,
    biological_discovery_manifest_path: str | None = None,
    protein_impact_manifest_path: str | None = None,
    quantum_proteomics_manifest_path: str | None = None,
    quantum_vqe_benchmark_manifest_path: str | None = None,
    brca1_structural_campaign_manifest_path: str | None = None,
    brca1_engine_execution_manifest_path: str | None = None,
    brca1_fragment_preparation_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    multigene_real_benchmark_manifest_path: str | None = None,
    multigene_annotation_enrichment_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    continuous_learning_manifest_path: str | None = None,
    validation_credibility_closure_manifest_path: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
) -> dict[str, Any]:
    prime_manifest = _load_json(prime_intelligence_manifest_path or _first_existing(
        "primevarclass_study_results_real_multicohort_robust/prime_intelligence_manifest.json",
        "primevarclass_multigene_real_benchmark_results/study_run/prime_intelligence_manifest.json",
    ))
    biological_manifest = _load_json(biological_discovery_manifest_path or _first_existing(
        "primevarclass_biological_discovery_results/biological_discovery_manifest.json"
    ))
    protein_manifest = _load_json(protein_impact_manifest_path or _first_existing(
        "primevarclass_protein_impact_results/protein_impact_manifest.json"
    ))
    quantum_manifest = _load_json(quantum_proteomics_manifest_path or _first_existing(
        "primevarclass_quantum_proteomics_results/quantum_proteomics_manifest.json"
    ))
    quantum_benchmark_manifest = _load_json(quantum_vqe_benchmark_manifest_path or _first_existing(
        "primevarclass_quantum_vqe_benchmark_results/quantum_vqe_benchmark_manifest.json"
    ))
    structural_manifest = _load_json(brca1_structural_campaign_manifest_path or _first_existing(
        "primevarclass_brca1_structural_campaign_results/brca1_structural_campaign_manifest.json"
    ))
    engine_execution_manifest = _load_json(brca1_engine_execution_manifest_path or _first_existing(
        "primevarclass_brca1_engine_execution_results/brca1_engine_execution_manifest.json"
    ))
    fragment_preparation_manifest = _load_json(brca1_fragment_preparation_manifest_path or _first_existing(
        "primevarclass_brca1_fragment_preparation_results/brca1_fragment_preparation_manifest.json"
    ))
    paired_mutant_manifest = _load_json(brca1_paired_mutant_execution_manifest_path or _first_existing(
        "primevarclass_brca1_paired_mutant_execution_results/brca1_paired_mutant_execution_manifest.json"
    ))
    mutant_geometry_qc_manifest = _load_json(brca1_mutant_geometry_qc_manifest_path or _first_existing(
        "primevarclass_brca1_mutant_geometry_qc_results/brca1_mutant_geometry_qc_manifest.json"
    ))
    multigene_manifest = _load_json(multigene_real_benchmark_manifest_path or _first_existing(
        "primevarclass_multigene_real_benchmark_results/multigene_real_benchmark_manifest.json"
    ))
    annotation_manifest = _load_json(multigene_annotation_enrichment_manifest_path or _first_existing(
        "primevarclass_multigene_annotation_enrichment_results/multigene_annotation_enrichment_manifest.json"
    ))
    public_sync_manifest = _load_json(public_sync_closure_manifest_path or _first_existing(
        "primevarclass_public_sync_closure_results/public_sync_closure_manifest.json"
    ))
    continuous_manifest = _load_json(continuous_learning_manifest_path or _first_existing(
        "primevarclass_continuous_learning_results/continuous_learning_manifest.json"
    ))
    validation_manifest = _load_json(validation_credibility_closure_manifest_path or _first_existing(
        "primevarclass_validation_credibility_closure_results/validation_credibility_closure_manifest.json"
    ))
    prospective_manifest = _load_json(prospective_validation_closure_manifest_path or _first_existing(
        "primevarclass_prospective_validation_closure_results/prospective_validation_closure_manifest.json"
    ))

    prime_summary = prime_manifest.get("summary") or {}
    biological_summary = biological_manifest.get("summary") or {}
    protein_summary = protein_manifest.get("summary") or {}
    quantum_summary = quantum_manifest.get("summary") or {}
    quantum_benchmark_summary = quantum_benchmark_manifest.get("summary") or {}
    structural_summary = structural_manifest.get("summary") or {}
    engine_execution_summary = engine_execution_manifest.get("summary") or {}
    fragment_preparation_summary = fragment_preparation_manifest.get("summary") or {}
    paired_mutant_summary = paired_mutant_manifest.get("summary") or {}
    mutant_geometry_qc_summary = mutant_geometry_qc_manifest.get("summary") or {}
    multigene_summary = multigene_manifest.get("summary") or {}
    annotation_summary = annotation_manifest.get("summary") or {}
    public_sync_summary = public_sync_manifest.get("summary") or {}
    continuous_summary = continuous_manifest.get("summary") or {}
    validation_summary = validation_manifest.get("summary") or {}
    prospective_summary = prospective_manifest.get("summary") or {}
    annotation_readiness = max(
        _percent(annotation_summary.get("line_level_annotation_readiness_percent"), 0),
        _percent(public_sync_summary.get("effective_line_level_annotation_readiness_percent"), 0),
    )

    if continuous_summary or annotation_summary or public_sync_summary:
        real_data_sync_percent = int(
            round(
                (
                    _percent(continuous_summary.get("continuous_learning_readiness_percent"), 0) * 0.25
                    + _percent(continuous_summary.get("auto_sync_coverage_percent"), 0) * 0.10
                    + _percent(continuous_summary.get("benchmark_readiness_percent"), 0) * 0.10
                    + annotation_readiness * 0.25
                    + _percent(public_sync_summary.get("public_sync_closure_percent"), 0) * 0.30
                )
            )
        )
    else:
        real_data_sync_percent = 40
    prime_method_percent = int(
        round(
            (
                _percent(prime_summary.get("overall_prime_intelligence_percent"), 0) * 0.60
                + _percent(quantum_benchmark_summary.get("benchmark_support_percent"), 0) * 0.40
            )
        )
    ) if prime_summary or quantum_benchmark_summary else 45
    biological_percent = min(
        100,
        int(
            round(
                35
                + min(int(biological_summary.get("hotspot_count") or 0), 6) * 7
                + min(int(biological_summary.get("review_upgrade_candidate_count") or 0), 10) * 2
                + min(int(biological_summary.get("hypothesis_variant_count") or 0), 900) / 20.0
            )
        ),
    ) if biological_summary else 35
    proteomic_percent = int(
        round(
                (
                    _percent(structural_summary.get("campaign_readiness_percent"), 0) * 0.20
                    + _percent(engine_execution_summary.get("execution_readiness_percent"), 0) * 0.18
                    + _percent(fragment_preparation_summary.get("fragment_preparation_readiness_percent"), 0) * 0.14
                    + _percent(paired_mutant_summary.get("paired_mutant_execution_readiness_percent"), 0) * 0.04
                    + _percent(mutant_geometry_qc_summary.get("mutant_geometry_qc_readiness_percent"), 0) * 0.02
                    + _percent(structural_summary.get("mean_surrogate_structural_signal_percent"), 0) * 0.12
                    + _percent(protein_summary.get("prime_mechanistic_alignment_percent"), 0) * 0.20
                    + min(int(protein_summary.get("modeling_queue_count") or 0), 25) * 0.6
                )
        )
    ) if protein_summary or structural_summary or engine_execution_summary or fragment_preparation_summary else 40
    quantum_percent = int(
        round(
            (
                _percent(quantum_summary.get("mean_vqe_readiness_score_percent"), 0) * 0.35
                + _percent(quantum_summary.get("mean_prime_quantum_coupling_score_percent"), 0) * 0.20
                + _percent(quantum_benchmark_summary.get("prime_guided_win_rate_percent"), 0) * 0.25
                + _percent(quantum_benchmark_summary.get("benchmark_support_percent"), 0) * 0.20
            )
        )
    ) if quantum_summary or quantum_benchmark_summary else 38
    multigene_percent = int(
        round(
            _percent(multigene_summary.get("overall_multigene_benchmark_percent"), 35) * 0.65
            + annotation_readiness * 0.35
        )
    ) if annotation_summary else _percent(multigene_summary.get("overall_multigene_benchmark_percent"), 35)
    prospective_artifact_readiness = _percent(
        prospective_summary.get("experimental_package_artifact_readiness_percent"),
        _percent(prospective_summary.get("prospective_validation_readiness_percent"), 0),
    )
    credibility_percent = min(
        92,
        int(
            round(
                _percent(validation_summary.get("scientific_credibility_percent"), 35) * 0.60
                + _percent(prospective_summary.get("prospective_validation_readiness_percent"), 0) * 0.25
                + prospective_artifact_readiness * 0.15
            )
        ),
    ) if prospective_summary else _percent(validation_summary.get("scientific_credibility_percent"), 35)
    translational_percent = int(
        round(
            (
                _percent(structural_summary.get("mean_drug_discovery_readiness_percent"), 0) * 0.40
                + _percent(quantum_summary.get("mean_quantum_priority_score_percent"), 0) * 0.20
                + _percent(engine_execution_summary.get("execution_readiness_percent"), 0) * 0.10
                + _percent(fragment_preparation_summary.get("fragment_preparation_readiness_percent"), 0) * 0.03
                + _percent(paired_mutant_summary.get("paired_mutant_execution_readiness_percent"), 0) * 0.01
                + _percent(mutant_geometry_qc_summary.get("mutant_geometry_qc_readiness_percent"), 0) * 0.01
                + _percent(validation_summary.get("software_evidence_closure_percent"), 0) * 0.15
                + _percent(multigene_summary.get("mean_gene_progress_percent"), 0) * 0.20
            )
        )
    ) if structural_summary or quantum_summary or validation_summary or multigene_summary or engine_execution_summary or fragment_preparation_summary else 30
    manual_path = Path("docs/manual_usuario.md")
    manual_en_path = Path("docs/user_manual_en.md")
    glossary_path = Path("docs/glossario_primevarclass.md")
    glossary_en_path = Path("docs/glossary_primevarclass_en.md")
    feedback_playbook_path = Path("docs/feedback_playbook.md")
    feedback_playbook_en_path = Path("docs/feedback_playbook_en.md")
    ux_references_path = Path("docs/ux_accessibility_references.md")
    workbench_path = Path("src/primevarclass/ui/workbench.html")
    api_path = Path("src/primevarclass/api.py")
    product_percent = min(
        100,
        46
        + (8 if workbench_path.exists() else 0)
        + (8 if _file_contains(api_path, '@app.post("/users/profiles")') else 0)
        + (8 if _file_contains(api_path, '@app.post("/teams")') else 0)
        + (8 if _file_contains(workbench_path, "save-pilot-feedback") else 0)
        + (6 if _file_contains(api_path, "@app.get(\"/knowledge\")") else 0)
        + (4 if _file_contains(api_path, '"/science/public-sync-closure"') else 0)
        + (5 if _file_contains(workbench_path, "language-select") else 0)
        + (5 if _file_contains(api_path, "manual_en") else 0)
    )
    enablement_percent = min(
        100,
        14
        + (18 if manual_path.exists() else 0)
        + (14 if manual_en_path.exists() else 0)
        + (16 if glossary_path.exists() else 0)
        + (12 if glossary_en_path.exists() else 0)
        + (12 if feedback_playbook_path.exists() else 0)
        + (8 if feedback_playbook_en_path.exists() else 0)
        + (4 if ux_references_path.exists() else 0)
        + (2 if _file_contains(workbench_path, "/knowledge/manual") else 0),
    )

    areas = [
        _area(
            "real_data_sync",
            "Dados reais e sincronizacao publica",
            real_data_sync_percent,
            f"Continuous learning readiness={continuous_summary.get('continuous_learning_readiness_percent', 'n/a')}%; row-level readiness={annotation_readiness}%; public sync closure={public_sync_summary.get('public_sync_closure_percent', 'n/a')}%",
            "Executar/resumir a fila gnomAD ate substituir consultas capped por sync completo por release.",
        ),
        _area(
            "prime_methodology",
            "Metodologia de numeros primos",
            prime_method_percent,
            f"Prime intelligence={prime_summary.get('overall_prime_intelligence_percent', 'n/a')}%; VQE support={quantum_benchmark_summary.get('benchmark_support_percent', 'n/a')}%",
            "Expandir ablations prime-guided vs non-prime com Hamiltonianos reais e novos genes.",
        ),
        _area(
            "biological_discovery",
            "Descoberta biologica",
            biological_percent,
            f"Hotspots={biological_summary.get('hotspot_count', 'n/a')}; hypotheses={biological_summary.get('hypothesis_variant_count', 'n/a')}",
            "Validar hotspots e hipoteses lideres com camadas funcionais ortogonais.",
        ),
        _area(
            "proteomics_structural",
            "Proteomica e estrutura 3D",
            proteomic_percent,
            f"Modeling queue={protein_summary.get('modeling_queue_count', 'n/a')}; BRCA1 campaign={structural_summary.get('campaign_readiness_percent', 'n/a')}%; engine execution={engine_execution_summary.get('execution_readiness_percent', 'n/a')}%; fragment prep={fragment_preparation_summary.get('fragment_preparation_readiness_percent', 'n/a')}%; paired mutant xTB={paired_mutant_summary.get('paired_xtb_completed_count', 'n/a')}; geometry QC={mutant_geometry_qc_summary.get('mutant_geometry_qc_readiness_percent', 'n/a')}%",
            "Revisar protonacao/dominio dos mutantes e executar DFT/OpenMM/Vina.",
        ),
        _area(
            "quantum_vqe",
            "Modulo quantico e VQE",
            quantum_percent,
            f"Mean VQE readiness={quantum_summary.get('mean_vqe_readiness_score_percent', 'n/a')}%; paired benchmark support={quantum_benchmark_summary.get('benchmark_support_percent', 'n/a')}%",
            "Converter o benchmark proxy em benchmark fisico com fragmentos e Hamiltonianos revisados.",
        ),
        _area(
            "multigene_validation",
            "Generalizacao multigenica",
            multigene_percent,
            f"Overall multigene benchmark={multigene_summary.get('overall_multigene_benchmark_percent', 'n/a')}%; row-level annotation={annotation_readiness}%",
            "Completar full sync gnomAD/MaveDB e ampliar o painel alem dos 6 genes atuais.",
        ),
        _area(
            "scientific_credibility",
            "Validacao e credibilidade cientifica",
            credibility_percent,
            f"Scientific credibility={validation_summary.get('scientific_credibility_percent', 'n/a')}%; prospective readiness={prospective_summary.get('prospective_validation_readiness_percent', 'n/a')}%; experimental package={prospective_summary.get('experimental_package_artifact_readiness_percent', 'n/a')}%; handoff targets={prospective_summary.get('partner_handoff_variant_count', 'n/a')}",
            "Executar validacao prospectiva independente e confirmacao estrutural/funcional experimental com parceiro.",
        ),
        _area(
            "translation",
            "Impacto translacional e descoberta terapeutica",
            translational_percent,
            f"Drug-discovery readiness={structural_summary.get('mean_drug_discovery_readiness_percent', 'n/a')}%; BRCA1 engine execution={engine_execution_summary.get('execution_readiness_percent', 'n/a')}%; xTB baseline fragments={fragment_preparation_summary.get('xtb_completed_count', 'n/a')}; paired mutant xTB={paired_mutant_summary.get('paired_xtb_completed_count', 'n/a')}; geometry QC={mutant_geometry_qc_summary.get('mutant_geometry_qc_readiness_percent', 'n/a')}%",
            "Ligar os alvos mecanisticos a ensaios de resgate, ligacao e priorizacao terapeutica.",
        ),
        _area(
            "product_public",
            "Produto publico e operacao multiusuario",
            product_percent,
            "Workbench, perfis, times, jobs, feedback, seletor PT-BR/EN e hub de conhecimento estao disponiveis; ainda falta hardening de deploy publico.",
            "Adicionar cadastro publico completo, convites, permissoes finas e deploy multiusuario endurecido.",
        ),
        _area(
            "user_enablement",
            "Manual, glossario e feedback guiado",
            enablement_percent,
            "Manual, glossario, playbook de feedback e referencias UX foram publicados no hub de conhecimento em PT-BR/EN.",
            "Expandir exemplos guiados, videos curtos, tutoriais por perfil e FAQ de troubleshooting.",
        ),
    ]
    area_table = pd.DataFrame(areas)
    overall_progress = int(round(float(area_table["progress_percent"].mean()))) if not area_table.empty else 0
    sorted_table = area_table.sort_values("progress_percent", ascending=False, kind="stable")
    summary = {
        "generated_at": _now_utc(),
        "overall_progress_percent": overall_progress,
        "areas_tracked": int(len(area_table)),
        "areas_above_80_percent": int((area_table["progress_percent"] >= 80).sum()) if not area_table.empty else 0,
        "areas_below_50_percent": int((area_table["progress_percent"] < 50).sum()) if not area_table.empty else 0,
        "highest_area": str(sorted_table.iloc[0]["area"]) if not sorted_table.empty else None,
        "lowest_area": str(area_table.sort_values("progress_percent", ascending=True).iloc[0]["area"]) if not area_table.empty else None,
    }
    area_table = area_table.sort_values(["progress_percent", "area"], ascending=[False, True], kind="stable").reset_index(drop=True)
    return {
        "summary": summary,
        "area_table": area_table,
    }


def _build_markdown(bundle: dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    area_table = bundle.get("area_table")
    area_df = area_table if isinstance(area_table, pd.DataFrame) else pd.DataFrame()
    lines = [
        "# PrimeVarClass Development Progress",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Overall progress: `{summary.get('overall_progress_percent', 0)}%`",
        f"- Areas tracked: `{summary.get('areas_tracked', 0)}`",
        f"- Areas above 80%: `{summary.get('areas_above_80_percent', 0)}`",
        f"- Areas below 50%: `{summary.get('areas_below_50_percent', 0)}`",
        "",
        "## Area table",
        "",
    ]
    if area_df.empty:
        lines.append("- No area progress rows were generated.")
    else:
        header = "| Area | Progress | Remaining | Status |"
        divider = "| --- | --- | --- | --- |"
        body = [
            f"| {row['area']} | {row['progress_percent']}% | {row['remaining_percent']}% | {row['status']} |"
            for row in area_df.to_dict(orient="records")
        ]
        lines.extend([header, divider, *body])
    return "\n".join(lines).strip()


def export_development_progress_dashboard(
    *,
    output_dir: str,
    prime_intelligence_manifest_path: str | None = None,
    biological_discovery_manifest_path: str | None = None,
    protein_impact_manifest_path: str | None = None,
    quantum_proteomics_manifest_path: str | None = None,
    quantum_vqe_benchmark_manifest_path: str | None = None,
    brca1_structural_campaign_manifest_path: str | None = None,
    brca1_engine_execution_manifest_path: str | None = None,
    brca1_fragment_preparation_manifest_path: str | None = None,
    brca1_paired_mutant_execution_manifest_path: str | None = None,
    brca1_mutant_geometry_qc_manifest_path: str | None = None,
    multigene_real_benchmark_manifest_path: str | None = None,
    multigene_annotation_enrichment_manifest_path: str | None = None,
    public_sync_closure_manifest_path: str | None = None,
    continuous_learning_manifest_path: str | None = None,
    validation_credibility_closure_manifest_path: str | None = None,
    prospective_validation_closure_manifest_path: str | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = build_development_progress_dashboard(
        prime_intelligence_manifest_path=prime_intelligence_manifest_path,
        biological_discovery_manifest_path=biological_discovery_manifest_path,
        protein_impact_manifest_path=protein_impact_manifest_path,
        quantum_proteomics_manifest_path=quantum_proteomics_manifest_path,
        quantum_vqe_benchmark_manifest_path=quantum_vqe_benchmark_manifest_path,
        brca1_structural_campaign_manifest_path=brca1_structural_campaign_manifest_path,
        brca1_engine_execution_manifest_path=brca1_engine_execution_manifest_path,
        brca1_fragment_preparation_manifest_path=brca1_fragment_preparation_manifest_path,
        brca1_paired_mutant_execution_manifest_path=brca1_paired_mutant_execution_manifest_path,
        brca1_mutant_geometry_qc_manifest_path=brca1_mutant_geometry_qc_manifest_path,
        multigene_real_benchmark_manifest_path=multigene_real_benchmark_manifest_path,
        multigene_annotation_enrichment_manifest_path=multigene_annotation_enrichment_manifest_path,
        public_sync_closure_manifest_path=public_sync_closure_manifest_path,
        continuous_learning_manifest_path=continuous_learning_manifest_path,
        validation_credibility_closure_manifest_path=validation_credibility_closure_manifest_path,
        prospective_validation_closure_manifest_path=prospective_validation_closure_manifest_path,
    )

    area_table_path = output_root / "development_progress_table.csv"
    markdown_path = output_root / "development_progress_report.md"
    html_path = output_root / "development_progress_report.html"
    manifest_path = output_root / "development_progress_manifest.json"

    area_df = bundle.get("area_table")
    (area_df if isinstance(area_df, pd.DataFrame) else pd.DataFrame()).to_csv(area_table_path, index=False)
    markdown_report = _build_markdown(bundle)
    markdown_path.write_text(markdown_report, encoding="utf-8")
    html_path.write_text(_render_markdown_html(markdown_report, "PrimeVarClass Development Progress"), encoding="utf-8")

    manifest_payload = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary") or {},
        "area_table_path": str(area_table_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
    }
    manifest_path.write_text(json.dumps(_jsonify(manifest_payload), indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "development_progress": bundle,
        "development_progress_manifest_path": str(manifest_path),
        "development_progress_table_path": str(area_table_path),
        "development_progress_report_markdown_path": str(markdown_path),
        "development_progress_report_html_path": str(html_path),
    }
