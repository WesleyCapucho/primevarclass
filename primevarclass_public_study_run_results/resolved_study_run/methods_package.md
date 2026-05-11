# Public BRCA Benchmark Example - Methods Package

- Generated at: 2026-04-03T04:33:16Z
- Study name: Public BRCA Benchmark Example
- Primary metric: auc_roc
- Baseline experiment: external_predictors_only
- Bootstrap replicates: 100

## Cohort Methods Snapshot

- public_brca_training: role=train, n=4, classes=2, source_tables=3
- bridges_like_external_validation: role=external_test, n=4, classes=2, source_tables=3

## Model Families

- random_forest: n=7, best AUC-ROC=0.5000, best AUC-PR=0.5000

## Best Internal Configuration

- biochemical_only (random_forest) with AUC-ROC=0.5000, AUC-PR=0.5000, MCC=0.0000.

## Data Provenance Snapshot

- public_brca_training: clinvar_variant_summary (file/cohort) preset=clinvar_variant_summary | provenance=yes
- public_brca_training: gnomad_brca_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- public_brca_training: mavedb_brca_scores (file/annotation) preset=mavedb_score_table | provenance=yes
- bridges_like_external_validation: bridges_like_validation (file/cohort) preset=clinvar_variant_summary | provenance=yes
- bridges_like_external_validation: gnomad_validation_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- bridges_like_external_validation: mavedb_validation_scores (file/annotation) preset=mavedb_score_table | provenance=yes

## Reproducibility Checklist

- Study config declared: yes (Public BRCA Benchmark Example)
- Training metrics exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_training_metrics.csv)
- Repeated holdout exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_repeated_holdout.csv)
- External evaluation exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_external_evaluation.csv)
- Pairwise comparison exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_external_pairwise.csv)
- Cohort independence audit exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\cohort_independence_manifest.json)
- Real-data cohort freeze exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\study_cohort_freeze_manifest.json)
- Claim strength package exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\claim_strength_manifest.json)
- Model registry exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_public_study_run_results\resolved_study_run\models\model_registry.csv)
- Per-cohort data release manifests exported: yes (2)

## Cohort Independence Audit

- Independence score: 100%
- Max train/external overlap: 0%
- Ready for external validation: yes

## Real-data Cohort Freeze

- Real-data readiness: 19%
- Ready for real-data study: not yet
- Example-blocked cohorts: 2

## Claim Strength Audit

- Claim strength: 37%
- Claim tier: insufficient
- Candidate experiment: hybrid_plus_external

## Notes

- Este pacote resume desenho experimental, familias de modelo, proveniencia de dados e itens minimos de reproducibilidade.
- O texto pode ser adaptado para a secao de Metodos do manuscrito e para materiais suplementares.