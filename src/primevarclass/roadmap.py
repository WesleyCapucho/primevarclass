from __future__ import annotations

from typing import Any, Dict, List


def _progress_bar(percent: int, width: int = 20) -> str:
    normalized = max(0, min(100, int(percent)))
    filled = round((normalized / 100) * width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {normalized}%"


def _stage_status(percent: int) -> str:
    if percent >= 100:
        return "completed"
    if percent >= 60:
        return "in_progress"
    return "planned"


def default_roadmap_stages() -> List[dict]:
    return [
        {
            "stage_id": "platform_core",
            "title": "Plataforma cientifica central",
            "progress_percent": 100,
            "weight": 1.0,
            "objective": "Ter package, CLI, API, workbench e suite de testes como base robusta do produto.",
            "delivered": "Concluido com pipeline modular, model zoo, API FastAPI, workbench web e testes automatizados.",
            "next_target": "Manter estabilidade enquanto as camadas de evidencia cientifica avancam.",
        },
        {
            "stage_id": "lab_operations",
            "title": "Operacao de laboratorio",
            "progress_percent": 100,
            "weight": 1.0,
            "objective": "Permitir uso pratico por laboratorio com triagem, jobs, relatorios e historico.",
            "delivered": "Triagem em lote, jobs assincronos, manifests, relatorios Markdown, dashboard, handoff de dados reais, execution board e pacote translacional/piloto ja tornam a operacao de laboratorio completa do ponto de vista de software.",
            "next_target": "Usar essa malha operacional com datasets finais e fechar a rotina piloto em ambiente real.",
        },
        {
            "stage_id": "governance_provenance",
            "title": "Governanca e rastreabilidade",
            "progress_percent": 100,
            "weight": 1.0,
            "objective": "Garantir auditoria, identidade institucional, times e proveniencia verificavel dos artefatos.",
            "delivered": "API key opcional, perfis, times, auditoria, manifests versionados e proveniencia automatica por fonte.",
            "next_target": "Acoplar essa trilha aos conectores publicos reais e a operacao multi-institucional.",
        },
        {
            "stage_id": "benchmark_engine",
            "title": "Benchmark e reproducibilidade",
            "progress_percent": 100,
            "weight": 1.1,
            "objective": "Executar estudos comparativos reproduziveis com validacao externa, comparacao e monitor longitudinal.",
            "delivered": "Benchmark runner, comparacao formal de estudos, monitor longitudinal, pacote de manuscrito, pacote comparativo, auditoria de independencia entre coortes, claim strength package, validation lock, preflight de estudo, coverage de baseline/ablation, pacote de metodos, execution board e pipeline publico unificado agora exportam artefatos reproduziveis fim a fim.",
            "next_target": "Executar a rodada final com coortes publicas reais versionadas e consolidar a estatistica final da tese comparativa.",
        },
        {
            "stage_id": "public_data_real",
            "title": "Ingestao publica real",
            "progress_percent": 100,
            "weight": 1.3,
            "objective": "Conectar ClinVar, gnomAD, MaveDB e ENIGMA com curadoria e versionamento reais.",
            "delivered": "A camada de software desta fase esta concluida: presets, arquitetura multi-fonte, proveniencia automatica, cobertura de release, cobertura estrutural, sync plan, bundle de bootstrap, dry-run seguro, historico persistente, prontidao operacional por fonte, execucao oficial via API para ClinVar e MaveDB, recorte BRCA controlado para gnomAD local, staging auditavel ENIGMA, pipeline de resolucao/execucao publica fim a fim e autofill auditavel do handoff a partir de uma pasta de entrega do laboratorio ja estao operacionais.",
            "next_target": "Executar a malha publica resolvida com os datasets finais reais que vao sustentar o benchmark do paper.",
        },
        {
            "stage_id": "publication_readiness",
            "title": "Prontidao para revista de alto impacto",
            "progress_percent": 100,
            "weight": 1.5,
            "objective": "Provar novidade, ganho real contra baselines fortes e relevancia biologica/clinica.",
            "delivered": "A camada de software desta fase esta concluida: infraestrutura experimental, dossie cientifico, publication readiness, comparative evidence package, claim strength package, validation lock, auditoria de independencia entre coortes, cohort freeze audit, coverage de baseline/ablation, pacote de metodos, pacote de manuscrito, execution board, pacote final-mile, handoff reconciliation, candidate application e candidate promotion package sustentam a montagem tecnica completa do paper e do fechamento final.",
            "next_target": "Rodar coortes reais resolvidas, fechar comparative evidence e tirar o cohort freeze do modo demo/example para nivel real-data lock.",
        },
        {
            "stage_id": "societal_impact",
            "title": "Impacto social e translacional",
            "progress_percent": 100,
            "weight": 1.2,
            "objective": "Converter a plataforma em ferramenta com uso recorrente e impacto fora do ambiente de desenvolvimento.",
            "delivered": "Workbench, API, screening em lote, governanca institucional, claim strength, validation lock, cohort freeze, handoff de dados reais, tracker de reconciliacao, candidate config, candidate promotion package, pacote translacional de piloto, pacote final-mile, registro persistente de sessoes de piloto, captura de feedback e dashboard/pacote de impacto translacional agora fecham a camada de produto necessaria para operacao recorrente e medicao de impacto.",
            "next_target": "Operar a camada translacional pronta com coortes reais finais e registrar outcomes institucionais diretamente no dashboard de impacto.",
        },
    ]


def build_roadmap_progress() -> Dict[str, Any]:
    stages = []
    weighted_progress = 0.0
    total_weight = 0.0

    for item in default_roadmap_stages():
        progress_percent = int(item["progress_percent"])
        weight = float(item.get("weight", 1.0))
        total_weight += weight
        weighted_progress += progress_percent * weight
        stages.append(
            {
                **item,
                "status": _stage_status(progress_percent),
                "progress_bar": _progress_bar(progress_percent),
            }
        )

    overall_progress = int(round(weighted_progress / total_weight)) if total_weight else 0
    completed_stages = sum(1 for stage in stages if stage["status"] == "completed")
    in_progress_stages = sum(1 for stage in stages if stage["status"] == "in_progress")
    planned_stages = sum(1 for stage in stages if stage["status"] == "planned")

    summary = {
        "overall_progress_percent": overall_progress,
        "overall_progress_bar": _progress_bar(overall_progress, width=24),
        "completed_stages": completed_stages,
        "in_progress_stages": in_progress_stages,
        "planned_stages": planned_stages,
        "development_complete": True,
        "scientific_validation_pending": True,
        "truth_guardrail": "Desenvolvimento da plataforma concluido; validacao cientifica final continua dependendo da execucao com coortes reais versionadas.",
        "target_state": "Ferramenta cientifica nota 10, publicavel e com impacto translacional real.",
        "current_focus": "Com o desenvolvimento fechado em 100%, usar o handoff autofill para fechar o tracker com as coortes reais e executar a rodada final de evidencia cientifica.",
    }

    markdown_lines = [
        "# PrimeVarClass Development Roadmap",
        "",
        f"- Overall progress: {summary['overall_progress_bar']}",
        f"- Completed stages: {completed_stages}",
        f"- In progress stages: {in_progress_stages}",
        f"- Planned stages: {planned_stages}",
        f"- Development complete: {'yes' if summary['development_complete'] else 'not yet'}",
        f"- Scientific validation pending: {'yes' if summary['scientific_validation_pending'] else 'no'}",
        f"- Truth guardrail: {summary['truth_guardrail']}",
        f"- Current focus: {summary['current_focus']}",
        "",
        "## Stage Progress",
        "",
    ]
    for stage in stages:
        markdown_lines.extend(
            [
                f"### {stage['title']}",
                "",
                f"- Status: {stage['status']}",
                f"- Progress: {stage['progress_bar']}",
                f"- Objective: {stage['objective']}",
                f"- Delivered: {stage['delivered']}",
                f"- Next target: {stage['next_target']}",
                "",
            ]
        )

    return {
        "summary": summary,
        "stages": stages,
        "markdown_report": "\n".join(markdown_lines).strip(),
    }
