# Public BRCA Benchmark Example - Manuscript Package

- Generated at: 2026-04-03T04:33:16Z
- Study: Public BRCA Benchmark Example
- Cohorts: 2
- Best internal experiment: biochemical_only (AUC-ROC=0.5000)
- Best external experiment: external_predictors_only (AUC-ROC=1.0000)
- Best pairwise delta AUC-ROC: consensus_top3 (0.0000)
- Cohort independence audit: 100%
- Real-data cohort freeze: 19%
- Claim strength audit: 37% (insufficient)

## Table Inventory

- Table 1: cohort design and release coverage
- Table 2: best internal experiment per feature set
- Table 3: combined external evaluation matrix
- Table 4: pairwise external delta AUC-ROC vs baseline

## Cohort Snapshot

- public_brca_training: role=train, n=4, release=45%, schema=100%
- bridges_like_external_validation: role=external_test, n=4, release=45%, schema=100%

## Internal Results Snapshot

- biochemical_only: biochemical_only (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- external_predictors_only: external_predictors_only (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- hybrid: hybrid (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- hybrid_plus_conservation: hybrid_plus_conservation (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- hybrid_plus_conservation_structure: hybrid_plus_conservation_structure (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- hybrid_plus_external: hybrid_plus_external (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- prime_only: prime_only (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)

## External Results Snapshot

- bridges_like_external_validation: external_predictors_only (AUC-ROC=1.0000, AUC-PR=1.0000, MCC=1.0000)

## Pairwise Deltas

- bridges_like_external_validation: consensus_top3 vs external_predictors_only => delta=0.0000 [0.0000, 0.0000]

## Figure Inventory

- Figure 1: internal AUC-ROC leaderboard by feature set
- Figure 2: external AUC-ROC leaderboard by cohort

## Notes

- Este pacote organiza tabelas e figuras para reaproveitamento direto no manuscrito.
- A independencia entre coortes foi auditada em 100%, reforcando a validade da avaliacao externa.
- A prontidao de dados reais ficou em 19%, ajudando a separar infraestrutura de evidencia biologica final.
- A forca da alegacao comparativa ficou em 37% (insufficient) para orientar a narrativa do artigo.
- Resultados baseados em datasets de exemplo servem para validar infraestrutura, nao para conclusao biologica final.