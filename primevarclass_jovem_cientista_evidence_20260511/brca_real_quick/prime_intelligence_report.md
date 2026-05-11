# Prime Intelligence

- Generated at: 2026-05-11T05:09:16Z
- Overall prime intelligence: 55%
- Tier: weak
- Best prime internal experiment: hybrid_plus_external__logistic_regression
- Best prime external experiment: hybrid__logistic_regression

## Criteria

### Internal prime competitiveness

- Score: 77%
- Status: promising
- Evidence: Melhor experimento primo/hibrido: hybrid_plus_external__logistic_regression vs melhor nao-primo: biochemical_only__logistic_regression (delta AUC-ROC=0.0062).
- Next step: Preservar o ganho interno do bloco primo/hibrido nas proximas rodadas multigene.

### External prime leadership

- Score: 36%
- Status: gap
- Evidence: Modelos primos/hibridos lideram 25% das coortes externas em AUC-ROC, com delta medio=-0.0448.
- Next step: Expandir a lideranca externa para novos genes e novas coortes clinicas independentes.

## External Prime Leadership

- bridges_like_external_validation_brca1: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta AUC-ROC=-0.0342
- bridges_like_external_validation_brca2: hybrid__logistic_regression vs consensus_top3 => delta AUC-ROC=0.0054
- clinvar_expert_external_validation_brca1: hybrid_plus_external__logistic_regression vs gene_balanced_specialist => delta AUC-ROC=-0.1451
- clinvar_expert_external_validation_brca2: hybrid_plus_conservation_structure__logistic_regression vs biochemical_only__logistic_regression => delta AUC-ROC=-0.0053