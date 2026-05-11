# External Robustness Package

- Generated at: 2026-05-11T05:09:16Z
- Selected candidate: hybrid_plus_external__logistic_regression
- Selection basis: claim_strength
- Baseline comparator: external_predictors_only__logistic_regression
- Overall external robustness: 75%
- Exact sign confidence: 100%
- Pooled calibration support: 100%
- Pooled high-confidence clinical support: 100%

## Criteria

### External robustness coverage

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: Calibration in 100% and discrimination in 100% of external cohorts.
- Next step: Guarantee paired score files and external metrics for every frozen cohort.

### Calibration leadership

- Score: 88%
- Status: ready
- Critical: yes
- Evidence: Brier win=75%, ECE win=75% and separation win=100% with pooled support=100%.
- Next step: Improve external calibration and score separation against the declared baseline.

### Calibration safety

- Score: 50%
- Status: gap
- Critical: yes
- Evidence: 50% of external cohorts show no relevant calibration regression.
- Next step: Reduce calibration regressions before claiming stronger translational use.

### Discrimination robustness

- Score: 81%
- Status: partial
- Critical: yes
- Evidence: AUC-ROC win=75%, AUC-PR win=75% and MCC win=75% with pooled support=100%.
- Next step: Consolidate external wins across the core benchmark metrics.

### Exact sign confidence

- Score: 100%
- Status: ready
- Critical: yes
- Evidence: 100% directional confidence across external calibration and discrimination wins or losses.
- Next step: Increase directional confidence with more independent cohorts or stronger signal.

### High-confidence clinical robustness

- Score: 98%
- Status: ready
- Critical: yes
- Evidence: Robustness in high-confidence clinical cohorts = 93% (effective=98%) with pooled support=100%.
- Next step: Strengthen calibration and discrimination specifically in expert-grade clinical cohorts.

### Cross-cohort stability

- Score: 0%
- Status: gap
- Critical: no
- Evidence: Cross-cohort stability based on the spread of AUC-ROC deltas = 0%.
- Next step: Reduce heterogeneity across external cohorts and genes before framing the result as stable.

## Cohort Calibration

- bridges_like_external_validation_brca1: dBrier=-0.0295, dECE=0.0412, dSeparation=0.0492.
- bridges_like_external_validation_brca2: dBrier=0.1556, dECE=0.2907, dSeparation=0.1891.
- clinvar_expert_external_validation_brca1: dBrier=0.0198, dECE=-0.0383, dSeparation=0.2461.
- clinvar_expert_external_validation_brca2: dBrier=0.0732, dECE=0.1668, dSeparation=0.2171.

## Cohort Discrimination

- bridges_like_external_validation_brca1: dAUC-ROC=-0.0342, dAUC-PR=-0.0071, dMCC=-0.0878.
- bridges_like_external_validation_brca2: dAUC-ROC=0.4533, dAUC-PR=0.0980, dMCC=0.2466.
- clinvar_expert_external_validation_brca1: dAUC-ROC=0.0352, dAUC-PR=0.0830, dMCC=0.3281.
- clinvar_expert_external_validation_brca2: dAUC-ROC=0.1109, dAUC-PR=0.1959, dMCC=0.2863.

## Pooled Support

- all_external / brier_improvement: delta=0.0680, CI95=[0.0531, 0.0812], support=100%.
- all_external / ece_improvement: delta=0.1377, CI95=[0.1217, 0.1515], support=100%.
- all_external / score_separation: delta=0.2643, CI95=[0.2172, 0.3136], support=100%.
- all_external / auc_pr: delta=0.2318, CI95=[0.1676, 0.3061], support=100%.
- all_external / auc_roc: delta=0.2215, CI95=[0.1579, 0.2841], support=100%.
- all_external / mcc: delta=0.3043, CI95=[0.2067, 0.3986], support=100%.
- high_confidence_clinical / brier_improvement: delta=0.0445, CI95=[0.0197, 0.0649], support=100%.
- high_confidence_clinical / ece_improvement: delta=0.0614, CI95=[0.0287, 0.0793], support=100%.
- high_confidence_clinical / score_separation: delta=0.2616, CI95=[0.2022, 0.3176], support=100%.
- high_confidence_clinical / auc_pr: delta=0.1847, CI95=[0.0995, 0.2710], support=100%.
- high_confidence_clinical / auc_roc: delta=0.0876, CI95=[0.0216, 0.1501], support=100%.
- high_confidence_clinical / mcc: delta=0.3494, CI95=[0.2072, 0.4760], support=100%.