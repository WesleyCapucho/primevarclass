# Claim Strength Package

- Generated at: 2026-05-11T05:08:02Z
- Study: Jovem Cientista BRCA Real Evidence Quick Pass
- Selected candidate: hybrid_plus_external__logistic_regression
- Baseline comparator: external_predictors_only__logistic_regression
- Claim strength: 98%
- Claim tier: strong
- Statement: O experimento hybrid_plus_external__logistic_regression sustenta uma alegacao forte de superioridade contra external_predictors_only__logistic_regression nas coortes externas auditadas.
- Pooled support: AUC-ROC=100% | cross-metric=100%

## Criteria

### External cohort depth

- Score: 100%
- Status: ready
- Critical: no
- Evidence: 4 coorte(s) externas sustentam o experimento candidato.
- Next step: Aumentar o numero de coortes externas independentes para sustentar uma alegacao mais forte.

### Pairwise multi-metric coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das combinacoes coorte-metrica foram materializadas para o candidato.
- Next step: Garantir AUC-ROC e AUC-PR pareados contra baseline em todas as coortes externas.

### Supported AUC-ROC gain

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 50% das coortes externas mostram ganho AUC-ROC com IC inferior > 0, enquanto o pooled multicohorte ficou em 100% com delta 0.2195.
- Next step: Buscar suporte estatistico do ganho AUC-ROC em mais coortes externas reais e preservar o suporte pooled multicohorte.

### High-confidence clinical holdout

- Score: 100%
- Status: ready
- Critical: no
- Evidence: Nas coortes clinicas de alta confianca, o candidato teve 100% de ganho positivo em AUC-ROC, 100% de vitorias diretas e 100% sem regressao relevante, com credibilidade clinica agregada em 100%.
- Next step: Transformar a lideranca nas coortes clinicas de alta confianca em suporte estatistico mais estrito.

### Aggregate AUC-ROC direction

- Score: 100%
- Status: ready
- Critical: no
- Evidence: 100% de confianca direcional no meta-agregado em AUC-ROC e 100% no pooled multicohorte, com delta pooled 0.2195.
- Next step: Fortalecer o efeito agregado ate convergir para suporte estrito e nao apenas direcional.

### Cross-metric support

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 50% das coortes externas sustentam ganho simultaneo em AUC-ROC e AUC-PR, com pooled em 100%.
- Next step: Fortalecer o sinal em mais de uma metrica para sustentar a alegacao central do paper.

### Head-to-head external win rate

- Score: 92%
- Status: ready
- Critical: yes
- Evidence: 75% das comparacoes externas diretas superam o baseline em AUC-ROC, AUC-PR ou MCC, com lideranca efetiva em 92%.
- Next step: Aumentar a taxa de vitoria direta do candidato nas metricas externas centrais.

### No-regression safety

- Score: 92%
- Status: ready
- Critical: yes
- Evidence: 75% das comparacoes externas nao mostram regressao relevante frente ao baseline, com seguranca efetiva em 92%.
- Next step: Reduzir sinais de regressao antes de sustentar uma alegacao forte de superioridade.

## Candidate Ranking

- hybrid_plus_external__logistic_regression: claim=98% (strong), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- hybrid_plus_conservation_structure__logistic_regression: claim=97% (moderate), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- hybrid__logistic_regression: claim=97% (moderate), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- hybrid_plus_conservation__logistic_regression: claim=97% (moderate), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- gene_balanced_specialist: claim=96% (strong), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- consensus_top3: claim=95% (strong), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- biochemical_only__logistic_regression: claim=94% (moderate), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=92%.
- prime_only__logistic_regression: claim=89% (suggestive), AUC-ROC support=100%, aggregate AUC-ROC=100%, cross-metric=100%, leadership=67%.

## Head-to-Head Evidence

- bridges_like_external_validation_brca1 | auc_roc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0342 (no win, regression risk).
- bridges_like_external_validation_brca1 | auc_pr: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0071 (no win, regression risk).
- bridges_like_external_validation_brca1 | mcc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0878 (no win, regression risk).
- bridges_like_external_validation_brca2 | auc_roc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.4533 (win, safe).
- bridges_like_external_validation_brca2 | auc_pr: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.0980 (win, safe).
- bridges_like_external_validation_brca2 | mcc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.2466 (win, safe).
- clinvar_expert_external_validation_brca1 | auc_roc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.0352 (win, safe).
- clinvar_expert_external_validation_brca1 | auc_pr: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.0830 (win, safe).
- clinvar_expert_external_validation_brca1 | mcc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.3281 (win, safe).
- clinvar_expert_external_validation_brca2 | auc_roc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1109 (win, safe).
- clinvar_expert_external_validation_brca2 | auc_pr: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1959 (win, safe).
- clinvar_expert_external_validation_brca2 | mcc: hybrid_plus_external__logistic_regression vs external_predictors_only__logistic_regression => delta=0.2863 (win, safe).
- bridges_like_external_validation_brca1 | auc_roc: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0400 (no win, regression risk).
- bridges_like_external_validation_brca1 | auc_pr: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0090 (no win, regression risk).
- bridges_like_external_validation_brca1 | mcc: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=-0.0743 (no win, regression risk).
- bridges_like_external_validation_brca2 | auc_roc: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.4725 (win, safe).
- bridges_like_external_validation_brca2 | auc_pr: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.1126 (win, safe).
- bridges_like_external_validation_brca2 | mcc: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression => delta=0.3035 (win, safe).

## Recommended Actions

- A alegacao comparativa parece pronta para consolidacao final.