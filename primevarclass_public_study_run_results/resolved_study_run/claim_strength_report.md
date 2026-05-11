# Claim Strength Package

- Generated at: 2026-04-03T04:33:16Z
- Study: Public BRCA Benchmark Example
- Selected candidate: hybrid_plus_external
- Baseline comparator: external_predictors_only
- Claim strength: 37%
- Claim tier: insufficient
- Statement: A evidencia atual ainda nao sustenta uma alegacao robusta de ganho para hybrid_plus_external contra external_predictors_only.

## Criteria

### External cohort depth

- Score: 25%
- Status: gap
- Critical: no
- Evidence: 1 coorte(s) externas sustentam o experimento candidato.
- Next step: Aumentar o numero de coortes externas independentes para sustentar uma alegacao mais forte.

### Pairwise multi-metric coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% das combinacoes coorte-metrica foram materializadas para o candidato.
- Next step: Garantir AUC-ROC e AUC-PR pareados contra baseline em todas as coortes externas.

### Supported AUC-ROC gain

- Score: 0%
- Status: gap
- Critical: yes
- Evidence: 0% das coortes externas mostram ganho AUC-ROC com IC inferior > 0.
- Next step: Buscar suporte estatistico do ganho AUC-ROC em mais coortes externas reais.

### Cross-metric support

- Score: 0%
- Status: gap
- Critical: yes
- Evidence: 0% das coortes externas sustentam ganho simultaneo em AUC-ROC e AUC-PR.
- Next step: Fortalecer o sinal em mais de uma metrica para sustentar a alegacao central do paper.

### Head-to-head external win rate

- Score: 0%
- Status: gap
- Critical: yes
- Evidence: 0% das comparacoes externas diretas superam o baseline em AUC-ROC, AUC-PR ou MCC.
- Next step: Aumentar a taxa de vitoria direta do candidato nas metricas externas centrais.

### No-regression safety

- Score: 67%
- Status: partial
- Critical: yes
- Evidence: 67% das comparacoes externas nao mostram regressao relevante frente ao baseline.
- Next step: Reduzir sinais de regressao antes de sustentar uma alegacao forte de superioridade.

## Candidate Ranking

- hybrid_plus_external: claim=37% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- consensus_top3: claim=33% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- hybrid_plus_conservation: claim=26% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- hybrid_plus_conservation_structure: claim=26% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- hybrid: claim=26% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- prime_only: claim=26% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.
- biochemical_only: claim=22% (insufficient), AUC-ROC support=0%, cross-metric=0%, wins=0%.

## Head-to-Head Evidence

- bridges_like_external_validation | auc_roc: hybrid_plus_external vs external_predictors_only => delta=0.0000 (no win, safe).
- bridges_like_external_validation | auc_pr: hybrid_plus_external vs external_predictors_only => delta=0.0000 (no win, safe).
- bridges_like_external_validation | mcc: hybrid_plus_external vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_roc: hybrid_plus_conservation vs external_predictors_only => delta=-0.8333 (no win, regression risk).
- bridges_like_external_validation | auc_pr: hybrid_plus_conservation vs external_predictors_only => delta=-0.3611 (no win, regression risk).
- bridges_like_external_validation | mcc: hybrid_plus_conservation vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_roc: hybrid_plus_conservation_structure vs external_predictors_only => delta=-0.8333 (no win, regression risk).
- bridges_like_external_validation | auc_pr: hybrid_plus_conservation_structure vs external_predictors_only => delta=-0.3333 (no win, regression risk).
- bridges_like_external_validation | mcc: hybrid_plus_conservation_structure vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_roc: hybrid vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_pr: hybrid vs external_predictors_only => delta=-0.3333 (no win, regression risk).
- bridges_like_external_validation | mcc: hybrid vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_roc: prime_only vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_pr: prime_only vs external_predictors_only => delta=-0.3611 (no win, regression risk).
- bridges_like_external_validation | mcc: prime_only vs external_predictors_only => delta=-1.0000 (no win, regression risk).
- bridges_like_external_validation | auc_roc: consensus_top3 vs external_predictors_only => delta=0.0000 (no win, safe).
- bridges_like_external_validation | auc_pr: consensus_top3 vs external_predictors_only => delta=0.0000 (no win, safe).
- bridges_like_external_validation | mcc: consensus_top3 vs external_predictors_only => delta=-1.0000 (no win, regression risk).

## Recommended Actions

- Aumentar o numero de coortes externas independentes para sustentar uma alegacao mais forte.
- Buscar suporte estatistico do ganho AUC-ROC em mais coortes externas reais.
- Fortalecer o sinal em mais de uma metrica para sustentar a alegacao central do paper.
- Aumentar a taxa de vitoria direta do candidato nas metricas externas centrais.
- Reduzir sinais de regressao antes de sustentar uma alegacao forte de superioridade.