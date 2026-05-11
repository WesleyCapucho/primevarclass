# PrimeVarClass Multigene Rollout

- Generated at: `2026-04-18T06:01:48Z`
- Overall rollout readiness: `77%`
- Phase 1 genes: `TP53`
- Phase 2 genes: `GCK, PTEN, MSH2, F9, KRAS`
- Prime top candidate gene: `TP53`

## Recommended Actions
- Abrir a proxima rodada real pelos genes da phase_1 com treino multicohorte e holdouts externos separados.
- Usar o bloco de numeros primos como eixo explicativo priorizando o gene mais alinhado ao prime-intelligence.
- Reservar os genes da phase_2 para expansao logo apos estabilizar os manifests reais da phase_1.

## Rollout Table

| gene | rank | rollout_phase | expansion_priority_percent | priority_band | clinvar_labeled_rows | clinvar_expert_rows | mavedb_score_set_count | mavedb_score_rows | gnomad_direct_api_ready | prime_priority | training_strategy | recommended_validation_stack |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP53 | 1 | phase_1_immediate | 85.3 | ready | 784 | 254 | 15 | 53905 | True | high | full_multicohort_train_plus_external_validation | clinical_holdout + functional_assay + population_annotations |
| GCK | 2 | phase_2_expansion | 77.4 | strong | 756 | 516 | 3 | 26950 | True | high | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| PTEN | 3 | phase_2_expansion | 74.5 | strong | 505 | 168 | 6 | 25537 | True | high | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| MSH2 | 4 | phase_2_expansion | 73.9 | strong | 858 | 150 | 3 | 18606 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| F9 | 5 | phase_2_expansion | 72.3 | strong | 436 | 70 | 7 | 49270 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| KRAS | 6 | phase_2_expansion | 70.6 | strong | 152 | 16 | 30 | 200525 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| MLH1 | 7 | phase_3_exploration | 68.6 | promising | 466 | 258 | 2 | 10112 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| SPTAN1 | 8 | phase_3_exploration | 67.4 | promising | 298 | 0 | 42 | 79722 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| KCNQ2 | 9 | phase_3_exploration | 64.8 | promising | 800 | 0 | 18 | 2057 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |
| OBSCN | 10 | phase_3_exploration | 60.9 | promising | 1430 | 0 | 3 | 10797 | True | medium | staged_training_then_external_lock | clinical_holdout + functional_assay + population_annotations |