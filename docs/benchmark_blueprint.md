# Benchmark blueprint

## Objetivo

Esta camada organiza o projeto no formato esperado por um estudo publicavel:

- uma coorte principal de treino
- uma ou mais coortes externas de validacao
- um conjunto fixo de experimentos de ablation
- tabelas exportadas para comparacao quantitativa

## Arquivo de estudo

O arquivo TOML de estudo define:

- nome do estudo
- modo de encoding
- baseline de comparacao
- numero de bootstraps
- familias de modelos opcionais em `model_families`
- tamanho do consenso automatico em `consensus_top_k`
- coortes com `role = "train"` ou `role = "external_test"`

Exemplo executavel:

- `configs/public_brca_benchmark_example.toml`

## Saidas principais

- `study_cohort_manifest.csv`
- `study_training_metrics.csv`
- `resolved_study_config.toml` when the public-study resolver is used before benchmark execution
- `study_public_config_resolution_manifest.json` for frozen cohort/source resolution
- `cohort_independence_report.md`
- `cohort_independence_report.html`
- `cohort_independence_manifest.json`
- `study_execution_board.md`
- `study_execution_board.html`
- `study_execution_board_manifest.json`
- `translational_pilot_package.md`
- `translational_pilot_package.html`
- `translational_pilot_package_manifest.json`
- `final_mile_package.md`
- `final_mile_package.html`
- `final_mile_package_manifest.json`
- `study_real_data_handoff_tracker.csv`
- `study_real_data_handoff_autofill.md`
- `study_real_data_handoff_autofill_manifest.json`
- `study_real_data_handoff_reconciliation.md`
- `study_real_data_handoff_reconciliation_manifest.json`
- `study_real_data_candidate_promotion.md`
- `study_real_data_candidate_promotion_manifest.json`
- `translational_impact_package.md`
- `translational_impact_package_manifest.json`
- `platform_completion.md`
- `platform_completion_manifest.json`
- `candidate_public_run_report.md`
- `candidate_public_run_manifest.json`
- `public_study_run_manifest.json`
- `public_study_run_report.md`
- `publication_readiness_report.md`
- `publication_readiness_report.html`
- `publication_readiness_manifest.json`
- `publication_readiness_criteria.csv`
- `publication_readiness_external_evidence.csv`
- `comparative_evidence_report.md`
- `comparative_evidence_report.html`
- `comparative_evidence_manifest.json`
- `comparative_evidence_experiments.csv`
- `comparative_evidence_feature_sets.csv`
- `claim_strength_report.md`
- `claim_strength_report.html`
- `claim_strength_manifest.json`
- `claim_strength_candidates.csv`
- `claim_strength_head_to_head.csv`
- `baseline_coverage_report.md`
- `baseline_coverage_report.html`
- `baseline_coverage_feature_sets.csv`
- `baseline_coverage_prime_vs_baseline.csv`
- `study_validation_lock.md`
- `study_validation_lock.html`
- `study_validation_lock_manifest.json`
- `methods_package.md`
- `methods_package.html`
- `methods_package_checklist.csv`
- `methods_package_sources.csv`
- `manuscript_package.md`
- `manuscript_package.html`
- `manuscript_table_internal.csv`
- `manuscript_table_external.csv`
- `manuscript_figure_internal_auc_roc.svg`
- `manuscript_figure_external_auc_roc.svg`
- `study_repeated_holdout.csv`
- `study_best_by_feature_set.csv`
- `study_model_family_summary.csv`
- `study_consensus_members.csv`
- `study_external_evaluation.csv`
- `study_external_pairwise.csv`
- `study_external_consensus.csv`
- `study_summary_report.txt`

## Perguntas cientificas que esse runner ajuda a responder

1. O encoding primo melhora o desempenho interno em relacao aos baselines?
2. O ganho se mantem em coortes externas?
3. O modelo continua competitivo contra sinais externos isolados?
4. Quais features carregam mais informacao no treino?
5. Qual a diferenca de AUC e AUPR contra o baseline externo em bootstrap?
6. Qual familia de modelos generaliza melhor?
7. Um consenso dos melhores experimentos melhora a robustez externa?

## Estrategia recomendada para artigo

- usar ClinVar curado como treino principal
- usar uma coorte independente tipo BRIDGES/ENIGMA/MAVE como validacao externa
- comparar pelo menos uma familia linear e uma familia de arvores
- reportar o desempenho do consenso dos melhores experimentos internos
- reportar:
  - AUC-ROC
  - AUC-PR
  - MCC
  - sensibilidade
  - especificidade
  - delta vs baseline com IC95%

## Proximo passo natural

Substituir os arquivos real-like do exemplo pelos datasets publicos reais baixados e curados no workspace, resolver os catalogos publicos para TOMLs congelados, fechar o `cohort freeze` em modo real-data, usar o `real-data handoff` para orientar a aquisicao final e executar o fluxo publico integrado ate o execution board final, elevando comparative evidence e claim strength ate um estado apto a submission lock e shadow-mode translacional.
