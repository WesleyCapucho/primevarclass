from __future__ import annotations

import csv
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return 0


def _status_from_percent(value: int) -> str:
    if value >= 85:
        return "ready"
    if value >= 60:
        return "partial"
    return "gap"


def _as_root(workspace_root: str | Path | None) -> Path:
    return Path(workspace_root or Path.cwd()).resolve()


def _relative_path(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(root))
    except Exception:
        return str(path)


def _latest_existing(root: Path, patterns: Iterable[str]) -> Path | None:
    matches: List[Path] = []
    for pattern in patterns:
        candidate = root / pattern
        if candidate.exists():
            matches.append(candidate)
            continue
        matches.extend([path for path in root.glob(pattern) if path.exists()])
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _load_json(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_summary_percent(payload: dict, keys: Iterable[str]) -> int | None:
    candidates = [
        payload,
        dict(payload.get("summary") or {}),
        dict(payload.get("publication_readiness") or {}).get("summary") or {},
        dict(payload.get("validation_credibility_closure") or {}).get("summary") or {},
        dict(payload.get("prospective_validation_closure") or {}).get("summary") or {},
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in keys:
            if key in candidate:
                return _safe_int(candidate.get(key))
    return None


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return values
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _env_value(root: Path, key: str) -> tuple[str, str]:
    runtime_value = os.environ.get(key, "").strip()
    if runtime_value:
        return runtime_value, "environment"
    for env_name in (".env", ".env.local", ".env.production"):
        env_path = root / env_name
        value = _load_env_file(env_path).get(key, "").strip()
        if value:
            return value, env_name
    return "", ""


def _is_real_api_key(value: str) -> bool:
    if len(value) < 32:
        return False
    lowered = value.lower()
    placeholders = ("troque", "change", "example", "placeholder", "secret", "senha")
    return not any(token in lowered for token in placeholders)


def _check_row(
    *,
    root: Path,
    gate_id: str,
    area: str,
    title: str,
    patterns: Iterable[str],
    weight: float = 1.0,
    critical: bool = False,
    evidence_keys: Iterable[str] = (),
    ready_action: str,
    gap_action: str,
    include_absolute_paths: bool = False,
    require_all_patterns: bool = False,
) -> dict:
    pattern_list = list(patterns)
    missing_patterns: List[str] = []
    if require_all_patterns:
        existing_paths = [(root / pattern) for pattern in pattern_list if (root / pattern).exists()]
        missing_patterns = [pattern for pattern in pattern_list if not (root / pattern).exists()]
        path = existing_paths[0] if existing_paths else None
        exists = not missing_patterns
    else:
        path = _latest_existing(root, pattern_list)
        exists = bool(path and path.exists())
    payload = _load_json(path)
    evidence_percent = _extract_summary_percent(payload, evidence_keys) if exists else None
    if require_all_patterns and pattern_list:
        completeness_percent = int(round(((len(pattern_list) - len(missing_patterns)) / len(pattern_list)) * 100))
        score_percent = int(evidence_percent if evidence_percent is not None else completeness_percent)
    else:
        score_percent = int(evidence_percent if evidence_percent is not None else (100 if exists else 0))
    row = {
        "gate_id": gate_id,
        "area": area,
        "title": title,
        "status": _status_from_percent(score_percent),
        "score_percent": score_percent,
        "weight": float(weight),
        "critical": bool(critical),
        "artifact_available": exists,
        "path": _relative_path(root, path),
        "missing": missing_patterns,
        "recommended_action": ready_action if exists else gap_action,
    }
    if include_absolute_paths:
        row["absolute_path"] = str(path.resolve()) if path else ""
    return row


def _weighted_percent(rows: List[dict]) -> int:
    if not rows:
        return 0
    total_weight = sum(float(row.get("weight") or 1.0) for row in rows)
    if total_weight <= 0:
        return 0
    weighted = sum(float(row.get("score_percent") or 0) * float(row.get("weight") or 1.0) for row in rows)
    return int(round(weighted / total_weight))


def _config_rows(root: Path) -> List[dict]:
    api_key_value, api_key_source = _env_value(root, "PRIMEVARCLASS_API_KEY")
    cors_value, cors_source = _env_value(root, "PRIMEVARCLASS_CORS_ORIGINS")
    job_root_value, job_root_source = _env_value(root, "PRIMEVARCLASS_JOB_ROOT")
    api_key_set = _is_real_api_key(api_key_value)
    cors_origins = [item.strip() for item in cors_value.split(",") if item.strip()]
    job_root_set = bool(job_root_value)
    rows = [
        {
            "gate_id": "auth_key",
            "area": "operations",
            "title": "API key configurada para ambiente web",
            "status": "ready" if api_key_set else "partial",
            "score_percent": 100 if api_key_set else 65,
            "weight": 1.1,
            "critical": True,
            "artifact_available": api_key_set,
            "path": api_key_source if api_key_source and api_key_source != "environment" else "",
            "recommended_action": (
                f"PRIMEVARCLASS_API_KEY está configurada via {api_key_source}."
                if api_key_set
                else "Definir PRIMEVARCLASS_API_KEY forte antes de expor a plataforma na web."
            ),
        },
        {
            "gate_id": "cors_origins",
            "area": "operations",
            "title": "Origens CORS declaradas",
            "status": "ready" if cors_origins else "partial",
            "score_percent": 100 if cors_origins else 70,
            "weight": 0.7,
            "critical": False,
            "artifact_available": bool(cors_origins),
            "path": cors_source if cors_source and cors_source != "environment" else "",
            "recommended_action": (
                f"CORS configurado para {len(cors_origins)} origem(ns)."
                if cors_origins
                else "Definir PRIMEVARCLASS_CORS_ORIGINS quando houver frontend hospedado em outro domínio."
            ),
        },
        {
            "gate_id": "persistent_state",
            "area": "operations",
            "title": "Diretório persistente para trabalhos/auditoria",
            "status": "ready" if job_root_set else "partial",
            "score_percent": 100 if job_root_set else 75,
            "weight": 0.8,
            "critical": False,
            "artifact_available": job_root_set,
            "path": job_root_source if job_root_source and job_root_source != "environment" else "",
            "recommended_action": (
                f"PRIMEVARCLASS_JOB_ROOT está configurado via {job_root_source}."
                if job_root_set
                else "Usar volume persistente e PRIMEVARCLASS_JOB_ROOT em produção."
            ),
        },
    ]
    if (root / ".env.example").exists():
        rows.append(
            {
                "gate_id": "env_example",
                "area": "operations",
                "title": "Modelo de variáveis de ambiente",
                "status": "ready",
                "score_percent": 100,
                "weight": 0.6,
                "critical": False,
                "artifact_available": True,
                "path": ".env.example",
                "recommended_action": "Usar .env.example como base para ambiente de staging/produção.",
            }
        )
    return rows


def build_launch_readiness_assessment(
    *,
    workspace_root: str | Path | None = None,
    include_absolute_paths: bool = False,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = _as_root(workspace_root)
    context = dict(report_context or {})

    scientific_rows = [
        _check_row(
            root=root,
            gate_id="real_data_manifest",
            area="science",
            title="Manifesto de dados reais",
            patterns=["primevarclass_real_data_preparation_results/real_data_preparation_manifest.json"],
            weight=1.2,
            critical=True,
            evidence_keys=["overall_real_data_readiness_percent", "real_data_readiness_percent"],
            ready_action="Dados reais preparados e rastreáveis.",
            gap_action="Executar --prepare-real-data com ClinVar, BRCA Exchange e MaveDB reais.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="publication_readiness",
            area="science",
            title="Prontidão de publicação computacional",
            patterns=["primevarclass_study_results_real_multicohort_robust/publication_readiness_manifest.json", "primevarclass_*/**/publication_readiness_manifest.json", "primevarclass_*/publication_readiness_manifest.json"],
            weight=1.3,
            critical=True,
            evidence_keys=["overall_readiness_percent", "publication_readiness_percent"],
            ready_action="Pacote de prontidão de publicação encontrado.",
            gap_action="Gerar publication_readiness_manifest.json a partir do estudo final.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="validation_credibility",
            area="science",
            title="Fechamento de validação e credibilidade",
            patterns=["primevarclass_validation_credibility_closure_results/validation_credibility_closure_manifest.json"],
            weight=1.25,
            critical=True,
            evidence_keys=["scientific_credibility_percent", "overall_validation_credibility_percent"],
            ready_action="Fechamento de credibilidade consolidado.",
            gap_action="Executar --build-validation-credibility-closure.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="independent_data_expansion",
            area="science",
            title="Bancos reais independentes para treino e validaÃ§Ã£o",
            patterns=["primevarclass_independent_data_expansion_results/independent_data_expansion_manifest.json"],
            weight=1.0,
            critical=True,
            evidence_keys=["independent_data_expansion_percent"],
            ready_action="Plano e templates de bancos independentes encontrados.",
            gap_action="Executar --build-independent-data-expansion para ampliar fontes reais independentes.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="independent_data_staging_closure",
            area="science",
            title="Staging local de bancos independentes",
            patterns=["primevarclass_independent_data_staging_closure_results/independent_data_staging_closure_manifest.json"],
            weight=1.05,
            critical=False,
            evidence_keys=["independent_data_staging_closure_percent", "line_level_real_data_execution_percent"],
            ready_action="Inventario local, gap plan e TOML de fontes independentes encontrados.",
            gap_action="Executar --build-independent-data-staging-closure para auditar bancos reais baixados e gerar config de treino.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="prospective_validation",
            area="science",
            title="Plano prospectivo e experimental",
            patterns=["primevarclass_prospective_validation_closure_results/prospective_validation_closure_manifest.json"],
            weight=1.1,
            critical=True,
            evidence_keys=[
                "prospective_validation_readiness_percent",
                "final_scientific_proof_cap_percent",
                "experimental_confirmation_completed_percent",
            ],
            ready_action="Plano prospectivo/experimental exportado.",
            gap_action="Executar --build-prospective-validation-closure com manifests finais.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="mechanistic_layers",
            area="science",
            title="Camadas mecanísticas: descoberta, proteômica e quantum",
            patterns=["primevarclass_quantum_proteomics_results/quantum_proteomics_manifest.json"],
            weight=0.95,
            critical=False,
            evidence_keys=["quantum_proteomics_readiness_percent", "overall_quantum_readiness_percent"],
            ready_action="Pacote quântico-proteômico encontrado.",
            gap_action="Gerar impacto proteico e proteômica quântica a partir das hipóteses biológicas.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="public_sync",
            area="science",
            title="Sincronização pública e rastreabilidade linha a linha",
            patterns=["primevarclass_public_sync_closure_results/public_sync_closure_manifest.json"],
            weight=0.9,
            critical=False,
            evidence_keys=["public_sync_closure_percent", "overall_public_sync_percent"],
            ready_action="Pacote de sincronização pública encontrado.",
            gap_action="Executar --build-public-sync-closure com gnomAD/MaveDB em nivel de linha.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="brca1_structural_execution",
            area="science",
            title="Campanha estrutural BRCA1 com motores reais",
            patterns=["primevarclass_brca1_engine_execution_results/brca1_engine_execution_manifest.json"],
            weight=0.85,
            critical=False,
            evidence_keys=["engine_execution_readiness_percent", "overall_engine_readiness_percent"],
            ready_action="Pacote de execução estrutural BRCA1 encontrado.",
            gap_action="Executar --build-brca1-engine-execution e revisar motores instalados.",
            include_absolute_paths=include_absolute_paths,
        ),
    ]

    web_rows = [
        _check_row(
            root=root,
            gate_id="api_service",
            area="web",
            title="API FastAPI",
            patterns=["src/primevarclass/api.py"],
            weight=1.1,
            critical=True,
            ready_action="API disponível no pacote.",
            gap_action="Restaurar src/primevarclass/api.py.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="workbench_ui",
            area="web",
            title="Workbench web multiusuário",
            patterns=["src/primevarclass/ui/workbench.html", "src/primevarclass/ui/workbench.css", "src/primevarclass/ui/workbench.js"],
            weight=1.0,
            critical=True,
            ready_action="Interface web empacotada.",
            gap_action="Restaurar HTML/CSS/JS da interface.",
            include_absolute_paths=include_absolute_paths,
            require_all_patterns=True,
        ),
        _check_row(
            root=root,
            gate_id="knowledge_docs",
            area="web",
            title="Manual, glossário e feedback bilíngues",
            patterns=[
                "docs/manual_usuario.md",
                "docs/user_manual_en.md",
                "docs/glossario_primevarclass.md",
                "docs/glossary_primevarclass_en.md",
                "docs/pdf/manual_usuario.pdf",
                "docs/pdf/user_manual_en.pdf",
                "docs/pdf/glossario_primevarclass.pdf",
                "docs/pdf/glossary_primevarclass_en.pdf",
                "docs/feedback_playbook.md",
                "docs/feedback_playbook_en.md",
            ],
            weight=0.95,
            critical=False,
            ready_action="Documentação bilíngue disponível.",
            gap_action="Completar manual, glossário e guia de feedback em pt-BR/en.",
            include_absolute_paths=include_absolute_paths,
            require_all_patterns=True,
        ),
        _check_row(
            root=root,
            gate_id="dockerfile",
            area="web",
            title="Container Docker",
            patterns=["Dockerfile"],
            weight=0.9,
            critical=False,
            ready_action="Dockerfile encontrado.",
            gap_action="Criar Dockerfile de produção.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="compose",
            area="web",
            title="Compose para staging local",
            patterns=["docker-compose.yml"],
            weight=0.7,
            critical=False,
            ready_action="docker-compose.yml encontrado.",
            gap_action="Criar docker-compose.yml com volume persistente.",
            include_absolute_paths=include_absolute_paths,
        ),
        _check_row(
            root=root,
            gate_id="launch_docs",
            area="web",
            title="Runbook de publicação e lançamento",
            patterns=["docs/scientific_publication_and_web_launch.md"],
            weight=0.8,
            critical=False,
            ready_action="Runbook de lançamento encontrado.",
            gap_action="Criar runbook de publicação científica e lançamento web.",
            include_absolute_paths=include_absolute_paths,
        ),
    ]
    operation_rows = _config_rows(root)

    all_rows = scientific_rows + web_rows + operation_rows
    scientific_percent = _weighted_percent(scientific_rows)
    web_percent = _weighted_percent(web_rows)
    operational_percent = _weighted_percent(operation_rows)
    overall_percent = int(round((scientific_percent * 0.52) + (web_percent * 0.33) + (operational_percent * 0.15)))

    critical_gaps = [
        row for row in all_rows
        if row.get("critical") and int(row.get("score_percent") or 0) < 85
    ]
    validation_payload = _load_json(root / "primevarclass_validation_credibility_closure_results/validation_credibility_closure_manifest.json")
    prospective_payload = _load_json(root / "primevarclass_prospective_validation_closure_results/prospective_validation_closure_manifest.json")
    validation_summary = dict(validation_payload.get("summary") or validation_payload)
    prospective_summary = dict(prospective_payload.get("summary") or prospective_payload)
    validation_proof_cap = _safe_int(validation_summary.get("final_proof_cap_percent") or 0)
    prospective_proof_cap = _safe_int(prospective_summary.get("final_scientific_proof_cap_percent") or 0)
    final_scientific_proof_cap = (
        min(value for value in [validation_proof_cap, prospective_proof_cap] if value)
        if (validation_proof_cap or prospective_proof_cap)
        else 0
    )
    experimental_confirmation_percent = _safe_int(prospective_summary.get("experimental_confirmation_completed_percent") or 0)
    ready_for_definitive_scientific_claims = bool(prospective_summary.get("ready_for_definitive_scientific_claims"))
    ready_for_definitive_therapeutic_claims = bool(
        prospective_summary.get("ready_for_definitive_therapeutic_claims")
        and validation_summary.get("ready_for_definitive_therapeutic_claims")
    )

    ready_for_web_staging = web_percent >= 85 and operational_percent >= 70
    ready_for_public_web = ready_for_web_staging and not any(row["gate_id"] == "auth_key" for row in critical_gaps)
    ready_for_computational_preprint = scientific_percent >= 80
    ready_for_external_validation_package = scientific_percent >= 85 and final_scientific_proof_cap >= 85
    ready_for_strong_scientific_claim = (
        scientific_percent >= 92
        and final_scientific_proof_cap >= 95
        and experimental_confirmation_percent >= 85
        and ready_for_definitive_scientific_claims
        and not critical_gaps
    )

    recommended_actions = [row["recommended_action"] for row in all_rows if int(row.get("score_percent") or 0) < 85]
    if not recommended_actions:
        recommended_actions.append("Executar revisão final de segurança, reprodutibilidade e texto do manuscrito antes do lançamento público.")
    if ready_for_computational_preprint and not ready_for_strong_scientific_claim:
        recommended_actions.append("A plataforma está próxima de preprint computacional; manter linguagem conservadora até confirmação funcional/estrutural independente.")
    if ready_for_web_staging and not ready_for_public_web:
        recommended_actions.append("A instância pode ir para staging, mas a exposição pública deve exigir API key forte.")

    summary = {
        "generated_at": _now_utc(),
        "workspace_root": str(root) if include_absolute_paths else "",
        "overall_launch_readiness_percent": overall_percent,
        "overall_launch_status": _status_from_percent(overall_percent),
        "scientific_publication_percent": scientific_percent,
        "web_launch_percent": web_percent,
        "operational_hardening_percent": operational_percent,
        "ready_for_web_staging": ready_for_web_staging,
        "ready_for_public_web": ready_for_public_web,
        "ready_for_computational_preprint": ready_for_computational_preprint,
        "ready_for_external_validation_package": ready_for_external_validation_package,
        "ready_for_strong_scientific_claim": ready_for_strong_scientific_claim,
        "ready_for_definitive_scientific_claims": ready_for_definitive_scientific_claims,
        "ready_for_definitive_therapeutic_claims": ready_for_definitive_therapeutic_claims,
        "experimental_confirmation_completed_percent": experimental_confirmation_percent,
        "final_scientific_proof_cap_percent": final_scientific_proof_cap,
        "critical_gap_count": len(critical_gaps),
        "truth_guardrail": (
            "Prontidão computacional não equivale a validade clínica; afirmações fortes ainda exigem "
            "confirmação funcional, estrutural e prospectiva independente."
        ),
    }

    markdown_report = build_launch_readiness_markdown(
        summary=summary,
        rows=all_rows,
        recommended_actions=recommended_actions,
        report_context=context,
    )
    return {
        "summary": summary,
        "checks": all_rows,
        "scientific_checks": scientific_rows,
        "web_checks": web_rows,
        "operational_checks": operation_rows,
        "critical_gaps": critical_gaps,
        "recommended_actions": recommended_actions,
        "report_context": context,
        "markdown_report": markdown_report,
    }


def build_launch_readiness_markdown(
    *,
    summary: dict,
    rows: List[dict],
    recommended_actions: List[str],
    report_context: Dict[str, Any] | None = None,
) -> str:
    context = dict(report_context or {})
    lines = [
        "# PrimeVarClass - prontidão para publicação científica e lançamento web",
        "",
        f"- Gerado em: {summary.get('generated_at')}",
        f"- Prontidão geral de lançamento: {summary.get('overall_launch_readiness_percent')}%",
        f"- Prontidão para publicação científica: {summary.get('scientific_publication_percent')}%",
        f"- Prontidão web: {summary.get('web_launch_percent')}%",
        f"- Endurecimento operacional: {summary.get('operational_hardening_percent')}%",
        f"- Pronto para staging web: {'sim' if summary.get('ready_for_web_staging') else 'ainda não'}",
        f"- Pronto para web pública: {'sim' if summary.get('ready_for_public_web') else 'ainda não'}",
        f"- Pronto para preprint computacional: {'sim' if summary.get('ready_for_computational_preprint') else 'ainda não'}",
        f"- Pronto para pacote de validação externa: {'sim' if summary.get('ready_for_external_validation_package') else 'ainda não'}",
        f"- Confirmação experimental concluída: {summary.get('experimental_confirmation_completed_percent')}%",
        f"- Teto de prova científica final: {summary.get('final_scientific_proof_cap_percent')}%",
        f"- Pronto para afirmação científica forte: {'sim' if summary.get('ready_for_strong_scientific_claim') else 'ainda não'}",
        f"- Pronto para afirmação terapêutica definitiva: {'sim' if summary.get('ready_for_definitive_therapeutic_claims') else 'ainda não'}",
    ]
    for key, label in [
            ("institution", "Instituição"),
            ("team_name", "Equipe"),
            ("operator_name", "Operador"),
            ("report_purpose", "Finalidade"),
    ]:
        if context.get(key):
            lines.append(f"- {label}: {context[key]}")

    lines.extend(
        [
            "",
            "## Guarda de Verdade Científica",
            "",
            f"- {summary.get('truth_guardrail')}",
            "- A plataforma pode ser lançada para fluxos de pesquisa antes de uso clínico, mas alegações clínicas ou terapêuticas devem permanecer fora do escopo até confirmação independente.",
            "",
            "## Checklist De Gates",
            "",
        ]
    )
    for row in rows:
        lines.append(
            f"- [{row.get('status')}] {row.get('area')} / {row.get('title')}: "
            f"{row.get('score_percent')}% - {row.get('recommended_action')}"
        )

    lines.extend(["", "## Próximas Ações Recomendadas", ""])
    for action in recommended_actions:
        lines.append(f"- {action}")
    return "\n".join(lines).strip()


def build_launch_readiness_html(bundle: dict) -> str:
    markdown = str(bundle.get("markdown_report") or "")
    blocks: List[str] = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            blocks.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("- "):
            items = "".join(f"<li>{html.escape(line[2:])}</li>" for line in stripped.splitlines() if line.startswith("- "))
            blocks.append(f"<ul>{items}</ul>")
            continue
        blocks.append(f"<p>{html.escape(stripped)}</p>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>PrimeVarClass Launch Readiness</title>"
        "<style>"
        "body{font-family:Georgia,serif;background:#f5f7f2;color:#17242f;max-width:1040px;margin:0 auto;padding:34px;line-height:1.66;}"
        "h1{font-size:2.25rem;margin-bottom:.4rem;}h2{margin-top:2rem;color:#1e6b68;}"
        "ul{background:#fff;border:1px solid #dbe7df;border-radius:18px;padding:18px 24px;box-shadow:0 14px 40px rgba(31,65,55,.08);}"
        "li{margin:.35rem 0;}"
        "</style></head><body>"
        + "".join(blocks)
        + "</body></html>"
    )


def export_launch_readiness_package(
    *,
    output_dir: str,
    workspace_root: str | Path | None = None,
    include_absolute_paths: bool = True,
    report_context: Dict[str, Any] | None = None,
) -> dict:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    bundle = build_launch_readiness_assessment(
        workspace_root=workspace_root,
        include_absolute_paths=include_absolute_paths,
        report_context=report_context,
    )
    markdown_path = root / "launch_readiness_report.md"
    html_path = root / "launch_readiness_report.html"
    checklist_path = root / "launch_readiness_checklist.csv"
    manifest_path = root / "launch_readiness_manifest.json"

    markdown_path.write_text(str(bundle.get("markdown_report") or ""), encoding="utf-8")
    html_path.write_text(build_launch_readiness_html(bundle), encoding="utf-8")
    with checklist_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "gate_id",
                "area",
                "title",
                "status",
                "score_percent",
                "critical",
                "artifact_available",
                "path",
                "recommended_action",
            ],
        )
        writer.writeheader()
        for row in bundle.get("checks") or []:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

    manifest = {
        "generated_at": _now_utc(),
        "summary": bundle.get("summary"),
        "critical_gaps": bundle.get("critical_gaps"),
        "recommended_actions": bundle.get("recommended_actions"),
        "report_context": bundle.get("report_context"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "checklist_path": str(checklist_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "launch_readiness": bundle,
        "launch_readiness_summary": bundle.get("summary") or {},
        "launch_readiness_manifest_path": str(manifest_path),
        "launch_readiness_report_markdown_path": str(markdown_path),
        "launch_readiness_report_html_path": str(html_path),
        "launch_readiness_checklist_path": str(checklist_path),
    }
