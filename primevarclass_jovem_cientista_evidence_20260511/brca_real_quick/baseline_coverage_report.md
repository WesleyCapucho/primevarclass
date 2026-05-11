# Baseline and Ablation Coverage

- Generated at: 2026-05-11T05:09:16Z
- Declared baseline: external_predictors_only
- Overall coverage: 74%

## Criteria

### Declared baseline presence

- Score: 0%
- Status: gap
- Evidence: Baseline 'external_predictors_only' nao esta no ranking interno e nao esta nas comparacoes externas.
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

- Score: 100%
- Status: ready
- Evidence: Melhor experimento com sinal primo/hibrido: hybrid__logistic_regression com delta AUC-ROC=0.5175.
- Next step: Buscar ganho consistente do bloco primo/hibrido contra o baseline declarado em dados reais.

## Feature-set Coverage

- prime_only: present (core_ablation)
- biochemical_only: present (core_ablation)
- hybrid: present (core_ablation)
- hybrid_plus_conservation: present (core_ablation)
- hybrid_plus_conservation_structure: present (core_ablation)
- hybrid_plus_external: present (core_ablation)
- external_predictors_only: present (core_ablation)
- gene_balanced_specialist: present (additional)

## Prime vs Baseline

- bridges_like_external_validation_brca1: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0437 [-0.1671, 0.0904]
- bridges_like_external_validation_brca1: hybrid__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0486 [-0.1653, 0.0959]
- bridges_like_external_validation_brca1: hybrid_plus_conservation__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0486 [-0.1653, 0.0959]
- bridges_like_external_validation_brca1: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0486 [-0.1653, 0.0959]
- bridges_like_external_validation_brca1: prime_only__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0907 [-0.2481, 0.0406]
- bridges_like_external_validation_brca2: hybrid__logistic_regression vs external_predictors_only__logistic_regression => delta=0.5175 [0.3516, 0.7461]
- bridges_like_external_validation_brca2: hybrid_plus_conservation__logistic_regression vs external_predictors_only__logistic_regression => delta=0.5175 [0.3516, 0.7461]
- bridges_like_external_validation_brca2: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.5175 [0.3516, 0.7461]
- bridges_like_external_validation_brca2: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.4979 [0.3222, 0.7318]
- bridges_like_external_validation_brca2: prime_only__logistic_regression vs external_predictors_only__logistic_regression => delta=0.3131 [0.0615, 0.5593]
- clinvar_expert_external_validation_brca1: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.0229 [-0.0801, 0.0943]
- clinvar_expert_external_validation_brca1: hybrid__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0008 [-0.1092, 0.0764]
- clinvar_expert_external_validation_brca1: hybrid_plus_conservation__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0008 [-0.1092, 0.0764]
- clinvar_expert_external_validation_brca1: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0008 [-0.1092, 0.0764]
- clinvar_expert_external_validation_brca1: prime_only__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0697 [-0.1764, 0.0266]
- clinvar_expert_external_validation_brca2: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1376 [0.0491, 0.2421]
- clinvar_expert_external_validation_brca2: hybrid__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1374 [0.0491, 0.2417]
- clinvar_expert_external_validation_brca2: hybrid_plus_conservation__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1374 [0.0491, 0.2417]
- clinvar_expert_external_validation_brca2: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1263 [0.0403, 0.2222]
- clinvar_expert_external_validation_brca2: prime_only__logistic_regression vs external_predictors_only__logistic_regression => delta=0.0035 [-0.1160, 0.1509]