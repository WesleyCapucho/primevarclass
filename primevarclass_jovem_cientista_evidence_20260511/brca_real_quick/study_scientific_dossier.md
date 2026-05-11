# Jovem Cientista BRCA Real Evidence Quick Pass - Scientific Dossier

- Generated at: 2026-05-11T05:05:58Z

## Executive Summary

- Best internal experiment: hybrid_plus_external__logistic_regression (AUC-ROC=0.8089, AUC-PR=0.5676, MCC=0.4039)
- bridges_like_external_validation_brca1: external_predictors_only__logistic_regression (AUC-ROC=0.5904, AUC-PR=0.1782, MCC=0.0923)
- bridges_like_external_validation_brca2: hybrid__logistic_regression (AUC-ROC=0.7509, AUC-PR=0.1539, MCC=0.1612)
- clinvar_expert_external_validation_brca1: gene_balanced_specialist (AUC-ROC=0.9223, AUC-PR=0.8640, MCC=0.6170)
- clinvar_expert_external_validation_brca2: biochemical_only__logistic_regression (AUC-ROC=0.7764, AUC-PR=0.5427, MCC=0.4173)
- Cohort independence: 100% (max overlap=0%).
- Real-data cohort freeze: 100% (ready=yes).

## Cohort Manifest

- public_brca_training (train): n=869, classes=2, source_tables=3
- clinvar_expert_external_validation_brca1 (external_test): n=204, classes=2, source_tables=3
- clinvar_expert_external_validation_brca2 (external_test): n=175, classes=2, source_tables=3
- bridges_like_external_validation_brca1 (external_test): n=168, classes=2, source_tables=3
- bridges_like_external_validation_brca2 (external_test): n=289, classes=2, source_tables=3

## Consensus Strategy

- Consensus members: hybrid_plus_external__logistic_regression, hybrid__logistic_regression, hybrid_plus_conservation__logistic_regression

## Pairwise Deltas

- bridges_like_external_validation_brca1: gene_balanced_specialist vs external_predictors_only__logistic_regression delta=-0.0071 [-0.1444, 0.1359]
- bridges_like_external_validation_brca2: hybrid__logistic_regression vs external_predictors_only__logistic_regression delta=0.5175 [0.3516, 0.7461]
- clinvar_expert_external_validation_brca1: gene_balanced_specialist vs external_predictors_only__logistic_regression delta=0.1704 [0.0918, 0.2292]
- clinvar_expert_external_validation_brca2: hybrid_plus_conservation_structure__logistic_regression vs external_predictors_only__logistic_regression delta=0.1376 [0.0491, 0.2421]

## Artifact Package

- training_metrics_path: primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_training_metrics.csv
- study_summary_report_path: primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_summary_report.txt
- external_evaluation_path: primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_external_evaluation.csv
- external_pairwise_path: primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_external_pairwise.csv
- cohort_independence_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\cohort_independence_manifest.json
- study_cohort_freeze_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_cohort_freeze_manifest.json
- consensus_members_path: primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_consensus_members.csv
- model_registry_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\models\model_registry.csv

## Interpretation Notes

- Este dossie resume desempenho interno, validacao externa, comparacoes bootstrap, freeze de coortes reais e a forca da alegacao cientifica.
- As conclusoes devem ser acompanhadas de curadoria dos datasets e revisao biologica especializada antes de uso clinico.