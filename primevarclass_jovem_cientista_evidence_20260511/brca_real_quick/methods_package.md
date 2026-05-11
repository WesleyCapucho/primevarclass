# Jovem Cientista BRCA Real Evidence Quick Pass - Methods Package

- Generated at: 2026-05-11T05:09:17Z
- Study name: Jovem Cientista BRCA Real Evidence Quick Pass
- Primary metric: auc_roc
- Baseline experiment: external_predictors_only
- Bootstrap replicates: 20

## Cohort Methods Snapshot

- public_brca_training: role=train, n=869, classes=2, source_tables=3
- clinvar_expert_external_validation_brca1: role=external_test, n=204, classes=2, source_tables=3
- clinvar_expert_external_validation_brca2: role=external_test, n=175, classes=2, source_tables=3
- bridges_like_external_validation_brca1: role=external_test, n=168, classes=2, source_tables=3
- bridges_like_external_validation_brca2: role=external_test, n=289, classes=2, source_tables=3

## Model Families

- logistic_regression: n=7, best AUC-ROC=0.8089, best AUC-PR=0.5676
- gene_specialist: n=1, best AUC-ROC=0.7570, best AUC-PR=0.4837

## Best Internal Configuration

- hybrid_plus_external__logistic_regression (logistic_regression) with AUC-ROC=0.8089, AUC-PR=0.5676, MCC=0.4039.

## Data Provenance Snapshot

- public_brca_training: clinvar_variant_summary (file/cohort) preset=clinvar_variant_summary | provenance=yes
- public_brca_training: gnomad_brca_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- public_brca_training: mavedb_brca_scores (file/annotation) preset=mavedb_score_table | provenance=yes
- clinvar_expert_external_validation_brca1: clinvar_expert_validation_brca1 (file/cohort) preset=clinvar_variant_summary | provenance=yes
- clinvar_expert_external_validation_brca1: gnomad_validation_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- clinvar_expert_external_validation_brca1: mavedb_validation_scores (file/annotation) preset=mavedb_score_table | provenance=yes
- clinvar_expert_external_validation_brca2: clinvar_expert_validation_brca2 (file/cohort) preset=clinvar_variant_summary | provenance=yes
- clinvar_expert_external_validation_brca2: gnomad_validation_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- clinvar_expert_external_validation_brca2: mavedb_validation_scores (file/annotation) preset=mavedb_score_table | provenance=yes
- bridges_like_external_validation_brca1: bridges_like_validation_brca1 (file/cohort) preset=clinvar_variant_summary | provenance=yes
- bridges_like_external_validation_brca1: gnomad_validation_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- bridges_like_external_validation_brca1: mavedb_validation_scores (file/annotation) preset=mavedb_score_table | provenance=yes
- bridges_like_external_validation_brca2: bridges_like_validation_brca2 (file/cohort) preset=clinvar_variant_summary | provenance=yes
- bridges_like_external_validation_brca2: gnomad_validation_annotations (file/annotation) preset=gnomad_variant_table | provenance=yes
- bridges_like_external_validation_brca2: mavedb_validation_scores (file/annotation) preset=mavedb_score_table | provenance=yes

## Reproducibility Checklist

- Study config declared: yes (Jovem Cientista BRCA Real Evidence Quick Pass)
- Training metrics exported: yes (primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_training_metrics.csv)
- Repeated holdout exported: yes (primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_repeated_holdout.csv)
- External evaluation exported: yes (primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_external_evaluation.csv)
- Pairwise comparison exported: yes (primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_external_pairwise.csv)
- Cohort independence audit exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\cohort_independence_manifest.json)
- Real-data cohort freeze exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\study_cohort_freeze_manifest.json)
- Claim strength package exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\claim_strength_manifest.json)
- Model registry exported: yes (C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260511\brca_real_quick\models\model_registry.csv)
- Per-cohort data release manifests exported: yes (5)

## Cohort Independence Audit

- Independence score: 100%
- Max train/external overlap: 0%
- Ready for external validation: yes

## Real-data Cohort Freeze

- Real-data readiness: 100%
- Ready for real-data study: yes
- Example-blocked cohorts: 0

## Claim Strength Audit

- Claim strength: 98%
- Claim tier: strong
- Candidate experiment: hybrid_plus_external__logistic_regression

## Notes

- Este pacote resume desenho experimental, familias de modelo, proveniencia de dados e itens minimos de reproducibilidade.
- O texto pode ser adaptado para a secao de Metodos do manuscrito e para materiais suplementares.