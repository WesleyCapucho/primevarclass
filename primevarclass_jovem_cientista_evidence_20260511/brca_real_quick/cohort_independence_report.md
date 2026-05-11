# Cohort Independence Audit

- Generated at: 2026-05-11T05:05:58Z
- Overall independence: 100%
- Train/external pairs: 4
- Max exact variant overlap: 0%
- Label-conflict pair rate: 0%

## Cohort Snapshot

- public_brca_training (train): rows=869, unique_variants=869, unique_genes=2
- clinvar_expert_external_validation_brca1 (external_test): rows=204, unique_variants=204, unique_genes=1
- clinvar_expert_external_validation_brca2 (external_test): rows=175, unique_variants=175, unique_genes=1
- bridges_like_external_validation_brca1 (external_test): rows=168, unique_variants=168, unique_genes=1
- bridges_like_external_validation_brca2 (external_test): rows=289, unique_variants=289, unique_genes=1

## Pairwise Audit

- public_brca_training vs clinvar_expert_external_validation_brca1 (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- public_brca_training vs clinvar_expert_external_validation_brca2 (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- public_brca_training vs bridges_like_external_validation_brca1 (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- public_brca_training vs bridges_like_external_validation_brca2 (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- clinvar_expert_external_validation_brca1 vs clinvar_expert_external_validation_brca2 (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- clinvar_expert_external_validation_brca1 vs bridges_like_external_validation_brca1 (external_test__external_test): variant_overlap=18 (10.71%), gene_overlap=1 (100.0%), label_conflicts=0
- clinvar_expert_external_validation_brca1 vs bridges_like_external_validation_brca2 (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- clinvar_expert_external_validation_brca2 vs bridges_like_external_validation_brca1 (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- clinvar_expert_external_validation_brca2 vs bridges_like_external_validation_brca2 (external_test__external_test): variant_overlap=7 (4.0%), gene_overlap=1 (100.0%), label_conflicts=0
- bridges_like_external_validation_brca1 vs bridges_like_external_validation_brca2 (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0

## Recommended Actions

- Nenhum ajuste prioritario de independencia foi identificado.