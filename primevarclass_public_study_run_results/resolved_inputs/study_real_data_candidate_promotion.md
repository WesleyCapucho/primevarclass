# Public BRCA Benchmark Example - Candidate Promotion Package

- Generated at: 2026-04-03T04:29:31Z
- Candidate promotion: 22%
- Candidate config exists: yes
- Validated tasks applied: 0/6
- Applied changes: 0
- Ready to promote candidate config: not yet
- Ready to run candidate public study: not yet

## Criteria

- Candidate config materialized: 100% | Arquivo candidato encontrado em C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_inputs\study_real_data_candidate_config.toml. | Next: Gerar o candidate config a partir do tracker validado antes de tentar promover a coorte.
- Validated changes applied: 0% | 0/6 tarefa(s) validada(s) e 0 alteracao(oes) aplicada(s) no candidate config. | Next: Continuar fechando e aplicando as tarefas validadas do tracker ate reduzir o gap operacional.
- Candidate resolution gate: 0% | Ainda nao ha base suficiente para promover a configuracao candidata a uma nova resolucao. | Next: Validar pelo menos uma entrega real no tracker para liberar a promocao do candidate config.
- Candidate public-study gate: 0% | Ainda existem 6 tarefa(s) pendente(s) antes da rerrodada controlada do estudo. | Next: Zerar tarefas pendentes e invalidas no tracker para rerrodar o public-study-run com confianca.

## Blockers

- [critical] Tarefas criticas do tracker continuam abertas: Existem 6 tarefa(s) critica(s) ainda pendente(s) no handoff. | Next: Fechar primeiro as tarefas criticas para reduzir risco na promocao do candidate config.
- [high] Candidate config ainda nao esta pronto para a rerrodada final: A aplicacao do handoff esta em 0% e ainda ha pendencias abertas. | Next: Usar o pacote de reconciliacao para fechar as pendencias restantes antes de rerrodar o estudo publico.

## Commands

- Candidate public study run: `primevarclass --study-config "C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_inputs\study_real_data_candidate_config.toml" --public-study-run --output-dir "C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_inputs\candidate_public_study_run"`

## Recommended Actions

- Concluir validacoes suficientes no tracker para liberar a promocao do candidate config.