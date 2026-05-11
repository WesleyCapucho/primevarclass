# Jovem Cientista BRCA Real Evidence Quick Pass - Manuscript Package

- Generated at: 2026-05-11T05:09:17Z
- Study: Jovem Cientista BRCA Real Evidence Quick Pass
- Cohorts: 5
- Best internal experiment: biochemical_only__logistic_regression (AUC-ROC=0.8027)
- Best external experiment: external_predictors_only__logistic_regression (AUC-ROC=0.5904)
- Best pairwise delta AUC-ROC: gene_balanced_specialist (-0.0071)
- Cohort independence audit: 100%
- Real-data cohort freeze: 100%
- Claim strength audit: 98% (strong)

## Table Inventory

- Table 1: cohort design and release coverage
- Table 2: best internal experiment per feature set
- Table 3: combined external evaluation matrix
- Table 4: pairwise external delta AUC-ROC vs baseline

## Cohort Snapshot

- public_brca_training: role=train, n=869, release=92%, schema=100%
- clinvar_expert_external_validation_brca1: role=external_test, n=204, release=92%, schema=100%
- clinvar_expert_external_validation_brca2: role=external_test, n=175, release=92%, schema=100%
- bridges_like_external_validation_brca1: role=external_test, n=168, release=92%, schema=100%
- bridges_like_external_validation_brca2: role=external_test, n=289, release=92%, schema=100%

## Internal Results Snapshot

- biochemical_only: biochemical_only__logistic_regression (AUC-ROC=0.8027, AUC-PR=0.5660, MCC=0.4193)
- external_predictors_only: external_predictors_only__logistic_regression (AUC-ROC=0.5246, AUC-PR=0.2726, MCC=0.0363)
- gene_balanced_specialist: gene_balanced_specialist (AUC-ROC=0.7570, AUC-PR=0.4837, MCC=0.3501)
- hybrid: hybrid__logistic_regression (AUC-ROC=0.8062, AUC-PR=0.5613, MCC=0.4029)
- hybrid_plus_conservation: hybrid_plus_conservation__logistic_regression (AUC-ROC=0.8062, AUC-PR=0.5613, MCC=0.4029)
- hybrid_plus_conservation_structure: hybrid_plus_conservation_structure__logistic_regression (AUC-ROC=0.8062, AUC-PR=0.5613, MCC=0.4029)
- hybrid_plus_external: hybrid_plus_external__logistic_regression (AUC-ROC=0.8089, AUC-PR=0.5676, MCC=0.4039)
- prime_only: prime_only__logistic_regression (AUC-ROC=0.7104, AUC-PR=0.4534, MCC=0.2665)

## External Results Snapshot

- bridges_like_external_validation_brca1: external_predictors_only__logistic_regression (AUC-ROC=0.5904, AUC-PR=0.1782, MCC=0.0923)
- bridges_like_external_validation_brca2: hybrid__logistic_regression (AUC-ROC=0.7509, AUC-PR=0.1539, MCC=0.1612)
- clinvar_expert_external_validation_brca1: gene_balanced_specialist (AUC-ROC=0.9223, AUC-PR=0.8640, MCC=0.6170)
- clinvar_expert_external_validation_brca2: biochemical_only__logistic_regression (AUC-ROC=0.7764, AUC-PR=0.5427, MCC=0.4173)

## Pairwise Deltas

- bridges_like_external_validation_brca1: gene_balanced_specialist vs external_predictors_only__logistic_regression => delta=-0.0071 [-0.1444, 0.1359]
- bridges_like_external_validation_brca2: hybrid__logistic_regression vs external_predictors_only__logistic_regression => delta=0.5175 [0.3516, 0.7461]
- clinvar_expert_external_validation_brca1: gene_balanced_specialist vs external_predictors_only__logistic_regression => delta=0.1704 [0.0918, 0.2292]
- clinvar_expert_external_validation_brca2: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1376 [0.0491, 0.2421]

## Figure Inventory

- Figure 1: internal AUC-ROC leaderboard by feature set
- Figure 2: external AUC-ROC leaderboard by cohort

## Notes

- Este pacote organiza tabelas e figuras para reaproveitamento direto no manuscrito.
- A independencia entre coortes foi auditada em 100%, reforcando a validade da avaliacao externa.
- A prontidao de dados reais ficou em 100%, ajudando a separar infraestrutura de evidencia biologica final.
- A forca da alegacao comparativa ficou em 98% (strong) para orientar a narrativa do artigo.
- Resultados baseados em datasets de exemplo servem para validar infraestrutura, nao para conclusao biologica final.