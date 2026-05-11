# Cohort Independence Audit

- Generated at: 2026-04-24T05:25:38Z
- Overall independence: 100%
- Train/external pairs: 7
- Max exact variant overlap: 0%
- Label-conflict pair rate: 0%

## Cohort Snapshot

- multigene_training (train): rows=580, unique_variants=580, unique_genes=4
- multigene_combined_external_validation (external_test): rows=978, unique_variants=978, unique_genes=6
- tp53_combined_external_validation (external_test): rows=264, unique_variants=264, unique_genes=1
- pten_combined_external_validation (external_test): rows=167, unique_variants=167, unique_genes=1
- msh2_combined_external_validation (external_test): rows=164, unique_variants=164, unique_genes=1
- kras_combined_external_validation (external_test): rows=32, unique_variants=32, unique_genes=1
- gck_combined_external_validation (external_test): rows=289, unique_variants=289, unique_genes=1
- f9_combined_external_validation (external_test): rows=62, unique_variants=62, unique_genes=1

## Pairwise Audit

- multigene_training vs multigene_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=4 (100.0%), label_conflicts=0
- multigene_training vs tp53_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_training vs pten_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- multigene_training vs msh2_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_training vs kras_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- multigene_training vs gck_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_training vs f9_combined_external_validation (train_external): variant_overlap=0 (0.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs tp53_combined_external_validation (external_test__external_test): variant_overlap=264 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs pten_combined_external_validation (external_test__external_test): variant_overlap=167 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs msh2_combined_external_validation (external_test__external_test): variant_overlap=164 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs kras_combined_external_validation (external_test__external_test): variant_overlap=32 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs gck_combined_external_validation (external_test__external_test): variant_overlap=289 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- multigene_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=62 (100.0%), gene_overlap=1 (100.0%), label_conflicts=0
- tp53_combined_external_validation vs pten_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- tp53_combined_external_validation vs msh2_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- tp53_combined_external_validation vs kras_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- tp53_combined_external_validation vs gck_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- tp53_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- pten_combined_external_validation vs msh2_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- pten_combined_external_validation vs kras_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- pten_combined_external_validation vs gck_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- pten_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- msh2_combined_external_validation vs kras_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- msh2_combined_external_validation vs gck_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- msh2_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- kras_combined_external_validation vs gck_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- kras_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0
- gck_combined_external_validation vs f9_combined_external_validation (external_test__external_test): variant_overlap=0 (0.0%), gene_overlap=0 (0.0%), label_conflicts=0

## Recommended Actions

- Nenhum ajuste prioritario de independencia foi identificado.