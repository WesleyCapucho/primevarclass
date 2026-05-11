# Public BRCA Benchmark Example - Translational Pilot Package

- Generated at: 2026-04-03T04:33:16Z
- Pilot package readiness: 87%
- Pilot mode: shadow_mode
- Ready for demo pilot: yes
- Ready for shadow pilot: yes
- Ready for live pilot: not yet

## Criteria

### Operator surface readiness

- Score: 100%
- Status: ready
- Critical: no
- Evidence: Workbench, API, jobs e manifests ja suportam uso guiado por laboratorio.
- Next step: Manter a superficie operacional consistente entre releases.

### Pilot artifact package

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% dos artefatos operacionais essenciais do piloto foram materializados.
- Next step: Garantir que todo piloto venha acompanhado de manifests, relatorios e release final.

### Lab handoff readiness

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: Handoff de dados reais em 100% com 6 tarefa(s) abertas.
- Next step: Fechar as tarefas do handoff para permitir uma rodada assistida pelo laboratorio.

### Shadow-mode pilot readiness

- Score: 90%
- Status: ready
- Critical: yes
- Evidence: Shadow-mode em 90% com preflight=94% e execution board=66%.
- Next step: Usar a workbench e o handoff para rodar o fluxo em paralelo com revisao humana.

### Live translational candidate

- Score: 49%
- Status: gap
- Critical: yes
- Evidence: Candidato live em 49% com freeze=19% e validation lock=69%.
- Next step: Trocar datasets demo por coortes reais e fortalecer claim/validation antes de qualquer piloto live.

## Pilot Checklist

- [ready] operator: Abrir /workbench e carregar o registry de modelos.
- [ready] data: Revisar study_real_data_handoff_tasks.csv e atribuir as tarefas criticas por coorte/fonte.
- [ready] benchmark: Executar preflight do estudo resolvido antes da rodada publica final.
- [ready] pilot: Usar a API e a workbench em modo assistido, com validacao humana e sem claims clinicos finais.
- [pending] pilot: Permitir piloto live apenas quando freeze real, validation lock e claim strength sustentarem a rodada.

## Recommended Actions

- Trocar datasets demo por coortes reais e fortalecer claim/validation antes de qualquer piloto live.