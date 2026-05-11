# Public BRCA Benchmark Example - Scientific Dossier

- Generated at: 2026-04-03T04:33:16Z

## Executive Summary

- Best internal experiment: biochemical_only (AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000)
- bridges_like_external_validation: external_predictors_only (AUC-ROC=1.0000, AUC-PR=1.0000, MCC=1.0000)
- Cohort independence: 100% (max overlap=0%).
- Real-data cohort freeze: 19% (ready=not yet).

## Cohort Manifest

- public_brca_training (train): n=4, classes=2, source_tables=3
- bridges_like_external_validation (external_test): n=4, classes=2, source_tables=3

## Consensus Strategy

- Consensus members: biochemical_only, external_predictors_only, hybrid

## Pairwise Deltas

- bridges_like_external_validation: hybrid_plus_external vs external_predictors_only delta=0.0000 [0.0000, 0.0000]

## Artifact Package

- training_metrics_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_training_metrics.csv
- study_summary_report_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_summary_report.txt
- external_evaluation_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_external_evaluation.csv
- external_pairwise_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_external_pairwise.csv
- cohort_independence_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\cohort_independence_manifest.json
- study_cohort_freeze_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_cohort_freeze_manifest.json
- consensus_members_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_consensus_members.csv
- model_registry_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\models\model_registry.csv

## Interpretation Notes

- Este dossie resume desempenho interno, validacao externa, comparacoes bootstrap, freeze de coortes reais e a forca da alegacao cientifica.
- As conclusoes devem ser acompanhadas de curadoria dos datasets e revisao biologica especializada antes de uso clinico.