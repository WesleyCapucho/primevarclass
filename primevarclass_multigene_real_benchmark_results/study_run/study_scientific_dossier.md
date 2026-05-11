# PrimeVarClass Multigene ClinVar Benchmark - Scientific Dossier

- Generated at: 2026-04-24T05:25:38Z

## Executive Summary

- Best internal experiment: biochemical_only__logistic_regression (AUC-ROC=0.9380, AUC-PR=0.9402, MCC=0.7409)
- f9_combined_external_validation: hybrid_plus_conservation (AUC-ROC=0.8365, AUC-PR=0.9690, MCC=0.1205)
- gck_combined_external_validation: biochemical_only (AUC-ROC=0.7909, AUC-PR=0.9926, MCC=0.2403)
- kras_combined_external_validation: biochemical_only (AUC-ROC=-, AUC-PR=-, MCC=-)
- msh2_combined_external_validation: biochemical_only (AUC-ROC=0.8295, AUC-PR=0.9007, MCC=0.3491)
- multigene_combined_external_validation: biochemical_only (AUC-ROC=0.8298, AUC-PR=0.9603, MCC=0.3555)
- pten_combined_external_validation: hybrid_plus_conservation_structure (AUC-ROC=0.7816, AUC-PR=0.9899, MCC=0.1046)
- tp53_combined_external_validation: gene_balanced_specialist (AUC-ROC=0.7367, AUC-PR=0.8638, MCC=0.3058)
- Cohort independence: 100% (max overlap=0%).
- Real-data cohort freeze: 52% (ready=not yet).

## Cohort Manifest

- multigene_training (train): n=580, classes=2, source_tables=1
- multigene_combined_external_validation (external_test): n=978, classes=2, source_tables=1
- tp53_combined_external_validation (external_test): n=264, classes=2, source_tables=1
- pten_combined_external_validation (external_test): n=167, classes=2, source_tables=1
- msh2_combined_external_validation (external_test): n=164, classes=2, source_tables=1
- kras_combined_external_validation (external_test): n=32, classes=1, source_tables=1
- gck_combined_external_validation (external_test): n=289, classes=2, source_tables=1
- f9_combined_external_validation (external_test): n=62, classes=2, source_tables=1

## Consensus Strategy

- Consensus members: biochemical_only__logistic_regression, hybrid__logistic_regression, hybrid_plus_conservation__logistic_regression

## Pairwise Deltas

- Pairwise bootstrap deltas unavailable.

## Artifact Package

- training_metrics_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_training_metrics.csv
- study_summary_report_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_summary_report.txt
- external_evaluation_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_external_evaluation.csv
- external_pairwise_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_external_pairwise.csv
- cohort_independence_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\cohort_independence_manifest.json
- study_cohort_freeze_manifest_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_cohort_freeze_manifest.json
- consensus_members_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\study_consensus_members.csv
- model_registry_path: C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_multigene_real_benchmark_results\study_run\models\model_registry.csv

## Interpretation Notes

- Este dossie resume desempenho interno, validacao externa, comparacoes bootstrap, freeze de coortes reais e a forca da alegacao cientifica.
- As conclusoes devem ser acompanhadas de curadoria dos datasets e revisao biologica especializada antes de uso clinico.