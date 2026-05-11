# Product blueprint

## Objetivo

Transformar o PrimeVarClass em uma ferramenta cientifica operavel por laboratorio, e nao apenas em um pipeline de pesquisa local.

## Camadas do produto

- Ingestao reprodutivel de dados multi-fonte
- Motor de modelagem com ablation e model zoo
- Benchmark publicavel com validacao externa
- Registry de modelos treinados com manifests versionados
- API cientifica para inferencia, treino e execucao de estudos
- Workbench web para uso interativo por pesquisadores e laboratorios
- Triagem em lote com ranking de prioridade e exportacao CSV/Markdown
- Fila assincrona com historico persistente para treinos e benchmarks longos
- API key opcional, perfis institucionais persistentes, times cientificos, trilha de auditoria, versionamento de releases, dashboards analiticos e relatorios por job

## Casos de uso imediatos

1. Um pesquisador executa um benchmark completo a partir de um TOML de estudo.
2. Um bioinformatas lista os modelos exportados e seleciona o melhor experimento.
3. Um laboratorio envia uma variante BRCA1/2 e recebe probabilidade, features usadas e resumo interpretavel.
4. Um pipeline externo integra o PrimeVarClass via HTTP sem depender de execucao manual em notebooks.
5. Um pesquisador sem perfil tecnico usa a workbench web para carregar modelos e consultar variantes.
6. Uma equipe de triagem cola dezenas de variantes e recebe uma lista priorizada para revisao.
7. Um benchmark longo roda em background enquanto a equipe acompanha status e artefatos pela interface.
8. Um laboratorio opera a plataforma com controle de acesso e rastreabilidade de eventos.
9. Uma equipe multiusuario registra perfis de operadores e preserva autoria institucional em jobs e auditoria.
10. Um laboratorio baixa relatorios formais para triagem em lote e revisao cientifica.
11. Um consorcio ou equipe cientifica opera por times, com contexto de pertencimento e governanca leve.
12. Um benchmark gera um dossie cientifico em Markdown e HTML pronto para reunioes, comites e manuscrito.
13. Um laboratorio compara duas rodadas de benchmark e mede ganho real por coorte externa.
14. Um gestor de time acompanha operacao, jobs e artefatos cientificos em um dashboard institucional.
15. Cada ingestao e cada estudo deixam manifests versionados para rastreabilidade reprodutivel.
16. O laboratorio acompanha a evolucao longitudinal de metricas entre versoes do benchmark.

## Artefatos de software agora disponiveis

- `model_registry.csv`
- `*_manifest.json` por experimento treinado
- API FastAPI com `/models`, `/predict/variant`, `/train/source-config` e `/study/run`
- Interface web em `/workbench` para operacao interativa
- Endpoint `/predict/batch` com classificacao em lote, tiers de prioridade e relatorio Markdown
- Endpoints `/jobs`, `/jobs/{job_id}`, `/jobs/train/source-config` e `/jobs/study/run`
- Endpoints `/users/context`, `/users/profiles`, `/teams/context`, `/teams`, `/auth/status`, `/audit/events` e download de `/jobs/{job_id}/report`
- Dossie cientifico exportado em `study_scientific_dossier.md` e `study_scientific_dossier.html`
- Pacote de publication readiness exportado em Markdown, HTML, JSON e CSVs de evidencia para criterios, coortes, fontes, artefatos e validacao externa
- Pacote de comparative evidence exportado em Markdown, HTML e CSVs para sustentar ganho contra baseline por coorte, experimento e feature set
- Pacote de claim strength exportado em Markdown, HTML e CSVs para classificar se a alegacao cientifica ja esta forte, moderada, sugestiva ou insuficiente
- Pacote de cohort independence exportado em Markdown, HTML e CSVs para auditar sobreposicao entre treino e validacao externa
- Pacote de cohort freeze exportado em Markdown, HTML, JSON e CSVs para deixar explicito se o estudo ainda depende de demo/example ou se ja esta congelado em coortes reais versionadas
- Pacote de real-data handoff exportado em Markdown, HTML, JSON e CSVs para transformar bloqueios cientificos em tarefas operacionais por coorte e por fonte
- Pacote translacional de piloto exportado em Markdown, HTML, JSON e CSVs para tornar explicito se a plataforma esta em demo mode, shadow mode ou live candidate
- Pacote final-mile exportado em Markdown, HTML, JSON e CSVs para priorizar os bloqueios finais rumo a dados reais, evidencia comparativa e submission closeout
- Tracker de handoff e pacote de reconciliacao para que o laboratorio marque tarefas como concluidas e o software valide automaticamente o fechamento
- Pacote de handoff autofill para varrer uma pasta de entrega do laboratorio, sugerir preenchimento do tracker e acelerar a substituicao dos arquivos demo/example
- Pacote de candidate promotion exportado em Markdown, HTML, JSON e CSVs para declarar quando o candidate config gerado ja pode ser promovido para a rerrodada controlada
- Registro persistente de sessoes de piloto e feedback de operadores para que a adocao no laboratorio seja medida, auditavel e institucionalizavel
- Pacote de impacto translacional exportado em Markdown, HTML, JSON e CSVs para consolidar rollout signal, satisfacao operacional e prontidao de institucionalizacao
- Pacote de platform completion exportado em Markdown, HTML e JSON para declarar o fechamento do desenvolvimento da plataforma sem mascarar a validacao cientifica real
- Runner dedicado de candidate public study para rerrodada controlada do benchmark a partir do candidate config e do pacote de promocao
- Pacote de baseline/ablation exportado em Markdown, HTML e CSVs para sustentar a tese comparativa do estudo
- Pacote de metodos e reproducibilidade exportado em Markdown, HTML e CSVs com checklist tecnico e proveniencia
- Pacote de manuscrito exportado em Markdown, HTML, tabelas CSV e figuras SVG para acelerar montagem de paper e apresentacoes cientificas
- Pacote de validation lock exportado em Markdown, HTML, JSON e CSV para consolidar readiness de validacao estatistica, submissao e piloto translacional
- Comparacao formal de estudos via `/study/compare` com relatorios e tabelas exportadas
- Dashboard operacional e cientifico por time via `/analytics/team-dashboard`
- Monitor longitudinal de estudos via `/monitoring/studies/longitudinal`
- Manifests `data_release_manifest.json` e `study_release_manifest.json` com registries CSV associados
- Proveniencia automatica por fonte nos manifests, com hash de arquivo, fingerprint de SQLite, metadata HTTP e hashes dos artefatos exportados
- Endpoint `/releases/manifest/load` e painel na `/workbench` para auditoria interativa de releases e proveniencia
- Endpoint `/roadmap/progress` e painel visual na `/workbench` com barras de progresso por macroetapa do produto
- Endpoint `/study/preflight` e painel na `/workbench` para validar configs e coortes antes de rodar benchmarks longos
- Endpoint `/study/bundle/inspect` e painel na `/workbench` para inspecionar publication readiness, cohort freeze, claim strength, validation lock, baseline coverage, methods e manuscript package de um estudo exportado
- Endpoint `/public-sources/catalog/inspect` e painel na `/workbench` para validar cobertura de release em catalogos publicos reais
- Planos de sincronizacao por fonte publica com entrypoints oficiais, estrategia de automacao e artefatos recomendados
- Bootstrap publico com execucao segura em `dry-run`, manifests de sync e historico persistente por fonte
- Endpoint `/public-sources/catalog/resolve` e painel na `/workbench` para congelar um catalogo publico em um TOML resolvido, apontando para artefatos staged ou arquivos locais versionados
- Endpoint `/study/public-config/resolve` e painel na `/workbench` para gerar uma configuracao de estudo resolvida, pronta para benchmark reprodutivel sem editar caminhos manualmente
- Endpoints `/study/public-run` e `/jobs/study/public-run` para executar o fluxo integrado de estudo publico: resolucao, preflight, benchmark e execution board
- `study_execution_board.md`, `study_execution_board.html` e `study_execution_board_manifest.json` para consolidar prontidao operacional, comparativa e translacional em um unico painel executivo
- `public_study_run_manifest.json` e `public_study_run_report.md` como pacote final do fluxo publico fim a fim
- `translational_pilot_package.md`, `translational_pilot_package.html` e `translational_pilot_package_manifest.json` como camada final de adocao para laboratorio e rollout controlado
- `final_mile_package.md`, `final_mile_package.html` e `final_mile_package_manifest.json` como camada de fechamento para a rodada cientifica final
- `study_real_data_handoff_tracker.csv` e `study_real_data_handoff_reconciliation_manifest.json` como camada de acompanhamento executavel do handoff
- `study_real_data_handoff_autofill.md`, `study_real_data_handoff_autofill_manifest.json` e `study_real_data_handoff_tracker_autofilled.csv` como camada intermediaria entre entrega do laboratorio e reconciliacao validada
- `study_real_data_candidate_promotion.md`, `study_real_data_candidate_promotion.html` e `study_real_data_candidate_promotion_manifest.json` como camada de promocao controlada do candidate config
- A workbench agora tambem destaca real-data readiness, handoff para laboratorio, claim strength e validation lock no painel de diagnostico, tornando mais visivel o estado cientifico real do estudo
- A camada publica final agora tambem deixa explicito o `pilot_mode` e a readiness para demo, shadow e live candidate
- Execucao oficial de bootstrap ja habilitada para ClinVar e MaveDB quando o catalogo fornece sinais de release suficientes
- Execucao controlada de recorte BRCA para gnomAD ja habilitada quando o catalogo aponta para uma tabela local exportada
- Staging auditavel de importacao curada ENIGMA ja habilitado quando o catalogo aponta para um arquivo local versionado
- Prontidao de benchmark publico calculada a partir do catalogo, do bootstrap e do historico operacional de sincronizacao

## Proximo salto de impacto social

- Grupos de usuarios, papeis e governanca institucional mais detalhada
- Interface web para upload de variantes e visualizacao de resultados
- Filas assicronas para estudos longos
- Curadoria real de ClinVar, gnomAD, MaveDB e ENIGMA com versionamento explicito
- Relatorios exportaveis para comites cientificos e laboratorios parceiros
- Monitoramento longitudinal de desempenho entre versoes do modelo e rodadas de benchmark
- Conectores reais com captura automatica de versao das fontes publicas
- Piloto assistido com coortes reais finais e feedback de laboratorio
