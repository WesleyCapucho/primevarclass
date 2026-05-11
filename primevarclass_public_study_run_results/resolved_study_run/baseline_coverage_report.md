# Baseline and Ablation Coverage

- Generated at: 2026-04-03T04:33:16Z
- Declared baseline: external_predictors_only
- Overall coverage: 79%

## Criteria

### Declared baseline presence

- Score: 100%
- Status: ready
- Evidence: Baseline 'external_predictors_only' esta no ranking interno e esta nas comparacoes externas.
- Next step: Garantir que o baseline declarado esteja presente no treino e nas comparacoes externas.

### Core ablation coverage

- Score: 100%
- Status: ready
- Evidence: 7/7 feature sets centrais de ablation estao presentes.
- Next step: Completar os feature sets centrais para sustentar a narrativa de ablation.

### Pairwise external coverage

- Score: 100%
- Status: ready
- Evidence: 100% das coortes externas possuem comparacao pareada AUC-ROC.
- Next step: Materializar comparacao pareada para todas as coortes externas do estudo.

### Prime-signal vs baseline

- Score: 25%
- Status: gap
- Evidence: Melhor experimento com sinal primo/hibrido: hybrid_plus_external com delta AUC-ROC=0.0000.
- Next step: Buscar ganho consistente do bloco primo/hibrido contra o baseline declarado em dados reais.

## Feature-set Coverage

- prime_only: present (core_ablation)
- biochemical_only: present (core_ablation)
- hybrid: present (core_ablation)
- hybrid_plus_conservation: present (core_ablation)
- hybrid_plus_conservation_structure: present (core_ablation)
- hybrid_plus_external: present (core_ablation)
- external_predictors_only: present (core_ablation)

## Prime vs Baseline

- bridges_like_external_validation: hybrid_plus_external vs external_predictors_only => delta=0.0000 [0.0000, 0.0000]
- bridges_like_external_validation: hybrid_plus_conservation vs external_predictors_only => delta=-0.8509 [-1.0000, -0.5000]
- bridges_like_external_validation: hybrid_plus_conservation_structure vs external_predictors_only => delta=-0.8509 [-1.0000, -0.5000]
- bridges_like_external_validation: hybrid vs external_predictors_only => delta=-1.0000 [-1.0000, -1.0000]
- bridges_like_external_validation: prime_only vs external_predictors_only => delta=-1.0000 [-1.0000, -1.0000]